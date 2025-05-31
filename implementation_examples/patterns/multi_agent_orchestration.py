#!/usr/bin/env python
"""
Multi-Agent Orchestration Patterns

This module demonstrates advanced patterns for coordinating multiple Codegen agents
to work together on complex tasks, including workflow orchestration, task delegation,
and result aggregation.
"""

import asyncio
import time
import json
from typing import List, Dict, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import logging

from codegen import Agent
from implementation_examples.patterns.enhanced_agent import EnhancedAgent, TaskResult


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class WorkflowTask:
    """Represents a task in a workflow"""
    id: str
    name: str
    agent_type: str
    prompt: str
    dependencies: List[str] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    status: TaskStatus = TaskStatus.PENDING
    result: Optional[str] = None
    error: Optional[str] = None
    execution_time: float = 0.0
    retry_count: int = 0


@dataclass
class WorkflowDefinition:
    """Defines a complete workflow"""
    id: str
    name: str
    description: str
    tasks: List[WorkflowTask]
    global_context: Dict[str, Any] = field(default_factory=dict)


class AgentRole(ABC):
    """Abstract base class for specialized agent roles"""
    
    def __init__(self, name: str, agent: EnhancedAgent):
        self.name = name
        self.agent = agent
        self.logger = logging.getLogger(f"{__name__}.{name}")
    
    @abstractmethod
    def get_system_prompt(self) -> str:
        """Return the system prompt for this agent role"""
        pass
    
    def execute_task(self, task: WorkflowTask, workflow_context: Dict[str, Any]) -> TaskResult:
        """Execute a task with role-specific enhancements"""
        # Combine task context with workflow context
        combined_context = {**workflow_context, **task.context}
        
        # Add role-specific system prompt
        enhanced_prompt = f"{self.get_system_prompt()}\n\n{task.prompt}"
        
        self.logger.info(f"Executing task {task.id}: {task.name}")
        return self.agent.run_with_retry(enhanced_prompt, combined_context)


class CodeGeneratorAgent(AgentRole):
    """Specialized agent for code generation tasks"""
    
    def get_system_prompt(self) -> str:
        return """You are a senior software engineer specializing in code generation.
        
        Guidelines:
        - Write clean, maintainable, and well-documented code
        - Follow language-specific best practices and conventions
        - Include appropriate error handling and edge case considerations
        - Add comprehensive docstrings and comments
        - Consider performance and security implications
        """


class CodeReviewAgent(AgentRole):
    """Specialized agent for code review tasks"""
    
    def get_system_prompt(self) -> str:
        return """You are a senior software engineer conducting code reviews.
        
        Focus areas:
        - Code quality and maintainability
        - Security vulnerabilities and best practices
        - Performance optimization opportunities
        - Test coverage and testing strategies
        - Documentation completeness and clarity
        - Adherence to coding standards and conventions
        
        Provide specific, actionable feedback with examples.
        """


class TestGeneratorAgent(AgentRole):
    """Specialized agent for test generation"""
    
    def get_system_prompt(self) -> str:
        return """You are a QA engineer specializing in test automation.
        
        Test generation guidelines:
        - Create comprehensive unit tests covering all code paths
        - Include edge cases and error conditions
        - Write integration tests for component interactions
        - Follow testing best practices (AAA pattern, descriptive names)
        - Ensure tests are maintainable and reliable
        - Include performance and security test cases where relevant
        """


class DocumentationAgent(AgentRole):
    """Specialized agent for documentation generation"""
    
    def get_system_prompt(self) -> str:
        return """You are a technical writer specializing in software documentation.
        
        Documentation standards:
        - Write clear, concise, and comprehensive documentation
        - Include usage examples and code snippets
        - Structure information logically with proper headings
        - Add diagrams and visual aids where helpful
        - Consider different audience levels (beginner to advanced)
        - Ensure documentation is maintainable and up-to-date
        """


