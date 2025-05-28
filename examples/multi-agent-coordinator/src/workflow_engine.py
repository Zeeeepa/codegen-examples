#!/usr/bin/env python
"""
Multi-Agent Workflow Engine

This module implements the core workflow orchestration engine that manages
parallel and sequential execution of AI agents with intelligent dependency
resolution and resource optimization.
"""

import asyncio
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Union
from datetime import datetime, timedelta
import json
import threading
from collections import defaultdict, deque

from .agent_registry import AgentRegistry, AgentType
from .coordination_protocols import MessageBus, AgentMessage, MessageType
from .resource_manager import ResourceManager, ResourceRequest
from .execution_planner import ExecutionPlanner, ExecutionPlan
from .monitoring_system import MonitoringSystem, WorkflowMetrics


class WorkflowStatus(Enum):
    """Workflow execution status."""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskStatus(Enum):
    """Individual task status."""
    WAITING = "waiting"
    READY = "ready"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    RETRYING = "retrying"


@dataclass
class Task:
    """Represents a single task in a workflow."""
    id: str
    name: str
    agent_type: AgentType
    parameters: Dict[str, Any]
    dependencies: Set[str] = field(default_factory=set)
    status: TaskStatus = TaskStatus.WAITING
    result: Optional[Any] = None
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
    timeout: Optional[int] = None
    priority: int = 0
    resource_requirements: Optional[ResourceRequest] = None
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate task execution duration."""
        if self.start_time and self.end_time:
            return self.end_time - self.start_time
        return None
    
    @property
    def is_ready(self) -> bool:
        """Check if task is ready to execute (all dependencies completed)."""
        return self.status == TaskStatus.READY
    
    @property
    def is_terminal(self) -> bool:
        """Check if task is in a terminal state."""
        return self.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.SKIPPED}


@dataclass
class Workflow:
    """Represents a complete workflow with tasks and dependencies."""
    id: str
    name: str
    description: str
    tasks: Dict[str, Task] = field(default_factory=dict)
    status: WorkflowStatus = WorkflowStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    max_parallel_tasks: int = 10
    timeout: Optional[int] = None
    retry_policy: Dict[str, Any] = field(default_factory=dict)
    
    def add_task(self, task: Task) -> None:
        """Add a task to the workflow."""
        self.tasks[task.id] = task
    
    def add_dependency(self, task_id: str, dependency_id: str) -> None:
        """Add a dependency between tasks."""
        if task_id in self.tasks and dependency_id in self.tasks:
            self.tasks[task_id].dependencies.add(dependency_id)
    
    def get_ready_tasks(self, completed_tasks: Set[str]) -> List[Task]:
        """Get tasks that are ready to execute."""
        ready_tasks = []
        for task in self.tasks.values():
            if (task.status == TaskStatus.WAITING and 
                task.dependencies.issubset(completed_tasks)):
                task.status = TaskStatus.READY
                ready_tasks.append(task)
        return sorted(ready_tasks, key=lambda t: t.priority, reverse=True)
    
    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """Get the dependency graph as adjacency list."""
        graph = {}
        for task_id, task in self.tasks.items():
            graph[task_id] = task.dependencies
        return graph
    
    @property
    def duration(self) -> Optional[timedelta]:
        """Calculate workflow execution duration."""
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def progress(self) -> float:
        """Calculate workflow completion progress (0.0 to 1.0)."""
        if not self.tasks:
            return 0.0
        
        completed = sum(1 for task in self.tasks.values() 
                       if task.status == TaskStatus.COMPLETED)
        return completed / len(self.tasks)


class WorkflowEngine:
    """
    Core workflow orchestration engine with advanced features:
    - Dynamic workflow plan generation
    - Intelligent dependency resolution
    - Resource-aware scheduling
    - Fault tolerance and recovery
    - Real-time monitoring and adaptation
    """
    
    def __init__(self, 
                 agent_registry: AgentRegistry,
                 resource_manager: ResourceManager,
                 monitoring_system: MonitoringSystem,
                 max_concurrent_workflows: int = 5,
                 enable_ml_optimization: bool = True):
        """Initialize the workflow engine."""
        self.agent_registry = agent_registry
        self.resource_manager = resource_manager
        self.monitoring_system = monitoring_system
        self.execution_planner = ExecutionPlanner(enable_ml_optimization)
        self.message_bus = MessageBus()
        
        # Workflow management
        self.workflows: Dict[str, Workflow] = {}
        self.active_workflows: Set[str] = set()
        self.max_concurrent_workflows = max_concurrent_workflows
        
        # Execution management
        self.executor = ThreadPoolExecutor(max_workers=20)
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.task_futures: Dict[str, asyncio.Future] = {}
        
        # Recovery and fault tolerance
        self.circuit_breakers: Dict[str, 'CircuitBreaker'] = {}
        self.retry_queues: Dict[str, deque] = defaultdict(deque)
        
        # Performance optimization
        self.performance_history: Dict[str, List[float]] = defaultdict(list)
        self.adaptive_scheduling = True
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Shutdown management
        self._shutdown_event = threading.Event()
        self._background_tasks: List[asyncio.Task] = []
        
        # Start background services
        self._start_background_services()
        
        logging.info("WorkflowEngine initialized with advanced orchestration capabilities")
    
    def _start_background_services(self) -> None:
        """Start background monitoring and optimization services."""
        # Start workflow monitor
        monitor_task = asyncio.create_task(self._workflow_monitor())
        self._background_tasks.append(monitor_task)
        
        # Start resource optimizer
        optimizer_task = asyncio.create_task(self._resource_optimizer())
        self._background_tasks.append(optimizer_task)
        
        # Start failure recovery service
        recovery_task = asyncio.create_task(self._failure_recovery_service())
        self._background_tasks.append(recovery_task)
    
    async def create_workflow(self, 
                            name: str, 
                            description: str,
                            tasks_config: List[Dict[str, Any]],
                            dependencies: List[Dict[str, str]] = None,
                            metadata: Dict[str, Any] = None) -> str:
        """
        Create a new workflow with intelligent optimization.
        
        Args:
            name: Workflow name
            description: Workflow description
            tasks_config: List of task configurations
            dependencies: List of dependency relationships
            metadata: Additional workflow metadata
            
        Returns:
            Workflow ID
        """
        workflow_id = str(uuid.uuid4())
        workflow = Workflow(
            id=workflow_id,
            name=name,
            description=description,
            metadata=metadata or {}
        )
        
        # Create tasks
        for task_config in tasks_config:
            task = Task(
                id=task_config.get('id', str(uuid.uuid4())),
                name=task_config['name'],
                agent_type=AgentType(task_config['agent_type']),
                parameters=task_config.get('parameters', {}),
                priority=task_config.get('priority', 0),
                timeout=task_config.get('timeout'),
                max_retries=task_config.get('max_retries', 3),
                resource_requirements=ResourceRequest(**task_config.get('resources', {}))
            )
            workflow.add_task(task)
        
        # Add dependencies
        if dependencies:
            for dep in dependencies:
                workflow.add_dependency(dep['task'], dep['depends_on'])
        
        # Validate workflow
        if not self._validate_workflow(workflow):
            raise ValueError("Invalid workflow configuration")
        
        # Optimize workflow plan
        execution_plan = await self.execution_planner.create_plan(workflow)
        workflow.metadata['execution_plan'] = execution_plan.to_dict()
        
        # Store workflow
        self.workflows[workflow_id] = workflow
        
        # Emit workflow created event
        await self._emit_event('workflow_created', {
            'workflow_id': workflow_id,
            'name': name,
            'task_count': len(workflow.tasks)
        })
        
        logging.info(f"Created workflow {workflow_id}: {name} with {len(workflow.tasks)} tasks")
        return workflow_id
    
    async def execute_workflow(self, workflow_id: str) -> bool:
        """
        Execute a workflow with intelligent orchestration.
        
        Args:
            workflow_id: ID of the workflow to execute
            
        Returns:
            True if workflow completed successfully, False otherwise
        """
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        workflow = self.workflows[workflow_id]
        
        # Check if we can start another workflow
        if len(self.active_workflows) >= self.max_concurrent_workflows:
            logging.warning(f"Maximum concurrent workflows reached. Queuing workflow {workflow_id}")
            return False
        
        # Mark workflow as active
        self.active_workflows.add(workflow_id)
        workflow.status = WorkflowStatus.RUNNING
        workflow.started_at = datetime.now()
        
        try:
            # Start workflow execution
            await self._emit_event('workflow_started', {'workflow_id': workflow_id})
            
            # Execute workflow tasks
            success = await self._execute_workflow_tasks(workflow)
            
            # Update workflow status
            workflow.status = WorkflowStatus.COMPLETED if success else WorkflowStatus.FAILED
            workflow.completed_at = datetime.now()
            
            # Emit completion event
            await self._emit_event('workflow_completed', {
                'workflow_id': workflow_id,
                'success': success,
                'duration': workflow.duration.total_seconds() if workflow.duration else 0
            })
            
            logging.info(f"Workflow {workflow_id} {'completed' if success else 'failed'}")
            return success
            
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now()
            logging.error(f"Workflow {workflow_id} failed with error: {e}")
            await self._emit_event('workflow_failed', {
                'workflow_id': workflow_id,
                'error': str(e)
            })
            return False
        
        finally:
            # Remove from active workflows
            self.active_workflows.discard(workflow_id)
    
    async def _execute_workflow_tasks(self, workflow: Workflow) -> bool:
        """Execute all tasks in a workflow with dependency resolution."""
        completed_tasks: Set[str] = set()
        failed_tasks: Set[str] = set()
        running_tasks: Dict[str, asyncio.Task] = {}
        
        while True:
            # Get ready tasks
            ready_tasks = workflow.get_ready_tasks(completed_tasks)
            
            # Start new tasks (respecting resource limits)
            for task in ready_tasks:
                if len(running_tasks) >= workflow.max_parallel_tasks:
                    break
                
                # Check resource availability
                if not await self.resource_manager.can_allocate(task.resource_requirements):
                    continue
                
                # Allocate resources
                allocation = await self.resource_manager.allocate(task.resource_requirements)
                if not allocation:
                    continue
                
                # Start task execution
                task_future = asyncio.create_task(self._execute_task(task, allocation))
                running_tasks[task.id] = task_future
                task.status = TaskStatus.RUNNING
                task.start_time = datetime.now()
                
                logging.info(f"Started task {task.id} ({task.name})")
            
            # Wait for at least one task to complete
            if not running_tasks:
                break
            
            done, pending = await asyncio.wait(
                running_tasks.values(),
                return_when=asyncio.FIRST_COMPLETED,
                timeout=1.0
            )
            
            # Process completed tasks
            for future in done:
                # Find the task that completed
                task_id = None
                for tid, tf in running_tasks.items():
                    if tf == future:
                        task_id = tid
                        break
                
                if task_id:
                    task = workflow.tasks[task_id]
                    task.end_time = datetime.now()
                    
                    try:
                        result = await future
                        task.result = result
                        task.status = TaskStatus.COMPLETED
                        completed_tasks.add(task_id)
                        
                        # Update performance history
                        if task.duration:
                            self.performance_history[task.agent_type.value].append(
                                task.duration.total_seconds()
                            )
                        
                        logging.info(f"Task {task_id} completed successfully")
                        
                    except Exception as e:
                        task.error = str(e)
                        task.status = TaskStatus.FAILED
                        failed_tasks.add(task_id)
                        
                        # Handle task failure
                        await self._handle_task_failure(task, workflow)
                        
                        logging.error(f"Task {task_id} failed: {e}")
                    
                    # Remove from running tasks
                    del running_tasks[task_id]
            
            # Check if workflow is complete
            all_tasks = set(workflow.tasks.keys())
            if completed_tasks.union(failed_tasks) == all_tasks:
                break
            
            # Check for deadlock (no tasks running and no tasks ready)
            if not running_tasks and not workflow.get_ready_tasks(completed_tasks):
                logging.error(f"Workflow {workflow.id} deadlocked")
                break
        
        # Cancel any remaining tasks
        for future in running_tasks.values():
            future.cancel()
        
        # Determine success
        return len(failed_tasks) == 0
    
    async def _execute_task(self, task: Task, resource_allocation: Any) -> Any:
        """Execute a single task with the allocated agent."""
        try:
            # Get agent for task
            agent = await self.agent_registry.get_agent(task.agent_type)
            if not agent:
                raise RuntimeError(f"No agent available for type {task.agent_type}")
            
            # Execute task with timeout
            if task.timeout:
                result = await asyncio.wait_for(
                    agent.execute(task.parameters),
                    timeout=task.timeout
                )
            else:
                result = await agent.execute(task.parameters)
            
            return result
            
        except asyncio.TimeoutError:
            raise RuntimeError(f"Task {task.id} timed out after {task.timeout} seconds")
        
        except Exception as e:
            raise RuntimeError(f"Task {task.id} execution failed: {e}")
        
        finally:
            # Release resources
            await self.resource_manager.release(resource_allocation)
    
    async def _handle_task_failure(self, task: Task, workflow: Workflow) -> None:
        """Handle task failure with retry logic and circuit breaker."""
        # Check if task should be retried
        if task.retry_count < task.max_retries:
            task.retry_count += 1
            task.status = TaskStatus.RETRYING
            
            # Add to retry queue with exponential backoff
            retry_delay = min(2 ** task.retry_count, 60)  # Max 60 seconds
            self.retry_queues[workflow.id].append((task.id, time.time() + retry_delay))
            
            logging.info(f"Task {task.id} scheduled for retry {task.retry_count}/{task.max_retries}")
        else:
            # Check circuit breaker
            circuit_breaker = self.circuit_breakers.get(task.agent_type.value)
            if circuit_breaker:
                circuit_breaker.record_failure()
    
    async def _workflow_monitor(self) -> None:
        """Background service to monitor workflow health and performance."""
        while not self._shutdown_event.is_set():
            try:
                # Monitor active workflows
                for workflow_id in list(self.active_workflows):
                    workflow = self.workflows.get(workflow_id)
                    if not workflow:
                        continue
                    
                    # Check for timeout
                    if (workflow.timeout and workflow.started_at and
                        datetime.now() - workflow.started_at > timedelta(seconds=workflow.timeout)):
                        await self._cancel_workflow(workflow_id, "Timeout")
                    
                    # Update metrics
                    metrics = WorkflowMetrics(
                        workflow_id=workflow_id,
                        status=workflow.status.value,
                        progress=workflow.progress,
                        task_count=len(workflow.tasks),
                        running_tasks=sum(1 for t in workflow.tasks.values() 
                                        if t.status == TaskStatus.RUNNING),
                        failed_tasks=sum(1 for t in workflow.tasks.values() 
                                       if t.status == TaskStatus.FAILED)
                    )
                    await self.monitoring_system.record_workflow_metrics(metrics)
                
                await asyncio.sleep(5)  # Monitor every 5 seconds
                
            except Exception as e:
                logging.error(f"Error in workflow monitor: {e}")
                await asyncio.sleep(10)
    
    async def _resource_optimizer(self) -> None:
        """Background service for ML-based resource optimization."""
        while not self._shutdown_event.is_set():
            try:
                if self.adaptive_scheduling:
                    # Analyze performance patterns
                    await self._optimize_resource_allocation()
                
                await asyncio.sleep(30)  # Optimize every 30 seconds
                
            except Exception as e:
                logging.error(f"Error in resource optimizer: {e}")
                await asyncio.sleep(60)
    
    async def _failure_recovery_service(self) -> None:
        """Background service for automatic failure recovery."""
        while not self._shutdown_event.is_set():
            try:
                # Process retry queues
                current_time = time.time()
                for workflow_id, retry_queue in self.retry_queues.items():
                    while retry_queue and retry_queue[0][1] <= current_time:
                        task_id, _ = retry_queue.popleft()
                        workflow = self.workflows.get(workflow_id)
                        if workflow and task_id in workflow.tasks:
                            task = workflow.tasks[task_id]
                            task.status = TaskStatus.WAITING
                            logging.info(f"Retrying task {task_id}")
                
                await asyncio.sleep(1)
                
            except Exception as e:
                logging.error(f"Error in failure recovery service: {e}")
                await asyncio.sleep(5)
    
    async def _optimize_resource_allocation(self) -> None:
        """Use ML to optimize resource allocation based on historical performance."""
        # Analyze performance patterns
        for agent_type, durations in self.performance_history.items():
            if len(durations) >= 10:  # Need sufficient data
                avg_duration = sum(durations[-10:]) / 10
                # Adjust resource allocation based on performance
                await self.resource_manager.update_allocation_strategy(
                    agent_type, avg_duration
                )
    
    def _validate_workflow(self, workflow: Workflow) -> bool:
        """Validate workflow for cycles and consistency."""
        # Check for circular dependencies
        graph = workflow.get_dependency_graph()
        visited = set()
        rec_stack = set()
        
        def has_cycle(node):
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in graph.get(node, set()):
                if neighbor not in visited:
                    if has_cycle(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for task_id in workflow.tasks:
            if task_id not in visited:
                if has_cycle(task_id):
                    logging.error(f"Circular dependency detected in workflow {workflow.id}")
                    return False
        
        return True
    
    async def _cancel_workflow(self, workflow_id: str, reason: str) -> None:
        """Cancel a running workflow."""
        if workflow_id in self.workflows:
            workflow = self.workflows[workflow_id]
            workflow.status = WorkflowStatus.CANCELLED
            workflow.completed_at = datetime.now()
            self.active_workflows.discard(workflow_id)
            
            await self._emit_event('workflow_cancelled', {
                'workflow_id': workflow_id,
                'reason': reason
            })
            
            logging.info(f"Cancelled workflow {workflow_id}: {reason}")
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit workflow events to registered handlers."""
        for handler in self.event_handlers.get(event_type, []):
            try:
                await handler(data)
            except Exception as e:
                logging.error(f"Error in event handler for {event_type}: {e}")
    
    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register an event handler for workflow events."""
        self.event_handlers[event_type].append(handler)
    
    async def get_workflow_status(self, workflow_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a workflow."""
        if workflow_id not in self.workflows:
            return None
        
        workflow = self.workflows[workflow_id]
        return {
            'id': workflow.id,
            'name': workflow.name,
            'status': workflow.status.value,
            'progress': workflow.progress,
            'created_at': workflow.created_at.isoformat(),
            'started_at': workflow.started_at.isoformat() if workflow.started_at else None,
            'completed_at': workflow.completed_at.isoformat() if workflow.completed_at else None,
            'duration': workflow.duration.total_seconds() if workflow.duration else None,
            'task_count': len(workflow.tasks),
            'tasks': {
                task_id: {
                    'name': task.name,
                    'status': task.status.value,
                    'agent_type': task.agent_type.value,
                    'start_time': task.start_time.isoformat() if task.start_time else None,
                    'end_time': task.end_time.isoformat() if task.end_time else None,
                    'duration': task.duration.total_seconds() if task.duration else None,
                    'retry_count': task.retry_count,
                    'error': task.error
                }
                for task_id, task in workflow.tasks.items()
            }
        }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the workflow engine."""
        logging.info("Shutting down WorkflowEngine...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel all background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for background tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Cancel active workflows
        for workflow_id in list(self.active_workflows):
            await self._cancel_workflow(workflow_id, "System shutdown")
        
        # Shutdown executor
        self.executor.shutdown(wait=True)
        
        logging.info("WorkflowEngine shutdown complete")


class CircuitBreaker:
    """Circuit breaker for fault tolerance."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open
    
    def record_failure(self) -> None:
        """Record a failure."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
    
    def record_success(self) -> None:
        """Record a success."""
        self.failure_count = 0
        self.state = "closed"
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == "closed":
            return True
        
        if self.state == "open":
            if (time.time() - self.last_failure_time) > self.recovery_timeout:
                self.state = "half-open"
                return True
            return False
        
        # half-open state
        return True

