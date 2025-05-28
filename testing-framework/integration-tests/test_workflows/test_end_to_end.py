"""
End-to-end integration tests for complete workflow execution.
"""
import pytest
import asyncio
import json
import time
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime, timedelta


class TestCompleteWorkflowExecution:
    """Test complete workflow execution from start to finish."""
    
    @pytest.fixture
    def workflow_config(self):
        """Create a test workflow configuration."""
        return {
            "id": "wf_e2e_test",
            "name": "End-to-End Test Workflow",
            "description": "Complete workflow for testing",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Initialize Task",
                    "type": "task_creation",
                    "config": {
                        "template": "code_review",
                        "auto_assign": True
                    }
                },
                {
                    "id": "step_2", 
                    "name": "Code Analysis",
                    "type": "claude_code_analysis",
                    "config": {
                        "analysis_type": "comprehensive",
                        "include_security": True
                    }
                },
                {
                    "id": "step_3",
                    "name": "Generate Code",
                    "type": "codegen_generation",
                    "config": {
                        "model": "claude-3-sonnet",
                        "temperature": 0.1
                    }
                },
                {
                    "id": "step_4",
                    "name": "Validate & Test",
                    "type": "validation",
                    "config": {
                        "run_tests": True,
                        "check_coverage": True
                    }
                },
                {
                    "id": "step_5",
                    "name": "Create PR",
                    "type": "github_pr",
                    "config": {
                        "auto_merge": False,
                        "request_review": True
                    }
                }
            ],
            "triggers": ["github_webhook", "manual"],
            "timeout": 3600  # 1 hour
        }
    
    @pytest.fixture
    def mock_github_webhook_payload(self):
        """Create a mock GitHub webhook payload."""
        return {
            "action": "opened",
            "pull_request": {
                "id": 123456,
                "number": 42,
                "title": "Add new feature",
                "body": "This PR adds a new feature for user authentication",
                "head": {
                    "ref": "feature/auth-system",
                    "sha": "abc123def456"
                },
                "base": {
                    "ref": "main",
                    "sha": "def456ghi789"
                }
            },
            "repository": {
                "name": "test-repo",
                "full_name": "org/test-repo",
                "clone_url": "https://github.com/org/test-repo.git"
            }
        }
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_github_webhook_to_pr_creation(self, workflow_config, mock_github_webhook_payload):
        """Test complete workflow from GitHub webhook to PR creation."""
        # Mock workflow execution steps
        execution_log = []
        
        async def mock_step_executor(step_id, step_config, context):
            """Mock step executor that logs execution."""
            execution_log.append({
                "step_id": step_id,
                "timestamp": datetime.utcnow(),
                "status": "completed",
                "duration": 0.1
            })
            
            # Simulate step-specific outputs
            if step_id == "step_1":
                return {"task_id": "task_12345", "status": "created"}
            elif step_id == "step_2":
                return {
                    "analysis_results": {
                        "issues_found": 2,
                        "security_score": 8.5,
                        "complexity_score": 6.2
                    }
                }
            elif step_id == "step_3":
                return {
                    "generated_files": ["src/auth.py", "tests/test_auth.py"],
                    "lines_of_code": 150
                }
            elif step_id == "step_4":
                return {
                    "tests_passed": True,
                    "coverage_percentage": 92.5,
                    "validation_errors": []
                }
            elif step_id == "step_5":
                return {
                    "pr_number": 43,
                    "pr_url": "https://github.com/org/test-repo/pull/43"
                }
        
        # Execute workflow
        workflow_result = await self._execute_workflow(
            workflow_config, 
            mock_github_webhook_payload,
            mock_step_executor
        )
        
        # Verify workflow execution
        assert workflow_result["status"] == "completed"
        assert len(execution_log) == 5
        assert all(step["status"] == "completed" for step in execution_log)
        
        # Verify step sequence
        expected_steps = ["step_1", "step_2", "step_3", "step_4", "step_5"]
        actual_steps = [step["step_id"] for step in execution_log]
        assert actual_steps == expected_steps
        
        # Verify final output
        assert "pr_number" in workflow_result["output"]
        assert workflow_result["output"]["pr_number"] == 43
    
    async def _execute_workflow(self, workflow_config, trigger_payload, step_executor):
        """Execute a workflow with given configuration and trigger."""
        start_time = datetime.utcnow()
        context = {"trigger_payload": trigger_payload}
        
        try:
            # Execute each step in sequence
            for step in workflow_config["steps"]:
                step_result = await step_executor(step["id"], step["config"], context)
                context[f"{step['id']}_result"] = step_result
            
            return {
                "status": "completed",
                "duration": (datetime.utcnow() - start_time).total_seconds(),
                "output": context.get("step_5_result", {})
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "duration": (datetime.utcnow() - start_time).total_seconds()
            }
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_error_recovery(self, workflow_config):
        """Test workflow error recovery and retry mechanisms."""
        retry_count = 0
        max_retries = 3
        
        async def failing_step_executor(step_id, step_config, context):
            nonlocal retry_count
            
            if step_id == "step_2" and retry_count < 2:
                retry_count += 1
                raise Exception(f"Simulated failure (attempt {retry_count})")
            
            return {"status": "success", "step_id": step_id}
        
        # Execute workflow with retry logic
        workflow_result = await self._execute_workflow_with_retry(
            workflow_config,
            {},
            failing_step_executor,
            max_retries
        )
        
        assert workflow_result["status"] == "completed"
        assert retry_count == 2  # Failed twice, succeeded on third attempt
    
    async def _execute_workflow_with_retry(self, workflow_config, trigger_payload, step_executor, max_retries):
        """Execute workflow with retry logic for failed steps."""
        context = {"trigger_payload": trigger_payload}
        
        for step in workflow_config["steps"]:
            retry_count = 0
            
            while retry_count <= max_retries:
                try:
                    step_result = await step_executor(step["id"], step["config"], context)
                    context[f"{step['id']}_result"] = step_result
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        return {"status": "failed", "error": str(e), "step": step["id"]}
                    
                    # Wait before retry
                    await asyncio.sleep(0.1)
        
        return {"status": "completed", "context": context}
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_parallel_workflow_execution(self):
        """Test execution of multiple workflows in parallel."""
        # Create multiple workflow instances
        workflows = [
            {"id": f"wf_{i}", "steps": [{"id": "step_1", "config": {}}]} 
            for i in range(5)
        ]
        
        async def simple_step_executor(step_id, step_config, context):
            await asyncio.sleep(0.1)  # Simulate work
            return {"status": "completed", "workflow_id": context.get("workflow_id")}
        
        # Execute workflows in parallel
        start_time = time.time()
        
        tasks = [
            self._execute_workflow(
                workflow, 
                {"workflow_id": workflow["id"]}, 
                simple_step_executor
            )
            for workflow in workflows
        ]
        
        results = await asyncio.gather(*tasks)
        
        execution_time = time.time() - start_time
        
        # Verify all workflows completed
        assert len(results) == 5
        assert all(result["status"] == "completed" for result in results)
        
        # Verify parallel execution was faster than sequential
        assert execution_time < 0.6  # Should be much faster than 5 * 0.1 = 0.5 seconds


