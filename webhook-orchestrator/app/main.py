"""
Main FastAPI application for the webhook orchestrator.
"""
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from .core.config import settings
from .core.database import db_manager, create_tables
from .core.logging import get_logger
from .api.endpoints import router as api_router
from .api.monitoring import (
    setup_instrumentation,
    prometheus_metrics_response,
    health_checker,
    metrics_collector,
)
from .tasks.celery_app import check_celery_health

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management."""
    # Startup
    logger.info("Starting webhook orchestrator", version=settings.app_version)
    
    try:
        # Initialize database
        await db_manager.initialize()
        await create_tables()
        
        # Register health checks
        health_checker.register_check("database", check_database_health)
        health_checker.register_check("celery", check_celery_health_async)
        health_checker.register_check("github_api", check_github_api_health)
        
        logger.info("Webhook orchestrator started successfully")
        
        yield
        
    except Exception as e:
        logger.error("Failed to start webhook orchestrator", error=str(e))
        raise
    finally:
        # Shutdown
        logger.info("Shutting down webhook orchestrator")
        await db_manager.close()
        logger.info("Webhook orchestrator shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Advanced webhook orchestrator for GitHub events with Codegen integration",
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
    openapi_url="/openapi.json" if settings.debug else None,
    lifespan=lifespan,
)

# Set up instrumentation
setup_instrumentation(app)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.debug else settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=settings.allowed_hosts,
)


# Custom middleware for metrics and logging
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    """Middleware for collecting request metrics."""
    start_time = asyncio.get_event_loop().time()
    
    # Process request
    response = await call_next(request)
    
    # Calculate duration
    duration = asyncio.get_event_loop().time() - start_time
    
    # Log request
    logger.info(
        "http_request",
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration_ms=duration * 1000,
        user_agent=request.headers.get("user-agent"),
        remote_addr=request.client.host if request.client else None,
    )
    
    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(
        "http_exception",
        status_code=exc.status_code,
        detail=exc.detail,
        path=request.url.path,
        method=request.method,
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "path": request.url.path,
        },
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(
        "unhandled_exception",
        error=str(exc),
        error_type=type(exc).__name__,
        path=request.url.path,
        method=request.method,
        exc_info=True,
    )
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "path": request.url.path,
        },
    )


# Include API routes
app.include_router(api_router, prefix="/api/v1")


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "running",
        "docs_url": "/docs" if settings.debug else None,
        "metrics_url": "/metrics",
        "health_url": "/health",
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Comprehensive health check endpoint."""
    try:
        health_result = await health_checker.run_all_checks()
        
        status_code = 200
        if health_result["status"] == "unhealthy":
            status_code = 503
        elif health_result["status"] == "degraded":
            status_code = 200  # Still serving traffic
        
        return JSONResponse(
            status_code=status_code,
            content=health_result,
        )
        
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
                "timestamp": asyncio.get_event_loop().time(),
            },
        )


# Metrics endpoint
@app.get("/metrics")
async def metrics():
    """Prometheus metrics endpoint."""
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics disabled")
    
    return prometheus_metrics_response()


# Custom OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=settings.app_name,
        version=settings.app_version,
        description="""
        # Webhook Orchestrator API
        
        Advanced webhook orchestrator for GitHub events with Codegen integration.
        
        ## Features
        
        - **Webhook Processing**: Secure GitHub webhook validation and processing
        - **Workflow Orchestration**: Intelligent task coordination and execution
        - **Background Tasks**: Async processing with Celery and Redis
        - **Monitoring**: Comprehensive metrics and health checks
        - **Retry Logic**: Advanced retry mechanisms with circuit breakers
        - **Distributed Tracing**: OpenTelemetry integration for observability
        
        ## Authentication
        
        GitHub webhooks are authenticated using HMAC-SHA256 signatures.
        
        ## Rate Limiting
        
        API endpoints are rate limited to prevent abuse.
        
        ## Error Handling
        
        All errors include detailed information and correlation IDs for debugging.
        """,
        routes=app.routes,
    )
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "GitHubWebhook": {
            "type": "apiKey",
            "in": "header",
            "name": "X-Hub-Signature-256",
            "description": "GitHub webhook HMAC-SHA256 signature",
        }
    }
    
    # Add tags
    openapi_schema["tags"] = [
        {
            "name": "webhooks",
            "description": "GitHub webhook processing endpoints",
        },
        {
            "name": "tasks",
            "description": "Workflow task management endpoints",
        },
        {
            "name": "monitoring",
            "description": "Health checks and metrics endpoints",
        },
        {
            "name": "admin",
            "description": "Administrative endpoints",
        },
    ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Health check functions
async def check_database_health() -> Dict[str, Any]:
    """Check database connectivity."""
    try:
        async with db_manager.get_async_session() as session:
            await session.execute("SELECT 1")
        
        return {"status": "healthy", "message": "Database connection successful"}
        
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_celery_health_async() -> Dict[str, Any]:
    """Async wrapper for Celery health check."""
    try:
        # Run Celery health check in thread pool
        loop = asyncio.get_event_loop()
        is_healthy, message = await loop.run_in_executor(None, check_celery_health)
        
        return {
            "status": "healthy" if is_healthy else "unhealthy",
            "message": message,
        }
        
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


async def check_github_api_health() -> Dict[str, Any]:
    """Check GitHub API connectivity."""
    try:
        import httpx
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                "https://api.github.com/zen",
                timeout=10.0,
            )
            
            if response.status_code == 200:
                return {
                    "status": "healthy",
                    "message": "GitHub API accessible",
                    "zen": response.text.strip(),
                }
            else:
                return {
                    "status": "degraded",
                    "message": f"GitHub API returned {response.status_code}",
                }
                
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        workers=1 if settings.debug else settings.workers,
    )

