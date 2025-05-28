"""
Advanced monitoring and observability with Prometheus metrics and distributed tracing.
"""
import time
from typing import Dict, Any, Optional
from functools import wraps
from contextlib import contextmanager

from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    CollectorRegistry,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from opentelemetry import trace, metrics
from opentelemetry.exporter.jaeger.thrift import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from fastapi import Response

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)

# Prometheus metrics registry
registry = CollectorRegistry()

# Webhook metrics
webhook_events_total = Counter(
    "webhook_events_total",
    "Total number of webhook events received",
    ["event_type", "source"],
    registry=registry,
)

webhook_processing_duration = Histogram(
    "webhook_processing_duration_seconds",
    "Time spent processing webhook events",
    ["event_type", "status"],
    registry=registry,
)

webhook_errors_total = Counter(
    "webhook_errors_total",
    "Total number of webhook processing errors",
    ["event_type", "error_type"],
    registry=registry,
)

# Task metrics
workflow_tasks_total = Counter(
    "workflow_tasks_total",
    "Total number of workflow tasks created",
    ["task_type"],
    registry=registry,
)

workflow_task_duration = Histogram(
    "workflow_task_duration_seconds",
    "Time spent executing workflow tasks",
    ["task_type", "status"],
    registry=registry,
)

workflow_task_retries_total = Counter(
    "workflow_task_retries_total",
    "Total number of workflow task retries",
    ["task_type"],
    registry=registry,
)

# Queue metrics
celery_queue_size = Gauge(
    "celery_queue_size",
    "Number of tasks in Celery queues",
    ["queue_name"],
    registry=registry,
)

celery_active_workers = Gauge(
    "celery_active_workers",
    "Number of active Celery workers",
    registry=registry,
)

# System metrics
system_info = Info(
    "system_info",
    "System information",
    registry=registry,
)

database_connections = Gauge(
    "database_connections_active",
    "Number of active database connections",
    registry=registry,
)

# GitHub API metrics
github_api_requests_total = Counter(
    "github_api_requests_total",
    "Total number of GitHub API requests",
    ["endpoint", "status"],
    registry=registry,
)

github_api_rate_limit_remaining = Gauge(
    "github_api_rate_limit_remaining",
    "GitHub API rate limit remaining",
    registry=registry,
)

# Codegen API metrics
codegen_api_requests_total = Counter(
    "codegen_api_requests_total",
    "Total number of Codegen API requests",
    ["endpoint", "status"],
    registry=registry,
)

codegen_agent_tasks_total = Counter(
    "codegen_agent_tasks_total",
    "Total number of Codegen agent tasks triggered",
    ["task_type"],
    registry=registry,
)


class MetricsCollector:
    """Centralized metrics collection and management."""
    
    def __init__(self):
        self.start_time = time.time()
        self._setup_system_info()
    
    def _setup_system_info(self):
        """Set up system information metrics."""
        system_info.info({
            "version": settings.app_version,
            "environment": settings.environment,
            "app_name": settings.app_name,
        })
    
    def record_webhook_event(self, event_type: str, source: str = "github"):
        """Record webhook event reception."""
        webhook_events_total.labels(
            event_type=event_type,
            source=source,
        ).inc()
    
    def record_webhook_processing(
        self,
        event_type: str,
        duration: float,
        status: str = "success",
    ):
        """Record webhook processing metrics."""
        webhook_processing_duration.labels(
            event_type=event_type,
            status=status,
        ).observe(duration)
    
    def record_webhook_error(self, event_type: str, error_type: str):
        """Record webhook processing error."""
        webhook_errors_total.labels(
            event_type=event_type,
            error_type=error_type,
        ).inc()
    
    def record_workflow_task(self, task_type: str):
        """Record workflow task creation."""
        workflow_tasks_total.labels(task_type=task_type).inc()
    
    def record_workflow_task_completion(
        self,
        task_type: str,
        duration: float,
        status: str = "success",
    ):
        """Record workflow task completion."""
        workflow_task_duration.labels(
            task_type=task_type,
            status=status,
        ).observe(duration)
    
    def record_workflow_task_retry(self, task_type: str):
        """Record workflow task retry."""
        workflow_task_retries_total.labels(task_type=task_type).inc()
    
    def update_queue_size(self, queue_name: str, size: int):
        """Update queue size metric."""
        celery_queue_size.labels(queue_name=queue_name).set(size)
    
    def update_active_workers(self, count: int):
        """Update active workers metric."""
        celery_active_workers.set(count)
    
    def update_database_connections(self, count: int):
        """Update database connections metric."""
        database_connections.set(count)
    
    def record_github_api_request(self, endpoint: str, status: str):
        """Record GitHub API request."""
        github_api_requests_total.labels(
            endpoint=endpoint,
            status=status,
        ).inc()
    
    def update_github_rate_limit(self, remaining: int):
        """Update GitHub API rate limit."""
        github_api_rate_limit_remaining.set(remaining)
    
    def record_codegen_api_request(self, endpoint: str, status: str):
        """Record Codegen API request."""
        codegen_api_requests_total.labels(
            endpoint=endpoint,
            status=status,
        ).inc()
    
    def record_codegen_agent_task(self, task_type: str):
        """Record Codegen agent task."""
        codegen_agent_tasks_total.labels(task_type=task_type).inc()
    
    def get_uptime(self) -> float:
        """Get system uptime in seconds."""
        return time.time() - self.start_time


# Global metrics collector
metrics_collector = MetricsCollector()


