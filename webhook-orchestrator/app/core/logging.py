"""
Structured logging configuration with OpenTelemetry integration.
"""
import logging
import sys
from typing import Any, Dict
import structlog
from opentelemetry import trace
from opentelemetry.instrumentation.logging import LoggingInstrumentor

from .config import settings


def configure_logging() -> None:
    """Configure structured logging with OpenTelemetry integration."""
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if settings.log_format == "json" 
            else structlog.dev.ConsoleRenderer(),
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
    
    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level),
    )
    
    # Instrument logging with OpenTelemetry
    if settings.enable_tracing:
        LoggingInstrumentor().instrument(set_logging_format=True)


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


class CorrelationIdProcessor:
    """Add correlation ID to log records."""
    
    def __call__(self, logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        # Add trace context if available
        span = trace.get_current_span()
        if span and span.is_recording():
            span_context = span.get_span_context()
            event_dict["trace_id"] = format(span_context.trace_id, "032x")
            event_dict["span_id"] = format(span_context.span_id, "016x")
        
        return event_dict


class WebhookLoggerMixin:
    """Mixin to add webhook-specific logging capabilities."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = get_logger(self.__class__.__name__)
    
    def log_webhook_received(self, event_type: str, delivery_id: str, payload_size: int):
        """Log webhook reception."""
        self.logger.info(
            "webhook_received",
            event_type=event_type,
            delivery_id=delivery_id,
            payload_size=payload_size,
        )
    
    def log_webhook_processed(self, event_type: str, delivery_id: str, processing_time: float):
        """Log successful webhook processing."""
        self.logger.info(
            "webhook_processed",
            event_type=event_type,
            delivery_id=delivery_id,
            processing_time_ms=processing_time * 1000,
        )
    
    def log_webhook_error(self, event_type: str, delivery_id: str, error: Exception):
        """Log webhook processing error."""
        self.logger.error(
            "webhook_error",
            event_type=event_type,
            delivery_id=delivery_id,
            error=str(error),
            error_type=type(error).__name__,
            exc_info=True,
        )
    
    def log_task_created(self, task_id: str, task_type: str, **kwargs):
        """Log task creation."""
        self.logger.info(
            "task_created",
            task_id=task_id,
            task_type=task_type,
            **kwargs,
        )
    
    def log_task_completed(self, task_id: str, task_type: str, execution_time: float):
        """Log task completion."""
        self.logger.info(
            "task_completed",
            task_id=task_id,
            task_type=task_type,
            execution_time_ms=execution_time * 1000,
        )
    
    def log_task_failed(self, task_id: str, task_type: str, error: Exception, retry_count: int):
        """Log task failure."""
        self.logger.error(
            "task_failed",
            task_id=task_id,
            task_type=task_type,
            error=str(error),
            error_type=type(error).__name__,
            retry_count=retry_count,
            exc_info=True,
        )


# Configure logging on module import
configure_logging()

