#!/usr/bin/env python
"""
Execution Planner

This module implements intelligent execution planning for multi-agent workflows
with advanced dependency resolution, optimization algorithms, and adaptive
scheduling capabilities.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Union, Tuple
from datetime import datetime, timedelta
import json
import threading
from collections import defaultdict, deque
import heapq
import networkx as nx
import math


class PlanningStrategy(Enum):
    """Execution planning strategies."""
    TOPOLOGICAL = "topological"
    CRITICAL_PATH = "critical_path"
    RESOURCE_AWARE = "resource_aware"
    ML_OPTIMIZED = "ml_optimized"
    ADAPTIVE = "adaptive"


class OptimizationObjective(Enum):
    """Optimization objectives for execution planning."""
    MINIMIZE_TIME = "minimize_time"
    MINIMIZE_COST = "minimize_cost"
    MAXIMIZE_THROUGHPUT = "maximize_throughput"
    BALANCE_LOAD = "balance_load"
    MINIMIZE_RESOURCE_USAGE = "minimize_resource_usage"


@dataclass
class ExecutionStep:
    """Represents a single execution step in a plan."""
    id: str
    task_id: str
    agent_type: str
    estimated_duration: float
    resource_requirements: Dict[str, float]
    dependencies: Set[str] = field(default_factory=set)
    earliest_start: float = 0.0
    latest_start: float = float('inf')
    slack: float = 0.0
    priority: int = 0
    
    @property
    def is_critical(self) -> bool:
        """Check if this step is on the critical path."""
        return self.slack <= 0.001  # Small epsilon for floating point comparison


@dataclass
class ExecutionPlan:
    """Represents a complete execution plan for a workflow."""
    id: str
    workflow_id: str
    steps: Dict[str, ExecutionStep] = field(default_factory=dict)
    dependency_graph: nx.DiGraph = field(default_factory=nx.DiGraph)
    critical_path: List[str] = field(default_factory=list)
    estimated_total_duration: float = 0.0
    estimated_cost: float = 0.0
    resource_profile: Dict[str, List[Tuple[float, float]]] = field(default_factory=dict)
    optimization_objective: OptimizationObjective = OptimizationObjective.MINIMIZE_TIME
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_step(self, step: ExecutionStep) -> None:
        """Add an execution step to the plan."""
        self.steps[step.id] = step
        self.dependency_graph.add_node(step.id, step=step)
        
        # Add dependency edges
        for dep_id in step.dependencies:
            if dep_id in self.steps:
                self.dependency_graph.add_edge(dep_id, step.id)
    
    def get_ready_steps(self, completed_steps: Set[str]) -> List[ExecutionStep]:
        """Get steps that are ready to execute."""
        ready_steps = []
        for step_id, step in self.steps.items():
            if (step_id not in completed_steps and 
                step.dependencies.issubset(completed_steps)):
                ready_steps.append(step)
        return ready_steps
    
    def get_parallel_groups(self) -> List[List[str]]:
        """Get groups of steps that can be executed in parallel."""
        # Topological sort with level grouping
        levels = []
        in_degree = {node: self.dependency_graph.in_degree(node) for node in self.dependency_graph.nodes()}
        queue = deque([node for node, degree in in_degree.items() if degree == 0])
        
        while queue:
            level = []
            for _ in range(len(queue)):
                node = queue.popleft()
                level.append(node)
                
                for successor in self.dependency_graph.successors(node):
                    in_degree[successor] -= 1
                    if in_degree[successor] == 0:
                        queue.append(successor)
            
            if level:
                levels.append(level)
        
        return levels
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plan to dictionary representation."""
        return {
            'id': self.id,
            'workflow_id': self.workflow_id,
            'steps': {
                step_id: {
                    'task_id': step.task_id,
                    'agent_type': step.agent_type,
                    'estimated_duration': step.estimated_duration,
                    'resource_requirements': step.resource_requirements,
                    'dependencies': list(step.dependencies),
                    'earliest_start': step.earliest_start,
                    'latest_start': step.latest_start,
                    'slack': step.slack,
                    'priority': step.priority,
                    'is_critical': step.is_critical
                }
                for step_id, step in self.steps.items()
            },
            'critical_path': self.critical_path,
            'estimated_total_duration': self.estimated_total_duration,
            'estimated_cost': self.estimated_cost,
            'optimization_objective': self.optimization_objective.value,
            'created_at': self.created_at.isoformat()
        }


