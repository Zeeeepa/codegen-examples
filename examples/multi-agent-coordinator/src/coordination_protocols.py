#!/usr/bin/env python
"""
Coordination Protocols

This module implements advanced communication and coordination protocols
for multi-agent systems with message passing, event handling, and
distributed coordination capabilities.
"""

import asyncio
import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Union, Tuple
from datetime import datetime, timedelta
import json
import threading
from collections import defaultdict, deque
import weakref


class MessageType(Enum):
    """Types of messages in the coordination system."""
    TASK_REQUEST = "task_request"
    TASK_RESPONSE = "task_response"
    STATUS_UPDATE = "status_update"
    HEARTBEAT = "heartbeat"
    COORDINATION = "coordination"
    BROADCAST = "broadcast"
    ERROR = "error"
    SHUTDOWN = "shutdown"


class MessagePriority(Enum):
    """Message priority levels."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class AgentMessage:
    """Represents a message between agents."""
    id: str
    sender_id: str
    receiver_id: Optional[str]  # None for broadcast messages
    message_type: MessageType
    priority: MessagePriority
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    ttl: Optional[int] = None  # Time to live in seconds
    retry_count: int = 0
    max_retries: int = 3
    
    @property
    def is_expired(self) -> bool:
        """Check if message has expired."""
        if self.ttl is None:
            return False
        return (datetime.now() - self.timestamp).total_seconds() > self.ttl
    
    @property
    def age(self) -> timedelta:
        """Get message age."""
        return datetime.now() - self.timestamp
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            'id': self.id,
            'sender_id': self.sender_id,
            'receiver_id': self.receiver_id,
            'message_type': self.message_type.value,
            'priority': self.priority.value,
            'payload': self.payload,
            'timestamp': self.timestamp.isoformat(),
            'correlation_id': self.correlation_id,
            'reply_to': self.reply_to,
            'ttl': self.ttl,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'AgentMessage':
        """Create message from dictionary."""
        return cls(
            id=data['id'],
            sender_id=data['sender_id'],
            receiver_id=data.get('receiver_id'),
            message_type=MessageType(data['message_type']),
            priority=MessagePriority(data['priority']),
            payload=data['payload'],
            timestamp=datetime.fromisoformat(data['timestamp']),
            correlation_id=data.get('correlation_id'),
            reply_to=data.get('reply_to'),
            ttl=data.get('ttl'),
            retry_count=data.get('retry_count', 0),
            max_retries=data.get('max_retries', 3)
        )


class MessageHandler(ABC):
    """Abstract base class for message handlers."""
    
    @abstractmethod
    async def handle_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Handle an incoming message and optionally return a response."""
        pass
    
    @abstractmethod
    def can_handle(self, message: AgentMessage) -> bool:
        """Check if this handler can process the given message."""
        pass


