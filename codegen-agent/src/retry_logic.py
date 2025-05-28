#!/usr/bin/env python
"""
Intelligent Retry Logic for Codegen Agent

This module provides sophisticated retry mechanisms with exponential backoff,
adaptive strategies, and failure analysis for robust code generation.
"""

import time
import random
import logging
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple
from enum import Enum
import json


class RetryReason(Enum):
    """Reasons for retry attempts."""
    QUALITY_THRESHOLD = "quality_threshold"
    API_ERROR = "api_error"
    TIMEOUT = "timeout"
    VALIDATION_FAILED = "validation_failed"
    RATE_LIMIT = "rate_limit"
    NETWORK_ERROR = "network_error"
    PARSING_ERROR = "parsing_error"
    CONTEXT_ERROR = "context_error"


class RetryStrategy(Enum):
    """Different retry strategies."""
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"
    ADAPTIVE = "adaptive"
    FIBONACCI = "fibonacci"


@dataclass
class RetryConfig:
    """Configuration for retry behavior."""
    
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_range: float = 0.1
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    
    # Reason-specific configurations
    reason_configs: Dict[RetryReason, Dict[str, Any]] = None
    
    # Circuit breaker settings
    circuit_breaker_enabled: bool = True
    failure_threshold: int = 5
    recovery_timeout: float = 300.0  # 5 minutes
    
    def __post_init__(self):
        if self.reason_configs is None:
            self.reason_configs = {
                RetryReason.QUALITY_THRESHOLD: {
                    'max_retries': 3,
                    'base_delay': 2.0,
                    'strategy': RetryStrategy.EXPONENTIAL_BACKOFF
                },
                RetryReason.API_ERROR: {
                    'max_retries': 5,
                    'base_delay': 1.0,
                    'strategy': RetryStrategy.EXPONENTIAL_BACKOFF
                },
                RetryReason.RATE_LIMIT: {
                    'max_retries': 10,
                    'base_delay': 30.0,
                    'strategy': RetryStrategy.LINEAR_BACKOFF
                },
                RetryReason.NETWORK_ERROR: {
                    'max_retries': 3,
                    'base_delay': 5.0,
                    'strategy': RetryStrategy.EXPONENTIAL_BACKOFF
                },
                RetryReason.TIMEOUT: {
                    'max_retries': 2,
                    'base_delay': 10.0,
                    'strategy': RetryStrategy.FIXED_DELAY
                },
                RetryReason.VALIDATION_FAILED: {
                    'max_retries': 2,
                    'base_delay': 1.0,
                    'strategy': RetryStrategy.FIXED_DELAY
                }
            }


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    
    attempt_number: int
    reason: RetryReason
    delay: float
    timestamp: float
    error_message: str
    context: Dict[str, Any]


@dataclass
class RetryResult:
    """Result of retry operation."""
    
    success: bool
    final_result: Any
    total_attempts: int
    total_time: float
    attempts: List[RetryAttempt]
    final_error: Optional[str] = None


