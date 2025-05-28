#!/usr/bin/env python
"""
Agent Registry

This module manages the registration, discovery, and lifecycle of AI agents
in the multi-agent coordination system.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Union
from datetime import datetime, timedelta
import json
import threading
from collections import defaultdict


class AgentType(Enum):
    """Types of agents in the system."""
    PLANNER = "planner"
    CODER = "coder"
    TESTER = "tester"
    REVIEWER = "reviewer"
    DEPLOYER = "deployer"
    MONITOR = "monitor"
    OPTIMIZER = "optimizer"
    CUSTOM = "custom"


class AgentStatus(Enum):
    """Agent status states."""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"
    MAINTENANCE = "maintenance"


@dataclass
class AgentCapability:
    """Represents an agent's capability."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    output_schema: Dict[str, Any]
    resource_requirements: Dict[str, Any] = field(default_factory=dict)
    performance_metrics: Dict[str, float] = field(default_factory=dict)


@dataclass
class AgentMetrics:
    """Agent performance and health metrics."""
    agent_id: str
    tasks_completed: int = 0
    tasks_failed: int = 0
    average_execution_time: float = 0.0
    success_rate: float = 1.0
    last_activity: Optional[datetime] = None
    resource_utilization: Dict[str, float] = field(default_factory=dict)
    error_count: int = 0
    uptime: timedelta = field(default_factory=timedelta)


