"""
Celery application configuration for background task processing.
"""
from celery import Celery
from celery.signals import worker_ready, worker_shutdown
from kombu import Queue

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

# Create Celery app
celery_app = Celery(
    "webhook_orchestrator",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "app.tasks.workflow_tasks",
        "app.tasks.retry_logic",
    ],
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer=settings.celery_task_serializer,
    result_serializer=settings.celery_result_serializer,
    accept_content=["json"],
    
    # Task routing
    task_routes={
        "app.tasks.workflow_tasks.process_pull_request_event": {"queue": "pr_analysis"},
        "app.tasks.workflow_tasks.process_check_run_event": {"queue": "check_analysis"},
        "app.tasks.workflow_tasks.process_check_suite_event": {"queue": "check_analysis"},
        "app.tasks.workflow_tasks.process_push_event": {"queue": "push_analysis"},
        "app.tasks.workflow_tasks.trigger_codegen_agent": {"queue": "codegen"},
        "app.tasks.workflow_tasks.validate_pr_changes": {"queue": "validation"},
        "app.tasks.retry_logic.*": {"queue": "retry"},
    },
    
    # Queue configuration
    task_default_queue="default",
    task_queues=(
        Queue("default", routing_key="default"),
        Queue("pr_analysis", routing_key="pr_analysis"),
        Queue("check_analysis", routing_key="check_analysis"),
        Queue("push_analysis", routing_key="push_analysis"),
        Queue("codegen", routing_key="codegen"),
        Queue("validation", routing_key="validation"),
        Queue("retry", routing_key="retry"),
        Queue("high_priority", routing_key="high_priority"),
    ),
    
    # Task execution
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_reject_on_worker_lost=True,
    
    # Retry configuration
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=settings.max_retries,
    
    # Result backend
    result_expires=3600,  # 1 hour
    result_persistent=True,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
    
    # Time limits
    task_soft_time_limit=settings.task_timeout,
    task_time_limit=settings.task_timeout + 60,
    
    # Timezone
    timezone="UTC",
    enable_utc=True,
    
    # Beat schedule (for periodic tasks)
    beat_schedule={
        "cleanup_old_tasks": {
            "task": "app.tasks.workflow_tasks.cleanup_old_tasks",
            "schedule": 3600.0,  # Every hour
        },
        "health_check": {
            "task": "app.tasks.workflow_tasks.health_check",
            "schedule": 300.0,  # Every 5 minutes
        },
        "collect_metrics": {
            "task": "app.tasks.workflow_tasks.collect_metrics",
            "schedule": 60.0,  # Every minute
        },
    },
)


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Handle worker ready signal."""
    logger.info(
        "celery_worker_ready",
        worker_id=sender.hostname,
        queues=[q.name for q in sender.app.amqp.queues.values()],
    )


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Handle worker shutdown signal."""
    logger.info(
        "celery_worker_shutdown",
        worker_id=sender.hostname,
    )


# Task base class with logging
class LoggedTask(celery_app.Task):
    """Base task class with structured logging."""
    
    def on_success(self, retval, task_id, args, kwargs):
        """Log task success."""
        logger.info(
            "task_success",
            task_id=task_id,
            task_name=self.name,
            result=retval,
        )
    
    def on_failure(self, exc, task_id, args, kwargs, einfo):
        """Log task failure."""
        logger.error(
            "task_failure",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            error_type=type(exc).__name__,
            traceback=str(einfo),
        )
    
    def on_retry(self, exc, task_id, args, kwargs, einfo):
        """Log task retry."""
        logger.warning(
            "task_retry",
            task_id=task_id,
            task_name=self.name,
            error=str(exc),
            retry_count=self.request.retries,
        )


# Set default task base
celery_app.Task = LoggedTask


# Health check function
def check_celery_health():
    """Check Celery worker health."""
    try:
        # Check if workers are available
        inspect = celery_app.control.inspect()
        stats = inspect.stats()
        
        if not stats:
            return False, "No workers available"
        
        # Check if queues are accessible
        active_queues = inspect.active_queues()
        if not active_queues:
            return False, "No active queues"
        
        return True, f"Workers: {len(stats)}, Queues: {sum(len(queues) for queues in active_queues.values())}"
        
    except Exception as e:
        return False, f"Celery health check failed: {e}"

