"""
Role-based access control (RBAC) models.
Implements hierarchical roles and granular permissions.
"""

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Text, ForeignKey, Table
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid

from .user_model import Base, user_roles

# Association table for many-to-many relationship between roles and permissions
role_permissions = Table(
    'role_permissions',
    Base.metadata,
    Column('role_id', UUID(as_uuid=True), ForeignKey('roles.id'), primary_key=True),
    Column('permission_id', UUID(as_uuid=True), ForeignKey('permissions.id'), primary_key=True)
)

class ResourceType(Enum):
    """Types of resources that can be protected."""
    USER = "user"
    ROLE = "role"
    PERMISSION = "permission"
    API_KEY = "api_key"
    TASK = "task"
    WORKFLOW = "workflow"
    WEBHOOK = "webhook"
    AUDIT_LOG = "audit_log"
    SECRET = "secret"
    SYSTEM = "system"

class Action(Enum):
    """Actions that can be performed on resources."""
    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    EXECUTE = "execute"
    MANAGE = "manage"  # Full control
    APPROVE = "approve"
    AUDIT = "audit"

class Role(Base):
    """Role model for RBAC system."""
    
    __tablename__ = 'roles'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    # Role hierarchy
    parent_role_id = Column(UUID(as_uuid=True), ForeignKey('roles.id'), nullable=True)
    is_system_role = Column(Boolean, default=False)  # Built-in system roles
    is_active = Column(Boolean, default=True)
    
    # Role metadata
    priority = Column(Integer, default=0)  # Higher priority roles override lower ones
    metadata = Column(JSONB, nullable=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    users = relationship("User", secondary=user_roles, back_populates="roles")
    permissions = relationship("Permission", secondary=role_permissions, back_populates="roles")
    parent_role = relationship("Role", remote_side=[id], backref="child_roles")
    
    def __repr__(self):
        return f"<Role(id={self.id}, name={self.name}, active={self.is_active})>"
    
    def get_all_permissions(self) -> List['Permission']:
        """Get all permissions including inherited from parent roles."""
        permissions = set(self.permissions)
        
        # Inherit permissions from parent roles
        current_role = self.parent_role
        while current_role:
            permissions.update(current_role.permissions)
            current_role = current_role.parent_role
        
        return list(permissions)
    
    def has_permission(self, resource_type: str, action: str, resource_id: Optional[str] = None) -> bool:
        """Check if role has specific permission."""
        all_permissions = self.get_all_permissions()
        
        for permission in all_permissions:
            if permission.matches(resource_type, action, resource_id):
                return True
        
        return False

class Permission(Base):
    """Permission model for fine-grained access control."""
    
    __tablename__ = 'permissions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    display_name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    
    # Permission definition
    resource_type = Column(String(50), nullable=False)  # What resource this applies to
    action = Column(String(50), nullable=False)  # What action is allowed
    resource_id = Column(String(255), nullable=True)  # Specific resource ID (optional)
    
    # Permission constraints
    conditions = Column(JSONB, nullable=True)  # Additional conditions (e.g., time-based, IP-based)
    is_system_permission = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Relationships
    roles = relationship("Role", secondary=role_permissions, back_populates="permissions")
    
    def __repr__(self):
        return f"<Permission(id={self.id}, name={self.name}, resource={self.resource_type}, action={self.action})>"
    
    def matches(self, resource_type: str, action: str, resource_id: Optional[str] = None) -> bool:
        """Check if this permission matches the given criteria."""
        if not self.is_active:
            return False
        
        # Check resource type
        if self.resource_type != resource_type and self.resource_type != "*":
            return False
        
        # Check action
        if self.action != action and self.action != "*":
            return False
        
        # Check specific resource ID if specified
        if self.resource_id and resource_id and self.resource_id != resource_id:
            return False
        
        # TODO: Implement condition checking (time-based, IP-based, etc.)
        
        return True

# Predefined system roles and permissions
SYSTEM_ROLES = {
    "super_admin": {
        "display_name": "Super Administrator",
        "description": "Full system access with all permissions",
        "permissions": ["*:*"]
    },
    "admin": {
        "display_name": "Administrator",
        "description": "Administrative access to most system functions",
        "permissions": [
            "user:*", "role:*", "permission:read",
            "task:*", "workflow:*", "webhook:*",
            "audit_log:read", "secret:read"
        ]
    },
    "developer": {
        "display_name": "Developer",
        "description": "Development and deployment access",
        "permissions": [
            "task:*", "workflow:*", "webhook:*",
            "user:read", "audit_log:read"
        ]
    },
    "operator": {
        "display_name": "Operator",
        "description": "Operational monitoring and basic management",
        "permissions": [
            "task:read", "task:execute", "workflow:read", "workflow:execute",
            "webhook:read", "audit_log:read", "user:read"
        ]
    },
    "viewer": {
        "display_name": "Viewer",
        "description": "Read-only access to most resources",
        "permissions": [
            "task:read", "workflow:read", "webhook:read",
            "user:read", "audit_log:read"
        ]
    },
    "api_user": {
        "display_name": "API User",
        "description": "Programmatic access for external integrations",
        "permissions": [
            "task:create", "task:read", "task:update",
            "workflow:execute", "webhook:create"
        ]
    }
}

SYSTEM_PERMISSIONS = [
    # User management
    ("user:create", "Create new users"),
    ("user:read", "View user information"),
    ("user:update", "Update user information"),
    ("user:delete", "Delete users"),
    ("user:manage", "Full user management"),
    
    # Role management
    ("role:create", "Create new roles"),
    ("role:read", "View role information"),
    ("role:update", "Update role information"),
    ("role:delete", "Delete roles"),
    ("role:manage", "Full role management"),
    
    # Permission management
    ("permission:read", "View permission information"),
    ("permission:manage", "Full permission management"),
    
    # API key management
    ("api_key:create", "Create API keys"),
    ("api_key:read", "View API key information"),
    ("api_key:update", "Update API keys"),
    ("api_key:delete", "Delete API keys"),
    ("api_key:manage", "Full API key management"),
    
    # Task management
    ("task:create", "Create new tasks"),
    ("task:read", "View task information"),
    ("task:update", "Update task information"),
    ("task:delete", "Delete tasks"),
    ("task:execute", "Execute tasks"),
    ("task:manage", "Full task management"),
    
    # Workflow management
    ("workflow:create", "Create new workflows"),
    ("workflow:read", "View workflow information"),
    ("workflow:update", "Update workflow information"),
    ("workflow:delete", "Delete workflows"),
    ("workflow:execute", "Execute workflows"),
    ("workflow:manage", "Full workflow management"),
    
    # Webhook management
    ("webhook:create", "Create new webhooks"),
    ("webhook:read", "View webhook information"),
    ("webhook:update", "Update webhook information"),
    ("webhook:delete", "Delete webhooks"),
    ("webhook:manage", "Full webhook management"),
    
    # Audit log access
    ("audit_log:read", "View audit logs"),
    ("audit_log:audit", "Perform audit operations"),
    
    # Secret management
    ("secret:read", "View secret information"),
    ("secret:create", "Create new secrets"),
    ("secret:update", "Update secrets"),
    ("secret:delete", "Delete secrets"),
    ("secret:manage", "Full secret management"),
    
    # System administration
    ("system:manage", "Full system administration"),
    ("system:audit", "System audit access"),
    
    # Wildcard permissions
    ("*:*", "All permissions on all resources"),
]