class BaseAgent(ABC):
    """Base class for all agents in the system."""
    
    def __init__(self, 
                 agent_id: str,
                 agent_type: AgentType,
                 name: str,
                 description: str,
                 capabilities: List[AgentCapability] = None):
        self.agent_id = agent_id
        self.agent_type = agent_type
        self.name = name
        self.description = description
        self.capabilities = capabilities or []
        self.status = AgentStatus.IDLE
        self.created_at = datetime.now()
        self.last_heartbeat = datetime.now()
        self.metrics = AgentMetrics(agent_id=agent_id)
        self.config: Dict[str, Any] = {}
        
        # Execution tracking
        self.current_task: Optional[str] = None
        self.task_history: List[Dict[str, Any]] = []
        
        # Health monitoring
        self.health_check_interval = 30  # seconds
        self._health_check_task: Optional[asyncio.Task] = None
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        logging.info(f"Initialized agent {self.agent_id} ({self.name}) of type {self.agent_type.value}")
    
    @abstractmethod
    async def execute(self, parameters: Dict[str, Any]) -> Any:
        """Execute a task with the given parameters."""
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """Perform a health check and return True if healthy."""
        pass
    
    async def start(self) -> None:
        """Start the agent and begin health monitoring."""
        self.status = AgentStatus.IDLE
        self._health_check_task = asyncio.create_task(self._health_monitor())
        await self._emit_event('agent_started', {'agent_id': self.agent_id})
        logging.info(f"Started agent {self.agent_id}")
    
    async def stop(self) -> None:
        """Stop the agent and cleanup resources."""
        self.status = AgentStatus.OFFLINE
        if self._health_check_task:
            self._health_check_task.cancel()
        await self._emit_event('agent_stopped', {'agent_id': self.agent_id})
        logging.info(f"Stopped agent {self.agent_id}")
    
    async def _health_monitor(self) -> None:
        """Background health monitoring."""
        while self.status != AgentStatus.OFFLINE:
            try:
                is_healthy = await self.health_check()
                if not is_healthy and self.status != AgentStatus.ERROR:
                    self.status = AgentStatus.ERROR
                    await self._emit_event('agent_unhealthy', {'agent_id': self.agent_id})
                elif is_healthy and self.status == AgentStatus.ERROR:
                    self.status = AgentStatus.IDLE
                    await self._emit_event('agent_recovered', {'agent_id': self.agent_id})
                
                self.last_heartbeat = datetime.now()
                await asyncio.sleep(self.health_check_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Health check failed for agent {self.agent_id}: {e}")
                self.status = AgentStatus.ERROR
                await asyncio.sleep(self.health_check_interval)
    
    async def execute_task(self, task_id: str, parameters: Dict[str, Any]) -> Any:
        """Execute a task and track metrics."""
        if self.status != AgentStatus.IDLE:
            raise RuntimeError(f"Agent {self.agent_id} is not available (status: {self.status.value})")
        
        self.status = AgentStatus.BUSY
        self.current_task = task_id
        start_time = time.time()
        
        try:
            # Execute the task
            result = await self.execute(parameters)
            
            # Update metrics
            execution_time = time.time() - start_time
            self.metrics.tasks_completed += 1
            self.metrics.last_activity = datetime.now()
            
            # Update average execution time
            total_tasks = self.metrics.tasks_completed + self.metrics.tasks_failed
            self.metrics.average_execution_time = (
                (self.metrics.average_execution_time * (total_tasks - 1) + execution_time) / total_tasks
            )
            
            # Update success rate
            self.metrics.success_rate = self.metrics.tasks_completed / total_tasks
            
            # Record task history
            self.task_history.append({
                'task_id': task_id,
                'start_time': start_time,
                'end_time': time.time(),
                'execution_time': execution_time,
                'success': True,
                'result_size': len(str(result)) if result else 0
            })
            
            await self._emit_event('task_completed', {
                'agent_id': self.agent_id,
                'task_id': task_id,
                'execution_time': execution_time
            })
            
            return result
            
        except Exception as e:
            # Update failure metrics
            self.metrics.tasks_failed += 1
            self.metrics.error_count += 1
            
            # Update success rate
            total_tasks = self.metrics.tasks_completed + self.metrics.tasks_failed
            self.metrics.success_rate = self.metrics.tasks_completed / total_tasks
            
            # Record failed task
            self.task_history.append({
                'task_id': task_id,
                'start_time': start_time,
                'end_time': time.time(),
                'execution_time': time.time() - start_time,
                'success': False,
                'error': str(e)
            })
            
            await self._emit_event('task_failed', {
                'agent_id': self.agent_id,
                'task_id': task_id,
                'error': str(e)
            })
            
            raise
        
        finally:
            self.status = AgentStatus.IDLE
            self.current_task = None
    
    def add_capability(self, capability: AgentCapability) -> None:
        """Add a new capability to the agent."""
        self.capabilities.append(capability)
    
    def has_capability(self, capability_name: str) -> bool:
        """Check if agent has a specific capability."""
        return any(cap.name == capability_name for cap in self.capabilities)
    
    def get_capability(self, capability_name: str) -> Optional[AgentCapability]:
        """Get a specific capability by name."""
        for cap in self.capabilities:
            if cap.name == capability_name:
                return cap
        return None
    
    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register an event handler."""
        self.event_handlers[event_type].append(handler)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit an event to registered handlers."""
        for handler in self.event_handlers.get(event_type, []):
            try:
                await handler(data)
            except Exception as e:
                logging.error(f"Error in event handler for {event_type}: {e}")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agent to dictionary representation."""
        return {
            'agent_id': self.agent_id,
            'agent_type': self.agent_type.value,
            'name': self.name,
            'description': self.description,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'last_heartbeat': self.last_heartbeat.isoformat(),
            'current_task': self.current_task,
            'capabilities': [
                {
                    'name': cap.name,
                    'description': cap.description,
                    'resource_requirements': cap.resource_requirements
                }
                for cap in self.capabilities
            ],
            'metrics': {
                'tasks_completed': self.metrics.tasks_completed,
                'tasks_failed': self.metrics.tasks_failed,
                'average_execution_time': self.metrics.average_execution_time,
                'success_rate': self.metrics.success_rate,
                'error_count': self.metrics.error_count,
                'uptime': self.metrics.uptime.total_seconds()
            }
        }


class AgentRegistry:
    """
    Central registry for managing AI agents with advanced features:
    - Dynamic agent discovery and registration
    - Load balancing and health monitoring
    - Capability-based agent selection
    - Performance tracking and optimization
    """
    
    def __init__(self, enable_auto_scaling: bool = True):
        self.agents: Dict[str, BaseAgent] = {}
        self.agents_by_type: Dict[AgentType, List[str]] = defaultdict(list)
        self.agents_by_capability: Dict[str, List[str]] = defaultdict(list)
        
        # Load balancing
        self.load_balancer_strategy = "round_robin"  # round_robin, least_loaded, performance_based
        self.round_robin_counters: Dict[AgentType, int] = defaultdict(int)
        
        # Auto-scaling
        self.enable_auto_scaling = enable_auto_scaling
        self.scaling_policies: Dict[AgentType, Dict[str, Any]] = {}
        
        # Health monitoring
        self.health_check_interval = 60  # seconds
        self._health_monitor_task: Optional[asyncio.Task] = None
        
        # Performance tracking
        self.performance_history: Dict[str, List[float]] = defaultdict(list)
        self.agent_rankings: Dict[AgentType, List[str]] = defaultdict(list)
        
        # Event handlers
        self.event_handlers: Dict[str, List[Callable]] = defaultdict(list)
        
        # Start background services
        self._start_background_services()
        
        logging.info("AgentRegistry initialized with advanced management capabilities")
    
    def _start_background_services(self) -> None:
        """Start background monitoring and optimization services."""
        self._health_monitor_task = asyncio.create_task(self._health_monitor())
    
    async def register_agent(self, agent: BaseAgent) -> bool:
        """
        Register a new agent in the registry.
        
        Args:
            agent: The agent to register
            
        Returns:
            True if registration successful, False otherwise
        """
        if agent.agent_id in self.agents:
            logging.warning(f"Agent {agent.agent_id} already registered")
            return False
        
        # Register agent
        self.agents[agent.agent_id] = agent
        self.agents_by_type[agent.agent_type].append(agent.agent_id)
        
        # Register capabilities
        for capability in agent.capabilities:
            self.agents_by_capability[capability.name].append(agent.agent_id)
        
        # Start agent
        await agent.start()
        
        # Register for agent events
        agent.register_event_handler('task_completed', self._on_task_completed)
        agent.register_event_handler('task_failed', self._on_task_failed)
        
        # Update rankings
        await self._update_agent_rankings(agent.agent_type)
        
        await self._emit_event('agent_registered', {
            'agent_id': agent.agent_id,
            'agent_type': agent.agent_type.value,
            'capabilities': [cap.name for cap in agent.capabilities]
        })
        
        logging.info(f"Registered agent {agent.agent_id} ({agent.name})")
        return True
    
    async def unregister_agent(self, agent_id: str) -> bool:
        """
        Unregister an agent from the registry.
        
        Args:
            agent_id: ID of the agent to unregister
            
        Returns:
            True if unregistration successful, False otherwise
        """
        if agent_id not in self.agents:
            logging.warning(f"Agent {agent_id} not found for unregistration")
            return False
        
        agent = self.agents[agent_id]
        
        # Stop agent
        await agent.stop()
        
        # Remove from registries
        del self.agents[agent_id]
        self.agents_by_type[agent.agent_type].remove(agent_id)
        
        # Remove from capability registries
        for capability in agent.capabilities:
            if agent_id in self.agents_by_capability[capability.name]:
                self.agents_by_capability[capability.name].remove(agent_id)
        
        # Update rankings
        await self._update_agent_rankings(agent.agent_type)
        
        await self._emit_event('agent_unregistered', {
            'agent_id': agent_id,
            'agent_type': agent.agent_type.value
        })
        
        logging.info(f"Unregistered agent {agent_id}")
        return True
    
    async def get_agent(self, agent_type: AgentType, 
                       capability: Optional[str] = None,
                       exclude_agents: Set[str] = None) -> Optional[BaseAgent]:
        """
        Get an available agent of the specified type with load balancing.
        
        Args:
            agent_type: Type of agent needed
            capability: Specific capability required (optional)
            exclude_agents: Set of agent IDs to exclude
            
        Returns:
            Available agent or None if no agent available
        """
        exclude_agents = exclude_agents or set()
        
        # Get candidate agents
        if capability:
            candidate_ids = [
                aid for aid in self.agents_by_capability.get(capability, [])
                if (aid in self.agents and 
                    self.agents[aid].agent_type == agent_type and
                    aid not in exclude_agents)
            ]
        else:
            candidate_ids = [
                aid for aid in self.agents_by_type.get(agent_type, [])
                if aid not in exclude_agents
            ]
        
        if not candidate_ids:
            return None
        
        # Filter available agents
        available_agents = [
            self.agents[aid] for aid in candidate_ids
            if self.agents[aid].status == AgentStatus.IDLE
        ]
        
        if not available_agents:
            return None
        
        # Apply load balancing strategy
        return await self._select_agent(available_agents, agent_type)
    
    async def _select_agent(self, agents: List[BaseAgent], agent_type: AgentType) -> BaseAgent:
        """Select an agent based on the load balancing strategy."""
        if self.load_balancer_strategy == "round_robin":
            # Round robin selection
            index = self.round_robin_counters[agent_type] % len(agents)
            self.round_robin_counters[agent_type] += 1
            return agents[index]
        
        elif self.load_balancer_strategy == "least_loaded":
            # Select agent with least current load
            return min(agents, key=lambda a: a.metrics.tasks_completed - a.metrics.tasks_failed)
        
        elif self.load_balancer_strategy == "performance_based":
            # Select agent with best performance
            ranked_agents = self.agent_rankings.get(agent_type, [])
            for agent_id in ranked_agents:
                for agent in agents:
                    if agent.agent_id == agent_id:
                        return agent
            # Fallback to first available
            return agents[0]
        
        else:
            # Default to first available
            return agents[0]
    
    async def get_agents_by_type(self, agent_type: AgentType) -> List[BaseAgent]:
        """Get all agents of a specific type."""
        agent_ids = self.agents_by_type.get(agent_type, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]
    
    async def get_agents_by_capability(self, capability: str) -> List[BaseAgent]:
        """Get all agents with a specific capability."""
        agent_ids = self.agents_by_capability.get(capability, [])
        return [self.agents[aid] for aid in agent_ids if aid in self.agents]
    
    async def get_agent_status(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Get detailed status of a specific agent."""
        if agent_id not in self.agents:
            return None
        
        agent = self.agents[agent_id]
        return agent.to_dict()
    
    async def get_registry_status(self) -> Dict[str, Any]:
        """Get overall registry status and statistics."""
        total_agents = len(self.agents)
        agents_by_status = defaultdict(int)
        agents_by_type = defaultdict(int)
        
        for agent in self.agents.values():
            agents_by_status[agent.status.value] += 1
            agents_by_type[agent.agent_type.value] += 1
        
        return {
            'total_agents': total_agents,
            'agents_by_status': dict(agents_by_status),
            'agents_by_type': dict(agents_by_type),
            'load_balancer_strategy': self.load_balancer_strategy,
            'auto_scaling_enabled': self.enable_auto_scaling,
            'capabilities': list(self.agents_by_capability.keys())
        }
    
    async def set_load_balancer_strategy(self, strategy: str) -> bool:
        """Set the load balancing strategy."""
        valid_strategies = ["round_robin", "least_loaded", "performance_based"]
        if strategy not in valid_strategies:
            return False
        
        self.load_balancer_strategy = strategy
        logging.info(f"Load balancer strategy set to {strategy}")
        return True
    
    async def _update_agent_rankings(self, agent_type: AgentType) -> None:
        """Update agent performance rankings."""
        agents = await self.get_agents_by_type(agent_type)
        
        # Sort by performance metrics (success rate, then average execution time)
        ranked_agents = sorted(
            agents,
            key=lambda a: (a.metrics.success_rate, -a.metrics.average_execution_time),
            reverse=True
        )
        
        self.agent_rankings[agent_type] = [a.agent_id for a in ranked_agents]
    
    async def _health_monitor(self) -> None:
        """Background health monitoring for all agents."""
        while True:
            try:
                unhealthy_agents = []
                
                for agent_id, agent in self.agents.items():
                    # Check if agent is responsive
                    time_since_heartbeat = datetime.now() - agent.last_heartbeat
                    if time_since_heartbeat > timedelta(seconds=self.health_check_interval * 2):
                        unhealthy_agents.append(agent_id)
                        if agent.status != AgentStatus.OFFLINE:
                            agent.status = AgentStatus.ERROR
                            await self._emit_event('agent_timeout', {
                                'agent_id': agent_id,
                                'last_heartbeat': agent.last_heartbeat.isoformat()
                            })
                
                # Handle unhealthy agents
                for agent_id in unhealthy_agents:
                    logging.warning(f"Agent {agent_id} appears unhealthy")
                    # Could implement auto-restart logic here
                
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                logging.error(f"Error in health monitor: {e}")
                await asyncio.sleep(60)
    
    async def _on_task_completed(self, data: Dict[str, Any]) -> None:
        """Handle task completion events."""
        agent_id = data['agent_id']
        execution_time = data['execution_time']
        
        # Update performance history
        self.performance_history[agent_id].append(execution_time)
        
        # Keep only recent history
        if len(self.performance_history[agent_id]) > 100:
            self.performance_history[agent_id] = self.performance_history[agent_id][-100:]
        
        # Update rankings
        if agent_id in self.agents:
            await self._update_agent_rankings(self.agents[agent_id].agent_type)
    
    async def _on_task_failed(self, data: Dict[str, Any]) -> None:
        """Handle task failure events."""
        agent_id = data['agent_id']
        
        # Update rankings
        if agent_id in self.agents:
            await self._update_agent_rankings(self.agents[agent_id].agent_type)
    
    def register_event_handler(self, event_type: str, handler: Callable) -> None:
        """Register an event handler for registry events."""
        self.event_handlers[event_type].append(handler)
    
    async def _emit_event(self, event_type: str, data: Dict[str, Any]) -> None:
        """Emit registry events to registered handlers."""
        for handler in self.event_handlers.get(event_type, []):
            try:
                await handler(data)
            except Exception as e:
                logging.error(f"Error in event handler for {event_type}: {e}")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the agent registry."""
        logging.info("Shutting down AgentRegistry...")
        
        # Cancel health monitor
        if self._health_monitor_task:
            self._health_monitor_task.cancel()
        
        # Stop all agents
        for agent in self.agents.values():
            await agent.stop()
        
        logging.info("AgentRegistry shutdown complete")


# Factory function for creating agents
def create_agent(agent_type: AgentType, 
                name: str,
                description: str,
                agent_class: type = None,
                **kwargs) -> BaseAgent:
    """
    Factory function to create agents of different types.
    
    Args:
        agent_type: Type of agent to create
        name: Agent name
        description: Agent description
        agent_class: Custom agent class (optional)
        **kwargs: Additional arguments for agent initialization
        
    Returns:
        Created agent instance
    """
    agent_id = str(uuid.uuid4())
    
    if agent_class:
        return agent_class(agent_id, agent_type, name, description, **kwargs)
    
    # Default agent implementations would be imported here
    # For now, return a basic agent
    from ..agents.base_agent import DefaultAgent
    return DefaultAgent(agent_id, agent_type, name, description, **kwargs)