class MLPlanningOptimizer:
    """Machine learning-based execution planning optimizer."""
    
    def __init__(self):
        self.execution_history: List[Dict[str, Any]] = []
        self.performance_models: Dict[str, Any] = {}
        self.duration_predictions: Dict[str, List[float]] = defaultdict(list)
        self.resource_predictions: Dict[str, List[float]] = defaultdict(list)
    
    def record_execution(self, 
                        plan: ExecutionPlan,
                        actual_duration: float,
                        actual_cost: float,
                        resource_usage: Dict[str, float]) -> None:
        """Record execution data for learning."""
        record = {
            'plan_id': plan.id,
            'workflow_id': plan.workflow_id,
            'estimated_duration': plan.estimated_total_duration,
            'actual_duration': actual_duration,
            'estimated_cost': plan.estimated_cost,
            'actual_cost': actual_cost,
            'resource_usage': resource_usage,
            'step_count': len(plan.steps),
            'critical_path_length': len(plan.critical_path),
            'timestamp': datetime.now().isoformat()
        }
        
        self.execution_history.append(record)
        
        # Keep only recent history
        if len(self.execution_history) > 1000:
            self.execution_history = self.execution_history[-1000:]
    
    def predict_duration(self, agent_type: str, task_complexity: float) -> float:
        """Predict task duration based on historical data."""
        key = f"{agent_type}_duration"
        historical_durations = self.duration_predictions.get(key, [])
        
        if not historical_durations:
            # Default estimates based on agent type
            defaults = {
                'planner': 30.0,
                'coder': 120.0,
                'tester': 60.0,
                'reviewer': 45.0,
                'deployer': 90.0
            }
            return defaults.get(agent_type, 60.0) * task_complexity
        
        # Simple prediction based on historical average with complexity factor
        avg_duration = sum(historical_durations) / len(historical_durations)
        return avg_duration * task_complexity
    
    def predict_resource_usage(self, agent_type: str, task_complexity: float) -> Dict[str, float]:
        """Predict resource usage based on historical data."""
        # Simplified prediction - in practice, this would use sophisticated ML models
        base_resources = {
            'planner': {'cpu': 0.5, 'memory': 1.0},
            'coder': {'cpu': 2.0, 'memory': 4.0},
            'tester': {'cpu': 1.5, 'memory': 2.0},
            'reviewer': {'cpu': 1.0, 'memory': 2.0},
            'deployer': {'cpu': 1.0, 'memory': 1.5}
        }
        
        base = base_resources.get(agent_type, {'cpu': 1.0, 'memory': 2.0})
        return {resource: amount * task_complexity for resource, amount in base.items()}
    
    def optimize_plan(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Optimize execution plan using ML insights."""
        # Update duration estimates based on predictions
        for step in plan.steps.values():
            task_complexity = self._estimate_task_complexity(step)
            predicted_duration = self.predict_duration(step.agent_type, task_complexity)
            step.estimated_duration = predicted_duration
            
            # Update resource requirements
            predicted_resources = self.predict_resource_usage(step.agent_type, task_complexity)
            step.resource_requirements.update(predicted_resources)
        
        return plan
    
    def _estimate_task_complexity(self, step: ExecutionStep) -> float:
        """Estimate task complexity based on various factors."""
        # Simplified complexity estimation
        base_complexity = 1.0
        
        # Factor in dependencies
        dependency_factor = 1.0 + (len(step.dependencies) * 0.1)
        
        # Factor in resource requirements
        resource_factor = 1.0 + sum(step.resource_requirements.values()) * 0.05
        
        return base_complexity * dependency_factor * resource_factor


class ExecutionPlanner:
    """
    Advanced execution planner with features:
    - Multiple planning strategies and optimization algorithms
    - Critical path analysis and resource-aware scheduling
    - ML-based duration and resource prediction
    - Adaptive planning based on execution feedback
    - Multi-objective optimization
    """
    
    def __init__(self, 
                 strategy: PlanningStrategy = PlanningStrategy.ML_OPTIMIZED,
                 enable_ml_optimization: bool = True):
        """Initialize the execution planner."""
        self.strategy = strategy
        self.enable_ml_optimization = enable_ml_optimization
        
        # ML optimizer
        self.ml_optimizer = MLPlanningOptimizer() if enable_ml_optimization else None
        
        # Planning cache
        self.plan_cache: Dict[str, ExecutionPlan] = {}
        
        # Performance tracking
        self.planning_metrics: Dict[str, List[float]] = defaultdict(list)
        
        logging.info(f"ExecutionPlanner initialized with {strategy.value} strategy")
    
    async def create_plan(self, workflow: Any, 
                         optimization_objective: OptimizationObjective = OptimizationObjective.MINIMIZE_TIME) -> ExecutionPlan:
        """
        Create an optimized execution plan for a workflow.
        
        Args:
            workflow: Workflow object to plan
            optimization_objective: Optimization objective
            
        Returns:
            Optimized execution plan
        """
        start_time = time.time()
        
        # Create initial plan
        plan = ExecutionPlan(
            id=str(uuid.uuid4()),
            workflow_id=workflow.id,
            optimization_objective=optimization_objective
        )
        
        # Convert workflow tasks to execution steps
        for task_id, task in workflow.tasks.items():
            step = ExecutionStep(
                id=str(uuid.uuid4()),
                task_id=task_id,
                agent_type=task.agent_type.value,
                estimated_duration=self._estimate_duration(task),
                resource_requirements=self._estimate_resources(task),
                dependencies=task.dependencies.copy(),
                priority=task.priority
            )
            plan.add_step(step)
        
        # Apply planning strategy
        if self.strategy == PlanningStrategy.CRITICAL_PATH:
            plan = await self._critical_path_planning(plan)
        elif self.strategy == PlanningStrategy.RESOURCE_AWARE:
            plan = await self._resource_aware_planning(plan)
        elif self.strategy == PlanningStrategy.ML_OPTIMIZED:
            plan = await self._ml_optimized_planning(plan)
        elif self.strategy == PlanningStrategy.ADAPTIVE:
            plan = await self._adaptive_planning(plan)
        else:
            plan = await self._topological_planning(plan)
        
        # Apply optimization
        plan = await self._optimize_plan(plan, optimization_objective)
        
        # Calculate final metrics
        plan.estimated_total_duration = self._calculate_total_duration(plan)
        plan.estimated_cost = self._calculate_total_cost(plan)
        plan.resource_profile = self._calculate_resource_profile(plan)
        
        # Cache plan
        self.plan_cache[plan.id] = plan
        
        # Record planning metrics
        planning_time = time.time() - start_time
        self.planning_metrics['planning_time'].append(planning_time)
        
        logging.info(f"Created execution plan {plan.id} for workflow {workflow.id} "
                    f"(duration: {plan.estimated_total_duration:.2f}s, steps: {len(plan.steps)})")
        
        return plan
    
    async def _topological_planning(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Basic topological sort planning."""
        # Ensure graph is acyclic
        if not nx.is_directed_acyclic_graph(plan.dependency_graph):
            raise ValueError("Workflow contains circular dependencies")
        
        # Perform topological sort
        topo_order = list(nx.topological_sort(plan.dependency_graph))
        
        # Assign execution order
        for i, step_id in enumerate(topo_order):
            step = plan.steps[step_id]
            step.earliest_start = i * 10.0  # Simple spacing
        
        return plan
    
    async def _critical_path_planning(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Critical path method (CPM) planning."""
        # Forward pass - calculate earliest start times
        topo_order = list(nx.topological_sort(plan.dependency_graph))
        
        for step_id in topo_order:
            step = plan.steps[step_id]
            
            # Calculate earliest start based on dependencies
            max_predecessor_finish = 0.0
            for pred_id in plan.dependency_graph.predecessors(step_id):
                pred_step = plan.steps[pred_id]
                pred_finish = pred_step.earliest_start + pred_step.estimated_duration
                max_predecessor_finish = max(max_predecessor_finish, pred_finish)
            
            step.earliest_start = max_predecessor_finish
        
        # Calculate project duration
        project_duration = max(
            step.earliest_start + step.estimated_duration
            for step in plan.steps.values()
        )
        
        # Backward pass - calculate latest start times
        for step_id in reversed(topo_order):
            step = plan.steps[step_id]
            
            # Calculate latest start based on successors
            min_successor_start = project_duration - step.estimated_duration
            for succ_id in plan.dependency_graph.successors(step_id):
                succ_step = plan.steps[succ_id]
                min_successor_start = min(min_successor_start, succ_step.latest_start)
            
            step.latest_start = min_successor_start
            step.slack = step.latest_start - step.earliest_start
        
        # Identify critical path
        critical_steps = [step_id for step_id, step in plan.steps.items() if step.is_critical]
        plan.critical_path = self._find_critical_path(plan, critical_steps)
        
        return plan
    
    async def _resource_aware_planning(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Resource-aware planning with resource leveling."""
        # Start with critical path planning
        plan = await self._critical_path_planning(plan)
        
        # Apply resource leveling
        plan = self._level_resources(plan)
        
        return plan
    
    async def _ml_optimized_planning(self, plan: ExecutionPlan) -> ExecutionPlan:
        """ML-optimized planning using historical data."""
        if self.ml_optimizer:
            # Apply ML optimizations
            plan = self.ml_optimizer.optimize_plan(plan)
        
        # Fall back to critical path planning
        plan = await self._critical_path_planning(plan)
        
        return plan
    
    async def _adaptive_planning(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Adaptive planning that combines multiple strategies."""
        # Try different strategies and pick the best
        strategies = [
            self._critical_path_planning,
            self._resource_aware_planning,
            self._ml_optimized_planning
        ]
        
        best_plan = None
        best_score = float('inf')
        
        for strategy in strategies:
            try:
                candidate_plan = await strategy(plan.copy() if hasattr(plan, 'copy') else plan)
                score = self._evaluate_plan(candidate_plan)
                
                if score < best_score:
                    best_score = score
                    best_plan = candidate_plan
            except Exception as e:
                logging.warning(f"Strategy failed: {e}")
                continue
        
        return best_plan or plan
    
    def _level_resources(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Apply resource leveling to smooth resource usage."""
        # Get parallel execution groups
        parallel_groups = plan.get_parallel_groups()
        
        # Track resource usage over time
        resource_timeline = defaultdict(list)
        
        for group in parallel_groups:
            group_start_time = min(plan.steps[step_id].earliest_start for step_id in group)
            
            # Sort steps in group by priority and resource requirements
            sorted_steps = sorted(
                group,
                key=lambda step_id: (
                    -plan.steps[step_id].priority,
                    sum(plan.steps[step_id].resource_requirements.values())
                )
            )
            
            # Schedule steps with resource constraints
            current_time = group_start_time
            for step_id in sorted_steps:
                step = plan.steps[step_id]
                
                # Find earliest time when resources are available
                while self._check_resource_conflict(step, current_time, resource_timeline):
                    current_time += 1.0
                
                # Schedule step
                step.earliest_start = current_time
                
                # Update resource timeline
                for resource, amount in step.resource_requirements.items():
                    resource_timeline[resource].append((current_time, current_time + step.estimated_duration, amount))
        
        return plan
    
    def _check_resource_conflict(self, step: ExecutionStep, start_time: float, 
                               resource_timeline: Dict[str, List[Tuple[float, float, float]]]) -> bool:
        """Check if scheduling a step at a given time would cause resource conflicts."""
        end_time = start_time + step.estimated_duration
        
        for resource, required_amount in step.resource_requirements.items():
            total_usage = 0.0
            
            for usage_start, usage_end, usage_amount in resource_timeline.get(resource, []):
                # Check for overlap
                if not (end_time <= usage_start or start_time >= usage_end):
                    total_usage += usage_amount
            
            # Assume resource limit of 10.0 for each resource type
            if total_usage + required_amount > 10.0:
                return True
        
        return False
    
    def _find_critical_path(self, plan: ExecutionPlan, critical_steps: List[str]) -> List[str]:
        """Find the critical path through the workflow."""
        if not critical_steps:
            return []
        
        # Build subgraph of critical steps
        critical_graph = plan.dependency_graph.subgraph(critical_steps)
        
        # Find longest path (critical path)
        try:
            # NetworkX doesn't have longest path for DAGs directly, so we use negative weights
            neg_graph = nx.DiGraph()
            for node in critical_graph.nodes():
                neg_graph.add_node(node)
            
            for u, v in critical_graph.edges():
                weight = -plan.steps[u].estimated_duration
                neg_graph.add_edge(u, v, weight=weight)
            
            # Find shortest path in negative graph (= longest path in original)
            if neg_graph.nodes():
                # Find start nodes (no predecessors)
                start_nodes = [n for n in neg_graph.nodes() if neg_graph.in_degree(n) == 0]
                # Find end nodes (no successors)
                end_nodes = [n for n in neg_graph.nodes() if neg_graph.out_degree(n) == 0]
                
                longest_path = []
                for start in start_nodes:
                    for end in end_nodes:
                        try:
                            path = nx.shortest_path(neg_graph, start, end, weight='weight')
                            if len(path) > len(longest_path):
                                longest_path = path
                        except nx.NetworkXNoPath:
                            continue
                
                return longest_path
        except Exception as e:
            logging.warning(f"Error finding critical path: {e}")
        
        return critical_steps
    
    async def _optimize_plan(self, plan: ExecutionPlan, objective: OptimizationObjective) -> ExecutionPlan:
        """Apply optimization based on the specified objective."""
        if objective == OptimizationObjective.MINIMIZE_TIME:
            return self._optimize_for_time(plan)
        elif objective == OptimizationObjective.MINIMIZE_COST:
            return self._optimize_for_cost(plan)
        elif objective == OptimizationObjective.MAXIMIZE_THROUGHPUT:
            return self._optimize_for_throughput(plan)
        elif objective == OptimizationObjective.BALANCE_LOAD:
            return self._optimize_for_load_balance(plan)
        elif objective == OptimizationObjective.MINIMIZE_RESOURCE_USAGE:
            return self._optimize_for_resource_usage(plan)
        else:
            return plan
    
    def _optimize_for_time(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Optimize plan to minimize total execution time."""
        # Focus on critical path optimization
        for step_id in plan.critical_path:
            step = plan.steps[step_id]
            # Could apply techniques like task splitting, resource allocation, etc.
            # For now, just ensure optimal scheduling
            pass
        
        return plan
    
    def _optimize_for_cost(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Optimize plan to minimize cost."""
        # Prioritize cheaper resources and longer execution times if cost-effective
        for step in plan.steps.values():
            # Adjust resource requirements to use cheaper alternatives
            pass
        
        return plan
    
    def _optimize_for_throughput(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Optimize plan to maximize throughput."""
        # Maximize parallel execution
        parallel_groups = plan.get_parallel_groups()
        
        # Try to balance group sizes
        for group in parallel_groups:
            # Could implement load balancing within groups
            pass
        
        return plan
    
    def _optimize_for_load_balance(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Optimize plan for load balancing."""
        # Distribute work evenly across available resources
        return self._level_resources(plan)
    
    def _optimize_for_resource_usage(self, plan: ExecutionPlan) -> ExecutionPlan:
        """Optimize plan to minimize resource usage."""
        # Reduce resource requirements where possible
        for step in plan.steps.values():
            # Could implement resource optimization techniques
            pass
        
        return plan
    
    def _estimate_duration(self, task: Any) -> float:
        """Estimate task duration."""
        if self.ml_optimizer:
            # Use ML prediction if available
            complexity = 1.0  # Would be calculated based on task parameters
            return self.ml_optimizer.predict_duration(task.agent_type.value, complexity)
        
        # Default estimates
        defaults = {
            'planner': 30.0,
            'coder': 120.0,
            'tester': 60.0,
            'reviewer': 45.0,
            'deployer': 90.0
        }
        return defaults.get(task.agent_type.value, 60.0)
    
    def _estimate_resources(self, task: Any) -> Dict[str, float]:
        """Estimate resource requirements for a task."""
        if self.ml_optimizer:
            # Use ML prediction if available
            complexity = 1.0  # Would be calculated based on task parameters
            return self.ml_optimizer.predict_resource_usage(task.agent_type.value, complexity)
        
        # Default resource estimates
        defaults = {
            'planner': {'cpu': 0.5, 'memory': 1.0},
            'coder': {'cpu': 2.0, 'memory': 4.0},
            'tester': {'cpu': 1.5, 'memory': 2.0},
            'reviewer': {'cpu': 1.0, 'memory': 2.0},
            'deployer': {'cpu': 1.0, 'memory': 1.5}
        }
        return defaults.get(task.agent_type.value, {'cpu': 1.0, 'memory': 2.0})
    
    def _calculate_total_duration(self, plan: ExecutionPlan) -> float:
        """Calculate total execution duration for the plan."""
        if not plan.steps:
            return 0.0
        
        return max(
            step.earliest_start + step.estimated_duration
            for step in plan.steps.values()
        )
    
    def _calculate_total_cost(self, plan: ExecutionPlan) -> float:
        """Calculate total cost for the plan."""
        # Simplified cost calculation
        total_cost = 0.0
        
        for step in plan.steps.values():
            # Cost based on duration and resource usage
            resource_cost = sum(step.resource_requirements.values()) * 0.1  # $0.1 per resource unit
            duration_cost = step.estimated_duration * 0.01  # $0.01 per second
            total_cost += resource_cost + duration_cost
        
        return total_cost
    
    def _calculate_resource_profile(self, plan: ExecutionPlan) -> Dict[str, List[Tuple[float, float]]]:
        """Calculate resource usage profile over time."""
        profile = defaultdict(list)
        
        for step in plan.steps.values():
            start_time = step.earliest_start
            end_time = start_time + step.estimated_duration
            
            for resource, amount in step.resource_requirements.items():
                profile[resource].append((start_time, end_time, amount))
        
        # Sort by start time
        for resource in profile:
            profile[resource].sort(key=lambda x: x[0])
        
        return dict(profile)
    
    def _evaluate_plan(self, plan: ExecutionPlan) -> float:
        """Evaluate plan quality (lower is better)."""
        # Multi-objective evaluation
        time_score = plan.estimated_total_duration
        cost_score = plan.estimated_cost
        resource_score = sum(
            sum(amounts for _, _, amounts in timeline)
            for timeline in plan.resource_profile.values()
        )
        
        # Weighted combination
        return time_score * 0.5 + cost_score * 0.3 + resource_score * 0.2
    
    async def update_plan(self, plan_id: str, execution_feedback: Dict[str, Any]) -> Optional[ExecutionPlan]:
        """Update a plan based on execution feedback."""
        if plan_id not in self.plan_cache:
            return None
        
        plan = self.plan_cache[plan_id]
        
        # Update ML models with feedback
        if self.ml_optimizer and 'actual_duration' in execution_feedback:
            self.ml_optimizer.record_execution(
                plan,
                execution_feedback['actual_duration'],
                execution_feedback.get('actual_cost', 0.0),
                execution_feedback.get('resource_usage', {})
            )
        
        # Could implement plan adaptation based on feedback
        return plan
    
    def get_planning_metrics(self) -> Dict[str, Any]:
        """Get planning performance metrics."""
        metrics = {}
        
        for metric_name, values in self.planning_metrics.items():
            if values:
                metrics[metric_name] = {
                    'count': len(values),
                    'average': sum(values) / len(values),
                    'min': min(values),
                    'max': max(values)
                }
        
        return metrics

