"""
Permission model and utilities for fine-grained access control.
Supports dynamic permission evaluation and context-aware authorization.
"""

from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Union
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
import re

from .user_model import Base

class PermissionContext(Base):
    """Context-aware permission evaluation for dynamic authorization."""
    
    __tablename__ = 'permission_contexts'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False, index=True)
    description = Column(Text, nullable=True)
    
    # Context definition
    context_type = Column(String(50), nullable=False)  # time, location, device, etc.
    conditions = Column(JSONB, nullable=False)  # JSON conditions for evaluation
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<PermissionContext(id={self.id}, name={self.name}, type={self.context_type})>"
    
    def evaluate(self, context_data: Dict[str, Any]) -> bool:
        """Evaluate if the current context matches the permission conditions."""
        if not self.is_active:
            return False
        
        return self._evaluate_conditions(self.conditions, context_data)
    
    def _evaluate_conditions(self, conditions: Dict[str, Any], context_data: Dict[str, Any]) -> bool:
        """Recursively evaluate permission conditions."""
        if not isinstance(conditions, dict):
            return False
        
        # Handle logical operators
        if 'and' in conditions:
            return all(self._evaluate_conditions(cond, context_data) for cond in conditions['and'])
        
        if 'or' in conditions:
            return any(self._evaluate_conditions(cond, context_data) for cond in conditions['or'])
        
        if 'not' in conditions:
            return not self._evaluate_conditions(conditions['not'], context_data)
        
        # Handle comparison operators
        for field, condition in conditions.items():
            if field in ['and', 'or', 'not']:
                continue
            
            context_value = context_data.get(field)
            
            if isinstance(condition, dict):
                # Handle complex conditions
                if not self._evaluate_field_condition(context_value, condition):
                    return False
            else:
                # Handle simple equality
                if context_value != condition:
                    return False
        
        return True
    
    def _evaluate_field_condition(self, value: Any, condition: Dict[str, Any]) -> bool:
        """Evaluate a single field condition."""
        for operator, expected in condition.items():
            if operator == 'eq' and value != expected:
                return False
            elif operator == 'ne' and value == expected:
                return False
            elif operator == 'gt' and (value is None or value <= expected):
                return False
            elif operator == 'gte' and (value is None or value < expected):
                return False
            elif operator == 'lt' and (value is None or value >= expected):
                return False
            elif operator == 'lte' and (value is None or value > expected):
                return False
            elif operator == 'in' and value not in expected:
                return False
            elif operator == 'not_in' and value in expected:
                return False
            elif operator == 'regex' and (value is None or not re.match(expected, str(value))):
                return False
            elif operator == 'contains' and (value is None or expected not in str(value)):
                return False
        
        return True

class ResourcePolicy(Base):
    """Resource-specific policies for fine-grained access control."""
    
    __tablename__ = 'resource_policies'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(50), nullable=False, index=True)
    resource_id = Column(String(255), nullable=True, index=True)  # Specific resource or pattern
    
    # Policy definition
    policy_document = Column(JSONB, nullable=False)  # JSON policy document
    is_active = Column(Boolean, default=True)
    priority = Column(Integer, default=0)  # Higher priority policies override lower ones
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    def __repr__(self):
        return f"<ResourcePolicy(id={self.id}, name={self.name}, resource={self.resource_type})>"
    
    def evaluate(self, user_id: str, action: str, context: Dict[str, Any]) -> Optional[bool]:
        """Evaluate policy for a specific user action."""
        if not self.is_active:
            return None
        
        policy = self.policy_document
        
        # Check if policy applies to this action
        if 'actions' in policy:
            if action not in policy['actions'] and '*' not in policy['actions']:
                return None
        
        # Check if policy applies to this user
        if 'principals' in policy:
            principals = policy['principals']
            if isinstance(principals, list):
                if user_id not in principals and '*' not in principals:
                    return None
            elif principals != '*' and principals != user_id:
                return None
        
        # Evaluate conditions
        if 'conditions' in policy:
            context_evaluator = PermissionContext(
                name=f"temp_{self.id}",
                context_type="policy",
                conditions=policy['conditions']
            )
            if not context_evaluator.evaluate(context):
                return None
        
        # Return effect (allow/deny)
        effect = policy.get('effect', 'allow')
        return effect.lower() == 'allow'