class CircuitBreaker:
    """Circuit breaker for preventing cascading failures."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: float = 300.0):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "closed"  # closed, open, half-open
        
        self.logger = logging.getLogger(__name__)
    
    def can_execute(self) -> bool:
        """Check if execution is allowed."""
        if self.state == "closed":
            return True
        elif self.state == "open":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "half-open"
                self.logger.info("Circuit breaker transitioning to half-open")
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self) -> None:
        """Record a successful execution."""
        if self.state == "half-open":
            self.state = "closed"
            self.failure_count = 0
            self.logger.info("Circuit breaker closed after successful execution")
    
    def record_failure(self) -> None:
        """Record a failed execution."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "open"
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class RetryManager:
    """Advanced retry manager with multiple strategies and circuit breaking."""
    
    def __init__(self, config: Optional[RetryConfig] = None):
        """Initialize retry manager.
        
        Args:
            config: Retry configuration, uses defaults if not provided
        """
        self.config = config or RetryConfig()
        self.circuit_breaker = CircuitBreaker(
            self.config.failure_threshold,
            self.config.recovery_timeout
        ) if self.config.circuit_breaker_enabled else None
        
        self.logger = logging.getLogger(__name__)
        
        # Statistics
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retries': 0,
            'retry_reasons': {reason: 0 for reason in RetryReason},
            'avg_attempts_per_operation': 0.0,
            'avg_time_per_operation': 0.0
        }
    
    def execute_with_retry(
        self,
        operation: Callable,
        operation_args: Tuple = (),
        operation_kwargs: Dict[str, Any] = None,
        retry_reason: RetryReason = RetryReason.API_ERROR,
        context: Dict[str, Any] = None,
        should_retry_func: Optional[Callable[[Exception], bool]] = None
    ) -> RetryResult:
        """Execute an operation with intelligent retry logic.
        
        Args:
            operation: Function to execute
            operation_args: Arguments for the operation
            operation_kwargs: Keyword arguments for the operation
            retry_reason: Reason for potential retries
            context: Additional context for retry decisions
            should_retry_func: Custom function to determine if retry should happen
            
        Returns:
            RetryResult with execution details
        """
        if operation_kwargs is None:
            operation_kwargs = {}
        if context is None:
            context = {}
        
        start_time = time.time()
        attempts = []
        
        # Check circuit breaker
        if self.circuit_breaker and not self.circuit_breaker.can_execute():
            self.logger.warning("Circuit breaker is open, operation blocked")
            return RetryResult(
                success=False,
                final_result=None,
                total_attempts=0,
                total_time=0,
                attempts=[],
                final_error="Circuit breaker is open"
            )
        
        # Get retry configuration for this reason
        reason_config = self.config.reason_configs.get(retry_reason, {})
        max_retries = reason_config.get('max_retries', self.config.max_retries)
        
        last_exception = None
        
        for attempt in range(max_retries + 1):
            try:
                self.logger.debug(f"Executing operation, attempt {attempt + 1}/{max_retries + 1}")
                
                # Execute the operation
                result = operation(*operation_args, **operation_kwargs)
                
                # Success!
                if self.circuit_breaker:
                    self.circuit_breaker.record_success()
                
                total_time = time.time() - start_time
                self._update_stats(True, len(attempts), total_time, retry_reason)
                
                return RetryResult(
                    success=True,
                    final_result=result,
                    total_attempts=attempt + 1,
                    total_time=total_time,
                    attempts=attempts
                )
                
            except Exception as e:
                last_exception = e
                self.logger.warning(f"Operation failed on attempt {attempt + 1}: {e}")
                
                # Check if we should retry
                should_retry = True
                if should_retry_func:
                    should_retry = should_retry_func(e)
                
                if not should_retry or attempt >= max_retries:
                    # No more retries
                    break
                
                # Calculate delay for next attempt
                delay = self._calculate_delay(attempt, retry_reason, reason_config)
                
                # Record this attempt
                attempts.append(RetryAttempt(
                    attempt_number=attempt + 1,
                    reason=retry_reason,
                    delay=delay,
                    timestamp=time.time(),
                    error_message=str(e),
                    context=context.copy()
                ))
                
                # Wait before next attempt
                self.logger.info(f"Retrying in {delay:.2f} seconds...")
                time.sleep(delay)
        
        # All retries failed
        if self.circuit_breaker:
            self.circuit_breaker.record_failure()
        
        total_time = time.time() - start_time
        self._update_stats(False, len(attempts), total_time, retry_reason)
        
        return RetryResult(
            success=False,
            final_result=None,
            total_attempts=len(attempts) + 1,
            total_time=total_time,
            attempts=attempts,
            final_error=str(last_exception) if last_exception else "Unknown error"
        )
    
    def _calculate_delay(
        self,
        attempt: int,
        retry_reason: RetryReason,
        reason_config: Dict[str, Any]
    ) -> float:
        """Calculate delay for the next retry attempt."""
        
        base_delay = reason_config.get('base_delay', self.config.base_delay)
        strategy = RetryStrategy(reason_config.get('strategy', self.config.strategy.value))
        max_delay = reason_config.get('max_delay', self.config.max_delay)
        
        if strategy == RetryStrategy.FIXED_DELAY:
            delay = base_delay
        elif strategy == RetryStrategy.LINEAR_BACKOFF:
            delay = base_delay * (attempt + 1)
        elif strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            exponential_base = reason_config.get('exponential_base', self.config.exponential_base)
            delay = base_delay * (exponential_base ** attempt)
        elif strategy == RetryStrategy.FIBONACCI:
            delay = base_delay * self._fibonacci(attempt + 1)
        elif strategy == RetryStrategy.ADAPTIVE:
            # Adaptive strategy based on recent success/failure patterns
            delay = self._calculate_adaptive_delay(attempt, retry_reason, base_delay)
        else:
            # Default to exponential backoff
            delay = base_delay * (self.config.exponential_base ** attempt)
        
        # Apply maximum delay limit
        delay = min(delay, max_delay)
        
        # Add jitter if enabled
        if self.config.jitter:
            jitter_amount = delay * self.config.jitter_range
            jitter = random.uniform(-jitter_amount, jitter_amount)
            delay = max(0.1, delay + jitter)
        
        return delay
    
    def _fibonacci(self, n: int) -> int:
        """Calculate nth Fibonacci number."""
        if n <= 1:
            return n
        a, b = 0, 1
        for _ in range(2, n + 1):
            a, b = b, a + b
        return b
    
    def _calculate_adaptive_delay(
        self,
        attempt: int,
        retry_reason: RetryReason,
        base_delay: float
    ) -> float:
        """Calculate adaptive delay based on historical patterns."""
        
        # Get recent success rate for this retry reason
        total_for_reason = self.stats['retry_reasons'][retry_reason]
        if total_for_reason == 0:
            # No history, use exponential backoff
            return base_delay * (self.config.exponential_base ** attempt)
        
        # Adjust delay based on success rate
        success_rate = self.stats['successful_operations'] / max(1, self.stats['total_operations'])
        
        if success_rate > 0.8:
            # High success rate, use shorter delays
            multiplier = 0.5 + (attempt * 0.3)
        elif success_rate > 0.5:
            # Medium success rate, use standard delays
            multiplier = 1.0 + (attempt * 0.5)
        else:
            # Low success rate, use longer delays
            multiplier = 2.0 + (attempt * 1.0)
        
        return base_delay * multiplier
    
    def _update_stats(
        self,
        success: bool,
        retry_count: int,
        execution_time: float,
        retry_reason: RetryReason
    ) -> None:
        """Update retry statistics."""
        
        self.stats['total_operations'] += 1
        if success:
            self.stats['successful_operations'] += 1
        else:
            self.stats['failed_operations'] += 1
        
        self.stats['total_retries'] += retry_count
        self.stats['retry_reasons'][retry_reason] += 1
        
        # Update running averages
        total_ops = self.stats['total_operations']
        self.stats['avg_attempts_per_operation'] = (
            (self.stats['avg_attempts_per_operation'] * (total_ops - 1) + retry_count + 1) / total_ops
        )
        self.stats['avg_time_per_operation'] = (
            (self.stats['avg_time_per_operation'] * (total_ops - 1) + execution_time) / total_ops
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get retry statistics."""
        total_ops = self.stats['total_operations']
        success_rate = self.stats['successful_operations'] / max(1, total_ops)
        
        return {
            **self.stats,
            'success_rate': success_rate,
            'circuit_breaker_state': self.circuit_breaker.state if self.circuit_breaker else None,
            'circuit_breaker_failures': self.circuit_breaker.failure_count if self.circuit_breaker else None
        }
    
    def reset_stats(self) -> None:
        """Reset retry statistics."""
        self.stats = {
            'total_operations': 0,
            'successful_operations': 0,
            'failed_operations': 0,
            'total_retries': 0,
            'retry_reasons': {reason: 0 for reason in RetryReason},
            'avg_attempts_per_operation': 0.0,
            'avg_time_per_operation': 0.0
        }
        
        if self.circuit_breaker:
            self.circuit_breaker.failure_count = 0
            self.circuit_breaker.state = "closed"
    
    def configure_for_reason(
        self,
        reason: RetryReason,
        max_retries: Optional[int] = None,
        base_delay: Optional[float] = None,
        strategy: Optional[RetryStrategy] = None
    ) -> None:
        """Configure retry behavior for a specific reason.
        
        Args:
            reason: The retry reason to configure
            max_retries: Maximum number of retries
            base_delay: Base delay between retries
            strategy: Retry strategy to use
        """
        if reason not in self.config.reason_configs:
            self.config.reason_configs[reason] = {}
        
        config = self.config.reason_configs[reason]
        
        if max_retries is not None:
            config['max_retries'] = max_retries
        if base_delay is not None:
            config['base_delay'] = base_delay
        if strategy is not None:
            config['strategy'] = strategy.value
        
        self.logger.info(f"Updated retry configuration for {reason.value}: {config}")


class RetryDecorator:
    """Decorator for adding retry logic to functions."""
    
    def __init__(
        self,
        retry_manager: Optional[RetryManager] = None,
        retry_reason: RetryReason = RetryReason.API_ERROR,
        should_retry_func: Optional[Callable[[Exception], bool]] = None
    ):
        """Initialize retry decorator.
        
        Args:
            retry_manager: RetryManager instance, creates default if None
            retry_reason: Reason for retries
            should_retry_func: Custom function to determine if retry should happen
        """
        self.retry_manager = retry_manager or RetryManager()
        self.retry_reason = retry_reason
        self.should_retry_func = should_retry_func
    
    def __call__(self, func: Callable) -> Callable:
        """Apply retry logic to a function."""
        
        def wrapper(*args, **kwargs):
            result = self.retry_manager.execute_with_retry(
                operation=func,
                operation_args=args,
                operation_kwargs=kwargs,
                retry_reason=self.retry_reason,
                should_retry_func=self.should_retry_func
            )
            
            if result.success:
                return result.final_result
            else:
                raise Exception(f"Operation failed after {result.total_attempts} attempts: {result.final_error}")
        
        return wrapper


# Utility functions for common retry scenarios

def is_retryable_api_error(exception: Exception) -> bool:
    """Determine if an API error is retryable."""
    error_str = str(exception).lower()
    
    # Retryable errors
    retryable_patterns = [
        'timeout',
        'connection',
        'network',
        'rate limit',
        'service unavailable',
        'internal server error',
        'bad gateway',
        'gateway timeout'
    ]
    
    # Non-retryable errors
    non_retryable_patterns = [
        'authentication',
        'authorization',
        'forbidden',
        'not found',
        'bad request',
        'invalid'
    ]
    
    # Check for non-retryable patterns first
    for pattern in non_retryable_patterns:
        if pattern in error_str:
            return False
    
    # Check for retryable patterns
    for pattern in retryable_patterns:
        if pattern in error_str:
            return True
    
    # Default to retryable for unknown errors
    return True


def is_retryable_validation_error(exception: Exception) -> bool:
    """Determine if a validation error is retryable."""
    error_str = str(exception).lower()
    
    # Usually validation errors are not retryable unless they're related to temporary issues
    retryable_patterns = [
        'timeout',
        'temporary',
        'try again'
    ]
    
    for pattern in retryable_patterns:
        if pattern in error_str:
            return True
    
    return False


# Pre-configured retry managers for common scenarios

def create_api_retry_manager() -> RetryManager:
    """Create a retry manager optimized for API calls."""
    config = RetryConfig(
        max_retries=5,
        base_delay=1.0,
        max_delay=30.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True
    )
    
    # Configure specific behaviors for different error types
    config.reason_configs[RetryReason.RATE_LIMIT] = {
        'max_retries': 10,
        'base_delay': 60.0,
        'strategy': RetryStrategy.LINEAR_BACKOFF.value
    }
    
    return RetryManager(config)


def create_quality_retry_manager() -> RetryManager:
    """Create a retry manager optimized for quality threshold retries."""
    config = RetryConfig(
        max_retries=3,
        base_delay=2.0,
        max_delay=10.0,
        strategy=RetryStrategy.FIXED_DELAY,
        jitter=False,
        circuit_breaker_enabled=False  # Quality retries shouldn't trigger circuit breaker
    )
    
    return RetryManager(config)


def create_network_retry_manager() -> RetryManager:
    """Create a retry manager optimized for network operations."""
    config = RetryConfig(
        max_retries=3,
        base_delay=5.0,
        max_delay=60.0,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        jitter=True,
        jitter_range=0.2
    )
    
    return RetryManager(config)

