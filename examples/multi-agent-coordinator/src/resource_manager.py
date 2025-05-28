#!/usr/bin/env python
"""
Resource Manager

This module implements intelligent resource allocation and management
for multi-agent systems with ML-based optimization, load balancing,
and distributed resource coordination.
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
import math
import statistics


class ResourceType(Enum):
    """Types of resources in the system."""
    CPU = "cpu"
    MEMORY = "memory"
    GPU = "gpu"
    STORAGE = "storage"
    NETWORK = "network"
    CUSTOM = "custom"


class AllocationStrategy(Enum):
    """Resource allocation strategies."""
    FIRST_FIT = "first_fit"
    BEST_FIT = "best_fit"
    WORST_FIT = "worst_fit"
    ML_OPTIMIZED = "ml_optimized"
    PRIORITY_BASED = "priority_based"


@dataclass
class ResourceSpec:
    """Specification for a resource."""
    resource_type: ResourceType
    amount: float
    unit: str
    constraints: Dict[str, Any] = field(default_factory=dict)
    
    def __str__(self) -> str:
        return f"{self.amount} {self.unit} of {self.resource_type.value}"


@dataclass
class ResourceRequest:
    """Request for resource allocation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    requester_id: str = ""
    resources: List[ResourceSpec] = field(default_factory=list)
    priority: int = 0
    duration: Optional[int] = None  # Expected duration in seconds
    constraints: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    
    def __post_init__(self):
        if not self.requester_id:
            self.requester_id = f"unknown_{int(time.time())}"


@dataclass
class ResourceAllocation:
    """Represents an allocated resource."""
    id: str
    request_id: str
    resource_spec: ResourceSpec
    allocated_amount: float
    node_id: str
    allocated_at: datetime = field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    
    @property
    def is_expired(self) -> bool:
        """Check if allocation has expired."""
        return self.expires_at and datetime.now() > self.expires_at


@dataclass
class ResourceNode:
    """Represents a compute node with resources."""
    id: str
    name: str
    location: str
    resources: Dict[ResourceType, float] = field(default_factory=dict)
    allocated: Dict[ResourceType, float] = field(default_factory=dict)
    reserved: Dict[ResourceType, float] = field(default_factory=dict)
    capabilities: Set[str] = field(default_factory=set)
    status: str = "active"  # active, maintenance, offline
    last_heartbeat: datetime = field(default_factory=datetime.now)
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def get_available(self, resource_type: ResourceType) -> float:
        """Get available amount of a resource type."""
        total = self.resources.get(resource_type, 0.0)
        allocated = self.allocated.get(resource_type, 0.0)
        reserved = self.reserved.get(resource_type, 0.0)
        return max(0.0, total - allocated - reserved)
    
    def get_utilization(self, resource_type: ResourceType) -> float:
        """Get utilization percentage for a resource type."""
        total = self.resources.get(resource_type, 0.0)
        if total == 0:
            return 0.0
        allocated = self.allocated.get(resource_type, 0.0)
        return (allocated / total) * 100.0
    
    def can_allocate(self, resource_spec: ResourceSpec) -> bool:
        """Check if node can allocate the requested resource."""
        available = self.get_available(resource_spec.resource_type)
        return available >= resource_spec.amount
    
    def allocate(self, resource_spec: ResourceSpec) -> bool:
        """Allocate resource on this node."""
        if not self.can_allocate(resource_spec):
            return False
        
        current_allocated = self.allocated.get(resource_spec.resource_type, 0.0)
        self.allocated[resource_spec.resource_type] = current_allocated + resource_spec.amount
        return True
    
    def deallocate(self, resource_spec: ResourceSpec) -> bool:
        """Deallocate resource from this node."""
        current_allocated = self.allocated.get(resource_spec.resource_type, 0.0)
        if current_allocated >= resource_spec.amount:
            self.allocated[resource_spec.resource_type] = current_allocated - resource_spec.amount
            return True
        return False