class MessageBus:
    """
    Advanced message bus for inter-agent communication with features:
    - Priority-based message queuing
    - Message routing and filtering
    - Reliable delivery with retries
    - Dead letter queue handling
    - Message persistence and replay
    - Performance monitoring
    """
    
    def __init__(self, 
                 max_queue_size: int = 10000,
                 enable_persistence: bool = True,
                 enable_metrics: bool = True):
        """Initialize the message bus."""
        self.max_queue_size = max_queue_size
        self.enable_persistence = enable_persistence
        self.enable_metrics = enable_metrics
        
        # Message queues (per agent)
        self.agent_queues: Dict[str, asyncio.PriorityQueue] = {}
        self.broadcast_queue: asyncio.PriorityQueue = asyncio.PriorityQueue(max_queue_size)
        
        # Message handlers
        self.handlers: Dict[str, List[MessageHandler]] = defaultdict(list)
        self.global_handlers: List[MessageHandler] = []
        
        # Routing and filtering
        self.routing_rules: List[Callable[[AgentMessage], Optional[str]]] = []
        self.message_filters: List[Callable[[AgentMessage], bool]] = []
        
        # Reliability features
        self.pending_messages: Dict[str, AgentMessage] = {}
        self.dead_letter_queue: deque = deque(maxlen=1000)
        self.retry_queue: asyncio.PriorityQueue = asyncio.PriorityQueue()
        
        # Persistence
        self.message_store: List[AgentMessage] = []
        self.max_stored_messages = 10000
        
        # Metrics
        self.metrics = {
            'messages_sent': 0,
            'messages_delivered': 0,
            'messages_failed': 0,
            'messages_retried': 0,
            'average_delivery_time': 0.0,
            'queue_sizes': defaultdict(int)
        }
        
        # Background services
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        # Start background services
        self._start_background_services()
        
        logging.info("MessageBus initialized with advanced coordination capabilities")
    
    def _start_background_services(self) -> None:
        """Start background services for message processing."""
        # Message retry processor
        retry_task = asyncio.create_task(self._retry_processor())
        self._background_tasks.append(retry_task)
        
        # Dead letter queue processor
        dlq_task = asyncio.create_task(self._dead_letter_processor())
        self._background_tasks.append(dlq_task)
        
        # Metrics collector
        if self.enable_metrics:
            metrics_task = asyncio.create_task(self._metrics_collector())
            self._background_tasks.append(metrics_task)
        
        # Queue maintenance
        maintenance_task = asyncio.create_task(self._queue_maintenance())
        self._background_tasks.append(maintenance_task)
    
    async def register_agent(self, agent_id: str) -> None:
        """Register an agent with the message bus."""
        if agent_id not in self.agent_queues:
            self.agent_queues[agent_id] = asyncio.PriorityQueue(self.max_queue_size)
            logging.info(f"Registered agent {agent_id} with message bus")
    
    async def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent from the message bus."""
        if agent_id in self.agent_queues:
            # Clear pending messages
            while not self.agent_queues[agent_id].empty():
                try:
                    self.agent_queues[agent_id].get_nowait()
                except asyncio.QueueEmpty:
                    break
            
            del self.agent_queues[agent_id]
            logging.info(f"Unregistered agent {agent_id} from message bus")
    
    async def send_message(self, message: AgentMessage) -> bool:
        """
        Send a message through the bus.
        
        Args:
            message: The message to send
            
        Returns:
            True if message was queued successfully, False otherwise
        """
        try:
            # Apply filters
            if not self._apply_filters(message):
                logging.debug(f"Message {message.id} filtered out")
                return False
            
            # Check if message is expired
            if message.is_expired:
                logging.warning(f"Message {message.id} expired before sending")
                return False
            
            # Apply routing rules
            target_agent = self._apply_routing(message)
            if target_agent:
                message.receiver_id = target_agent
            
            # Store message if persistence is enabled
            if self.enable_persistence:
                self._store_message(message)
            
            # Queue message
            priority = -message.priority.value  # Negative for priority queue (higher priority first)
            
            if message.receiver_id is None:
                # Broadcast message
                await self.broadcast_queue.put((priority, time.time(), message))
            else:
                # Direct message
                if message.receiver_id not in self.agent_queues:
                    await self.register_agent(message.receiver_id)
                
                await self.agent_queues[message.receiver_id].put((priority, time.time(), message))
            
            # Track pending message for reliability
            self.pending_messages[message.id] = message
            
            # Update metrics
            if self.enable_metrics:
                self.metrics['messages_sent'] += 1
            
            logging.debug(f"Queued message {message.id} from {message.sender_id} to {message.receiver_id}")
            return True
            
        except Exception as e:
            logging.error(f"Failed to send message {message.id}: {e}")
            return False
    
    async def receive_message(self, agent_id: str, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """
        Receive a message for a specific agent.
        
        Args:
            agent_id: ID of the agent receiving the message
            timeout: Maximum time to wait for a message
            
        Returns:
            Received message or None if timeout
        """
        if agent_id not in self.agent_queues:
            await self.register_agent(agent_id)
        
        try:
            if timeout:
                priority, timestamp, message = await asyncio.wait_for(
                    self.agent_queues[agent_id].get(),
                    timeout=timeout
                )
            else:
                priority, timestamp, message = await self.agent_queues[agent_id].get()
            
            # Process message through handlers
            response = await self._process_message(message)
            
            # Mark message as delivered
            if message.id in self.pending_messages:
                del self.pending_messages[message.id]
            
            # Update metrics
            if self.enable_metrics:
                self.metrics['messages_delivered'] += 1
                delivery_time = time.time() - timestamp
                self._update_average_delivery_time(delivery_time)
            
            # Send response if generated
            if response:
                await self.send_message(response)
            
            logging.debug(f"Delivered message {message.id} to {agent_id}")
            return message
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logging.error(f"Error receiving message for {agent_id}: {e}")
            return None
    
    async def receive_broadcast(self, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """
        Receive a broadcast message.
        
        Args:
            timeout: Maximum time to wait for a message
            
        Returns:
            Received broadcast message or None if timeout
        """
        try:
            if timeout:
                priority, timestamp, message = await asyncio.wait_for(
                    self.broadcast_queue.get(),
                    timeout=timeout
                )
            else:
                priority, timestamp, message = await self.broadcast_queue.get()
            
            # Process message through handlers
            response = await self._process_message(message)
            
            # Mark message as delivered
            if message.id in self.pending_messages:
                del self.pending_messages[message.id]
            
            # Update metrics
            if self.enable_metrics:
                self.metrics['messages_delivered'] += 1
                delivery_time = time.time() - timestamp
                self._update_average_delivery_time(delivery_time)
            
            # Send response if generated
            if response:
                await self.send_message(response)
            
            logging.debug(f"Delivered broadcast message {message.id}")
            return message
            
        except asyncio.TimeoutError:
            return None
        except Exception as e:
            logging.error(f"Error receiving broadcast message: {e}")
            return None
    
    def register_handler(self, agent_id: str, handler: MessageHandler) -> None:
        """Register a message handler for a specific agent."""
        self.handlers[agent_id].append(handler)
        logging.debug(f"Registered handler for agent {agent_id}")
    
    def register_global_handler(self, handler: MessageHandler) -> None:
        """Register a global message handler."""
        self.global_handlers.append(handler)
        logging.debug("Registered global message handler")
    
    def add_routing_rule(self, rule: Callable[[AgentMessage], Optional[str]]) -> None:
        """Add a message routing rule."""
        self.routing_rules.append(rule)
    
    def add_message_filter(self, filter_func: Callable[[AgentMessage], bool]) -> None:
        """Add a message filter."""
        self.message_filters.append(filter_func)
    
    async def _process_message(self, message: AgentMessage) -> Optional[AgentMessage]:
        """Process a message through registered handlers."""
        response = None
        
        # Process through global handlers first
        for handler in self.global_handlers:
            if handler.can_handle(message):
                try:
                    handler_response = await handler.handle_message(message)
                    if handler_response and not response:
                        response = handler_response
                except Exception as e:
                    logging.error(f"Error in global handler: {e}")
        
        # Process through agent-specific handlers
        if message.receiver_id and message.receiver_id in self.handlers:
            for handler in self.handlers[message.receiver_id]:
                if handler.can_handle(message):
                    try:
                        handler_response = await handler.handle_message(message)
                        if handler_response and not response:
                            response = handler_response
                    except Exception as e:
                        logging.error(f"Error in agent handler: {e}")
        
        return response
    
    def _apply_filters(self, message: AgentMessage) -> bool:
        """Apply message filters."""
        for filter_func in self.message_filters:
            try:
                if not filter_func(message):
                    return False
            except Exception as e:
                logging.error(f"Error in message filter: {e}")
        return True
    
    def _apply_routing(self, message: AgentMessage) -> Optional[str]:
        """Apply routing rules to determine target agent."""
        for rule in self.routing_rules:
            try:
                target = rule(message)
                if target:
                    return target
            except Exception as e:
                logging.error(f"Error in routing rule: {e}")
        return None
    
    def _store_message(self, message: AgentMessage) -> None:
        """Store message for persistence."""
        self.message_store.append(message)
        
        # Maintain size limit
        if len(self.message_store) > self.max_stored_messages:
            self.message_store = self.message_store[-self.max_stored_messages:]
    
    def _update_average_delivery_time(self, delivery_time: float) -> None:
        """Update average delivery time metric."""
        current_avg = self.metrics['average_delivery_time']
        delivered_count = self.metrics['messages_delivered']
        
        if delivered_count == 1:
            self.metrics['average_delivery_time'] = delivery_time
        else:
            self.metrics['average_delivery_time'] = (
                (current_avg * (delivered_count - 1) + delivery_time) / delivered_count
            )
    
    async def _retry_processor(self) -> None:
        """Background processor for message retries."""
        while not self._shutdown_event.is_set():
            try:
                # Check for messages that need retry
                current_time = time.time()
                messages_to_retry = []
                
                for message_id, message in list(self.pending_messages.items()):
                    # Check if message should be retried
                    if (message.age.total_seconds() > 30 and  # 30 second timeout
                        message.retry_count < message.max_retries):
                        messages_to_retry.append(message)
                
                # Retry messages
                for message in messages_to_retry:
                    message.retry_count += 1
                    await self.send_message(message)
                    
                    if self.enable_metrics:
                        self.metrics['messages_retried'] += 1
                    
                    logging.info(f"Retrying message {message.id} (attempt {message.retry_count})")
                
                # Move failed messages to dead letter queue
                for message_id, message in list(self.pending_messages.items()):
                    if (message.age.total_seconds() > 300 or  # 5 minute total timeout
                        message.retry_count >= message.max_retries):
                        self.dead_letter_queue.append(message)
                        del self.pending_messages[message_id]
                        
                        if self.enable_metrics:
                            self.metrics['messages_failed'] += 1
                        
                        logging.warning(f"Message {message.id} moved to dead letter queue")
                
                await asyncio.sleep(10)  # Check every 10 seconds
                
            except Exception as e:
                logging.error(f"Error in retry processor: {e}")
                await asyncio.sleep(30)
    
    async def _dead_letter_processor(self) -> None:
        """Background processor for dead letter queue."""
        while not self._shutdown_event.is_set():
            try:
                # Process dead letter queue
                # Could implement recovery strategies here
                
                await asyncio.sleep(60)  # Process every minute
                
            except Exception as e:
                logging.error(f"Error in dead letter processor: {e}")
                await asyncio.sleep(120)
    
    async def _metrics_collector(self) -> None:
        """Background metrics collection."""
        while not self._shutdown_event.is_set():
            try:
                # Update queue size metrics
                for agent_id, queue in self.agent_queues.items():
                    self.metrics['queue_sizes'][agent_id] = queue.qsize()
                
                self.metrics['queue_sizes']['broadcast'] = self.broadcast_queue.qsize()
                
                await asyncio.sleep(30)  # Collect every 30 seconds
                
            except Exception as e:
                logging.error(f"Error in metrics collector: {e}")
                await asyncio.sleep(60)
    
    async def _queue_maintenance(self) -> None:
        """Background queue maintenance."""
        while not self._shutdown_event.is_set():
            try:
                # Clean up expired messages
                for agent_id, queue in self.agent_queues.items():
                    # This is a simplified approach - in practice, you'd need
                    # a more sophisticated way to clean expired messages from queues
                    pass
                
                await asyncio.sleep(300)  # Maintenance every 5 minutes
                
            except Exception as e:
                logging.error(f"Error in queue maintenance: {e}")
                await asyncio.sleep(600)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current message bus metrics."""
        return {
            'messages_sent': self.metrics['messages_sent'],
            'messages_delivered': self.metrics['messages_delivered'],
            'messages_failed': self.metrics['messages_failed'],
            'messages_retried': self.metrics['messages_retried'],
            'average_delivery_time': self.metrics['average_delivery_time'],
            'pending_messages': len(self.pending_messages),
            'dead_letter_queue_size': len(self.dead_letter_queue),
            'queue_sizes': dict(self.metrics['queue_sizes']),
            'registered_agents': len(self.agent_queues)
        }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the message bus."""
        logging.info("Shutting down MessageBus...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        # Clear queues
        for queue in self.agent_queues.values():
            while not queue.empty():
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
        
        while not self.broadcast_queue.empty():
            try:
                self.broadcast_queue.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        logging.info("MessageBus shutdown complete")


class CoordinationProtocol(ABC):
    """Abstract base class for coordination protocols."""
    
    @abstractmethod
    async def coordinate(self, agents: List[str], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate a task among multiple agents."""
        pass


