"""
GitHub webhook event handlers.
"""
import asyncio
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.database import WebhookEvent, WorkflowTask, db_manager
from ..core.logging import WebhookLoggerMixin, get_logger
from ..tasks.workflow_tasks import (
    process_pull_request_event,
    process_check_run_event,
    process_check_suite_event,
    process_push_event,
)
from .validation import WebhookHeaders

logger = get_logger(__name__)


class GitHubWebhookHandler(WebhookLoggerMixin):
    """Handler for GitHub webhook events."""
    
    def __init__(self):
        super().__init__()
        self.event_handlers = {
            "pull_request": self._handle_pull_request,
            "check_run": self._handle_check_run,
            "check_suite": self._handle_check_suite,
            "push": self._handle_push,
            "ping": self._handle_ping,
            "installation": self._handle_installation,
            "installation_repositories": self._handle_installation_repositories,
        }
    
    async def handle_webhook(
        self,
        headers: WebhookHeaders,
        payload: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Handle incoming webhook event."""
        start_time = asyncio.get_event_loop().time()
        
        # Log webhook reception
        self.log_webhook_received(
            headers.x_github_event,
            headers.x_github_delivery,
            len(str(payload)),
        )
        
        try:
            # Store webhook event
            webhook_event = await self._store_webhook_event(headers, payload, session)
            
            # Process event based on type
            handler = self.event_handlers.get(headers.x_github_event)
            if handler:
                result = await handler(webhook_event, payload, session)
            else:
                self.logger.warning(
                    "unhandled_event_type",
                    event_type=headers.x_github_event,
                    delivery_id=headers.x_github_delivery,
                )
                result = {"status": "ignored", "reason": "unsupported_event_type"}
            
            # Mark webhook as processed
            webhook_event.processed = True
            webhook_event.processing_completed_at = datetime.utcnow()
            await session.commit()
            
            # Log successful processing
            processing_time = asyncio.get_event_loop().time() - start_time
            self.log_webhook_processed(
                headers.x_github_event,
                headers.x_github_delivery,
                processing_time,
            )
            
            return result
            
        except Exception as e:
            # Log error and update webhook event
            self.log_webhook_error(headers.x_github_event, headers.x_github_delivery, e)
            
            # Update webhook event with error
            try:
                webhook_event = await session.get(WebhookEvent, webhook_event.id)
                if webhook_event:
                    webhook_event.error_message = str(e)
                    webhook_event.retry_count += 1
                    await session.commit()
            except Exception as db_error:
                self.logger.error("failed_to_update_webhook_error", error=str(db_error))
            
            raise
    
    async def _store_webhook_event(
        self,
        headers: WebhookHeaders,
        payload: Dict[str, Any],
        session: AsyncSession,
    ) -> WebhookEvent:
        """Store webhook event in database."""
        webhook_event = WebhookEvent(
            delivery_id=headers.x_github_delivery,
            event_type=headers.x_github_event,
            payload=payload,
            headers={
                "x-github-delivery": headers.x_github_delivery,
                "x-github-event": headers.x_github_event,
                "x-github-hook-id": headers.x_github_hook_id,
                "user-agent": headers.user_agent,
                "content-type": headers.content_type,
            },
            signature=headers.x_hub_signature_256,
            processing_started_at=datetime.utcnow(),
        )
        
        session.add(webhook_event)
        await session.commit()
        await session.refresh(webhook_event)
        
        return webhook_event
    
    async def _handle_pull_request(
        self,
        webhook_event: WebhookEvent,
        payload: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Handle pull request events."""
        action = payload.get("action")
        pr_data = payload.get("pull_request", {})
        repository = payload.get("repository", {})
        
        self.logger.info(
            "processing_pull_request_event",
            action=action,
            pr_number=pr_data.get("number"),
            repository=repository.get("full_name"),
        )
        
        # Create workflow task for relevant actions
        if action in ["opened", "synchronize", "reopened", "ready_for_review"]:
            task = await self._create_workflow_task(
                webhook_event=webhook_event,
                task_type="pull_request_analysis",
                repository=repository.get("full_name"),
                pr_number=pr_data.get("number"),
                branch=pr_data.get("head", {}).get("ref"),
                commit_sha=pr_data.get("head", {}).get("sha"),
                config={
                    "action": action,
                    "pr_state": pr_data.get("state"),
                    "draft": pr_data.get("draft", False),
                },
                input_data=payload,
                session=session,
            )
            
            # Queue background task
            process_pull_request_event.delay(task.task_id, payload)
            
            return {
                "status": "queued",
                "task_id": task.task_id,
                "action": action,
            }
        
        return {"status": "ignored", "reason": f"action_{action}_not_handled"}
    
    async def _handle_check_run(
        self,
        webhook_event: WebhookEvent,
        payload: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Handle check run events."""
        action = payload.get("action")
        check_run = payload.get("check_run", {})
        repository = payload.get("repository", {})
        
        self.logger.info(
            "processing_check_run_event",
            action=action,
            check_run_id=check_run.get("id"),
            status=check_run.get("status"),
            conclusion=check_run.get("conclusion"),
            repository=repository.get("full_name"),
        )
        
        # Handle completed check runs with failures
        if action == "completed" and check_run.get("conclusion") in ["failure", "cancelled", "timed_out"]:
            pull_requests = check_run.get("pull_requests", [])
            
            for pr in pull_requests:
                task = await self._create_workflow_task(
                    webhook_event=webhook_event,
                    task_type="check_failure_analysis",
                    repository=repository.get("full_name"),
                    pr_number=pr.get("number"),
                    branch=pr.get("head", {}).get("ref"),
                    commit_sha=pr.get("head", {}).get("sha"),
                    config={
                        "check_run_id": check_run.get("id"),
                        "check_name": check_run.get("name"),
                        "conclusion": check_run.get("conclusion"),
                        "details_url": check_run.get("details_url"),
                    },
                    input_data=payload,
                    session=session,
                )
                
                # Queue background task
                process_check_run_event.delay(task.task_id, payload)
            
            return {
                "status": "queued",
                "tasks_created": len(pull_requests),
                "action": action,
            }
        
        return {"status": "ignored", "reason": f"action_{action}_not_handled"}
    
    async def _handle_check_suite(
        self,
        webhook_event: WebhookEvent,
        payload: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Handle check suite events."""
        action = payload.get("action")
        check_suite = payload.get("check_suite", {})
        repository = payload.get("repository", {})
        
        self.logger.info(
            "processing_check_suite_event",
            action=action,
            check_suite_id=check_suite.get("id"),
            status=check_suite.get("status"),
            conclusion=check_suite.get("conclusion"),
            repository=repository.get("full_name"),
        )
        
        # Handle completed check suites with failures
        if action == "completed" and check_suite.get("conclusion") in ["failure", "cancelled", "timed_out"]:
            pull_requests = check_suite.get("pull_requests", [])
            
            for pr in pull_requests:
                task = await self._create_workflow_task(
                    webhook_event=webhook_event,
                    task_type="check_suite_failure_analysis",
                    repository=repository.get("full_name"),
                    pr_number=pr.get("number"),
                    branch=pr.get("head", {}).get("ref"),
                    commit_sha=pr.get("head", {}).get("sha"),
                    config={
                        "check_suite_id": check_suite.get("id"),
                        "conclusion": check_suite.get("conclusion"),
                        "head_branch": check_suite.get("head_branch"),
                    },
                    input_data=payload,
                    session=session,
                )
                
                # Queue background task
                process_check_suite_event.delay(task.task_id, payload)
            
            return {
                "status": "queued",
                "tasks_created": len(pull_requests),
                "action": action,
            }
        
        return {"status": "ignored", "reason": f"action_{action}_not_handled"}
    
    async def _handle_push(
        self,
        webhook_event: WebhookEvent,
        payload: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Handle push events."""
        repository = payload.get("repository", {})
        ref = payload.get("ref", "")
        commits = payload.get("commits", [])
        
        self.logger.info(
            "processing_push_event",
            repository=repository.get("full_name"),
            ref=ref,
            commits_count=len(commits),
        )
        
        # Only process pushes to main/master branches
        if ref in ["refs/heads/main", "refs/heads/master"]:
            task = await self._create_workflow_task(
                webhook_event=webhook_event,
                task_type="push_analysis",
                repository=repository.get("full_name"),
                branch=ref.replace("refs/heads/", ""),
                commit_sha=payload.get("after"),
                config={
                    "ref": ref,
                    "before": payload.get("before"),
                    "after": payload.get("after"),
                    "commits_count": len(commits),
                },
                input_data=payload,
                session=session,
            )
            
            # Queue background task
            process_push_event.delay(task.task_id, payload)
            
            return {
                "status": "queued",
                "task_id": task.task_id,
                "ref": ref,
            }
        
        return {"status": "ignored", "reason": "not_main_branch"}
    
    async def _handle_ping(
        self,
        webhook_event: WebhookEvent,
        payload: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Handle ping events."""
        self.logger.info("ping_event_received", zen=payload.get("zen"))
        return {"status": "pong", "zen": payload.get("zen")}
    
    async def _handle_installation(
        self,
        webhook_event: WebhookEvent,
        payload: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Handle installation events."""
        action = payload.get("action")
        installation = payload.get("installation", {})
        
        self.logger.info(
            "installation_event",
            action=action,
            installation_id=installation.get("id"),
            account=installation.get("account", {}).get("login"),
        )
        
        return {"status": "processed", "action": action}
    
    async def _handle_installation_repositories(
        self,
        webhook_event: WebhookEvent,
        payload: Dict[str, Any],
        session: AsyncSession,
    ) -> Dict[str, Any]:
        """Handle installation repositories events."""
        action = payload.get("action")
        installation = payload.get("installation", {})
        repositories_added = payload.get("repositories_added", [])
        repositories_removed = payload.get("repositories_removed", [])
        
        self.logger.info(
            "installation_repositories_event",
            action=action,
            installation_id=installation.get("id"),
            added_count=len(repositories_added),
            removed_count=len(repositories_removed),
        )
        
        return {
            "status": "processed",
            "action": action,
            "repositories_added": len(repositories_added),
            "repositories_removed": len(repositories_removed),
        }
    
    async def _create_workflow_task(
        self,
        webhook_event: WebhookEvent,
        task_type: str,
        repository: Optional[str] = None,
        pr_number: Optional[int] = None,
        branch: Optional[str] = None,
        commit_sha: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        input_data: Optional[Dict[str, Any]] = None,
        session: AsyncSession,
    ) -> WorkflowTask:
        """Create a workflow task."""
        import uuid
        
        task_id = str(uuid.uuid4())
        
        task = WorkflowTask(
            task_id=task_id,
            webhook_event_id=webhook_event.id,
            task_type=task_type,
            repository=repository,
            pr_number=pr_number,
            branch=branch,
            commit_sha=commit_sha,
            config=config or {},
            input_data=input_data or {},
        )
        
        session.add(task)
        await session.commit()
        await session.refresh(task)
        
        self.log_task_created(
            task_id=task_id,
            task_type=task_type,
            repository=repository,
            pr_number=pr_number,
        )
        
        return task


# Global handler instance
github_handler = GitHubWebhookHandler()