class MLResourceOptimizer:
    """Machine learning-based resource optimization."""
    
    def __init__(self):
        self.allocation_history: List[Dict[str, Any]] = []
        self.performance_data: Dict[str, List[float]] = defaultdict(list)
        self.prediction_models: Dict[str, Any] = {}
        
    def record_allocation(self, 
                         request: ResourceRequest,
                         allocation: List[ResourceAllocation],
                         performance_metrics: Dict[str, float]) -> None:
        """Record allocation data for learning."""
        record = {
            'timestamp': datetime.now().isoformat(),
            'request_id': request.id,
            'requester_id': request.requester_id,
            'resources': [
                {
                    'type': spec.resource_type.value,
                    'amount': spec.amount,
                    'unit': spec.unit
                }
                for spec in request.resources
            ],
            'priority': request.priority,
            'allocations': [
                {
                    'node_id': alloc.node_id,
                    'allocated_amount': alloc.allocated_amount,
                    'resource_type': alloc.resource_spec.resource_type.value
                }
                for alloc in allocation
            ],
            'performance': performance_metrics
        }
        
        self.allocation_history.append(record)
        
        # Keep only recent history
        if len(self.allocation_history) > 10000:
            self.allocation_history = self.allocation_history[-10000:]
    
    def predict_optimal_allocation(self, 
                                 request: ResourceRequest,
                                 available_nodes: List[ResourceNode]) -> List[Tuple[str, float]]:
        """Predict optimal resource allocation using ML."""
        # Simplified ML prediction - in practice, this would use
        # sophisticated ML models like neural networks or ensemble methods
        
        predictions = []
        
        for resource_spec in request.resources:
            # Score nodes based on historical performance
            node_scores = []
            
            for node in available_nodes:
                if not node.can_allocate(resource_spec):
                    continue
                
                # Calculate score based on multiple factors
                utilization = node.get_utilization(resource_spec.resource_type)
                available_ratio = node.get_available(resource_spec.resource_type) / node.resources.get(resource_spec.resource_type, 1.0)
                
                # Historical performance factor
                perf_key = f"{node.id}_{resource_spec.resource_type.value}"
                avg_performance = statistics.mean(self.performance_data.get(perf_key, [1.0]))
                
                # Combined score (lower is better)
                score = (
                    utilization * 0.3 +  # Prefer less utilized nodes
                    (1.0 - available_ratio) * 0.3 +  # Prefer nodes with more available resources
                    (1.0 / avg_performance) * 0.4  # Prefer historically better performing nodes
                )
                
                node_scores.append((node.id, score))
            
            # Sort by score and select best node
            if node_scores:
                node_scores.sort(key=lambda x: x[1])
                best_node_id = node_scores[0][0]
                predictions.append((best_node_id, resource_spec.amount))
        
        return predictions
    
    def update_performance_data(self, 
                              node_id: str,
                              resource_type: ResourceType,
                              performance_score: float) -> None:
        """Update performance data for a node and resource type."""
        key = f"{node_id}_{resource_type.value}"
        self.performance_data[key].append(performance_score)
        
        # Keep only recent data
        if len(self.performance_data[key]) > 100:
            self.performance_data[key] = self.performance_data[key][-100:]


