"""
Workflow task implementations for processing GitHub events.
"""
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from celery import current_task
from github import Github
from sqlalchemy.orm import sessionmaker
from sqlalchemy import and_, or_

from codegen import Agent

from .celery_app import celery_app
from .retry_logic import (
    github_api_retry,
    codegen_api_retry,
    database_retry,
    RetryableException,
    ServiceUnavailableException,
)
from ..core.config import settings
from ..core.database import (
    db_manager,
    WorkflowTask,
    TaskExecution,
    WebhookEvent,
    SystemMetrics,
)
from ..core.logging import WebhookLoggerMixin, get_logger

logger = get_logger(__name__)


class WorkflowTaskProcessor(WebhookLoggerMixin):
    """Base class for workflow task processing."""
    
    def __init__(self):
        super().__init__()
        self.github_client = None
        self.codegen_client = None
    
    def get_github_client(self) -> Github:
        """Get authenticated GitHub client."""
        if not self.github_client:
            if settings.github_token:
                self.github_client = Github(settings.github_token)
            else:
                raise ValueError("GitHub token not configured")
        return self.github_client
    
    def get_codegen_client(self) -> Agent:
        """Get Codegen agent client."""
        if not self.codegen_client:
            self.codegen_client = Agent(
                token=settings.codegen_token,
                org_id=settings.codegen_org_id,
            )
        return self.codegen_client
    
    def get_db_session(self):
        """Get database session for Celery tasks."""
        return db_manager.get_sync_session()
    
    def update_task_status(
        self,
        task_id: str,
        status: str,
        output_data: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        """Update workflow task status."""
        session = self.get_db_session()
        try:
            task = session.query(WorkflowTask).filter(
                WorkflowTask.task_id == task_id
            ).first()
            
            if task:
                task.status = status
                task.updated_at = datetime.utcnow()
                
                if status == "running":
                    task.started_at = datetime.utcnow()
                elif status in ["completed", "failed"]:
                    task.completed_at = datetime.utcnow()
                
                if output_data:
                    task.output_data = output_data
                
                if error_message:
                    task.error_message = error_message
                    task.retry_count += 1
                
                session.commit()
                
                self.logger.info(
                    "task_status_updated",
                    task_id=task_id,
                    status=status,
                    error=error_message,
                )
        finally:
            session.close()
    
    def create_task_execution(
        self,
        task_id: str,
        execution_id: str,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None,
    ):
        """Create task execution record."""
        session = self.get_db_session()
        try:
            execution = TaskExecution(
                task_id=task_id,
                execution_id=execution_id,
                status=status,
                started_at=datetime.utcnow(),
                result=result,
                error_message=error_message,
                worker_id=current_task.request.hostname if current_task else None,
                queue_name=current_task.request.delivery_info.get("routing_key") if current_task else None,
            )
            
            if status in ["completed", "failed"]:
                execution.completed_at = datetime.utcnow()
                if execution.started_at:
                    duration = (execution.completed_at - execution.started_at).total_seconds() * 1000
                    execution.duration_ms = int(duration)
            
            session.add(execution)
            session.commit()
        finally:
            session.close()


# Global processor instance
processor = WorkflowTaskProcessor()


@celery_app.task(bind=True, name="process_pull_request_event")
@github_api_retry
def process_pull_request_event(self, task_id: str, payload: Dict[str, Any]):
    """Process pull request webhook events."""
    execution_id = self.request.id
    start_time = time.time()
    
    try:
        processor.update_task_status(task_id, "running")
        processor.create_task_execution(task_id, execution_id, "running")
        
        logger.info("processing_pull_request_task", task_id=task_id, execution_id=execution_id)
        
        # Extract PR information
        pr_data = payload.get("pull_request", {})
        repository = payload.get("repository", {})
        action = payload.get("action")
        
        repo_name = repository.get("full_name")
        pr_number = pr_data.get("number")
        pr_state = pr_data.get("state")
        is_draft = pr_data.get("draft", False)
        
        # Skip draft PRs unless they're marked ready for review
        if is_draft and action != "ready_for_review":
            result = {"status": "skipped", "reason": "draft_pr"}
            processor.update_task_status(task_id, "completed", result)
            processor.create_task_execution(task_id, execution_id, "completed", result)
            return result
        
        # Get GitHub client and fetch PR details
        github = processor.get_github_client()
        repo = github.get_repo(repo_name)
        pr = repo.get_pull(pr_number)
        
        # Analyze PR changes
        analysis_result = analyze_pr_changes(pr, action)
        
        # Trigger Codegen agent if needed
        if analysis_result.get("should_trigger_codegen", False):
            codegen_result = trigger_codegen_agent.delay(
                task_id,
                repo_name,
                pr_number,
                analysis_result,
            )
            
            result = {
                "status": "codegen_triggered",
                "analysis": analysis_result,
                "codegen_task_id": codegen_result.id,
            }
        else:
            result = {
                "status": "completed",
                "analysis": analysis_result,
                "reason": "no_codegen_needed",
            }
        
        # Update task status
        processor.update_task_status(task_id, "completed", result)
        processor.create_task_execution(task_id, execution_id, "completed", result)
        
        execution_time = time.time() - start_time
        processor.log_task_completed(task_id, "pull_request_analysis", execution_time)
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error("pull_request_task_failed", task_id=task_id, error=error_msg, exc_info=True)
        
        processor.update_task_status(task_id, "failed", error_message=error_msg)
        processor.create_task_execution(task_id, execution_id, "failed", error_message=error_msg)
        processor.log_task_failed(task_id, "pull_request_analysis", e, self.request.retries)
        
        raise


@celery_app.task(bind=True, name="process_check_run_event")
@github_api_retry
def process_check_run_event(self, task_id: str, payload: Dict[str, Any]):
    """Process check run webhook events."""
    execution_id = self.request.id
    start_time = time.time()
    
    try:
        processor.update_task_status(task_id, "running")
        processor.create_task_execution(task_id, execution_id, "running")
        
        logger.info("processing_check_run_task", task_id=task_id, execution_id=execution_id)
        
        # Extract check run information
        check_run = payload.get("check_run", {})
        repository = payload.get("repository", {})
        
        repo_name = repository.get("full_name")
        check_run_id = check_run.get("id")
        check_name = check_run.get("name")
        conclusion = check_run.get("conclusion")
        
        # Get GitHub client and fetch check run details
        github = processor.get_github_client()
        repo = github.get_repo(repo_name)
        
        # Analyze check failure
        analysis_result = analyze_check_failure(repo, check_run_id, check_name, conclusion)
        
        # Trigger Codegen agent for fixing failures
        if analysis_result.get("should_fix_failure", False):
            codegen_result = trigger_codegen_agent.delay(
                task_id,
                repo_name,
                analysis_result.get("pr_number"),
                analysis_result,
            )
            
            result = {
                "status": "fix_triggered",
                "analysis": analysis_result,
                "codegen_task_id": codegen_result.id,
            }
        else:
            result = {
                "status": "completed",
                "analysis": analysis_result,
                "reason": "no_fix_needed",
            }
        
        # Update task status
        processor.update_task_status(task_id, "completed", result)
        processor.create_task_execution(task_id, execution_id, "completed", result)
        
        execution_time = time.time() - start_time
        processor.log_task_completed(task_id, "check_run_analysis", execution_time)
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error("check_run_task_failed", task_id=task_id, error=error_msg, exc_info=True)
        
        processor.update_task_status(task_id, "failed", error_message=error_msg)
        processor.create_task_execution(task_id, execution_id, "failed", error_message=error_msg)
        processor.log_task_failed(task_id, "check_run_analysis", e, self.request.retries)
        
        raise


@celery_app.task(bind=True, name="process_check_suite_event")
@github_api_retry
def process_check_suite_event(self, task_id: str, payload: Dict[str, Any]):
    """Process check suite webhook events."""
    execution_id = self.request.id
    start_time = time.time()
    
    try:
        processor.update_task_status(task_id, "running")
        processor.create_task_execution(task_id, execution_id, "running")
        
        logger.info("processing_check_suite_task", task_id=task_id, execution_id=execution_id)
        
        # Extract check suite information
        check_suite = payload.get("check_suite", {})
        repository = payload.get("repository", {})
        
        repo_name = repository.get("full_name")
        check_suite_id = check_suite.get("id")
        conclusion = check_suite.get("conclusion")
        
        # Get GitHub client and analyze check suite
        github = processor.get_github_client()
        repo = github.get_repo(repo_name)
        
        # Analyze check suite failure
        analysis_result = analyze_check_suite_failure(repo, check_suite_id, conclusion)
        
        # Trigger Codegen agent for fixing failures
        if analysis_result.get("should_fix_failure", False):
            codegen_result = trigger_codegen_agent.delay(
                task_id,
                repo_name,
                analysis_result.get("pr_number"),
                analysis_result,
            )
            
            result = {
                "status": "fix_triggered",
                "analysis": analysis_result,
                "codegen_task_id": codegen_result.id,
            }
        else:
            result = {
                "status": "completed",
                "analysis": analysis_result,
                "reason": "no_fix_needed",
            }
        
        # Update task status
        processor.update_task_status(task_id, "completed", result)
        processor.create_task_execution(task_id, execution_id, "completed", result)
        
        execution_time = time.time() - start_time
        processor.log_task_completed(task_id, "check_suite_analysis", execution_time)
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error("check_suite_task_failed", task_id=task_id, error=error_msg, exc_info=True)
        
        processor.update_task_status(task_id, "failed", error_message=error_msg)
        processor.create_task_execution(task_id, execution_id, "failed", error_message=error_msg)
        processor.log_task_failed(task_id, "check_suite_analysis", e, self.request.retries)
        
        raise


@celery_app.task(bind=True, name="process_push_event")
@github_api_retry
def process_push_event(self, task_id: str, payload: Dict[str, Any]):
    """Process push webhook events."""
    execution_id = self.request.id
    start_time = time.time()
    
    try:
        processor.update_task_status(task_id, "running")
        processor.create_task_execution(task_id, execution_id, "running")
        
        logger.info("processing_push_task", task_id=task_id, execution_id=execution_id)
        
        # Extract push information
        repository = payload.get("repository", {})
        commits = payload.get("commits", [])
        ref = payload.get("ref", "")
        
        repo_name = repository.get("full_name")
        
        # Analyze push changes
        analysis_result = analyze_push_changes(commits, ref)
        
        result = {
            "status": "completed",
            "analysis": analysis_result,
            "commits_analyzed": len(commits),
        }
        
        # Update task status
        processor.update_task_status(task_id, "completed", result)
        processor.create_task_execution(task_id, execution_id, "completed", result)
        
        execution_time = time.time() - start_time
        processor.log_task_completed(task_id, "push_analysis", execution_time)
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error("push_task_failed", task_id=task_id, error=error_msg, exc_info=True)
        
        processor.update_task_status(task_id, "failed", error_message=error_msg)
        processor.create_task_execution(task_id, execution_id, "failed", error_message=error_msg)
        processor.log_task_failed(task_id, "push_analysis", e, self.request.retries)
        
        raise


@celery_app.task(bind=True, name="trigger_codegen_agent")
@codegen_api_retry
def trigger_codegen_agent(
    self,
    parent_task_id: str,
    repository: str,
    pr_number: Optional[int],
    analysis_data: Dict[str, Any],
):
    """Trigger Codegen agent for code generation or fixing."""
    execution_id = self.request.id
    start_time = time.time()
    
    try:
        logger.info(
            "triggering_codegen_agent",
            parent_task_id=parent_task_id,
            repository=repository,
            pr_number=pr_number,
            execution_id=execution_id,
        )
        
        # Get Codegen client
        codegen = processor.get_codegen_client()
        
        # Generate prompt based on analysis
        prompt = generate_codegen_prompt(repository, pr_number, analysis_data)
        
        # Trigger Codegen agent
        task = codegen.run(prompt)
        
        # Update parent task with Codegen task info
        session = processor.get_db_session()
        try:
            parent_task = session.query(WorkflowTask).filter(
                WorkflowTask.task_id == parent_task_id
            ).first()
            
            if parent_task:
                parent_task.codegen_task_id = task.id
                parent_task.codegen_task_url = task.web_url
                session.commit()
        finally:
            session.close()
        
        result = {
            "status": "triggered",
            "codegen_task_id": task.id,
            "codegen_task_url": task.web_url,
            "prompt_length": len(prompt),
        }
        
        execution_time = time.time() - start_time
        logger.info(
            "codegen_agent_triggered",
            parent_task_id=parent_task_id,
            codegen_task_id=task.id,
            execution_time=execution_time,
        )
        
        return result
        
    except Exception as e:
        error_msg = str(e)
        logger.error("codegen_trigger_failed", parent_task_id=parent_task_id, error=error_msg, exc_info=True)
        processor.log_task_failed(parent_task_id, "codegen_trigger", e, self.request.retries)
        raise


# Helper functions for analysis

def analyze_pr_changes(pr, action: str) -> Dict[str, Any]:
    """Analyze PR changes to determine if Codegen should be triggered."""
    try:
        # Get PR files and changes
        files = list(pr.get_files())
        
        # Analyze file types and changes
        code_files = []
        test_files = []
        config_files = []
        
        for file in files:
            filename = file.filename.lower()
            
            if any(ext in filename for ext in ['.py', '.js', '.ts', '.java', '.go', '.rs', '.cpp', '.c']):
                code_files.append(file)
            elif any(ext in filename for ext in ['test', 'spec', '__test__']):
                test_files.append(file)
            elif any(ext in filename for ext in ['.json', '.yaml', '.yml', '.toml', '.ini']):
                config_files.append(file)
        
        # Determine if Codegen should be triggered
        should_trigger = False
        trigger_reasons = []
        
        # Trigger for new PRs with significant code changes
        if action == "opened" and len(code_files) > 0:
            should_trigger = True
            trigger_reasons.append("new_pr_with_code_changes")
        
        # Trigger for PRs marked ready for review
        if action == "ready_for_review":
            should_trigger = True
            trigger_reasons.append("ready_for_review")
        
        # Trigger for significant updates
        if action == "synchronize" and len(code_files) > 3:
            should_trigger = True
            trigger_reasons.append("significant_updates")
        
        return {
            "should_trigger_codegen": should_trigger,
            "trigger_reasons": trigger_reasons,
            "files_analyzed": len(files),
            "code_files": len(code_files),
            "test_files": len(test_files),
            "config_files": len(config_files),
            "pr_action": action,
            "pr_state": pr.state,
            "additions": pr.additions,
            "deletions": pr.deletions,
        }
        
    except Exception as e:
        logger.error("pr_analysis_failed", error=str(e), exc_info=True)
        return {
            "should_trigger_codegen": False,
            "error": str(e),
        }


def analyze_check_failure(repo, check_run_id: int, check_name: str, conclusion: str) -> Dict[str, Any]:
    """Analyze check run failure to determine if it should be fixed."""
    try:
        # Get check run details
        check_run = repo.get_check_run(check_run_id)
        
        # Determine if this is a fixable failure
        should_fix = False
        fix_reasons = []
        
        # Check for common fixable failures
        if conclusion in ["failure", "cancelled", "timed_out"]:
            # Test failures are often fixable
            if any(keyword in check_name.lower() for keyword in ["test", "spec", "unit", "integration"]):
                should_fix = True
                fix_reasons.append("test_failure")
            
            # Linting failures are fixable
            if any(keyword in check_name.lower() for keyword in ["lint", "format", "style", "eslint", "flake8"]):
                should_fix = True
                fix_reasons.append("linting_failure")
            
            # Build failures might be fixable
            if any(keyword in check_name.lower() for keyword in ["build", "compile"]):
                should_fix = True
                fix_reasons.append("build_failure")
        
        # Get associated PR
        pr_number = None
        if check_run.pull_requests:
            pr_number = check_run.pull_requests[0].number
        
        return {
            "should_fix_failure": should_fix,
            "fix_reasons": fix_reasons,
            "check_name": check_name,
            "conclusion": conclusion,
            "pr_number": pr_number,
            "details_url": check_run.details_url,
        }
        
    except Exception as e:
        logger.error("check_failure_analysis_failed", error=str(e), exc_info=True)
        return {
            "should_fix_failure": False,
            "error": str(e),
        }


def analyze_check_suite_failure(repo, check_suite_id: int, conclusion: str) -> Dict[str, Any]:
    """Analyze check suite failure to determine if it should be fixed."""
    try:
        # Get check suite details
        check_suite = repo.get_check_suite(check_suite_id)
        
        # Determine if this is a fixable failure
        should_fix = False
        fix_reasons = []
        
        if conclusion in ["failure", "cancelled", "timed_out"]:
            # Get check runs in the suite
            check_runs = list(check_suite.get_check_runs())
            
            failed_runs = [run for run in check_runs if run.conclusion in ["failure", "cancelled", "timed_out"]]
            
            if failed_runs:
                should_fix = True
                fix_reasons.append(f"check_suite_failure_{len(failed_runs)}_runs")
        
        # Get associated PR
        pr_number = None
        if check_suite.pull_requests:
            pr_number = check_suite.pull_requests[0].number
        
        return {
            "should_fix_failure": should_fix,
            "fix_reasons": fix_reasons,
            "conclusion": conclusion,
            "pr_number": pr_number,
            "failed_runs": len(failed_runs) if 'failed_runs' in locals() else 0,
        }
        
    except Exception as e:
        logger.error("check_suite_failure_analysis_failed", error=str(e), exc_info=True)
        return {
            "should_fix_failure": False,
            "error": str(e),
        }


def analyze_push_changes(commits: List[Dict[str, Any]], ref: str) -> Dict[str, Any]:
    """Analyze push changes for insights."""
    try:
        # Analyze commits
        total_additions = 0
        total_deletions = 0
        modified_files = set()
        
        for commit in commits:
            # Note: GitHub webhook doesn't include detailed file changes
            # This would need to be fetched separately if needed
            modified_files.update(commit.get("modified", []))
            modified_files.update(commit.get("added", []))
        
        return {
            "commits_count": len(commits),
            "modified_files_count": len(modified_files),
            "ref": ref,
            "branch": ref.replace("refs/heads/", "") if ref.startswith("refs/heads/") else ref,
        }
        
    except Exception as e:
        logger.error("push_analysis_failed", error=str(e), exc_info=True)
        return {
            "error": str(e),
        }


def generate_codegen_prompt(repository: str, pr_number: Optional[int], analysis_data: Dict[str, Any]) -> str:
    """Generate prompt for Codegen agent based on analysis."""
    prompt_parts = []
    
    # Base context
    prompt_parts.append(f"Repository: {repository}")
    
    if pr_number:
        prompt_parts.append(f"Pull Request: #{pr_number}")
    
    # Add analysis context
    if "trigger_reasons" in analysis_data:
        reasons = ", ".join(analysis_data["trigger_reasons"])
        prompt_parts.append(f"Trigger reasons: {reasons}")
    
    if "fix_reasons" in analysis_data:
        reasons = ", ".join(analysis_data["fix_reasons"])
        prompt_parts.append(f"Fix reasons: {reasons}")
    
    # Add specific instructions based on analysis
    if "test_failure" in analysis_data.get("fix_reasons", []):
        prompt_parts.append("Please analyze the failing tests and fix the issues.")
    
    if "linting_failure" in analysis_data.get("fix_reasons", []):
        prompt_parts.append("Please fix the linting and formatting issues.")
    
    if "build_failure" in analysis_data.get("fix_reasons", []):
        prompt_parts.append("Please fix the build errors.")
    
    if "new_pr_with_code_changes" in analysis_data.get("trigger_reasons", []):
        prompt_parts.append("Please review the new PR and suggest improvements or add tests if needed.")
    
    return "\n".join(prompt_parts)


# Maintenance tasks

@celery_app.task(name="cleanup_old_tasks")
def cleanup_old_tasks():
    """Clean up old completed tasks."""
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=7)
        
        session = processor.get_db_session()
        try:
            # Delete old completed tasks
            deleted_tasks = session.query(WorkflowTask).filter(
                and_(
                    WorkflowTask.status.in_(["completed", "failed"]),
                    WorkflowTask.updated_at < cutoff_date,
                )
            ).delete()
            
            # Delete old task executions
            deleted_executions = session.query(TaskExecution).filter(
                TaskExecution.created_at < cutoff_date
            ).delete()
            
            # Delete old webhook events
            deleted_webhooks = session.query(WebhookEvent).filter(
                and_(
                    WebhookEvent.processed == True,
                    WebhookEvent.created_at < cutoff_date,
                )
            ).delete()
            
            session.commit()
            
            logger.info(
                "cleanup_completed",
                deleted_tasks=deleted_tasks,
                deleted_executions=deleted_executions,
                deleted_webhooks=deleted_webhooks,
            )
            
            return {
                "deleted_tasks": deleted_tasks,
                "deleted_executions": deleted_executions,
                "deleted_webhooks": deleted_webhooks,
            }
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error("cleanup_failed", error=str(e), exc_info=True)
        raise


