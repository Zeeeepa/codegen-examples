"""
Comprehensive audit logging system for security and compliance.
Supports structured logging, event correlation, and compliance reporting.
"""

import json
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from enum import Enum
from dataclasses import dataclass, asdict
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor

Base = declarative_base()

class AuditEventType(Enum):
    """Types of audit events."""
    # Authentication events
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILURE = "login_failure"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"
    MFA_SETUP = "mfa_setup"
    MFA_VERIFICATION = "mfa_verification"
    
    # Authorization events
    PERMISSION_GRANTED = "permission_granted"
    PERMISSION_DENIED = "permission_denied"
    ROLE_ASSIGNED = "role_assigned"
    ROLE_REMOVED = "role_removed"
    
    # Resource access events
    RESOURCE_CREATE = "resource_create"
    RESOURCE_READ = "resource_read"
    RESOURCE_UPDATE = "resource_update"
    RESOURCE_DELETE = "resource_delete"
    
    # Administrative events
    USER_CREATE = "user_create"
    USER_UPDATE = "user_update"
    USER_DELETE = "user_delete"
    USER_SUSPEND = "user_suspend"
    USER_ACTIVATE = "user_activate"
    
    # API events
    API_KEY_CREATE = "api_key_create"
    API_KEY_DELETE = "api_key_delete"
    API_REQUEST = "api_request"
    
    # Secret management events
    SECRET_CREATE = "secret_create"
    SECRET_READ = "secret_read"
    SECRET_UPDATE = "secret_update"
    SECRET_DELETE = "secret_delete"
    SECRET_ROTATE = "secret_rotate"
    
    # System events
    SYSTEM_START = "system_start"
    SYSTEM_STOP = "system_stop"
    CONFIG_CHANGE = "config_change"
    BACKUP_CREATE = "backup_create"
    BACKUP_RESTORE = "backup_restore"
    
    # Security events
    SECURITY_ALERT = "security_alert"
    INTRUSION_ATTEMPT = "intrusion_attempt"
    VULNERABILITY_DETECTED = "vulnerability_detected"
    COMPLIANCE_VIOLATION = "compliance_violation"