class TestWorkflowDataFlow:
    """Test data flow between workflow steps."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_data_passing_between_steps(self):
        """Test that data flows correctly between workflow steps."""
        workflow_data = {}
        
        async def data_flow_executor(step_id, step_config, context):
            if step_id == "extract":
                data = {"user_id": 123, "action": "login", "timestamp": datetime.utcnow().isoformat()}
                workflow_data["extracted_data"] = data
                return data
            
            elif step_id == "transform":
                input_data = context.get("extract_result", {})
                transformed = {
                    "user_id": input_data["user_id"],
                    "event_type": input_data["action"],
                    "processed_at": datetime.utcnow().isoformat()
                }
                workflow_data["transformed_data"] = transformed
                return transformed
            
            elif step_id == "load":
                input_data = context.get("transform_result", {})
                # Simulate loading to database
                loaded = {"record_id": "rec_456", "status": "saved", "data": input_data}
                workflow_data["loaded_data"] = loaded
                return loaded
        
        # Define ETL workflow
        etl_workflow = {
            "steps": [
                {"id": "extract", "config": {}},
                {"id": "transform", "config": {}},
                {"id": "load", "config": {}}
            ]
        }
        
        # Execute workflow
        result = await self._execute_workflow(etl_workflow, {}, data_flow_executor)
        
        # Verify data flow
        assert "extracted_data" in workflow_data
        assert "transformed_data" in workflow_data
        assert "loaded_data" in workflow_data
        
        # Verify data transformation
        assert workflow_data["extracted_data"]["user_id"] == 123
        assert workflow_data["transformed_data"]["user_id"] == 123
        assert workflow_data["transformed_data"]["event_type"] == "login"
        assert workflow_data["loaded_data"]["record_id"] == "rec_456"
    
    async def _execute_workflow(self, workflow_config, trigger_payload, step_executor):
        """Execute workflow and track data flow."""
        context = {"trigger_payload": trigger_payload}
        
        for step in workflow_config["steps"]:
            step_result = await step_executor(step["id"], step["config"], context)
            context[f"{step['id']}_result"] = step_result
        
        return {"status": "completed", "context": context}


class TestWorkflowPerformance:
    """Test workflow performance and scalability."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    @pytest.mark.slow
    async def test_workflow_performance_under_load(self):
        """Test workflow performance under high load."""
        # Create a performance test workflow
        performance_workflow = {
            "steps": [
                {"id": "cpu_intensive", "config": {"iterations": 1000}},
                {"id": "io_intensive", "config": {"file_operations": 100}},
                {"id": "memory_intensive", "config": {"data_size": "1MB"}}
            ]
        }
        
        async def performance_step_executor(step_id, step_config, context):
            if step_id == "cpu_intensive":
                # Simulate CPU-intensive work
                iterations = step_config.get("iterations", 100)
                result = sum(i * i for i in range(iterations))
                return {"result": result, "iterations": iterations}
            
            elif step_id == "io_intensive":
                # Simulate I/O operations
                operations = step_config.get("file_operations", 10)
                await asyncio.sleep(0.001 * operations)  # Simulate I/O delay
                return {"operations_completed": operations}
            
            elif step_id == "memory_intensive":
                # Simulate memory-intensive work
                data_size = step_config.get("data_size", "1KB")
                size_bytes = 1024 if data_size == "1KB" else 1024 * 1024
                data = bytearray(size_bytes)
                return {"data_size": len(data)}
        
        # Measure execution time
        start_time = time.time()
        
        # Execute multiple workflows concurrently
        tasks = [
            self._execute_workflow(performance_workflow, {}, performance_step_executor)
            for _ in range(10)
        ]
        
        results = await asyncio.gather(*tasks)
        
        execution_time = time.time() - start_time
        
        # Verify performance metrics
        assert len(results) == 10
        assert all(result["status"] == "completed" for result in results)
        assert execution_time < 5.0  # Should complete within 5 seconds
    
    async def _execute_workflow(self, workflow_config, trigger_payload, step_executor):
        """Execute workflow for performance testing."""
        start_time = time.time()
        context = {"trigger_payload": trigger_payload}
        
        for step in workflow_config["steps"]:
            step_result = await step_executor(step["id"], step["config"], context)
            context[f"{step['id']}_result"] = step_result
        
        return {
            "status": "completed",
            "duration": time.time() - start_time,
            "context": context
        }