def setup_tracing():
    """Set up distributed tracing with Jaeger."""
    if not settings.enable_tracing:
        return
    
    # Set up tracer provider
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    # Set up Jaeger exporter if endpoint is configured
    if settings.jaeger_endpoint:
        jaeger_exporter = JaegerExporter(
            agent_host_name=settings.jaeger_endpoint.split("://")[1].split(":")[0],
            agent_port=int(settings.jaeger_endpoint.split(":")[-1]),
        )
        
        span_processor = BatchSpanProcessor(jaeger_exporter)
        trace.get_tracer_provider().add_span_processor(span_processor)
        
        logger.info("Distributed tracing enabled with Jaeger", endpoint=settings.jaeger_endpoint)
    else:
        logger.info("Distributed tracing enabled without Jaeger exporter")


def setup_instrumentation(app):
    """Set up automatic instrumentation for FastAPI, SQLAlchemy, and Redis."""
    if not settings.enable_tracing:
        return
    
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)
    
    # Instrument SQLAlchemy
    SQLAlchemyInstrumentor().instrument()
    
    # Instrument Redis
    RedisInstrumentor().instrument()
    
    logger.info("Automatic instrumentation enabled")


@contextmanager
def trace_operation(operation_name: str, **attributes):
    """Context manager for tracing operations."""
    if not settings.enable_tracing:
        yield
        return
    
    tracer = trace.get_tracer(__name__)
    with tracer.start_as_current_span(operation_name) as span:
        # Add attributes
        for key, value in attributes.items():
            span.set_attribute(key, value)
        
        try:
            yield span
        except Exception as e:
            span.record_exception(e)
            span.set_status(trace.Status(trace.StatusCode.ERROR, str(e)))
            raise


def trace_webhook_processing(func):
    """Decorator for tracing webhook processing."""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract event type from arguments
        event_type = "unknown"
        if len(args) > 0 and hasattr(args[0], 'x_github_event'):
            event_type = args[0].x_github_event
        
        with trace_operation("webhook_processing", event_type=event_type):
            return await func(*args, **kwargs)
    
    return wrapper


def trace_task_execution(func):
    """Decorator for tracing task execution."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Extract task type from function name or arguments
        task_type = func.__name__
        
        with trace_operation("task_execution", task_type=task_type):
            return func(*args, **kwargs)
    
    return wrapper


def metrics_middleware(func):
    """Decorator for collecting metrics on function execution."""
    @wraps(func)
    async def async_wrapper(*args, **kwargs):
        start_time = time.time()
        status = "success"
        
        try:
            result = await func(*args, **kwargs)
            return result
        except Exception as e:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            
            # Record metrics based on function name
            if "webhook" in func.__name__:
                event_type = getattr(args[0], 'x_github_event', 'unknown') if args else 'unknown'
                metrics_collector.record_webhook_processing(event_type, duration, status)
            elif "task" in func.__name__:
                task_type = func.__name__
                metrics_collector.record_workflow_task_completion(task_type, duration, status)
    
    @wraps(func)
    def sync_wrapper(*args, **kwargs):
        start_time = time.time()
        status = "success"
        
        try:
            result = func(*args, **kwargs)
            return result
        except Exception as e:
            status = "error"
            raise
        finally:
            duration = time.time() - start_time
            
            # Record metrics based on function name
            if "task" in func.__name__:
                task_type = func.__name__
                metrics_collector.record_workflow_task_completion(task_type, duration, status)
    
    # Return appropriate wrapper based on function type
    import asyncio
    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def get_prometheus_metrics() -> str:
    """Get Prometheus metrics in text format."""
    return generate_latest(registry).decode('utf-8')


def prometheus_metrics_response() -> Response:
    """Return Prometheus metrics as HTTP response."""
    metrics_data = get_prometheus_metrics()
    return Response(
        content=metrics_data,
        media_type=CONTENT_TYPE_LATEST,
    )


class HealthChecker:
    """Advanced health checking with dependency monitoring."""
    
    def __init__(self):
        self.checks = {}
        self.last_check_time = {}
        self.check_cache_duration = 30  # seconds
    
    def register_check(self, name: str, check_func, cache_duration: int = 30):
        """Register a health check function."""
        self.checks[name] = check_func
        self.last_check_time[name] = 0
    
    async def run_check(self, name: str) -> Dict[str, Any]:
        """Run a specific health check."""
        if name not in self.checks:
            return {"status": "unknown", "error": "Check not found"}
        
        current_time = time.time()
        
        # Use cached result if available and fresh
        if (current_time - self.last_check_time.get(name, 0)) < self.check_cache_duration:
            return getattr(self, f"_cached_{name}", {"status": "unknown"})
        
        try:
            with trace_operation("health_check", check_name=name):
                result = await self.checks[name]()
                result["timestamp"] = current_time
                
                # Cache result
                setattr(self, f"_cached_{name}", result)
                self.last_check_time[name] = current_time
                
                return result
                
        except Exception as e:
            logger.error(f"Health check {name} failed", error=str(e))
            return {
                "status": "unhealthy",
                "error": str(e),
                "timestamp": current_time,
            }
    
    async def run_all_checks(self) -> Dict[str, Any]:
        """Run all registered health checks."""
        results = {}
        overall_status = "healthy"
        
        for name in self.checks:
            result = await self.run_check(name)
            results[name] = result
            
            if result.get("status") == "unhealthy":
                overall_status = "unhealthy"
            elif result.get("status") == "degraded" and overall_status == "healthy":
                overall_status = "degraded"
        
        return {
            "status": overall_status,
            "checks": results,
            "timestamp": time.time(),
            "uptime": metrics_collector.get_uptime(),
        }


# Global health checker
health_checker = HealthChecker()


# Initialize tracing on module import
setup_tracing()