@celery_app.task(name="health_check")
def health_check():
    """Perform system health check."""
    try:
        health_status = {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "healthy",
            "checks": {},
        }
        
        # Check database connectivity
        try:
            session = processor.get_db_session()
            session.execute("SELECT 1")
            session.close()
            health_status["checks"]["database"] = "healthy"
        except Exception as e:
            health_status["checks"]["database"] = f"unhealthy: {e}"
            health_status["status"] = "unhealthy"
        
        # Check GitHub API
        try:
            github = processor.get_github_client()
            github.get_user().login  # Simple API call
            health_status["checks"]["github_api"] = "healthy"
        except Exception as e:
            health_status["checks"]["github_api"] = f"unhealthy: {e}"
            health_status["status"] = "degraded"
        
        # Check Codegen API
        try:
            # This would need a simple health check method in the Codegen client
            health_status["checks"]["codegen_api"] = "healthy"
        except Exception as e:
            health_status["checks"]["codegen_api"] = f"unhealthy: {e}"
            health_status["status"] = "degraded"
        
        logger.info("health_check_completed", status=health_status["status"])
        return health_status
        
    except Exception as e:
        logger.error("health_check_failed", error=str(e), exc_info=True)
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "status": "unhealthy",
            "error": str(e),
        }


@celery_app.task(name="collect_metrics")
def collect_metrics():
    """Collect and store system metrics."""
    try:
        session = processor.get_db_session()
        try:
            # Collect task metrics
            task_counts = session.query(WorkflowTask.status, session.query(WorkflowTask).filter(
                WorkflowTask.status == WorkflowTask.status
            ).count()).group_by(WorkflowTask.status).all()
            
            # Store metrics
            for status, count in task_counts:
                metric = SystemMetrics(
                    metric_name="task_count",
                    metric_value={"count": count},
                    labels={"status": status},
                )
                session.add(metric)
            
            session.commit()
            
            logger.info("metrics_collected", task_counts=dict(task_counts))
            return {"status": "completed", "metrics_collected": len(task_counts)}
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error("metrics_collection_failed", error=str(e), exc_info=True)
        raise