class AuditSeverity(Enum):
    """Severity levels for audit events."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class AuditEvent:
    """Structured audit event data."""
    event_id: str
    event_type: AuditEventType
    severity: AuditSeverity
    timestamp: datetime
    user_id: Optional[str]
    session_id: Optional[str]
    ip_address: Optional[str]
    user_agent: Optional[str]
    resource_type: Optional[str]
    resource_id: Optional[str]
    action: Optional[str]
    outcome: str  # success, failure, error
    message: str
    details: Dict[str, Any]
    correlation_id: Optional[str]
    compliance_tags: List[str]

class AuditLog(Base):
    """Database model for audit logs."""
    
    __tablename__ = 'audit_logs'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    severity = Column(String(20), nullable=False, index=True)
    
    # Timestamp information
    timestamp = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # User and session information
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=True, index=True)
    session_id = Column(String(255), nullable=True, index=True)
    
    # Request information
    ip_address = Column(String(45), nullable=True, index=True)  # IPv6 support
    user_agent = Column(Text, nullable=True)
    
    # Resource information
    resource_type = Column(String(100), nullable=True, index=True)
    resource_id = Column(String(255), nullable=True, index=True)
    action = Column(String(100), nullable=True, index=True)
    
    # Event outcome and details
    outcome = Column(String(20), nullable=False, index=True)
    message = Column(Text, nullable=False)
    details = Column(JSONB, nullable=True)
    
    # Correlation and compliance
    correlation_id = Column(String(255), nullable=True, index=True)
    compliance_tags = Column(JSONB, nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    user = relationship("User", back_populates="audit_logs")
    
    def __repr__(self):
        return f"<AuditLog(id={self.id}, event_type={self.event_type}, user_id={self.user_id})>"

class AuditLogger:
    """
    Comprehensive audit logging service with async processing.
    Supports structured logging, event correlation, and compliance tracking.
    """
    
    def __init__(
        self,
        db_session_factory,
        enable_async: bool = True,
        max_workers: int = 4,
        batch_size: int = 100,
        flush_interval: int = 5
    ):
        self.db_session_factory = db_session_factory
        self.enable_async = enable_async
        self.max_workers = max_workers
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        
        # Async processing
        self.executor = ThreadPoolExecutor(max_workers=max_workers) if enable_async else None
        self.event_queue = asyncio.Queue() if enable_async else None
        self.processing_task = None
        
        # Event correlation
        self.correlation_context = {}
        
        # Compliance mappings
        self.compliance_mappings = self._init_compliance_mappings()
        
        # Start async processing if enabled
        if self.enable_async:
            self._start_async_processing()
    
    def _init_compliance_mappings(self) -> Dict[AuditEventType, List[str]]:
        """Initialize compliance framework mappings."""
        return {
            # SOC 2 mappings
            AuditEventType.LOGIN_SUCCESS: ["SOC2-CC6.1", "SOC2-CC6.2"],
            AuditEventType.LOGIN_FAILURE: ["SOC2-CC6.1", "SOC2-CC6.7"],
            AuditEventType.PERMISSION_DENIED: ["SOC2-CC6.3"],
            AuditEventType.USER_CREATE: ["SOC2-CC6.2"],
            AuditEventType.USER_DELETE: ["SOC2-CC6.2"],
            AuditEventType.SECRET_READ: ["SOC2-CC6.1", "SOC2-CC6.7"],
            AuditEventType.CONFIG_CHANGE: ["SOC2-CC8.1"],
            
            # GDPR mappings
            AuditEventType.USER_CREATE: ["GDPR-Art.30"],
            AuditEventType.USER_UPDATE: ["GDPR-Art.30"],
            AuditEventType.USER_DELETE: ["GDPR-Art.17"],
            AuditEventType.RESOURCE_READ: ["GDPR-Art.30"],
            
            # PCI DSS mappings
            AuditEventType.LOGIN_SUCCESS: ["PCI-10.2.1"],
            AuditEventType.LOGIN_FAILURE: ["PCI-10.2.4"],
            AuditEventType.PERMISSION_DENIED: ["PCI-10.2.5"],
            AuditEventType.SECRET_READ: ["PCI-10.2.2"],
            
            # HIPAA mappings
            AuditEventType.LOGIN_SUCCESS: ["HIPAA-164.312(b)"],
            AuditEventType.RESOURCE_READ: ["HIPAA-164.312(b)"],
            AuditEventType.USER_CREATE: ["HIPAA-164.308(a)(5)"],
        }
    
    def _start_async_processing(self):
        """Start async event processing."""
        if self.processing_task is None or self.processing_task.done():
            self.processing_task = asyncio.create_task(self._process_events_async())
    
    async def _process_events_async(self):
        """Async event processing loop."""
        batch = []
        
        while True:
            try:
                # Wait for events with timeout
                try:
                    event = await asyncio.wait_for(
                        self.event_queue.get(),
                        timeout=self.flush_interval
                    )
                    batch.append(event)
                except asyncio.TimeoutError:
                    # Flush batch on timeout
                    if batch:
                        await self._flush_batch(batch)
                        batch = []
                    continue
                
                # Flush batch when it reaches max size
                if len(batch) >= self.batch_size:
                    await self._flush_batch(batch)
                    batch = []
                    
            except Exception as e:
                print(f"Error in async audit processing: {e}")
                await asyncio.sleep(1)
    
    async def _flush_batch(self, events: List[AuditEvent]):
        """Flush batch of events to database."""
        if not events:
            return
        
        def write_batch():
            db_session = self.db_session_factory()
            try:
                for event in events:
                    audit_log = AuditLog(
                        event_id=event.event_id,
                        event_type=event.event_type.value,
                        severity=event.severity.value,
                        timestamp=event.timestamp,
                        user_id=event.user_id,
                        session_id=event.session_id,
                        ip_address=event.ip_address,
                        user_agent=event.user_agent,
                        resource_type=event.resource_type,
                        resource_id=event.resource_id,
                        action=event.action,
                        outcome=event.outcome,
                        message=event.message,
                        details=event.details,
                        correlation_id=event.correlation_id,
                        compliance_tags=event.compliance_tags
                    )
                    db_session.add(audit_log)
                
                db_session.commit()
                
            except Exception as e:
                db_session.rollback()
                print(f"Error writing audit batch: {e}")
            finally:
                db_session.close()
        
        # Execute in thread pool
        if self.executor:
            await asyncio.get_event_loop().run_in_executor(self.executor, write_batch)
        else:
            write_batch()
    
    def log_event(
        self,
        event_type: AuditEventType,
        message: str,
        severity: AuditSeverity = AuditSeverity.MEDIUM,
        user_id: Optional[str] = None,
        session_id: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
        resource_type: Optional[str] = None,
        resource_id: Optional[str] = None,
        action: Optional[str] = None,
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None
    ):
        """
        Log an audit event.
        
        Args:
            event_type: Type of audit event
            message: Human-readable event message
            severity: Event severity level
            user_id: ID of user associated with event
            session_id: Session ID if applicable
            ip_address: Client IP address
            user_agent: Client user agent
            resource_type: Type of resource accessed
            resource_id: ID of specific resource
            action: Action performed
            outcome: Event outcome (success, failure, error)
            details: Additional event details
            correlation_id: ID for correlating related events
        """
        # Generate event ID
        event_id = str(uuid.uuid4())
        
        # Get compliance tags
        compliance_tags = self.compliance_mappings.get(event_type, [])
        
        # Create audit event
        event = AuditEvent(
            event_id=event_id,
            event_type=event_type,
            severity=severity,
            timestamp=datetime.now(timezone.utc),
            user_id=user_id,
            session_id=session_id,
            ip_address=ip_address,
            user_agent=user_agent,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            message=message,
            details=details or {},
            correlation_id=correlation_id,
            compliance_tags=compliance_tags
        )
        
        # Process event
        if self.enable_async and self.event_queue:
            # Add to async queue
            try:
                self.event_queue.put_nowait(event)
            except asyncio.QueueFull:
                # Fallback to sync processing
                self._write_event_sync(event)
        else:
            # Sync processing
            self._write_event_sync(event)
    
    def _write_event_sync(self, event: AuditEvent):
        """Write event synchronously to database."""
        db_session = self.db_session_factory()
        try:
            audit_log = AuditLog(
                event_id=event.event_id,
                event_type=event.event_type.value,
                severity=event.severity.value,
                timestamp=event.timestamp,
                user_id=event.user_id,
                session_id=event.session_id,
                ip_address=event.ip_address,
                user_agent=event.user_agent,
                resource_type=event.resource_type,
                resource_id=event.resource_id,
                action=event.action,
                outcome=event.outcome,
                message=event.message,
                details=event.details,
                correlation_id=event.correlation_id,
                compliance_tags=event.compliance_tags
            )
            
            db_session.add(audit_log)
            db_session.commit()
            
        except Exception as e:
            db_session.rollback()
            print(f"Error writing audit event: {e}")
        finally:
            db_session.close()
    
    def log_authentication_event(
        self,
        event_type: AuditEventType,
        user_id: Optional[str],
        ip_address: str,
        user_agent: str,
        outcome: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authentication-related events."""
        severity = AuditSeverity.HIGH if outcome == "failure" else AuditSeverity.MEDIUM
        
        self.log_event(
            event_type=event_type,
            message=f"Authentication event: {event_type.value}",
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent,
            outcome=outcome,
            details=details
        )
    
    def log_authorization_event(
        self,
        user_id: str,
        resource_type: str,
        resource_id: Optional[str],
        action: str,
        outcome: str,
        ip_address: str,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log authorization-related events."""
        event_type = AuditEventType.PERMISSION_GRANTED if outcome == "success" else AuditEventType.PERMISSION_DENIED
        severity = AuditSeverity.HIGH if outcome == "failure" else AuditSeverity.LOW
        
        self.log_event(
            event_type=event_type,
            message=f"Authorization {outcome}: {action} on {resource_type}",
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            details=details
        )
    
    def log_resource_access(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        action: str,
        ip_address: str,
        outcome: str = "success",
        details: Optional[Dict[str, Any]] = None
    ):
        """Log resource access events."""
        # Map action to event type
        action_mapping = {
            "create": AuditEventType.RESOURCE_CREATE,
            "read": AuditEventType.RESOURCE_READ,
            "update": AuditEventType.RESOURCE_UPDATE,
            "delete": AuditEventType.RESOURCE_DELETE
        }
        
        event_type = action_mapping.get(action, AuditEventType.RESOURCE_READ)
        severity = AuditSeverity.HIGH if action == "delete" else AuditSeverity.MEDIUM
        
        self.log_event(
            event_type=event_type,
            message=f"Resource access: {action} {resource_type} {resource_id}",
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            resource_type=resource_type,
            resource_id=resource_id,
            action=action,
            outcome=outcome,
            details=details
        )
    
    def log_security_event(
        self,
        event_type: AuditEventType,
        message: str,
        severity: AuditSeverity,
        ip_address: Optional[str] = None,
        user_id: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        """Log security-related events."""
        self.log_event(
            event_type=event_type,
            message=message,
            severity=severity,
            user_id=user_id,
            ip_address=ip_address,
            outcome="alert",
            details=details
        )
    
    def create_correlation_context(self, correlation_id: Optional[str] = None) -> str:
        """Create a correlation context for related events."""
        if not correlation_id:
            correlation_id = str(uuid.uuid4())
        
        self.correlation_context[correlation_id] = {
            "created_at": datetime.now(timezone.utc),
            "events": []
        }
        
        return correlation_id
    
    def search_events(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        event_types: Optional[List[AuditEventType]] = None,
        user_id: Optional[str] = None,
        resource_type: Optional[str] = None,
        severity: Optional[AuditSeverity] = None,
        outcome: Optional[str] = None,
        limit: int = 1000
    ) -> List[AuditLog]:
        """Search audit events with filters."""
        db_session = self.db_session_factory()
        try:
            query = db_session.query(AuditLog)
            
            if start_time:
                query = query.filter(AuditLog.timestamp >= start_time)
            
            if end_time:
                query = query.filter(AuditLog.timestamp <= end_time)
            
            if event_types:
                event_type_values = [et.value for et in event_types]
                query = query.filter(AuditLog.event_type.in_(event_type_values))
            
            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            
            if resource_type:
                query = query.filter(AuditLog.resource_type == resource_type)
            
            if severity:
                query = query.filter(AuditLog.severity == severity.value)
            
            if outcome:
                query = query.filter(AuditLog.outcome == outcome)
            
            return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
            
        finally:
            db_session.close()
    
    def close(self):
        """Close the audit logger and cleanup resources."""
        if self.processing_task:
            self.processing_task.cancel()
        
        if self.executor:
            self.executor.shutdown(wait=True)

# Convenience functions for common audit events
def log_login_success(logger: AuditLogger, user_id: str, ip_address: str, user_agent: str):
    """Log successful login."""
    logger.log_authentication_event(
        AuditEventType.LOGIN_SUCCESS,
        user_id,
        ip_address,
        user_agent,
        "success"
    )

def log_login_failure(logger: AuditLogger, email: str, ip_address: str, user_agent: str, reason: str):
    """Log failed login attempt."""
    logger.log_authentication_event(
        AuditEventType.LOGIN_FAILURE,
        None,
        ip_address,
        user_agent,
        "failure",
        {"email": email, "reason": reason}
    )

def log_permission_denied(logger: AuditLogger, user_id: str, resource: str, action: str, ip_address: str):
    """Log permission denied event."""
    logger.log_authorization_event(
        user_id,
        resource,
        None,
        action,
        "failure",
        ip_address,
        {"reason": "insufficient_permissions"}
    )

