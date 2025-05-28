#!/usr/bin/env python
"""
Tests for the Workflow Engine
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
from datetime import datetime

from src.workflow_engine import WorkflowEngine, Workflow, Task, TaskStatus, WorkflowStatus
from src.agent_registry import AgentRegistry, AgentType
from src.resource_manager import ResourceManager
from src.monitoring_system import MonitoringSystem


@pytest.fixture
async def workflow_engine():
    """Create a workflow engine for testing."""
    agent_registry = Mock(spec=AgentRegistry)
    resource_manager = Mock(spec=ResourceManager)
    monitoring_system = Mock(spec=MonitoringSystem)
    
    engine = WorkflowEngine(
        agent_registry=agent_registry,
        resource_manager=resource_manager,
        monitoring_system=monitoring_system,
        max_concurrent_workflows=2
    )
    
    yield engine
    
    await engine.shutdown()


@pytest.mark.asyncio
async def test_create_workflow(workflow_engine):
    """Test workflow creation."""
    tasks_config = [
        {
            'name': 'Test Task',
            'agent_type': 'planner',
            'parameters': {'test': 'value'},
            'priority': 5
        }
    ]
    
    workflow_id = await workflow_engine.create_workflow(
        name="Test Workflow",
        description="A test workflow",
        tasks_config=tasks_config
    )
    
    assert workflow_id is not None
    assert workflow_id in workflow_engine.workflows
    
    workflow = workflow_engine.workflows[workflow_id]
    assert workflow.name == "Test Workflow"
    assert workflow.description == "A test workflow"
    assert len(workflow.tasks) == 1


@pytest.mark.asyncio
async def test_workflow_with_dependencies(workflow_engine):
    """Test workflow creation with task dependencies."""
    tasks_config = [
        {
            'id': 'task1',
            'name': 'First Task',
            'agent_type': 'planner',
            'parameters': {}
        },
        {
            'id': 'task2',
            'name': 'Second Task',
            'agent_type': 'coder',
            'parameters': {}
        }
    ]
    
    dependencies = [
        {'task': 'task2', 'depends_on': 'task1'}
    ]
    
    workflow_id = await workflow_engine.create_workflow(
        name="Dependency Test",
        description="Test workflow with dependencies",
        tasks_config=tasks_config,
        dependencies=dependencies
    )
    
    workflow = workflow_engine.workflows[workflow_id]
    assert len(workflow.tasks) == 2
    assert 'task1' in workflow.tasks['task2'].dependencies


@pytest.mark.asyncio
async def test_workflow_validation_circular_dependency(workflow_engine):
    """Test that circular dependencies are detected."""
    tasks_config = [
        {
            'id': 'task1',
            'name': 'First Task',
            'agent_type': 'planner',
            'parameters': {}
        },
        {
            'id': 'task2',
            'name': 'Second Task',
            'agent_type': 'coder',
            'parameters': {}
        }
    ]
    
    dependencies = [
        {'task': 'task1', 'depends_on': 'task2'},
        {'task': 'task2', 'depends_on': 'task1'}
    ]
    
    with pytest.raises(ValueError, match="Invalid workflow configuration"):
        await workflow_engine.create_workflow(
            name="Circular Dependency Test",
            description="Test workflow with circular dependencies",
            tasks_config=tasks_config,
            dependencies=dependencies
        )


@pytest.mark.asyncio
async def test_get_workflow_status(workflow_engine):
    """Test getting workflow status."""
    tasks_config = [
        {
            'name': 'Test Task',
            'agent_type': 'planner',
            'parameters': {}
        }
    ]
    
    workflow_id = await workflow_engine.create_workflow(
        name="Status Test",
        description="Test workflow status",
        tasks_config=tasks_config
    )
    
    status = await workflow_engine.get_workflow_status(workflow_id)
    
    assert status is not None
    assert status['id'] == workflow_id
    assert status['name'] == "Status Test"
    assert status['status'] == WorkflowStatus.PENDING.value
    assert status['progress'] == 0.0
    assert status['task_count'] == 1


@pytest.mark.asyncio
async def test_workflow_progress_calculation():
    """Test workflow progress calculation."""
    workflow = Workflow(
        id="test_workflow",
        name="Test Workflow",
        description="Test"
    )
    
    # Add tasks
    task1 = Task(
        id="task1",
        name="Task 1",
        agent_type=AgentType.PLANNER,
        parameters={}
    )
    task1.status = TaskStatus.COMPLETED
    
    task2 = Task(
        id="task2",
        name="Task 2",
        agent_type=AgentType.CODER,
        parameters={}
    )
    task2.status = TaskStatus.RUNNING
    
    workflow.add_task(task1)
    workflow.add_task(task2)
    
    # Progress should be 50% (1 out of 2 tasks completed)
    assert workflow.progress == 0.5


@pytest.mark.asyncio
async def test_task_ready_status():
    """Test task ready status calculation."""
    workflow = Workflow(
        id="test_workflow",
        name="Test Workflow",
        description="Test"
    )
    
    # Create tasks with dependencies
    task1 = Task(
        id="task1",
        name="Task 1",
        agent_type=AgentType.PLANNER,
        parameters={}
    )
    
    task2 = Task(
        id="task2",
        name="Task 2",
        agent_type=AgentType.CODER,
        parameters={},
        dependencies={'task1'}
    )
    
    workflow.add_task(task1)
    workflow.add_task(task2)
    
    # Initially, only task1 should be ready
    completed_tasks = set()
    ready_tasks = workflow.get_ready_tasks(completed_tasks)
    assert len(ready_tasks) == 1
    assert ready_tasks[0].id == "task1"
    
    # After task1 is completed, task2 should be ready
    completed_tasks.add("task1")
    ready_tasks = workflow.get_ready_tasks(completed_tasks)
    assert len(ready_tasks) == 1
    assert ready_tasks[0].id == "task2"


def test_task_duration_calculation():
    """Test task duration calculation."""
    task = Task(
        id="test_task",
        name="Test Task",
        agent_type=AgentType.PLANNER,
        parameters={}
    )
    
    # No duration when not started
    assert task.duration is None
    
    # Set start time
    task.start_time = datetime.now()
    assert task.duration is None  # Still no end time
    
    # Set end time
    task.end_time = datetime.now()
    assert task.duration is not None
    assert task.duration.total_seconds() >= 0


def test_workflow_duration_calculation():
    """Test workflow duration calculation."""
    workflow = Workflow(
        id="test_workflow",
        name="Test Workflow",
        description="Test"
    )
    
    # No duration when not started
    assert workflow.duration is None
    
    # Set start time
    workflow.started_at = datetime.now()
    assert workflow.duration is None  # Still no end time
    
    # Set end time
    workflow.completed_at = datetime.now()
    assert workflow.duration is not None
    assert workflow.duration.total_seconds() >= 0


@pytest.mark.asyncio
async def test_max_concurrent_workflows(workflow_engine):
    """Test maximum concurrent workflows limit."""
    # Set max concurrent workflows to 1 for this test
    workflow_engine.max_concurrent_workflows = 1
    
    tasks_config = [
        {
            'name': 'Test Task',
            'agent_type': 'planner',
            'parameters': {}
        }
    ]
    
    # Create first workflow
    workflow_id1 = await workflow_engine.create_workflow(
        name="Workflow 1",
        description="First workflow",
        tasks_config=tasks_config
    )
    
    # Mock the execution to not complete immediately
    workflow_engine._execute_workflow_tasks = AsyncMock(return_value=True)
    
    # Start first workflow (should succeed)
    task1 = asyncio.create_task(workflow_engine.execute_workflow(workflow_id1))
    await asyncio.sleep(0.1)  # Let it start
    
    # Create second workflow
    workflow_id2 = await workflow_engine.create_workflow(
        name="Workflow 2",
        description="Second workflow",
        tasks_config=tasks_config
    )
    
    # Try to start second workflow (should be queued/rejected)
    result2 = await workflow_engine.execute_workflow(workflow_id2)
    assert result2 is False  # Should be rejected due to limit
    
    # Clean up
    task1.cancel()
    try:
        await task1
    except asyncio.CancelledError:
        pass