class ConsensusProtocol(CoordinationProtocol):
    """Consensus-based coordination protocol."""
    
    def __init__(self, message_bus: MessageBus, timeout: int = 60):
        self.message_bus = message_bus
        self.timeout = timeout
    
    async def coordinate(self, agents: List[str], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate using consensus algorithm."""
        consensus_id = str(uuid.uuid4())
        
        # Phase 1: Propose
        proposals = {}
        for agent_id in agents:
            proposal_msg = AgentMessage(
                id=str(uuid.uuid4()),
                sender_id="coordinator",
                receiver_id=agent_id,
                message_type=MessageType.COORDINATION,
                priority=MessagePriority.HIGH,
                payload={
                    'action': 'propose',
                    'consensus_id': consensus_id,
                    'task_data': task_data
                }
            )
            await self.message_bus.send_message(proposal_msg)
        
        # Collect proposals
        start_time = time.time()
        while len(proposals) < len(agents) and (time.time() - start_time) < self.timeout:
            for agent_id in agents:
                if agent_id not in proposals:
                    response = await self.message_bus.receive_message(agent_id, timeout=1.0)
                    if (response and 
                        response.payload.get('consensus_id') == consensus_id and
                        response.payload.get('action') == 'proposal'):
                        proposals[agent_id] = response.payload.get('proposal')
        
        # Phase 2: Decide
        if len(proposals) >= len(agents) // 2 + 1:  # Majority
            # Simple majority vote (could be more sophisticated)
            decision = max(proposals.values(), key=lambda x: list(proposals.values()).count(x))
            
            # Phase 3: Commit
            for agent_id in agents:
                commit_msg = AgentMessage(
                    id=str(uuid.uuid4()),
                    sender_id="coordinator",
                    receiver_id=agent_id,
                    message_type=MessageType.COORDINATION,
                    priority=MessagePriority.HIGH,
                    payload={
                        'action': 'commit',
                        'consensus_id': consensus_id,
                        'decision': decision
                    }
                )
                await self.message_bus.send_message(commit_msg)
            
            return {'success': True, 'decision': decision, 'consensus_id': consensus_id}
        else:
            return {'success': False, 'reason': 'Failed to reach consensus', 'consensus_id': consensus_id}


class LeaderElectionProtocol(CoordinationProtocol):
    """Leader election coordination protocol."""
    
    def __init__(self, message_bus: MessageBus):
        self.message_bus = message_bus
        self.current_leader: Optional[str] = None
    
    async def coordinate(self, agents: List[str], task_data: Dict[str, Any]) -> Dict[str, Any]:
        """Coordinate using leader election."""
        if not self.current_leader or self.current_leader not in agents:
            # Elect new leader
            self.current_leader = await self._elect_leader(agents)
        
        if self.current_leader:
            # Send task to leader
            task_msg = AgentMessage(
                id=str(uuid.uuid4()),
                sender_id="coordinator",
                receiver_id=self.current_leader,
                message_type=MessageType.TASK_REQUEST,
                priority=MessagePriority.HIGH,
                payload=task_data
            )
            await self.message_bus.send_message(task_msg)
            
            return {'success': True, 'leader': self.current_leader}
        else:
            return {'success': False, 'reason': 'Failed to elect leader'}
    
    async def _elect_leader(self, agents: List[str]) -> Optional[str]:
        """Elect a leader from the available agents."""
        # Simple election based on agent ID (could be more sophisticated)
        if agents:
            return min(agents)  # Agent with smallest ID becomes leader
        return None


# Utility functions for creating common message types
def create_task_request(sender_id: str, receiver_id: str, task_data: Dict[str, Any]) -> AgentMessage:
    """Create a task request message."""
    return AgentMessage(
        id=str(uuid.uuid4()),
        sender_id=sender_id,
        receiver_id=receiver_id,
        message_type=MessageType.TASK_REQUEST,
        priority=MessagePriority.NORMAL,
        payload=task_data
    )


def create_status_update(sender_id: str, status_data: Dict[str, Any]) -> AgentMessage:
    """Create a status update broadcast message."""
    return AgentMessage(
        id=str(uuid.uuid4()),
        sender_id=sender_id,
        receiver_id=None,  # Broadcast
        message_type=MessageType.STATUS_UPDATE,
        priority=MessagePriority.LOW,
        payload=status_data
    )


def create_heartbeat(sender_id: str) -> AgentMessage:
    """Create a heartbeat message."""
    return AgentMessage(
        id=str(uuid.uuid4()),
        sender_id=sender_id,
        receiver_id=None,  # Broadcast
        message_type=MessageType.HEARTBEAT,
        priority=MessagePriority.LOW,
        payload={'timestamp': datetime.now().isoformat()}
    )

