#!/usr/bin/env python
"""
Advanced Codegen Agent

A comprehensive, context-aware code generation agent with intelligent retry logic,
quality assessment, and feedback integration.
"""

from .context_engine import ContextEngine, TaskContext, TeamContext, CodebaseContext
from .codegen_client import AdvancedCodegenClient, GenerationRequest, GenerationResult, GenerationMode
from .retry_logic import RetryManager, RetryConfig, RetryStrategy, RetryReason
from .quality_assessor import QualityAssessor, QualityMetrics
from .feedback_processor import FeedbackProcessor, FeedbackType, FeedbackSeverity

__version__ = "1.0.0"
__author__ = "Codegen Team"
__description__ = "Advanced Codegen Agent with Context Awareness"

__all__ = [
    # Core components
    "AdvancedCodegenClient",
    "ContextEngine", 
    "QualityAssessor",
    "FeedbackProcessor",
    "RetryManager",
    
    # Data classes
    "GenerationRequest",
    "GenerationResult", 
    "TaskContext",
    "TeamContext",
    "CodebaseContext",
    "QualityMetrics",
    "RetryConfig",
    
    # Enums
    "GenerationMode",
    "RetryStrategy",
    "RetryReason", 
    "FeedbackType",
    "FeedbackSeverity",
]

