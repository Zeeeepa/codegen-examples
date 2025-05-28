"""
FastAPI authentication middleware with JWT token handling and session management.
Supports multiple authentication methods and comprehensive security features.
"""

import jwt
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Callable
from fastapi import Request, Response, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import httpx

from ..models.user_model import User, UserSession, APIKey
from ..models.permission_model import PermissionEvaluator
from ..services.token_service import TokenService
from ..services.session_service import SessionService

class AuthenticationMiddleware(BaseHTTPMiddleware):
    """
    Comprehensive authentication middleware for FastAPI.
    Supports JWT tokens, API keys, and session-based authentication.
    """
    
    def __init__(
        self,
        app,
        db_session_factory: Callable,
        token_service: TokenService,
        session_service: SessionService,
        permission_evaluator: PermissionEvaluator,
        excluded_paths: Optional[List[str]] = None,
        api_key_header: str = "X-API-Key",
        require_mfa_paths: Optional[List[str]] = None
    ):
        super().__init__(app)
        self.db_session_factory = db_session_factory
        self.token_service = token_service
        self.session_service = session_service
        self.permission_evaluator = permission_evaluator
        self.api_key_header = api_key_header
        
        # Default excluded paths (public endpoints)
        self.excluded_paths = excluded_paths or [
            "/health",
            "/docs",
            "/openapi.json",
            "/auth/login",
            "/auth/register",
            "/auth/oauth2",
            "/auth/saml",
            "/auth/forgot-password",
            "/auth/reset-password"
        ]
        
        # Paths that require MFA verification
        self.require_mfa_paths = require_mfa_paths or [
            "/admin",
            "/users/delete",
            "/secrets",
            "/system"
        ]
    
    async def dispatch(self, request: Request, call_next):
        """Main middleware dispatch method."""
        # Skip authentication for excluded paths
        if self._is_excluded_path(request.url.path):
            return await call_next(request)
        
        # Get database session
        db_session = self.db_session_factory()
        
        try:
            # Attempt authentication
            auth_result = await self._authenticate_request(request, db_session)
            
            if not auth_result["authenticated"]:
                return self._create_auth_error_response(auth_result["error"])
            
            # Add authentication context to request
            request.state.user = auth_result["user"]
            request.state.session = auth_result.get("session")
            request.state.api_key = auth_result.get("api_key")
            request.state.auth_method = auth_result["auth_method"]
            request.state.db_session = db_session
            
            # Check MFA requirements
            if self._requires_mfa(request.url.path) and not auth_result.get("mfa_verified", False):
                return self._create_mfa_required_response()
            
            # Check permissions
            if not await self._check_permissions(request, auth_result["user"], db_session):
                return self._create_permission_denied_response()
            
            # Update session activity
            if auth_result.get("session"):
                await self._update_session_activity(auth_result["session"], request, db_session)
            
            # Process request
            response = await call_next(request)
            
            # Add security headers
            self._add_security_headers(response)
            
            return response
            
        except Exception as e:
            print(f"Authentication middleware error: {e}")
            return self._create_auth_error_response("Internal authentication error")
        
        finally:
            db_session.close()
    
    def _is_excluded_path(self, path: str) -> bool:
        """Check if path is excluded from authentication."""
        for excluded_path in self.excluded_paths:
            if path.startswith(excluded_path):
                return True
        return False
    
    def _requires_mfa(self, path: str) -> bool:
        """Check if path requires MFA verification."""
        for mfa_path in self.require_mfa_paths:
            if path.startswith(mfa_path):
                return True
        return False
    
    async def _authenticate_request(self, request: Request, db_session) -> Dict[str, Any]:
        """Attempt to authenticate the request using various methods."""
        
        # Try API key authentication first
        api_key_result = await self._authenticate_api_key(request, db_session)
        if api_key_result["authenticated"]:
            return api_key_result
        
        # Try JWT token authentication
        jwt_result = await self._authenticate_jwt(request, db_session)
        if jwt_result["authenticated"]:
            return jwt_result
        
        # Try session authentication
        session_result = await self._authenticate_session(request, db_session)
        if session_result["authenticated"]:
            return session_result
        
        return {"authenticated": False, "error": "No valid authentication found"}
    
    async def _authenticate_api_key(self, request: Request, db_session) -> Dict[str, Any]:
        """Authenticate using API key."""
        api_key = request.headers.get(self.api_key_header)
        if not api_key:
            return {"authenticated": False, "error": "No API key provided"}
        
        # Find API key in database
        api_key_obj = db_session.query(APIKey).filter(
            APIKey.key_hash == self.token_service.hash_api_key(api_key),
            APIKey.is_active == True
        ).first()
        
        if not api_key_obj or not api_key_obj.is_valid:
            return {"authenticated": False, "error": "Invalid API key"}
        
        # Get associated user
        user = db_session.query(User).filter(User.id == api_key_obj.user_id).first()
        if not user or not user.can_login():
            return {"authenticated": False, "error": "API key user not found or inactive"}
        
        # Update API key usage
        api_key_obj.last_used = datetime.now(timezone.utc)
        api_key_obj.usage_count += 1
        db_session.commit()
        
        return {
            "authenticated": True,
            "user": user,
            "api_key": api_key_obj,
            "auth_method": "api_key",
            "mfa_verified": True  # API keys bypass MFA
        }
    
    async def _authenticate_jwt(self, request: Request, db_session) -> Dict[str, Any]:
        """Authenticate using JWT token."""
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            return {"authenticated": False, "error": "No JWT token provided"}
        
        token = auth_header[7:]  # Remove "Bearer " prefix
        
        try:
            # Verify and decode token
            payload = self.token_service.verify_access_token(token)
            if not payload:
                return {"authenticated": False, "error": "Invalid JWT token"}
            
            # Get user from token
            user_id = payload.get("sub")
            user = db_session.query(User).filter(User.id == user_id).first()
            
            if not user or not user.can_login():
                return {"authenticated": False, "error": "User not found or inactive"}
            
            return {
                "authenticated": True,
                "user": user,
                "auth_method": "jwt",
                "mfa_verified": payload.get("mfa_verified", False),
                "token_payload": payload
            }
            
        except Exception as e:
            return {"authenticated": False, "error": f"JWT verification failed: {str(e)}"}
    
    async def _authenticate_session(self, request: Request, db_session) -> Dict[str, Any]:
        """Authenticate using session cookie."""
        session_token = request.cookies.get("session_token")
        if not session_token:
            return {"authenticated": False, "error": "No session token provided"}
        
        # Find session in database
        session = db_session.query(UserSession).filter(
            UserSession.session_token == session_token,
            UserSession.is_active == True
        ).first()
        
        if not session or session.is_expired:
            return {"authenticated": False, "error": "Invalid or expired session"}
        
        # Get associated user
        user = db_session.query(User).filter(User.id == session.user_id).first()
        if not user or not user.can_login():
            return {"authenticated": False, "error": "Session user not found or inactive"}
        
        return {
            "authenticated": True,
            "user": user,
            "session": session,
            "auth_method": "session",
            "mfa_verified": session.is_mfa_verified
        }
    
    async def _check_permissions(self, request: Request, user: User, db_session) -> bool:
        """Check if user has permission to access the requested resource."""
        # Extract resource information from request
        method = request.method.lower()
        path = request.url.path
        
        # Map HTTP methods to actions
        action_mapping = {
            "get": "read",
            "post": "create",
            "put": "update",
            "patch": "update",
            "delete": "delete"
        }
        
        action = action_mapping.get(method, "read")
        
        # Determine resource type from path
        resource_type = self._extract_resource_type(path)
        
        # Build permission context
        context = {
            "ip_address": self._get_client_ip(request),
            "user_agent": request.headers.get("User-Agent"),
            "method": method,
            "path": path,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Check permission
        return self.permission_evaluator.check_permission(
            user_id=str(user.id),
            resource_type=resource_type,
            action=action,
            context=context
        )
    
    def _extract_resource_type(self, path: str) -> str:
        """Extract resource type from request path."""
        # Simple path-based resource type extraction
        path_parts = path.strip("/").split("/")
        
        if not path_parts or path_parts[0] == "":
            return "system"
        
        # Map common paths to resource types
        resource_mapping = {
            "users": "user",
            "roles": "role",
            "permissions": "permission",
            "api-keys": "api_key",
            "tasks": "task",
            "workflows": "workflow",
            "webhooks": "webhook",
            "secrets": "secret",
            "audit": "audit_log",
            "admin": "system"
        }
        
        return resource_mapping.get(path_parts[0], "system")
    
    def _get_client_ip(self, request: Request) -> str:
        """Get client IP address from request."""
        # Check for forwarded headers first
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        # Fall back to direct connection
        if hasattr(request.client, "host"):
            return request.client.host
        
        return "unknown"
    
    async def _update_session_activity(self, session: UserSession, request: Request, db_session):
        """Update session last activity."""
        session.last_activity = datetime.now(timezone.utc)
        session.ip_address = self._get_client_ip(request)
        session.user_agent = request.headers.get("User-Agent")
        db_session.commit()
    
    def _add_security_headers(self, response: Response):
        """Add security headers to response."""
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
    
    def _create_auth_error_response(self, error_message: str) -> JSONResponse:
        """Create authentication error response."""
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={
                "error": "authentication_required",
                "message": error_message,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    def _create_mfa_required_response(self) -> JSONResponse:
        """Create MFA required response."""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "mfa_required",
                "message": "Multi-factor authentication required for this resource",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )
    
    def _create_permission_denied_response(self) -> JSONResponse:
        """Create permission denied response."""
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "error": "permission_denied",
                "message": "Insufficient permissions to access this resource",
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
        )

