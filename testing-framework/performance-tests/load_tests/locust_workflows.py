"""
Locust load testing for workflow execution and API endpoints.
"""
import json
import random
import time
from locust import HttpUser, task, between, events
from datetime import datetime


class WorkflowAPIUser(HttpUser):
    """Locust user for testing workflow API endpoints."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Initialize user session."""
        self.auth_token = self.login()
        self.workflow_ids = []
        self.task_ids = []
    
    def login(self):
        """Authenticate user and get auth token."""
        response = self.client.post("/auth/login", json={
            "username": f"test_user_{random.randint(1000, 9999)}",
            "password": "test_password"
        })
        
        if response.status_code == 200:
            return response.json().get("token", "mock_token")
        return "mock_token"
    
    @task(3)
    def create_workflow(self):
        """Create a new workflow."""
        workflow_data = {
            "name": f"Load Test Workflow {random.randint(1, 1000)}",
            "description": "Workflow created during load testing",
            "steps": [
                {
                    "id": "step_1",
                    "name": "Initialize",
                    "type": "initialization",
                    "config": {"timeout": 30}
                },
                {
                    "id": "step_2",
                    "name": "Process",
                    "type": "processing",
                    "config": {"batch_size": 100}
                },
                {
                    "id": "step_3",
                    "name": "Finalize",
                    "type": "finalization",
                    "config": {"cleanup": True}
                }
            ],
            "triggers": ["manual", "webhook"],
            "timeout": 3600
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.post(
            "/api/workflows",
            json=workflow_data,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                workflow_id = response.json().get("id")
                if workflow_id:
                    self.workflow_ids.append(workflow_id)
                response.success()
            else:
                response.failure(f"Failed to create workflow: {response.status_code}")
    
    @task(5)
    def execute_workflow(self):
        """Execute an existing workflow."""
        if not self.workflow_ids:
            return
        
        workflow_id = random.choice(self.workflow_ids)
        execution_data = {
            "workflow_id": workflow_id,
            "input_data": {
                "source": "load_test",
                "timestamp": datetime.utcnow().isoformat(),
                "batch_id": random.randint(1, 100)
            },
            "priority": random.choice([1, 2, 3])
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.post(
            f"/api/workflows/{workflow_id}/execute",
            json=execution_data,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 202:
                execution_id = response.json().get("execution_id")
                response.success()
                
                # Monitor execution status
                self.monitor_execution(execution_id)
            else:
                response.failure(f"Failed to execute workflow: {response.status_code}")
    
    def monitor_execution(self, execution_id):
        """Monitor workflow execution status."""
        if not execution_id:
            return
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        max_polls = 10
        poll_count = 0
        
        while poll_count < max_polls:
            with self.client.get(
                f"/api/executions/{execution_id}/status",
                headers=headers,
                catch_response=True
            ) as response:
                if response.status_code == 200:
                    status = response.json().get("status")
                    if status in ["completed", "failed"]:
                        response.success()
                        break
                    elif status in ["pending", "running"]:
                        response.success()
                        time.sleep(1)
                        poll_count += 1
                    else:
                        response.failure(f"Unknown status: {status}")
                        break
                else:
                    response.failure(f"Failed to get execution status: {response.status_code}")
                    break
    
    @task(2)
    def create_task(self):
        """Create a new task."""
        task_data = {
            "title": f"Load Test Task {random.randint(1, 1000)}",
            "description": "Task created during load testing",
            "priority": random.choice([1, 2, 3, 4, 5]),
            "assignee": f"agent_{random.randint(1, 10)}",
            "metadata": {
                "source": "load_test",
                "category": random.choice(["bug_fix", "feature", "improvement"]),
                "estimated_hours": random.randint(1, 8)
            }
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.post(
            "/api/tasks",
            json=task_data,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 201:
                task_id = response.json().get("id")
                if task_id:
                    self.task_ids.append(task_id)
                response.success()
            else:
                response.failure(f"Failed to create task: {response.status_code}")
    
    @task(4)
    def update_task_status(self):
        """Update task status."""
        if not self.task_ids:
            return
        
        task_id = random.choice(self.task_ids)
        status_update = {
            "status": random.choice(["pending", "in_progress", "completed", "failed"]),
            "progress": random.randint(0, 100),
            "notes": f"Updated during load test at {datetime.utcnow().isoformat()}"
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.patch(
            f"/api/tasks/{task_id}",
            json=status_update,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Failed to update task: {response.status_code}")
    
    @task(2)
    def list_workflows(self):
        """List workflows with pagination."""
        params = {
            "page": random.randint(1, 5),
            "limit": random.choice([10, 20, 50]),
            "status": random.choice(["active", "inactive", "all"])
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.get(
            "/api/workflows",
            params=params,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                workflows = response.json().get("workflows", [])
                response.success()
            else:
                response.failure(f"Failed to list workflows: {response.status_code}")
    
    @task(2)
    def list_tasks(self):
        """List tasks with filtering."""
        params = {
            "page": random.randint(1, 3),
            "limit": random.choice([10, 25, 50]),
            "status": random.choice(["pending", "in_progress", "completed"]),
            "assignee": f"agent_{random.randint(1, 10)}"
        }
        
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.get(
            "/api/tasks",
            params=params,
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                tasks = response.json().get("tasks", [])
                response.success()
            else:
                response.failure(f"Failed to list tasks: {response.status_code}")
    
    @task(1)
    def get_workflow_metrics(self):
        """Get workflow execution metrics."""
        headers = {"Authorization": f"Bearer {self.auth_token}"}
        
        with self.client.get(
            "/api/metrics/workflows",
            headers=headers,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                metrics = response.json()
                response.success()
            else:
                response.failure(f"Failed to get metrics: {response.status_code}")
    
    @task(1)
    def webhook_simulation(self):
        """Simulate incoming webhook."""
        webhook_data = {
            "event": "pull_request",
            "action": random.choice(["opened", "closed", "synchronize"]),
            "repository": {
                "name": f"test-repo-{random.randint(1, 100)}",
                "full_name": f"org/test-repo-{random.randint(1, 100)}"
            },
            "pull_request": {
                "number": random.randint(1, 1000),
                "title": f"Test PR {random.randint(1, 1000)}",
                "state": random.choice(["open", "closed"])
            }
        }
        
        with self.client.post(
            "/webhooks/github",
            json=webhook_data,
            headers={"X-GitHub-Event": "pull_request"},
            catch_response=True
        ) as response:
            if response.status_code in [200, 202]:
                response.success()
            else:
                response.failure(f"Webhook failed: {response.status_code}")


class MCPServerUser(HttpUser):
    """Locust user for testing MCP server endpoints."""
    
    wait_time = between(0.5, 2)
    
    @task(3)
    def mcp_create_task(self):
        """Test MCP create_task tool."""
        mcp_request = {
            "jsonrpc": "2.0",
            "id": random.randint(1, 10000),
            "method": "tools/call",
            "params": {
                "name": "create_task",
                "arguments": {
                    "title": f"MCP Task {random.randint(1, 1000)}",
                    "description": "Task created via MCP during load test",
                    "priority": random.randint(1, 5)
                }
            }
        }
        
        with self.client.post(
            "/mcp",
            json=mcp_request,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if "error" not in result:
                    response.success()
                else:
                    response.failure(f"MCP error: {result['error']}")
            else:
                response.failure(f"MCP request failed: {response.status_code}")
    
    @task(2)
    def mcp_get_task(self):
        """Test MCP get_task tool."""
        mcp_request = {
            "jsonrpc": "2.0",
            "id": random.randint(1, 10000),
            "method": "tools/call",
            "params": {
                "name": "get_task",
                "arguments": {
                    "task_id": f"task_{random.randint(1, 100)}"
                }
            }
        }
        
        with self.client.post(
            "/mcp",
            json=mcp_request,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                result = response.json()
                if "error" not in result:
                    response.success()
                else:
                    response.success()  # Task not found is acceptable
            else:
                response.failure(f"MCP request failed: {response.status_code}")
    
    @task(1)
    def mcp_list_capabilities(self):
        """Test MCP capabilities listing."""
        mcp_request = {
            "jsonrpc": "2.0",
            "id": random.randint(1, 10000),
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "load-test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        with self.client.post(
            "/mcp",
            json=mcp_request,
            catch_response=True
        ) as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"MCP initialize failed: {response.status_code}")


# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Custom request event handler."""
    if exception:
        print(f"Request failed: {name} - {exception}")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Test start event handler."""
    print("Load test starting...")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Test stop event handler."""
    print("Load test completed.")
    
    # Print summary statistics
    stats = environment.stats
    print(f"Total requests: {stats.total.num_requests}")
    print(f"Total failures: {stats.total.num_failures}")
    print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
    print(f"Max response time: {stats.total.max_response_time:.2f}ms")


# Custom load test scenarios
class HighVolumeWorkflowUser(WorkflowAPIUser):
    """High-volume workflow execution user."""
    
    wait_time = between(0.1, 0.5)  # Faster execution
    weight = 3  # Higher weight for more users
    
    @task(10)
    def rapid_workflow_execution(self):
        """Execute workflows rapidly."""
        self.execute_workflow()


class BurstTrafficUser(WorkflowAPIUser):
    """User that simulates burst traffic patterns."""
    
    wait_time = between(0, 0.1)  # Very fast execution
    weight = 1
    
    def on_start(self):
        """Initialize burst user."""
        super().on_start()
        self.burst_count = 0
    
    @task
    def burst_requests(self):
        """Send burst of requests."""
        if self.burst_count < 10:
            self.create_task()
            self.burst_count += 1
        else:
            # Reset and wait
            self.burst_count = 0
            time.sleep(5)