class ResourceManager:
    """
    Advanced resource manager with features:
    - ML-based resource allocation optimization
    - Multi-node distributed resource management
    - Dynamic load balancing and auto-scaling
    - Resource reservation and scheduling
    - Performance monitoring and optimization
    """
    
    def __init__(self, 
                 allocation_strategy: AllocationStrategy = AllocationStrategy.ML_OPTIMIZED,
                 enable_auto_scaling: bool = True,
                 enable_ml_optimization: bool = True):
        """Initialize the resource manager."""
        self.allocation_strategy = allocation_strategy
        self.enable_auto_scaling = enable_auto_scaling
        self.enable_ml_optimization = enable_ml_optimization
        
        # Resource tracking
        self.nodes: Dict[str, ResourceNode] = {}
        self.allocations: Dict[str, ResourceAllocation] = {}
        self.pending_requests: Dict[str, ResourceRequest] = {}
        self.allocation_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # ML optimization
        self.ml_optimizer = MLResourceOptimizer() if enable_ml_optimization else None
        
        # Performance tracking
        self.allocation_metrics: Dict[str, List[float]] = defaultdict(list)
        self.node_performance: Dict[str, Dict[str, float]] = defaultdict(dict)
        
        # Auto-scaling
        self.scaling_policies: Dict[ResourceType, Dict[str, Any]] = {}
        self.scaling_cooldown: Dict[str, datetime] = {}
        
        # Background services
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        # Locks for thread safety
        self._allocation_lock = asyncio.Lock()
        
        # Start background services
        self._start_background_services()
        
        logging.info(f"ResourceManager initialized with {allocation_strategy.value} strategy")
    
    def _start_background_services(self) -> None:
        """Start background services."""
        # Resource monitor
        monitor_task = asyncio.create_task(self._resource_monitor())
        self._background_tasks.append(monitor_task)
        
        # Allocation processor
        processor_task = asyncio.create_task(self._allocation_processor())
        self._background_tasks.append(processor_task)
        
        # Auto-scaler
        if self.enable_auto_scaling:
            scaler_task = asyncio.create_task(self._auto_scaler())
            self._background_tasks.append(scaler_task)
        
        # Cleanup service
        cleanup_task = asyncio.create_task(self._cleanup_service())
        self._background_tasks.append(cleanup_task)
    
    async def register_node(self, node: ResourceNode) -> bool:
        """Register a new resource node."""
        if node.id in self.nodes:
            logging.warning(f"Node {node.id} already registered")
            return False
        
        self.nodes[node.id] = node
        logging.info(f"Registered resource node {node.id} with resources: {node.resources}")
        return True
    
    async def unregister_node(self, node_id: str) -> bool:
        """Unregister a resource node."""
        if node_id not in self.nodes:
            logging.warning(f"Node {node_id} not found for unregistration")
            return False
        
        # Check for active allocations
        active_allocations = [
            alloc for alloc in self.allocations.values()
            if alloc.node_id == node_id
        ]
        
        if active_allocations:
            logging.error(f"Cannot unregister node {node_id} with active allocations")
            return False
        
        del self.nodes[node_id]
        logging.info(f"Unregistered resource node {node_id}")
        return True
    
    async def request_resources(self, request: ResourceRequest) -> Optional[str]:
        """
        Request resource allocation.
        
        Args:
            request: Resource request specification
            
        Returns:
            Request ID if queued successfully, None otherwise
        """
        # Validate request
        if not request.resources:
            logging.error("Resource request must specify at least one resource")
            return None
        
        # Queue request for processing
        self.pending_requests[request.id] = request
        
        # Add to priority queue (negative priority for max-heap behavior)
        priority = -request.priority
        await self.allocation_queue.put((priority, time.time(), request.id))
        
        logging.info(f"Queued resource request {request.id} from {request.requester_id}")
        return request.id
    
    async def allocate(self, request: ResourceRequest) -> Optional[List[ResourceAllocation]]:
        """
        Allocate resources for a request.
        
        Args:
            request: Resource request to allocate
            
        Returns:
            List of allocations if successful, None otherwise
        """
        async with self._allocation_lock:
            try:
                # Find suitable allocation
                allocation_plan = await self._find_allocation(request)
                if not allocation_plan:
                    return None
                
                # Execute allocation
                allocations = []
                for node_id, resource_spec, amount in allocation_plan:
                    node = self.nodes[node_id]
                    
                    # Create allocation
                    allocation = ResourceAllocation(
                        id=str(uuid.uuid4()),
                        request_id=request.id,
                        resource_spec=resource_spec,
                        allocated_amount=amount,
                        node_id=node_id
                    )
                    
                    # Set expiration if duration specified
                    if request.duration:
                        allocation.expires_at = datetime.now() + timedelta(seconds=request.duration)
                    
                    # Allocate on node
                    if node.allocate(resource_spec):
                        allocations.append(allocation)
                        self.allocations[allocation.id] = allocation
                    else:
                        # Rollback previous allocations
                        for prev_alloc in allocations:
                            self.nodes[prev_alloc.node_id].deallocate(prev_alloc.resource_spec)
                            del self.allocations[prev_alloc.id]
                        return None
                
                # Record allocation for ML learning
                if self.ml_optimizer:
                    performance_metrics = self._calculate_allocation_performance(allocations)
                    self.ml_optimizer.record_allocation(request, allocations, performance_metrics)
                
                logging.info(f"Allocated resources for request {request.id}: {len(allocations)} allocations")
                return allocations
                
            except Exception as e:
                logging.error(f"Error allocating resources for request {request.id}: {e}")
                return None
    
    async def release(self, allocation_id: str) -> bool:
        """
        Release a resource allocation.
        
        Args:
            allocation_id: ID of allocation to release
            
        Returns:
            True if released successfully, False otherwise
        """
        if allocation_id not in self.allocations:
            logging.warning(f"Allocation {allocation_id} not found for release")
            return False
        
        allocation = self.allocations[allocation_id]
        node = self.nodes.get(allocation.node_id)
        
        if not node:
            logging.error(f"Node {allocation.node_id} not found for allocation {allocation_id}")
            return False
        
        # Deallocate from node
        if node.deallocate(allocation.resource_spec):
            del self.allocations[allocation_id]
            logging.info(f"Released allocation {allocation_id} from node {allocation.node_id}")
            return True
        else:
            logging.error(f"Failed to deallocate resources for allocation {allocation_id}")
            return False
    
    async def can_allocate(self, request: ResourceRequest) -> bool:
        """
        Check if resources can be allocated for a request.
        
        Args:
            request: Resource request to check
            
        Returns:
            True if allocation is possible, False otherwise
        """
        allocation_plan = await self._find_allocation(request)
        return allocation_plan is not None
    
    async def _find_allocation(self, request: ResourceRequest) -> Optional[List[Tuple[str, ResourceSpec, float]]]:
        """Find an allocation plan for a resource request."""
        if self.allocation_strategy == AllocationStrategy.ML_OPTIMIZED and self.ml_optimizer:
            return await self._ml_allocation(request)
        elif self.allocation_strategy == AllocationStrategy.BEST_FIT:
            return await self._best_fit_allocation(request)
        elif self.allocation_strategy == AllocationStrategy.FIRST_FIT:
            return await self._first_fit_allocation(request)
        elif self.allocation_strategy == AllocationStrategy.PRIORITY_BASED:
            return await self._priority_based_allocation(request)
        else:
            return await self._first_fit_allocation(request)  # Default fallback
    
    async def _ml_allocation(self, request: ResourceRequest) -> Optional[List[Tuple[str, ResourceSpec, float]]]:
        """ML-optimized allocation strategy."""
        available_nodes = [node for node in self.nodes.values() if node.status == "active"]
        
        if not available_nodes:
            return None
        
        # Get ML predictions
        predictions = self.ml_optimizer.predict_optimal_allocation(request, available_nodes)
        
        allocation_plan = []
        for i, resource_spec in enumerate(request.resources):
            if i < len(predictions):
                node_id, amount = predictions[i]
                node = self.nodes.get(node_id)
                
                if node and node.can_allocate(resource_spec):
                    allocation_plan.append((node_id, resource_spec, amount))
                else:
                    # Fallback to first fit for this resource
                    fallback = await self._first_fit_for_resource(resource_spec)
                    if fallback:
                        allocation_plan.append(fallback)
                    else:
                        return None
            else:
                # No prediction available, use first fit
                fallback = await self._first_fit_for_resource(resource_spec)
                if fallback:
                    allocation_plan.append(fallback)
                else:
                    return None
        
        return allocation_plan
    
    async def _best_fit_allocation(self, request: ResourceRequest) -> Optional[List[Tuple[str, ResourceSpec, float]]]:
        """Best fit allocation strategy."""
        allocation_plan = []
        
        for resource_spec in request.resources:
            best_node = None
            best_fit_score = float('inf')
            
            for node in self.nodes.values():
                if node.status != "active" or not node.can_allocate(resource_spec):
                    continue
                
                # Calculate fit score (remaining capacity after allocation)
                available = node.get_available(resource_spec.resource_type)
                remaining = available - resource_spec.amount
                
                if remaining >= 0 and remaining < best_fit_score:
                    best_fit_score = remaining
                    best_node = node
            
            if best_node:
                allocation_plan.append((best_node.id, resource_spec, resource_spec.amount))
            else:
                return None
        
        return allocation_plan
    
    async def _first_fit_allocation(self, request: ResourceRequest) -> Optional[List[Tuple[str, ResourceSpec, float]]]:
        """First fit allocation strategy."""
        allocation_plan = []
        
        for resource_spec in request.resources:
            allocation = await self._first_fit_for_resource(resource_spec)
            if allocation:
                allocation_plan.append(allocation)
            else:
                return None
        
        return allocation_plan
    
    async def _first_fit_for_resource(self, resource_spec: ResourceSpec) -> Optional[Tuple[str, ResourceSpec, float]]:
        """Find first fit for a single resource."""
        for node in self.nodes.values():
            if node.status == "active" and node.can_allocate(resource_spec):
                return (node.id, resource_spec, resource_spec.amount)
        return None
    
    async def _priority_based_allocation(self, request: ResourceRequest) -> Optional[List[Tuple[str, ResourceSpec, float]]]:
        """Priority-based allocation strategy."""
        # Sort nodes by priority (could be based on performance, location, etc.)
        sorted_nodes = sorted(
            [node for node in self.nodes.values() if node.status == "active"],
            key=lambda n: n.performance_metrics.get('priority_score', 0.0),
            reverse=True
        )
        
        allocation_plan = []
        
        for resource_spec in request.resources:
            allocated = False
            for node in sorted_nodes:
                if node.can_allocate(resource_spec):
                    allocation_plan.append((node.id, resource_spec, resource_spec.amount))
                    allocated = True
                    break
            
            if not allocated:
                return None
        
        return allocation_plan
    
    def _calculate_allocation_performance(self, allocations: List[ResourceAllocation]) -> Dict[str, float]:
        """Calculate performance metrics for an allocation."""
        metrics = {}
        
        # Calculate fragmentation
        total_nodes = len(set(alloc.node_id for alloc in allocations))
        metrics['node_fragmentation'] = total_nodes / len(allocations) if allocations else 0.0
        
        # Calculate average utilization
        utilizations = []
        for alloc in allocations:
            node = self.nodes.get(alloc.node_id)
            if node:
                util = node.get_utilization(alloc.resource_spec.resource_type)
                utilizations.append(util)
        
        metrics['average_utilization'] = statistics.mean(utilizations) if utilizations else 0.0
        
        return metrics
    
    async def _allocation_processor(self) -> None:
        """Background processor for allocation requests."""
        while not self._shutdown_event.is_set():
            try:
                # Process allocation queue
                try:
                    priority, timestamp, request_id = await asyncio.wait_for(
                        self.allocation_queue.get(),
                        timeout=1.0
                    )
                    
                    if request_id in self.pending_requests:
                        request = self.pending_requests[request_id]
                        
                        # Attempt allocation
                        allocations = await self.allocate(request)
                        
                        if allocations:
                            # Remove from pending
                            del self.pending_requests[request_id]
                            logging.info(f"Successfully processed allocation request {request_id}")
                        else:
                            # Re-queue with lower priority if not too old
                            age = time.time() - timestamp
                            if age < 300:  # 5 minutes max age
                                await self.allocation_queue.put((priority + 1, timestamp, request_id))
                            else:
                                del self.pending_requests[request_id]
                                logging.warning(f"Allocation request {request_id} expired")
                
                except asyncio.TimeoutError:
                    continue
                
            except Exception as e:
                logging.error(f"Error in allocation processor: {e}")
                await asyncio.sleep(5)
    
    async def _resource_monitor(self) -> None:
        """Background resource monitoring."""
        while not self._shutdown_event.is_set():
            try:
                # Update node performance metrics
                for node in self.nodes.values():
                    # Check node health
                    time_since_heartbeat = datetime.now() - node.last_heartbeat
                    if time_since_heartbeat > timedelta(minutes=5):
                        if node.status == "active":
                            node.status = "offline"
                            logging.warning(f"Node {node.id} marked as offline due to missed heartbeat")
                    
                    # Update performance metrics
                    for resource_type in ResourceType:
                        utilization = node.get_utilization(resource_type)
                        node.performance_metrics[f'{resource_type.value}_utilization'] = utilization
                
                await asyncio.sleep(30)  # Monitor every 30 seconds
                
            except Exception as e:
                logging.error(f"Error in resource monitor: {e}")
                await asyncio.sleep(60)
    
    async def _auto_scaler(self) -> None:
        """Background auto-scaling service."""
        while not self._shutdown_event.is_set():
            try:
                # Check scaling conditions
                for resource_type in ResourceType:
                    await self._check_scaling_conditions(resource_type)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logging.error(f"Error in auto-scaler: {e}")
                await asyncio.sleep(120)
    
    async def _check_scaling_conditions(self, resource_type: ResourceType) -> None:
        """Check if scaling is needed for a resource type."""
        # Calculate overall utilization
        total_capacity = sum(
            node.resources.get(resource_type, 0.0)
            for node in self.nodes.values()
            if node.status == "active"
        )
        
        total_allocated = sum(
            node.allocated.get(resource_type, 0.0)
            for node in self.nodes.values()
            if node.status == "active"
        )
        
        if total_capacity == 0:
            return
        
        utilization = (total_allocated / total_capacity) * 100.0
        
        # Check scaling policies
        policy = self.scaling_policies.get(resource_type, {})
        scale_up_threshold = policy.get('scale_up_threshold', 80.0)
        scale_down_threshold = policy.get('scale_down_threshold', 20.0)
        
        # Check cooldown
        cooldown_key = f"{resource_type.value}_scaling"
        if cooldown_key in self.scaling_cooldown:
            if datetime.now() - self.scaling_cooldown[cooldown_key] < timedelta(minutes=10):
                return
        
        if utilization > scale_up_threshold:
            # Scale up
            await self._trigger_scale_up(resource_type)
            self.scaling_cooldown[cooldown_key] = datetime.now()
        elif utilization < scale_down_threshold:
            # Scale down
            await self._trigger_scale_down(resource_type)
            self.scaling_cooldown[cooldown_key] = datetime.now()
    
    async def _trigger_scale_up(self, resource_type: ResourceType) -> None:
        """Trigger scale-up for a resource type."""
        logging.info(f"Triggering scale-up for {resource_type.value}")
        # In a real implementation, this would integrate with container orchestration
        # platforms like Kubernetes to add new nodes or increase resource limits
    
    async def _trigger_scale_down(self, resource_type: ResourceType) -> None:
        """Trigger scale-down for a resource type."""
        logging.info(f"Triggering scale-down for {resource_type.value}")
        # In a real implementation, this would safely remove underutilized nodes
    
    async def _cleanup_service(self) -> None:
        """Background cleanup service for expired allocations."""
        while not self._shutdown_event.is_set():
            try:
                # Clean up expired allocations
                expired_allocations = [
                    alloc_id for alloc_id, alloc in self.allocations.items()
                    if alloc.is_expired
                ]
                
                for alloc_id in expired_allocations:
                    await self.release(alloc_id)
                    logging.info(f"Released expired allocation {alloc_id}")
                
                await asyncio.sleep(60)  # Cleanup every minute
                
            except Exception as e:
                logging.error(f"Error in cleanup service: {e}")
                await asyncio.sleep(120)
    
    async def update_allocation_strategy(self, agent_type: str, performance_data: float) -> None:
        """Update allocation strategy based on performance feedback."""
        if self.ml_optimizer:
            # Update ML model with performance feedback
            # This is a simplified version - real implementation would be more sophisticated
            pass
    
    def get_resource_status(self) -> Dict[str, Any]:
        """Get overall resource status."""
        total_nodes = len(self.nodes)
        active_nodes = sum(1 for node in self.nodes.values() if node.status == "active")
        total_allocations = len(self.allocations)
        
        # Calculate resource utilization by type
        utilization_by_type = {}
        for resource_type in ResourceType:
            total_capacity = sum(
                node.resources.get(resource_type, 0.0)
                for node in self.nodes.values()
                if node.status == "active"
            )
            total_allocated = sum(
                node.allocated.get(resource_type, 0.0)
                for node in self.nodes.values()
                if node.status == "active"
            )
            
            if total_capacity > 0:
                utilization_by_type[resource_type.value] = (total_allocated / total_capacity) * 100.0
            else:
                utilization_by_type[resource_type.value] = 0.0
        
        return {
            'total_nodes': total_nodes,
            'active_nodes': active_nodes,
            'total_allocations': total_allocations,
            'pending_requests': len(self.pending_requests),
            'allocation_strategy': self.allocation_strategy.value,
            'utilization_by_type': utilization_by_type,
            'auto_scaling_enabled': self.enable_auto_scaling,
            'ml_optimization_enabled': self.enable_ml_optimization
        }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the resource manager."""
        logging.info("Shutting down ResourceManager...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Release all allocations
        for allocation_id in list(self.allocations.keys()):
            await self.release(allocation_id)
        
        logging.info("ResourceManager shutdown complete")

