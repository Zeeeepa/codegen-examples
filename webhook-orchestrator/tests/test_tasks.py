"""
Tests for Celery task functionality.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from app.tasks.workflow_tasks import (
    process_pull_request_event,
    process_check_run_event,
    analyze_pr_changes,
    analyze_check_failure,
    generate_codegen_prompt,
)
from app.tasks.retry_logic import (
    RetryManager,
    RetryStrategy,
    RetryableException,
    NonRetryableException,
    resilient_task,
)


class TestWorkflowTasks:
    """Test workflow task processing."""
    
    @patch('app.tasks.workflow_tasks.processor')
    @patch('app.tasks.workflow_tasks.trigger_codegen_agent')
    def test_process_pull_request_event_success(self, mock_trigger, mock_processor):
        """Test successful pull request event processing."""
        # Mock processor methods
        mock_processor.update_task_status = Mock()
        mock_processor.create_task_execution = Mock()
        mock_processor.get_github_client = Mock()
        mock_processor.log_task_completed = Mock()
        
        # Mock GitHub client
        mock_github = Mock()
        mock_repo = Mock()
        mock_pr = Mock()
        
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_pull.return_value = mock_pr
        mock_processor.get_github_client.return_value = mock_github
        
        # Mock PR files
        mock_file = Mock()
        mock_file.filename = "test.py"
        mock_pr.get_files.return_value = [mock_file]
        mock_pr.state = "open"
        mock_pr.additions = 100
        mock_pr.deletions = 50
        
        # Mock Celery task
        mock_task = Mock()
        mock_task.request.id = "test-execution-id"
        mock_task.request.retries = 0
        
        # Sample payload
        payload = {
            "action": "opened",
            "pull_request": {
                "number": 123,
                "state": "open",
                "draft": False,
            },
            "repository": {
                "full_name": "test-org/test-repo",
            },
        }
        
        # Mock trigger_codegen_agent
        mock_trigger.delay.return_value = Mock(id="codegen-task-123")
        
        with patch('app.tasks.workflow_tasks.analyze_pr_changes') as mock_analyze:
            mock_analyze.return_value = {
                "should_trigger_codegen": True,
                "trigger_reasons": ["new_pr_with_code_changes"],
            }
            
            # Call the task function directly (not through Celery)
            result = process_pull_request_event.__wrapped__(
                mock_task, "task-123", payload
            )
            
            assert result["status"] == "codegen_triggered"
            assert "analysis" in result
            assert "codegen_task_id" in result
            
            # Verify processor calls
            mock_processor.update_task_status.assert_called()
            mock_processor.create_task_execution.assert_called()
    
    @patch('app.tasks.workflow_tasks.processor')
    def test_process_check_run_event_failure(self, mock_processor):
        """Test check run event processing for failures."""
        # Mock processor methods
        mock_processor.update_task_status = Mock()
        mock_processor.create_task_execution = Mock()
        mock_processor.get_github_client = Mock()
        mock_processor.log_task_completed = Mock()
        
        # Mock GitHub client
        mock_github = Mock()
        mock_repo = Mock()
        mock_check_run = Mock()
        
        mock_github.get_repo.return_value = mock_repo
        mock_repo.get_check_run.return_value = mock_check_run
        mock_processor.get_github_client.return_value = mock_github
        
        # Mock check run data
        mock_check_run.pull_requests = [Mock(number=123)]
        mock_check_run.details_url = "https://example.com/check/123"
        
        # Mock Celery task
        mock_task = Mock()
        mock_task.request.id = "test-execution-id"
        mock_task.request.retries = 0
        
        # Sample payload
        payload = {
            "action": "completed",
            "check_run": {
                "id": 12345,
                "name": "test-check",
                "conclusion": "failure",
            },
            "repository": {
                "full_name": "test-org/test-repo",
            },
        }
        
        with patch('app.tasks.workflow_tasks.analyze_check_failure') as mock_analyze:
            with patch('app.tasks.workflow_tasks.trigger_codegen_agent') as mock_trigger:
                mock_analyze.return_value = {
                    "should_fix_failure": True,
                    "fix_reasons": ["test_failure"],
                    "pr_number": 123,
                }
                mock_trigger.delay.return_value = Mock(id="codegen-task-456")
                
                # Call the task function directly
                result = process_check_run_event.__wrapped__(
                    mock_task, "task-456", payload
                )
                
                assert result["status"] == "fix_triggered"
                assert "analysis" in result
                assert "codegen_task_id" in result
    
    def test_analyze_pr_changes_new_pr(self):
        """Test PR analysis for new pull request."""
        # Mock PR object
        mock_pr = Mock()
        mock_pr.state = "open"
        mock_pr.additions = 150
        mock_pr.deletions = 75
        
        # Mock files
        mock_files = [
            Mock(filename="src/main.py"),
            Mock(filename="tests/test_main.py"),
            Mock(filename="config.json"),
        ]
        mock_pr.get_files.return_value = mock_files
        
        result = analyze_pr_changes(mock_pr, "opened")
        
        assert result["should_trigger_codegen"] is True
        assert "new_pr_with_code_changes" in result["trigger_reasons"]
        assert result["code_files"] == 1
        assert result["test_files"] == 1
        assert result["config_files"] == 1
    
    def test_analyze_pr_changes_draft_pr(self):
        """Test PR analysis for draft pull request."""
        mock_pr = Mock()
        mock_pr.state = "open"
        mock_pr.additions = 50
        mock_pr.deletions = 25
        
        # Mock files - only config files
        mock_files = [Mock(filename="package.json")]
        mock_pr.get_files.return_value = mock_files
        
        result = analyze_pr_changes(mock_pr, "converted_to_draft")
        
        assert result["should_trigger_codegen"] is False
        assert result["code_files"] == 0
    
    def test_analyze_check_failure_test_failure(self):
        """Test check failure analysis for test failures."""
        # Mock repository and check run
        mock_repo = Mock()
        mock_check_run = Mock()
        mock_check_run.pull_requests = [Mock(number=123)]
        mock_check_run.details_url = "https://example.com/check/123"
        
        mock_repo.get_check_run.return_value = mock_check_run
        
        result = analyze_check_failure(mock_repo, 12345, "pytest", "failure")
        
        assert result["should_fix_failure"] is True
        assert "test_failure" in result["fix_reasons"]
        assert result["pr_number"] == 123
    
    def test_analyze_check_failure_lint_failure(self):
        """Test check failure analysis for linting failures."""
        mock_repo = Mock()
        mock_check_run = Mock()
        mock_check_run.pull_requests = [Mock(number=456)]
        mock_check_run.details_url = "https://example.com/check/456"
        
        mock_repo.get_check_run.return_value = mock_check_run
        
        result = analyze_check_failure(mock_repo, 67890, "eslint", "failure")
        
        assert result["should_fix_failure"] is True
        assert "linting_failure" in result["fix_reasons"]
        assert result["pr_number"] == 456
    
    def test_generate_codegen_prompt_pr_analysis(self):
        """Test Codegen prompt generation for PR analysis."""
        analysis_data = {
            "trigger_reasons": ["new_pr_with_code_changes", "ready_for_review"],
            "code_files": 5,
            "test_files": 2,
        }
        
        prompt = generate_codegen_prompt("test-org/test-repo", 123, analysis_data)
        
        assert "Repository: test-org/test-repo" in prompt
        assert "Pull Request: #123" in prompt
        assert "new_pr_with_code_changes" in prompt
        assert "ready_for_review" in prompt
    
    def test_generate_codegen_prompt_check_failure(self):
        """Test Codegen prompt generation for check failures."""
        analysis_data = {
            "fix_reasons": ["test_failure", "linting_failure"],
            "check_name": "pytest",
            "conclusion": "failure",
        }
        
        prompt = generate_codegen_prompt("test-org/test-repo", 456, analysis_data)
        
        assert "Repository: test-org/test-repo" in prompt
        assert "Pull Request: #456" in prompt
        assert "test_failure" in prompt
        assert "Please analyze the failing tests" in prompt
        assert "Please fix the linting" in prompt


class TestRetryLogic:
    """Test retry logic and resilience patterns."""
    
    def test_retry_manager_exponential_delay(self):
        """Test exponential backoff delay calculation."""
        manager = RetryManager()
        
        # Test exponential backoff
        delay1 = manager.get_retry_delay(1, RetryStrategy.EXPONENTIAL, 1.0, 300.0, 2.0)
        delay2 = manager.get_retry_delay(2, RetryStrategy.EXPONENTIAL, 1.0, 300.0, 2.0)
        delay3 = manager.get_retry_delay(3, RetryStrategy.EXPONENTIAL, 1.0, 300.0, 2.0)
        
        assert delay1 == 1.0
        assert delay2 == 2.0
        assert delay3 == 4.0
    
    def test_retry_manager_linear_delay(self):
        """Test linear backoff delay calculation."""
        manager = RetryManager()
        
        delay1 = manager.get_retry_delay(1, RetryStrategy.LINEAR, 2.0, 300.0)
        delay2 = manager.get_retry_delay(2, RetryStrategy.LINEAR, 2.0, 300.0)
        delay3 = manager.get_retry_delay(3, RetryStrategy.LINEAR, 2.0, 300.0)
        
        assert delay1 == 2.0
        assert delay2 == 4.0
        assert delay3 == 6.0
    
    def test_retry_manager_should_retry_retryable_exception(self):
        """Test retry decision for retryable exceptions."""
        manager = RetryManager()
        
        # Should retry for retryable exceptions
        assert manager.should_retry(RetryableException("test"), 1, 3) is True
        assert manager.should_retry(RetryableException("test"), 3, 3) is False  # Max attempts reached
    
    def test_retry_manager_should_retry_non_retryable_exception(self):
        """Test retry decision for non-retryable exceptions."""
        manager = RetryManager()
        
        # Should not retry for non-retryable exceptions
        assert manager.should_retry(NonRetryableException("test"), 1, 3) is False
        assert manager.should_retry(ValueError("test"), 1, 3) is False
    
    def test_retry_manager_should_retry_rate_limit(self):
        """Test retry decision for rate limit errors."""
        manager = RetryManager()
        
        # Should retry for rate limit errors
        rate_limit_error = Exception("Rate limit exceeded")
        assert manager.should_retry(rate_limit_error, 1, 3) is True
        
        too_many_requests_error = Exception("Too many requests")
        assert manager.should_retry(too_many_requests_error, 1, 3) is True
    
    def test_retry_manager_record_attempt(self):
        """Test retry attempt recording."""
        manager = RetryManager()
        
        # Record successful attempt
        manager.record_attempt("test_operation", True, 1.5)
        
        stats = manager.get_stats("test_operation")
        assert stats["total_attempts"] == 1
        assert stats["successful_attempts"] == 1
        assert stats["failed_attempts"] == 0
        assert stats["avg_duration"] == 1.5
        
        # Record failed attempt
        manager.record_attempt("test_operation", False, 2.0)
        
        stats = manager.get_stats("test_operation")
        assert stats["total_attempts"] == 2
        assert stats["successful_attempts"] == 1
        assert stats["failed_attempts"] == 1
        assert stats["avg_duration"] == 1.75  # (1.5 + 2.0) / 2
    
    @pytest.mark.asyncio
    async def test_resilient_task_decorator_success(self):
        """Test resilient task decorator with successful execution."""
        call_count = 0
        
        @resilient_task(max_retries=3)
        async def test_function():
            nonlocal call_count
            call_count += 1
            return "success"
        
        result = await test_function()
        
        assert result == "success"
        assert call_count == 1
    
    @pytest.mark.asyncio
    async def test_resilient_task_decorator_retry_and_success(self):
        """Test resilient task decorator with retry and eventual success."""
        call_count = 0
        
        @resilient_task(max_retries=3, base_delay=0.01)  # Fast retry for testing
        async def test_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RetryableException("Temporary failure")
            return "success"
        
        result = await test_function()
        
        assert result == "success"
        assert call_count == 3
    
    @pytest.mark.asyncio
    async def test_resilient_task_decorator_max_retries_exceeded(self):
        """Test resilient task decorator with max retries exceeded."""
        call_count = 0
        
        @resilient_task(max_retries=2, base_delay=0.01)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise RetryableException("Persistent failure")
        
        with pytest.raises(RetryableException):
            await test_function()
        
        assert call_count == 2  # Should try max_retries times
    
    @pytest.mark.asyncio
    async def test_resilient_task_decorator_non_retryable_exception(self):
        """Test resilient task decorator with non-retryable exception."""
        call_count = 0
        
        @resilient_task(max_retries=3)
        async def test_function():
            nonlocal call_count
            call_count += 1
            raise NonRetryableException("Non-retryable failure")
        
        with pytest.raises(NonRetryableException):
            await test_function()
        
        assert call_count == 1  # Should not retry


class TestTaskIntegration:
    """Integration tests for task processing."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_task_processing(self):
        """Test end-to-end task processing flow."""
        # This would require a test database and Celery setup
        # For now, we'll test the main components in isolation
        pass
    
    def test_task_error_handling(self):
        """Test task error handling and recovery."""
        # Test error scenarios and recovery mechanisms
        pass
    
    def test_task_monitoring_and_metrics(self):
        """Test task monitoring and metrics collection."""
        # Test metrics collection during task execution
        pass