class RequireAuth:
    """Dependency for requiring authentication in FastAPI endpoints."""
    
    def __init__(self, require_mfa: bool = False, required_permissions: Optional[List[str]] = None):
        self.require_mfa = require_mfa
        self.required_permissions = required_permissions or []
    
    def __call__(self, request: Request) -> User:
        """Dependency callable that returns authenticated user."""
        if not hasattr(request.state, "user"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required"
            )
        
        user = request.state.user
        
        # Check MFA requirement
        if self.require_mfa and not getattr(request.state, "mfa_verified", False):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Multi-factor authentication required"
            )
        
        # Check specific permissions
        if self.required_permissions:
            db_session = request.state.db_session
            permission_evaluator = PermissionEvaluator(db_session)
            
            for permission in self.required_permissions:
                resource_type, action = permission.split(":", 1)
                if not permission_evaluator.check_permission(
                    user_id=str(user.id),
                    resource_type=resource_type,
                    action=action
                ):
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Permission denied: {permission}"
                    )
        
        return user

# Convenience dependency instances
require_auth = RequireAuth()
require_mfa = RequireAuth(require_mfa=True)
require_admin = RequireAuth(required_permissions=["system:manage"])

def require_permission(permission: str):
    """Create a dependency that requires a specific permission."""
    return RequireAuth(required_permissions=[permission])

def require_permissions(*permissions: str):
    """Create a dependency that requires multiple permissions."""
    return RequireAuth(required_permissions=list(permissions))

