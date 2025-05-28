"""
REST API endpoints for webhook orchestrator.
"""
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks, Query
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_, desc, func
from pydantic import BaseModel, Field

from ..core.database import (
    get_db_session,
    WebhookEvent,
    WorkflowTask,
    TaskExecution,
    SystemMetrics,
)
from ..core.logging import get_logger
from ..webhooks.validation import webhook_validator
from ..webhooks.github_handler import github_handler
from ..tasks.workflow_tasks import (
    process_pull_request_event,
    process_check_run_event,
    process_check_suite_event,
    process_push_event,
    cleanup_old_tasks,
    health_check,
)

logger = get_logger(__name__)

# Create router
router = APIRouter()


# Pydantic models for API responses
class WebhookEventResponse(BaseModel):
    id: int
    delivery_id: str
    event_type: str
    processed: bool
    created_at: datetime
    error_message: Optional[str] = None


class WorkflowTaskResponse(BaseModel):
    id: int
    task_id: str
    task_type: str
    status: str
    repository: Optional[str] = None
    pr_number: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    codegen_task_url: Optional[str] = None


class TaskExecutionResponse(BaseModel):
    id: int
    execution_id: str
    status: str
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    error_message: Optional[str] = None


class HealthCheckResponse(BaseModel):
    status: str
    timestamp: datetime
    checks: Dict[str, str]
    uptime_seconds: Optional[float] = None


class MetricsResponse(BaseModel):
    webhook_events_total: int
    workflow_tasks_total: int
    task_executions_total: int
    tasks_by_status: Dict[str, int]
    events_by_type: Dict[str, int]
    avg_processing_time_ms: Optional[float] = None


