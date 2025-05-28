"""
Advanced retry logic with exponential backoff and circuit breaker patterns.
"""
import asyncio
import time
from typing import Any, Callable, Dict, Optional, Type, Union
from functools import wraps
from enum import Enum

from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
    after_log,
)
from circuitbreaker import circuit

from ..core.config import settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class RetryStrategy(Enum):
    """Retry strategy types."""
    EXPONENTIAL = "exponential"
    LINEAR = "linear"
    FIXED = "fixed"
    FIBONACCI = "fibonacci"


class CircuitBreakerState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class RetryableException(Exception):
    """Base exception for retryable errors."""
    pass


class NonRetryableException(Exception):
    """Base exception for non-retryable errors."""
    pass


class RateLimitException(RetryableException):
    """Exception for rate limit errors."""
    pass


class ServiceUnavailableException(RetryableException):
    """Exception for service unavailable errors."""
    pass


class AuthenticationException(NonRetryableException):
    """Exception for authentication errors."""
    pass


class ValidationException(NonRetryableException):
    """Exception for validation errors."""
    pass


def exponential_backoff_retry(
    max_attempts: int = None,
    base_delay: float = 1.0,
    max_delay: float = None,
    exponential_base: float = 2.0,
    jitter: bool = True,
    retryable_exceptions: tuple = (RetryableException,),
):
    """
    Decorator for exponential backoff retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential calculation
        jitter: Whether to add jitter to delay
        retryable_exceptions: Tuple of exceptions to retry on
    """
    max_attempts = max_attempts or settings.max_retries
    max_delay = max_delay or settings.retry_max_delay
    
    return retry(
        stop=stop_after_attempt(max_attempts),
        wait=wait_exponential(
            multiplier=base_delay,
            max=max_delay,
            exp_base=exponential_base,
        ),
        retry=retry_if_exception_type(retryable_exceptions),
        before_sleep=before_sleep_log(logger, logger.level),
        after=after_log(logger, logger.level),
    )


def circuit_breaker(
    failure_threshold: int = None,
    recovery_timeout: int = None,
    expected_exception: Type[Exception] = Exception,
    name: str = None,
):
    """
    Circuit breaker decorator.
    
    Args:
        failure_threshold: Number of failures before opening circuit
        recovery_timeout: Time in seconds before attempting recovery
        expected_exception: Exception type to count as failure
        name: Circuit breaker name for monitoring
    """
    failure_threshold = failure_threshold or settings.circuit_breaker_failure_threshold
    recovery_timeout = recovery_timeout or settings.circuit_breaker_recovery_timeout
    
    return circuit(
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        expected_exception=expected_exception,
        name=name,
    )


class RetryManager:
    """Advanced retry manager with multiple strategies."""
    
    def __init__(self):
        self.retry_stats = {}
        self.circuit_breakers = {}
    
    def get_retry_delay(
        self,
        attempt: int,
        strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
        base_delay: float = 1.0,
        max_delay: float = 300.0,
        exponential_base: float = 2.0,
    ) -> float:
        """Calculate retry delay based on strategy."""
        if strategy == RetryStrategy.EXPONENTIAL:
            delay = base_delay * (exponential_base ** (attempt - 1))
        elif strategy == RetryStrategy.LINEAR:
            delay = base_delay * attempt
        elif strategy == RetryStrategy.FIXED:
            delay = base_delay
        elif strategy == RetryStrategy.FIBONACCI:
            delay = base_delay * self._fibonacci(attempt)
        else:
            delay = base_delay
        
        return min(delay, max_delay)
    
    def _fibonacci(self, n: int) -> int:
        """Calculate Fibonacci number."""
        if n <= 1:
            return n
        return self._fibonacci(n - 1) + self._fibonacci(n - 2)
    
    def should_retry(
        self,
        exception: Exception,
        attempt: int,
        max_attempts: int,
        retryable_exceptions: tuple = (RetryableException,),
    ) -> bool:
        """Determine if operation should be retried."""
        if attempt >= max_attempts:
            return False
        
        if isinstance(exception, retryable_exceptions):
            return True
        
        # Check for specific error patterns
        error_message = str(exception).lower()
        
        # Rate limiting
        if any(keyword in error_message for keyword in ["rate limit", "too many requests", "429"]):
            return True
        
        # Temporary service issues
        if any(keyword in error_message for keyword in ["timeout", "connection", "503", "502", "504"]):
            return True
        
        return False
    
    def record_attempt(self, operation_name: str, success: bool, duration: float):
        """Record retry attempt statistics."""
        if operation_name not in self.retry_stats:
            self.retry_stats[operation_name] = {
                "total_attempts": 0,
                "successful_attempts": 0,
                "failed_attempts": 0,
                "total_duration": 0.0,
                "avg_duration": 0.0,
            }
        
        stats = self.retry_stats[operation_name]
        stats["total_attempts"] += 1
        stats["total_duration"] += duration
        stats["avg_duration"] = stats["total_duration"] / stats["total_attempts"]
        
        if success:
            stats["successful_attempts"] += 1
        else:
            stats["failed_attempts"] += 1
    
    def get_stats(self, operation_name: str = None) -> Dict[str, Any]:
        """Get retry statistics."""
        if operation_name:
            return self.retry_stats.get(operation_name, {})
        return self.retry_stats