class PermissionEvaluator:
    """Central permission evaluation engine."""
    
    def __init__(self, db_session):
        self.db_session = db_session
    
    def check_permission(
        self,
        user_id: str,
        resource_type: str,
        action: str,
        resource_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Comprehensive permission check with context evaluation.
        
        Args:
            user_id: ID of the user requesting access
            resource_type: Type of resource being accessed
            action: Action being performed
            resource_id: Specific resource ID (optional)
            context: Additional context for evaluation
        
        Returns:
            True if permission is granted, False otherwise
        """
        if context is None:
            context = {}
        
        # Add default context
        context.update({
            'user_id': user_id,
            'resource_type': resource_type,
            'action': action,
            'resource_id': resource_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        
        # Get user and roles
        from .user_model import User
        user = self.db_session.query(User).filter(User.id == user_id).first()
        if not user or not user.can_login():
            return False
        
        # Check if user is super admin
        if user.is_admin:
            admin_roles = [role for role in user.roles if role.name == 'super_admin']
            if admin_roles:
                return True
        
        # Evaluate resource policies first (they can override role permissions)
        policy_result = self._evaluate_resource_policies(user_id, resource_type, action, resource_id, context)
        if policy_result is not None:
            return policy_result
        
        # Check role-based permissions
        for role in user.roles:
            if role.has_permission(resource_type, action, resource_id):
                # Additional context validation for the permission
                if self._validate_permission_context(role, resource_type, action, context):
                    return True
        
        return False
    
    def _evaluate_resource_policies(
        self,
        user_id: str,
        resource_type: str,
        action: str,
        resource_id: Optional[str],
        context: Dict[str, Any]
    ) -> Optional[bool]:
        """Evaluate resource-specific policies."""
        policies = self.db_session.query(ResourcePolicy).filter(
            ResourcePolicy.resource_type == resource_type,
            ResourcePolicy.is_active == True
        ).order_by(ResourcePolicy.priority.desc()).all()
        
        # Also check for wildcard policies
        wildcard_policies = self.db_session.query(ResourcePolicy).filter(
            ResourcePolicy.resource_type == '*',
            ResourcePolicy.is_active == True
        ).order_by(ResourcePolicy.priority.desc()).all()
        
        all_policies = policies + wildcard_policies
        
        for policy in all_policies:
            # Check if policy applies to specific resource
            if policy.resource_id and resource_id:
                if not self._resource_matches(policy.resource_id, resource_id):
                    continue
            
            result = policy.evaluate(user_id, action, context)
            if result is not None:
                return result
        
        return None
    
    def _resource_matches(self, pattern: str, resource_id: str) -> bool:
        """Check if resource ID matches the policy pattern."""
        if pattern == '*':
            return True
        
        # Support for regex patterns
        if pattern.startswith('regex:'):
            regex_pattern = pattern[6:]
            return bool(re.match(regex_pattern, resource_id))
        
        # Support for wildcard patterns
        if '*' in pattern:
            regex_pattern = pattern.replace('*', '.*')
            return bool(re.match(f'^{regex_pattern}$', resource_id))
        
        # Exact match
        return pattern == resource_id
    
    def _validate_permission_context(
        self,
        role,
        resource_type: str,
        action: str,
        context: Dict[str, Any]
    ) -> bool:
        """Validate additional context conditions for permissions."""
        # Get permissions that match the resource and action
        matching_permissions = [
            p for p in role.get_all_permissions()
            if p.matches(resource_type, action)
        ]
        
        for permission in matching_permissions:
            if permission.conditions:
                context_evaluator = PermissionContext(
                    name=f"temp_{permission.id}",
                    context_type="permission",
                    conditions=permission.conditions
                )
                if not context_evaluator.evaluate(context):
                    continue
            
            # If we reach here, permission is valid
            return True
        
        return len(matching_permissions) > 0

# Example permission contexts and policies
EXAMPLE_CONTEXTS = {
    "business_hours": {
        "name": "business_hours",
        "description": "Allow access only during business hours",
        "context_type": "time",
        "conditions": {
            "and": [
                {"hour": {"gte": 9, "lt": 17}},
                {"weekday": {"in": [0, 1, 2, 3, 4]}}  # Monday to Friday
            ]
        }
    },
    "secure_network": {
        "name": "secure_network",
        "description": "Allow access only from secure network ranges",
        "context_type": "network",
        "conditions": {
            "or": [
                {"ip_address": {"regex": r"^10\.0\..*"}},
                {"ip_address": {"regex": r"^192\.168\..*"}},
                {"vpn_connected": {"eq": True}}
            ]
        }
    },
    "mfa_required": {
        "name": "mfa_required",
        "description": "Require MFA for sensitive operations",
        "context_type": "security",
        "conditions": {
            "mfa_verified": {"eq": True}
        }
    }
}

EXAMPLE_POLICIES = {
    "admin_full_access": {
        "name": "admin_full_access",
        "resource_type": "*",
        "policy_document": {
            "effect": "allow",
            "actions": ["*"],
            "principals": ["role:admin", "role:super_admin"],
            "conditions": {
                "mfa_verified": {"eq": True}
            }
        }
    },
    "sensitive_data_protection": {
        "name": "sensitive_data_protection",
        "resource_type": "secret",
        "policy_document": {
            "effect": "deny",
            "actions": ["read", "update", "delete"],
            "principals": ["*"],
            "conditions": {
                "and": [
                    {"not": {"mfa_verified": {"eq": True}}},
                    {"resource_classification": {"eq": "sensitive"}}
                ]
            }
        }
    },
    "business_hours_restriction": {
        "name": "business_hours_restriction",
        "resource_type": "system",
        "policy_document": {
            "effect": "deny",
            "actions": ["manage", "delete"],
            "principals": ["*"],
            "conditions": {
                "or": [
                    {"hour": {"lt": 9}},
                    {"hour": {"gte": 17}},
                    {"weekday": {"in": [5, 6]}}  # Weekend
                ]
            }
        }
    }
}

