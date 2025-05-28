"""
Main FastAPI application for the Security & Authentication System.
Integrates all security components into a comprehensive platform.
"""

import os
import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import redis
from prometheus_client import make_asgi_app

# Import our security system components
from auth.middleware.auth_middleware import AuthenticationMiddleware, require_auth
from auth.models.user_model import Base, User
from auth.models.role_model import Role, Permission
from auth.services.token_service import TokenService, create_token_service
from auth.services.session_service import SessionService
from auth.providers.oauth2_provider import create_oauth2_manager
from auth.providers.saml_provider import create_saml_manager
from auth.providers.local_auth import create_local_auth_provider, MFAProvider
from secrets.vault_client import create_vault_client
from audit.audit_logger import AuditLogger, AuditEventType, AuditSeverity
from security.vulnerability_scanner import VulnerabilityScanner
from security.threat_detector import ThreatDetector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost/security_db")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-super-secret-jwt-key")
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")

# Database setup
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Redis setup for rate limiting and caching
redis_client = redis.from_url(REDIS_URL)
limiter = Limiter(key_func=get_remote_address, storage_uri=REDIS_URL)

# Global services
token_service: TokenService = None
audit_logger: AuditLogger = None
oauth2_manager = None
saml_manager = None
local_auth_provider = None
mfa_provider = None
vault_client = None
vulnerability_scanner = None
threat_detector = None