# Webhook endpoints
@router.post("/webhooks/github", response_model=Dict[str, Any])
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db_session),
):
    """Handle GitHub webhook events."""
    try:
        # Validate webhook
        headers, payload = await webhook_validator.validate_webhook(request)
        
        # Process webhook in background
        result = await github_handler.handle_webhook(headers, payload, session)
        
        return {
            "status": "accepted",
            "delivery_id": headers.x_github_delivery,
            "event_type": headers.x_github_event,
            "result": result,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("webhook_processing_error", error=str(e), exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")


# Webhook event management
@router.get("/webhooks/events", response_model=List[WebhookEventResponse])
async def list_webhook_events(
    limit: int = Query(default=50, le=1000),
    offset: int = Query(default=0, ge=0),
    event_type: Optional[str] = Query(default=None),
    processed: Optional[bool] = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    """List webhook events with filtering."""
    query = session.query(WebhookEvent)
    
    # Apply filters
    if event_type:
        query = query.filter(WebhookEvent.event_type == event_type)
    
    if processed is not None:
        query = query.filter(WebhookEvent.processed == processed)
    
    # Order by creation time (newest first)
    query = query.order_by(desc(WebhookEvent.created_at))
    
    # Apply pagination
    events = await session.execute(
        query.offset(offset).limit(limit)
    )
    
    return [
        WebhookEventResponse(
            id=event.id,
            delivery_id=event.delivery_id,
            event_type=event.event_type,
            processed=event.processed,
            created_at=event.created_at,
            error_message=event.error_message,
        )
        for event in events.scalars().all()
    ]


@router.get("/webhooks/events/{event_id}", response_model=Dict[str, Any])
async def get_webhook_event(
    event_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """Get detailed webhook event information."""
    event = await session.get(WebhookEvent, event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    
    return {
        "id": event.id,
        "delivery_id": event.delivery_id,
        "event_type": event.event_type,
        "source": event.source,
        "payload": event.payload,
        "headers": event.headers,
        "processed": event.processed,
        "processing_started_at": event.processing_started_at,
        "processing_completed_at": event.processing_completed_at,
        "error_message": event.error_message,
        "retry_count": event.retry_count,
        "created_at": event.created_at,
        "updated_at": event.updated_at,
    }


@router.post("/webhooks/events/{event_id}/reprocess")
async def reprocess_webhook_event(
    event_id: int,
    session: AsyncSession = Depends(get_db_session),
):
    """Reprocess a failed webhook event."""
    event = await session.get(WebhookEvent, event_id)
    
    if not event:
        raise HTTPException(status_code=404, detail="Webhook event not found")
    
    if event.processed and not event.error_message:
        raise HTTPException(status_code=400, detail="Event already processed successfully")
    
    try:
        # Reset event status
        event.processed = False
        event.error_message = None
        event.processing_started_at = None
        event.processing_completed_at = None
        
        # Reprocess based on event type
        if event.event_type == "pull_request":
            task = process_pull_request_event.delay("reprocess", event.payload)
        elif event.event_type == "check_run":
            task = process_check_run_event.delay("reprocess", event.payload)
        elif event.event_type == "check_suite":
            task = process_check_suite_event.delay("reprocess", event.payload)
        elif event.event_type == "push":
            task = process_push_event.delay("reprocess", event.payload)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported event type: {event.event_type}")
        
        await session.commit()
        
        return {
            "status": "reprocessing",
            "task_id": task.id,
            "event_id": event_id,
        }
        
    except Exception as e:
        logger.error("reprocess_webhook_error", event_id=event_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to reprocess event")


# Workflow task management
@router.get("/tasks", response_model=List[WorkflowTaskResponse])
async def list_workflow_tasks(
    limit: int = Query(default=50, le=1000),
    offset: int = Query(default=0, ge=0),
    status: Optional[str] = Query(default=None),
    task_type: Optional[str] = Query(default=None),
    repository: Optional[str] = Query(default=None),
    session: AsyncSession = Depends(get_db_session),
):
    """List workflow tasks with filtering."""
    query = session.query(WorkflowTask)
    
    # Apply filters
    if status:
        query = query.filter(WorkflowTask.status == status)
    
    if task_type:
        query = query.filter(WorkflowTask.task_type == task_type)
    
    if repository:
        query = query.filter(WorkflowTask.repository == repository)
    
    # Order by creation time (newest first)
    query = query.order_by(desc(WorkflowTask.created_at))
    
    # Apply pagination
    tasks = await session.execute(
        query.offset(offset).limit(limit)
    )
    
    return [
        WorkflowTaskResponse(
            id=task.id,
            task_id=task.task_id,
            task_type=task.task_type,
            status=task.status,
            repository=task.repository,
            pr_number=task.pr_number,
            created_at=task.created_at,
            completed_at=task.completed_at,
            error_message=task.error_message,
            codegen_task_url=task.codegen_task_url,
        )
        for task in tasks.scalars().all()
    ]


@router.get("/tasks/{task_id}", response_model=Dict[str, Any])
async def get_workflow_task(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get detailed workflow task information."""
    task = await session.execute(
        session.query(WorkflowTask).filter(WorkflowTask.task_id == task_id)
    )
    task = task.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Workflow task not found")
    
    # Get task executions
    executions = await session.execute(
        session.query(TaskExecution)
        .filter(TaskExecution.task_id == task_id)
        .order_by(desc(TaskExecution.started_at))
    )
    
    return {
        "id": task.id,
        "task_id": task.task_id,
        "webhook_event_id": task.webhook_event_id,
        "task_type": task.task_type,
        "status": task.status,
        "priority": task.priority,
        "repository": task.repository,
        "pr_number": task.pr_number,
        "branch": task.branch,
        "commit_sha": task.commit_sha,
        "config": task.config,
        "input_data": task.input_data,
        "output_data": task.output_data,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "error_message": task.error_message,
        "retry_count": task.retry_count,
        "max_retries": task.max_retries,
        "codegen_task_id": task.codegen_task_id,
        "codegen_task_url": task.codegen_task_url,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "executions": [
            TaskExecutionResponse(
                id=exec.id,
                execution_id=exec.execution_id,
                status=exec.status,
                started_at=exec.started_at,
                completed_at=exec.completed_at,
                duration_ms=exec.duration_ms,
                error_message=exec.error_message,
            )
            for exec in executions.scalars().all()
        ],
    }


@router.post("/tasks/{task_id}/retry")
async def retry_workflow_task(
    task_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Retry a failed workflow task."""
    task = await session.execute(
        session.query(WorkflowTask).filter(WorkflowTask.task_id == task_id)
    )
    task = task.scalar_one_or_none()
    
    if not task:
        raise HTTPException(status_code=404, detail="Workflow task not found")
    
    if task.status not in ["failed", "cancelled"]:
        raise HTTPException(status_code=400, detail="Task is not in a retryable state")
    
    if task.retry_count >= task.max_retries:
        raise HTTPException(status_code=400, detail="Task has exceeded maximum retries")
    
    try:
        # Reset task status
        task.status = "pending"
        task.error_message = None
        task.started_at = None
        task.completed_at = None
        
        # Requeue based on task type
        if task.task_type == "pull_request_analysis":
            celery_task = process_pull_request_event.delay(task_id, task.input_data)
        elif task.task_type == "check_failure_analysis":
            celery_task = process_check_run_event.delay(task_id, task.input_data)
        elif task.task_type == "check_suite_failure_analysis":
            celery_task = process_check_suite_event.delay(task_id, task.input_data)
        elif task.task_type == "push_analysis":
            celery_task = process_push_event.delay(task_id, task.input_data)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported task type: {task.task_type}")
        
        await session.commit()
        
        return {
            "status": "retrying",
            "celery_task_id": celery_task.id,
            "task_id": task_id,
        }
        
    except Exception as e:
        logger.error("retry_task_error", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retry task")


# System management
@router.get("/health", response_model=HealthCheckResponse)
async def health_check_endpoint():
    """System health check endpoint."""
    try:
        # Run health check task
        result = health_check.delay()
        health_data = result.get(timeout=30)  # 30 second timeout
        
        return HealthCheckResponse(
            status=health_data["status"],
            timestamp=datetime.fromisoformat(health_data["timestamp"]),
            checks=health_data["checks"],
        )
        
    except Exception as e:
        logger.error("health_check_endpoint_error", error=str(e))
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.utcnow(),
            checks={"error": str(e)},
        )


@router.get("/metrics", response_model=MetricsResponse)
async def get_metrics(
    session: AsyncSession = Depends(get_db_session),
):
    """Get system metrics."""
    try:
        # Count webhook events
        webhook_events_total = await session.scalar(
            func.count(WebhookEvent.id)
        )
        
        # Count workflow tasks
        workflow_tasks_total = await session.scalar(
            func.count(WorkflowTask.id)
        )
        
        # Count task executions
        task_executions_total = await session.scalar(
            func.count(TaskExecution.id)
        )
        
        # Tasks by status
        tasks_by_status_result = await session.execute(
            session.query(WorkflowTask.status, func.count(WorkflowTask.id))
            .group_by(WorkflowTask.status)
        )
        tasks_by_status = dict(tasks_by_status_result.all())
        
        # Events by type
        events_by_type_result = await session.execute(
            session.query(WebhookEvent.event_type, func.count(WebhookEvent.id))
            .group_by(WebhookEvent.event_type)
        )
        events_by_type = dict(events_by_type_result.all())
        
        # Average processing time
        avg_processing_time = await session.scalar(
            func.avg(TaskExecution.duration_ms)
        )
        
        return MetricsResponse(
            webhook_events_total=webhook_events_total or 0,
            workflow_tasks_total=workflow_tasks_total or 0,
            task_executions_total=task_executions_total or 0,
            tasks_by_status=tasks_by_status,
            events_by_type=events_by_type,
            avg_processing_time_ms=float(avg_processing_time) if avg_processing_time else None,
        )
        
    except Exception as e:
        logger.error("metrics_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve metrics")


@router.post("/admin/cleanup")
async def trigger_cleanup():
    """Trigger cleanup of old data."""
    try:
        task = cleanup_old_tasks.delay()
        
        return {
            "status": "cleanup_triggered",
            "task_id": task.id,
        }
        
    except Exception as e:
        logger.error("cleanup_trigger_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to trigger cleanup")


@router.get("/admin/stats")
async def get_admin_stats(
    session: AsyncSession = Depends(get_db_session),
):
    """Get administrative statistics."""
    try:
        # Recent activity (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        
        recent_webhooks = await session.scalar(
            func.count(WebhookEvent.id).filter(WebhookEvent.created_at >= yesterday)
        )
        
        recent_tasks = await session.scalar(
            func.count(WorkflowTask.id).filter(WorkflowTask.created_at >= yesterday)
        )
        
        # Error rates
        failed_webhooks = await session.scalar(
            func.count(WebhookEvent.id).filter(
                and_(
                    WebhookEvent.error_message.isnot(None),
                    WebhookEvent.created_at >= yesterday,
                )
            )
        )
        
        failed_tasks = await session.scalar(
            func.count(WorkflowTask.id).filter(
                and_(
                    WorkflowTask.status == "failed",
                    WorkflowTask.created_at >= yesterday,
                )
            )
        )
        
        return {
            "recent_activity": {
                "webhooks_24h": recent_webhooks or 0,
                "tasks_24h": recent_tasks or 0,
            },
            "error_rates": {
                "failed_webhooks_24h": failed_webhooks or 0,
                "failed_tasks_24h": failed_tasks or 0,
                "webhook_error_rate": (failed_webhooks / max(recent_webhooks, 1)) * 100 if recent_webhooks else 0,
                "task_error_rate": (failed_tasks / max(recent_tasks, 1)) * 100 if recent_tasks else 0,
            },
        }
        
    except Exception as e:
        logger.error("admin_stats_error", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to retrieve admin stats")