# Global retry manager
retry_manager = RetryManager()


def resilient_task(
    max_retries: int = None,
    retry_strategy: RetryStrategy = RetryStrategy.EXPONENTIAL,
    base_delay: float = 1.0,
    max_delay: float = None,
    circuit_breaker_enabled: bool = True,
    retryable_exceptions: tuple = (RetryableException,),
):
    """
    Decorator for resilient task execution with retry and circuit breaker.
    
    Args:
        max_retries: Maximum number of retries
        retry_strategy: Retry strategy to use
        base_delay: Base delay between retries
        max_delay: Maximum delay between retries
        circuit_breaker_enabled: Whether to enable circuit breaker
        retryable_exceptions: Exceptions to retry on
    """
    max_retries = max_retries or settings.max_retries
    max_delay = max_delay or settings.retry_max_delay
    
    def decorator(func: Callable) -> Callable:
        operation_name = f"{func.__module__}.{func.__name__}"
        
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            attempt = 0
            last_exception = None
            start_time = time.time()
            
            while attempt < max_retries:
                attempt += 1
                
                try:
                    # Execute function
                    if asyncio.iscoroutinefunction(func):
                        result = await func(*args, **kwargs)
                    else:
                        result = func(*args, **kwargs)
                    
                    # Record successful attempt
                    duration = time.time() - start_time
                    retry_manager.record_attempt(operation_name, True, duration)
                    
                    if attempt > 1:
                        logger.info(
                            "retry_success",
                            operation=operation_name,
                            attempt=attempt,
                            duration=duration,
                        )
                    
                    return result
                    
                except Exception as e:
                    last_exception = e
                    
                    # Check if should retry
                    if not retry_manager.should_retry(e, attempt, max_retries, retryable_exceptions):
                        logger.error(
                            "retry_failed_non_retryable",
                            operation=operation_name,
                            attempt=attempt,
                            error=str(e),
                            error_type=type(e).__name__,
                        )
                        break
                    
                    # Calculate delay
                    delay = retry_manager.get_retry_delay(
                        attempt,
                        retry_strategy,
                        base_delay,
                        max_delay,
                    )
                    
                    logger.warning(
                        "retry_attempt",
                        operation=operation_name,
                        attempt=attempt,
                        max_attempts=max_retries,
                        delay=delay,
                        error=str(e),
                        error_type=type(e).__name__,
                    )
                    
                    # Wait before retry
                    if attempt < max_retries:
                        await asyncio.sleep(delay)
            
            # All retries exhausted
            duration = time.time() - start_time
            retry_manager.record_attempt(operation_name, False, duration)
            
            logger.error(
                "retry_exhausted",
                operation=operation_name,
                attempts=attempt,
                duration=duration,
                final_error=str(last_exception),
            )
            
            raise last_exception
        
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # For sync functions, convert to async and run
            async def async_func():
                return func(*args, **kwargs)
            
            return asyncio.run(async_wrapper())
        
        # Return appropriate wrapper based on function type
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


# Predefined retry decorators for common use cases
github_api_retry = resilient_task(
    max_retries=5,
    retry_strategy=RetryStrategy.EXPONENTIAL,
    base_delay=1.0,
    max_delay=60.0,
    retryable_exceptions=(RateLimitException, ServiceUnavailableException, ConnectionError),
)

codegen_api_retry = resilient_task(
    max_retries=3,
    retry_strategy=RetryStrategy.EXPONENTIAL,
    base_delay=2.0,
    max_delay=120.0,
    retryable_exceptions=(ServiceUnavailableException, ConnectionError),
)

database_retry = resilient_task(
    max_retries=3,
    retry_strategy=RetryStrategy.LINEAR,
    base_delay=0.5,
    max_delay=5.0,
    retryable_exceptions=(ConnectionError,),
)