class WorkflowOrchestrator:
    """Orchestrates multi-agent workflows"""
    
    def __init__(self, token: str, org_id: int):
        self.token = token
        self.org_id = org_id
        self.agents = {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize specialized agents
        self._initialize_agents()
    
    def _initialize_agents(self):
        """Initialize specialized agent roles"""
        base_agent = EnhancedAgent(self.token, self.org_id)
        
        self.agents = {
            "code_generator": CodeGeneratorAgent("CodeGenerator", base_agent),
            "code_reviewer": CodeReviewAgent("CodeReviewer", base_agent),
            "test_generator": TestGeneratorAgent("TestGenerator", base_agent),
            "documentation": DocumentationAgent("Documentation", base_agent)
        }
    
    def execute_workflow(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Execute a complete workflow"""
        self.logger.info(f"Starting workflow: {workflow.name}")
        start_time = time.time()
        
        # Track task execution
        task_results = {}
        execution_order = self._calculate_execution_order(workflow.tasks)
        
        try:
            for task in execution_order:
                # Check dependencies
                if not self._dependencies_satisfied(task, task_results):
                    raise Exception(f"Dependencies not satisfied for task {task.id}")
                
                # Update task context with dependency results
                self._update_task_context(task, task_results, workflow.global_context)
                
                # Execute task
                task.status = TaskStatus.RUNNING
                agent = self.agents.get(task.agent_type)
                
                if not agent:
                    raise Exception(f"Unknown agent type: {task.agent_type}")
                
                result = agent.execute_task(task, workflow.global_context)
                
                # Update task status
                if result.status == "completed":
                    task.status = TaskStatus.COMPLETED
                    task.result = result.result
                else:
                    task.status = TaskStatus.FAILED
                    task.error = result.error
                
                task.execution_time = result.execution_time
                task.retry_count = result.retry_count
                task_results[task.id] = task
                
                self.logger.info(f"Task {task.id} completed with status: {task.status}")
        
        except Exception as e:
            self.logger.error(f"Workflow failed: {e}")
            return {
                "status": "failed",
                "error": str(e),
                "execution_time": time.time() - start_time,
                "completed_tasks": len([t for t in task_results.values() if t.status == TaskStatus.COMPLETED]),
                "total_tasks": len(workflow.tasks)
            }
        
        execution_time = time.time() - start_time
        
        return {
            "status": "completed",
            "execution_time": execution_time,
            "tasks": task_results,
            "summary": self._generate_workflow_summary(task_results)
        }
    
    def _calculate_execution_order(self, tasks: List[WorkflowTask]) -> List[WorkflowTask]:
        """Calculate task execution order based on dependencies"""
        # Simple topological sort
        task_map = {task.id: task for task in tasks}
        visited = set()
        temp_visited = set()
        order = []
        
        def visit(task_id: str):
            if task_id in temp_visited:
                raise Exception(f"Circular dependency detected involving task {task_id}")
            if task_id in visited:
                return
            
            temp_visited.add(task_id)
            task = task_map[task_id]
            
            for dep_id in task.dependencies:
                if dep_id not in task_map:
                    raise Exception(f"Unknown dependency {dep_id} for task {task_id}")
                visit(dep_id)
            
            temp_visited.remove(task_id)
            visited.add(task_id)
            order.append(task)
        
        for task in tasks:
            if task.id not in visited:
                visit(task.id)
        
        return order
    
    def _dependencies_satisfied(self, task: WorkflowTask, completed_tasks: Dict[str, WorkflowTask]) -> bool:
        """Check if all task dependencies are satisfied"""
        for dep_id in task.dependencies:
            if dep_id not in completed_tasks or completed_tasks[dep_id].status != TaskStatus.COMPLETED:
                return False
        return True
    
    def _update_task_context(self, task: WorkflowTask, completed_tasks: Dict[str, WorkflowTask], global_context: Dict[str, Any]):
        """Update task context with results from dependency tasks"""
        for dep_id in task.dependencies:
            if dep_id in completed_tasks:
                dep_task = completed_tasks[dep_id]
                task.context[f"dependency_{dep_id}_result"] = dep_task.result
    
    def _generate_workflow_summary(self, task_results: Dict[str, WorkflowTask]) -> Dict[str, Any]:
        """Generate a summary of workflow execution"""
        completed = len([t for t in task_results.values() if t.status == TaskStatus.COMPLETED])
        failed = len([t for t in task_results.values() if t.status == TaskStatus.FAILED])
        total_time = sum(t.execution_time for t in task_results.values())
        
        return {
            "total_tasks": len(task_results),
            "completed_tasks": completed,
            "failed_tasks": failed,
            "success_rate": completed / len(task_results) * 100,
            "total_execution_time": total_time,
            "average_task_time": total_time / len(task_results) if task_results else 0
        }


class WorkflowBuilder:
    """Builder pattern for creating workflows"""
    
    def __init__(self, workflow_id: str, name: str, description: str = ""):
        self.workflow = WorkflowDefinition(
            id=workflow_id,
            name=name,
            description=description,
            tasks=[]
        )
    
    def add_task(self, task_id: str, name: str, agent_type: str, prompt: str, 
                 dependencies: List[str] = None, context: Dict[str, Any] = None) -> 'WorkflowBuilder':
        """Add a task to the workflow"""
        task = WorkflowTask(
            id=task_id,
            name=name,
            agent_type=agent_type,
            prompt=prompt,
            dependencies=dependencies or [],
            context=context or {}
        )
        self.workflow.tasks.append(task)
        return self
    
    def set_global_context(self, context: Dict[str, Any]) -> 'WorkflowBuilder':
        """Set global context for the workflow"""
        self.workflow.global_context = context
        return self
    
    def build(self) -> WorkflowDefinition:
        """Build and return the workflow definition"""
        return self.workflow


# Predefined workflow templates
class WorkflowTemplates:
    """Collection of predefined workflow templates"""
    
    @staticmethod
    def feature_development_workflow(feature_name: str, requirements: str) -> WorkflowDefinition:
        """Complete feature development workflow"""
        return (WorkflowBuilder("feature_dev", f"Feature Development: {feature_name}")
                .add_task(
                    "design", "Design Architecture", "code_generator",
                    f"Design the architecture for feature: {feature_name}\n\nRequirements:\n{requirements}\n\nProvide a detailed design including components, interfaces, and data flow."
                )
                .add_task(
                    "implement", "Implement Code", "code_generator",
                    f"Implement the feature based on the design.\n\nFeature: {feature_name}\nRequirements: {requirements}",
                    dependencies=["design"]
                )
                .add_task(
                    "review", "Code Review", "code_reviewer",
                    "Review the implemented code for quality, security, and best practices.",
                    dependencies=["implement"]
                )
                .add_task(
                    "tests", "Generate Tests", "test_generator",
                    "Create comprehensive tests for the implemented feature.",
                    dependencies=["implement"]
                )
                .add_task(
                    "docs", "Generate Documentation", "documentation",
                    "Create user and developer documentation for the feature.",
                    dependencies=["implement", "tests"]
                )
                .set_global_context({
                    "feature_name": feature_name,
                    "requirements": requirements,
                    "language": "python",
                    "framework": "fastapi"
                })
                .build())
    
    @staticmethod
    def code_refactoring_workflow(code_to_refactor: str, refactoring_goals: str) -> WorkflowDefinition:
        """Code refactoring workflow"""
        return (WorkflowBuilder("refactoring", "Code Refactoring")
                .add_task(
                    "analyze", "Analyze Code", "code_reviewer",
                    f"Analyze the following code and identify refactoring opportunities:\n\n{code_to_refactor}\n\nGoals: {refactoring_goals}"
                )
                .add_task(
                    "refactor", "Refactor Code", "code_generator",
                    f"Refactor the code based on the analysis.\n\nOriginal code:\n{code_to_refactor}\n\nGoals: {refactoring_goals}",
                    dependencies=["analyze"]
                )
                .add_task(
                    "test_refactored", "Test Refactored Code", "test_generator",
                    "Create tests to verify the refactored code maintains the same functionality.",
                    dependencies=["refactor"]
                )
                .add_task(
                    "document_changes", "Document Changes", "documentation",
                    "Document the refactoring changes and their benefits.",
                    dependencies=["refactor"]
                )
                .set_global_context({
                    "original_code": code_to_refactor,
                    "refactoring_goals": refactoring_goals
                })
                .build())


# Example usage and demonstration
def main():
    """Demonstrate multi-agent orchestration patterns"""
    import os
    
    # Setup logging
    logging.basicConfig(level=logging.INFO)
    
    # Initialize orchestrator
    token = os.getenv("CODEGEN_TOKEN")
    if not token:
        print("Please set CODEGEN_TOKEN environment variable")
        return
    
    orchestrator = WorkflowOrchestrator(token=token, org_id=1)
    
    # Example 1: Feature development workflow
    print("=== Example 1: Feature Development Workflow ===")
    
    feature_workflow = WorkflowTemplates.feature_development_workflow(
        feature_name="User Authentication",
        requirements="""
        - JWT-based authentication
        - User registration and login endpoints
        - Password hashing with bcrypt
        - Rate limiting for login attempts
        - Email verification for new accounts
        """
    )
    
    result = orchestrator.execute_workflow(feature_workflow)
    print(f"Workflow Status: {result['status']}")
    print(f"Execution Time: {result['execution_time']:.2f}s")
    
    if result['status'] == 'completed':
        summary = result['summary']
        print(f"Tasks Completed: {summary['completed_tasks']}/{summary['total_tasks']}")
        print(f"Success Rate: {summary['success_rate']:.1f}%")
    
    # Example 2: Custom workflow
    print("\n=== Example 2: Custom Workflow ===")
    
    custom_workflow = (WorkflowBuilder("api_development", "REST API Development")
                      .add_task(
                          "spec", "API Specification", "documentation",
                          "Create an OpenAPI specification for a todo list API with CRUD operations."
                      )
                      .add_task(
                          "models", "Data Models", "code_generator",
                          "Create Pydantic models for the todo list API.",
                          dependencies=["spec"]
                      )
                      .add_task(
                          "endpoints", "API Endpoints", "code_generator",
                          "Implement FastAPI endpoints for the todo list API.",
                          dependencies=["models"]
                      )
                      .add_task(
                          "tests", "API Tests", "test_generator",
                          "Create pytest tests for all API endpoints.",
                          dependencies=["endpoints"]
                      )
                      .set_global_context({
                          "framework": "fastapi",
                          "database": "postgresql",
                          "orm": "sqlalchemy"
                      })
                      .build())
    
    result = orchestrator.execute_workflow(custom_workflow)
    print(f"Custom Workflow Status: {result['status']}")
    
    # Example 3: Parallel task execution simulation
    print("\n=== Example 3: Workflow with Parallel Tasks ===")
    
    parallel_workflow = (WorkflowBuilder("parallel_dev", "Parallel Development")
                        .add_task(
                            "frontend", "Frontend Component", "code_generator",
                            "Create a React component for user profile display."
                        )
                        .add_task(
                            "backend", "Backend API", "code_generator",
                            "Create a FastAPI endpoint for user profile data."
                        )
                        .add_task(
                            "integration", "Integration", "code_generator",
                            "Create integration code to connect frontend and backend.",
                            dependencies=["frontend", "backend"]
                        )
                        .build())
    
    result = orchestrator.execute_workflow(parallel_workflow)
    print(f"Parallel Workflow Status: {result['status']}")


if __name__ == "__main__":
    main()