def get_db():
    """Database dependency."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Security & Authentication System...")
    
    # Initialize database tables
    Base.metadata.create_all(bind=engine)
    
    # Initialize global services
    global token_service, audit_logger, oauth2_manager, saml_manager
    global local_auth_provider, mfa_provider, vault_client
    global vulnerability_scanner, threat_detector
    
    # Token service
    token_config = {
        "secret_key": JWT_SECRET_KEY,
        "algorithm": "HS256",
        "access_token_expire_minutes": 15,
        "refresh_token_expire_days": 30,
        "issuer": "ai-workflow-platform",
        "audience": "ai-workflow-platform"
    }
    token_service = create_token_service(token_config)
    
    # Audit logger
    audit_logger = AuditLogger(SessionLocal, enable_async=True)
    
    # OAuth2 manager
    oauth2_config = {
        "google": {
            "client_id": os.getenv("GOOGLE_CLIENT_ID"),
            "client_secret": os.getenv("GOOGLE_CLIENT_SECRET"),
            "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/auth/oauth2/google/callback")
        },
        "github": {
            "client_id": os.getenv("GITHUB_CLIENT_ID"),
            "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
            "redirect_uri": os.getenv("GITHUB_REDIRECT_URI", "http://localhost:8000/auth/oauth2/github/callback")
        },
        "microsoft": {
            "client_id": os.getenv("MICROSOFT_CLIENT_ID"),
            "client_secret": os.getenv("MICROSOFT_CLIENT_SECRET"),
            "redirect_uri": os.getenv("MICROSOFT_REDIRECT_URI", "http://localhost:8000/auth/oauth2/microsoft/callback"),
            "tenant_id": os.getenv("MICROSOFT_TENANT_ID", "common")
        }
    }
    oauth2_manager = create_oauth2_manager(oauth2_config)
    
    # SAML manager
    saml_config = {
        "enterprise": {
            "entity_id": os.getenv("SAML_ENTITY_ID", "https://your-app.com"),
            "acs_url": os.getenv("SAML_ACS_URL", "https://your-app.com/auth/saml/acs"),
            "sso_url": os.getenv("SAML_SSO_URL"),
            "slo_url": os.getenv("SAML_SLO_URL"),
            "idp_cert": os.getenv("SAML_IDP_CERT")
        }
    }
    saml_manager = create_saml_manager(saml_config)
    
    # Local auth provider
    local_auth_config = {
        "password_policy": {
            "min_length": 8,
            "require_uppercase": True,
            "require_lowercase": True,
            "require_digits": True,
            "require_special": True
        },
        "lockout_policy": {
            "max_attempts": 5,
            "lockout_duration_minutes": 30,
            "progressive_lockout": True
        }
    }
    local_auth_provider = create_local_auth_provider(local_auth_config)
    
    # MFA provider
    mfa_provider = MFAProvider("AI Workflow Platform")
    
    # Vault client (optional)
    if os.getenv("VAULT_URL"):
        vault_config = {
            "url": os.getenv("VAULT_URL"),
            "auth_method": "token",
            "auth_config": {"token": os.getenv("VAULT_TOKEN")}
        }
        vault_client = create_vault_client(vault_config)
    
    # Security services
    vulnerability_scanner = VulnerabilityScanner()
    threat_detector = ThreatDetector(redis_client)
    
    logger.info("Security & Authentication System started successfully")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Security & Authentication System...")
    if audit_logger:
        audit_logger.close()
    if vault_client:
        vault_client.close()

# Create FastAPI app
app = FastAPI(
    title="Security & Authentication System",
    description="Comprehensive enterprise-grade security and authentication platform",
    version="1.0.0",
    lifespan=lifespan
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if ENVIRONMENT == "development" else ["https://your-domain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"] if ENVIRONMENT == "development" else ["your-domain.com"]
)

# Add rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Add authentication middleware
session_service = SessionService(SessionLocal, token_service)
from auth.models.permission_model import PermissionEvaluator
permission_evaluator = PermissionEvaluator(SessionLocal())

app.add_middleware(
    AuthenticationMiddleware,
    db_session_factory=SessionLocal,
    token_service=token_service,
    session_service=session_service,
    permission_evaluator=permission_evaluator,
    excluded_paths=[
        "/",
        "/health",
        "/metrics",
        "/docs",
        "/openapi.json",
        "/auth/login",
        "/auth/register",
        "/auth/oauth2",
        "/auth/saml",
        "/auth/forgot-password",
        "/auth/reset-password",
        "/auth/verify-email"
    ]
)

# Add Prometheus metrics
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with audit logging."""
    if audit_logger:
        audit_logger.log_event(
            event_type=AuditEventType.SECURITY_ALERT,
            message=f"HTTP Exception: {exc.status_code} - {exc.detail}",
            severity=AuditSeverity.MEDIUM,
            ip_address=request.client.host if request.client else None,
            details={"status_code": exc.status_code, "detail": exc.detail}
        )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": exc.detail, "status_code": exc.status_code}
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions with audit logging."""
    if audit_logger:
        audit_logger.log_event(
            event_type=AuditEventType.SECURITY_ALERT,
            message=f"Unhandled Exception: {str(exc)}",
            severity=AuditSeverity.HIGH,
            ip_address=request.client.host if request.client else None,
            details={"exception_type": type(exc).__name__, "exception_message": str(exc)}
        )
    
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error", "status_code": 500}
    )

# Health check endpoint
@app.get("/health")
@limiter.limit("10/minute")
async def health_check(request: Request):
    """Health check endpoint."""
    health_status = {
        "status": "healthy",
        "timestamp": "2024-01-01T00:00:00Z",
        "services": {
            "database": "healthy",
            "redis": "healthy",
            "vault": "healthy" if vault_client and vault_client.is_authenticated() else "unavailable"
        }
    }
    
    # Check database connection
    try:
        db = SessionLocal()
        db.execute("SELECT 1")
        db.close()
    except Exception:
        health_status["services"]["database"] = "unhealthy"
        health_status["status"] = "degraded"
    
    # Check Redis connection
    try:
        redis_client.ping()
    except Exception:
        health_status["services"]["redis"] = "unhealthy"
        health_status["status"] = "degraded"
    
    return health_status

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with system information."""
    return {
        "name": "Security & Authentication System",
        "version": "1.0.0",
        "description": "Comprehensive enterprise-grade security and authentication platform",
        "features": [
            "Multi-factor Authentication (MFA)",
            "OAuth2 & SAML Integration",
            "Role-Based Access Control (RBAC)",
            "Secret Management",
            "Comprehensive Audit Logging",
            "Security Scanning & Threat Detection"
        ],
        "endpoints": {
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs",
            "authentication": "/auth/*",
            "admin": "/admin/*"
        }
    }

# Authentication endpoints
from auth.routes import auth_router
app.include_router(auth_router, prefix="/auth", tags=["Authentication"])

# Admin endpoints
from admin.routes import admin_router
app.include_router(admin_router, prefix="/admin", tags=["Administration"])

# User management endpoints
from users.routes import users_router
app.include_router(users_router, prefix="/users", tags=["User Management"])

# Secret management endpoints
from secrets.routes import secrets_router
app.include_router(secrets_router, prefix="/secrets", tags=["Secret Management"])

# Audit endpoints
from audit.routes import audit_router
app.include_router(audit_router, prefix="/audit", tags=["Audit & Compliance"])

# Security endpoints
from security.routes import security_router
app.include_router(security_router, prefix="/security", tags=["Security"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=ENVIRONMENT == "development",
        log_level="info"
    )