class TestWorkflowMonitoring:
    """Test workflow monitoring and observability."""
    
    @pytest.mark.asyncio
    @pytest.mark.integration
    async def test_workflow_metrics_collection(self):
        """Test collection of workflow execution metrics."""
        metrics = {
            "executions": 0,
            "successes": 0,
            "failures": 0,
            "total_duration": 0,
            "step_metrics": {}
        }
        
        async def metrics_collecting_executor(step_id, step_config, context):
            step_start = time.time()
            
            # Simulate step execution
            await asyncio.sleep(0.05)
            
            step_duration = time.time() - step_start
            
            # Collect step metrics
            if step_id not in metrics["step_metrics"]:
                metrics["step_metrics"][step_id] = {
                    "executions": 0,
                    "total_duration": 0,
                    "avg_duration": 0
                }
            
            step_metrics = metrics["step_metrics"][step_id]
            step_metrics["executions"] += 1
            step_metrics["total_duration"] += step_duration
            step_metrics["avg_duration"] = step_metrics["total_duration"] / step_metrics["executions"]
            
            return {"status": "completed", "duration": step_duration}
        
        # Execute multiple workflows to collect metrics
        workflow = {"steps": [{"id": "step_1", "config": {}}, {"id": "step_2", "config": {}}]}
        
        for _ in range(5):
            start_time = time.time()
            metrics["executions"] += 1
            
            try:
                result = await self._execute_workflow(workflow, {}, metrics_collecting_executor)
                metrics["successes"] += 1
                metrics["total_duration"] += time.time() - start_time
            except Exception:
                metrics["failures"] += 1
        
        # Verify metrics collection
        assert metrics["executions"] == 5
        assert metrics["successes"] == 5
        assert metrics["failures"] == 0
        assert len(metrics["step_metrics"]) == 2
        assert metrics["step_metrics"]["step_1"]["executions"] == 5
        assert metrics["step_metrics"]["step_2"]["executions"] == 5
    
    async def _execute_workflow(self, workflow_config, trigger_payload, step_executor):
        """Execute workflow with metrics collection."""
        context = {"trigger_payload": trigger_payload}
        
        for step in workflow_config["steps"]:
            step_result = await step_executor(step["id"], step["config"], context)
            context[f"{step['id']}_result"] = step_result
        
        return {"status": "completed", "context": context}

