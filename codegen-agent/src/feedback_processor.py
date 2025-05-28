#!/usr/bin/env python
"""
Feedback Processing Module for Codegen Agent

This module processes validation feedback and integrates it back into the
code generation process for continuous improvement.
"""

import json
import logging
import re
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict, Counter
from enum import Enum


class FeedbackType(Enum):
    """Types of feedback that can be processed."""
    QUALITY_FEEDBACK = "quality_feedback"
    ERROR_FEEDBACK = "error_feedback"
    VALIDATION_FEEDBACK = "validation_feedback"
    PERFORMANCE_FEEDBACK = "performance_feedback"
    SECURITY_FEEDBACK = "security_feedback"
    USER_FEEDBACK = "user_feedback"
    AUTOMATED_FEEDBACK = "automated_feedback"


class FeedbackSeverity(Enum):
    """Severity levels for feedback."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class FeedbackItem:
    """Individual feedback item."""
    
    feedback_type: FeedbackType
    severity: FeedbackSeverity
    message: str
    category: str
    suggestion: Optional[str] = None
    code_location: Optional[str] = None
    timestamp: float = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()


@dataclass
class ProcessedFeedback:
    """Processed feedback with actionable improvements."""
    
    original_feedback: List[FeedbackItem]
    improvement_suggestions: List[str]
    prompt_enhancements: List[str]
    priority_fixes: List[str]
    learning_points: List[str]
    confidence_score: float
    processing_timestamp: float


class FeedbackProcessor:
    """Advanced feedback processing and integration system."""
    
    def __init__(self):
        """Initialize the feedback processor."""
        self.logger = logging.getLogger(__name__)
        
        # Feedback patterns and their corresponding improvements
        self.feedback_patterns = {
            'quality': {
                'low_documentation': {
                    'patterns': [
                        r'documentation.*low',
                        r'missing.*docstring',
                        r'add.*comment',
                        r'document.*function'
                    ],
                    'suggestions': [
                        "Add comprehensive docstrings to all functions and classes",
                        "Include parameter descriptions and return value documentation",
                        "Add inline comments for complex logic sections"
                    ]
                },
                'high_complexity': {
                    'patterns': [
                        r'complexity.*high',
                        r'function.*too.*long',
                        r'reduce.*nesting',
                        r'simplify.*logic'
                    ],
                    'suggestions': [
                        "Break down large functions into smaller, focused functions",
                        "Reduce nesting depth by using early returns or guard clauses",
                        "Extract complex logic into separate helper functions"
                    ]
                },
                'poor_naming': {
                    'patterns': [
                        r'naming.*convention',
                        r'variable.*name',
                        r'unclear.*name',
                        r'improve.*naming'
                    ],
                    'suggestions': [
                        "Use descriptive, meaningful variable and function names",
                        "Follow consistent naming conventions (snake_case for Python)",
                        "Avoid abbreviations and single-letter variables"
                    ]
                }
            },
            'security': {
                'sql_injection': {
                    'patterns': [
                        r'sql.*injection',
                        r'parameterized.*query',
                        r'unsafe.*query'
                    ],
                    'suggestions': [
                        "Use parameterized queries or prepared statements",
                        "Validate and sanitize all user inputs",
                        "Use ORM frameworks when possible"
                    ]
                },
                'xss_vulnerability': {
                    'patterns': [
                        r'xss.*vulnerability',
                        r'cross.*site.*scripting',
                        r'unsafe.*html'
                    ],
                    'suggestions': [
                        "Escape or sanitize user input before rendering",
                        "Use secure templating engines",
                        "Implement Content Security Policy (CSP)"
                    ]
                }
            },
            'performance': {
                'inefficient_loops': {
                    'patterns': [
                        r'inefficient.*loop',
                        r'nested.*loop',
                        r'optimize.*iteration'
                    ],
                    'suggestions': [
                        "Use list comprehensions or generator expressions",
                        "Consider using built-in functions like map(), filter()",
                        "Optimize nested loops or use more efficient algorithms"
                    ]
                },
                'memory_usage': {
                    'patterns': [
                        r'memory.*usage',
                        r'large.*data.*structure',
                        r'optimize.*memory'
                    ],
                    'suggestions': [
                        "Use generators for large datasets",
                        "Implement lazy loading where appropriate",
                        "Consider using more memory-efficient data structures"
                    ]
                }
            },
            'error_handling': {
                'missing_error_handling': {
                    'patterns': [
                        r'error.*handling',
                        r'exception.*handling',
                        r'try.*catch',
                        r'add.*validation'
                    ],
                    'suggestions': [
                        "Add proper exception handling with try-catch blocks",
                        "Validate input parameters and handle edge cases",
                        "Provide meaningful error messages to users"
                    ]
                }
            }
        }
        
        # Common error patterns and their solutions
        self.error_patterns = {
            'syntax_error': {
                'patterns': [
                    r'syntax.*error',
                    r'invalid.*syntax',
                    r'unexpected.*token'
                ],
                'solutions': [
                    "Check for missing colons, parentheses, or brackets",
                    "Verify proper indentation",
                    "Ensure all strings are properly quoted"
                ]
            },
            'import_error': {
                'patterns': [
                    r'import.*error',
                    r'module.*not.*found',
                    r'no.*module.*named'
                ],
                'solutions': [
                    "Verify the module is installed and available",
                    "Check the import path and module name",
                    "Add necessary dependencies to requirements"
                ]
            },
            'type_error': {
                'patterns': [
                    r'type.*error',
                    r'unsupported.*operand',
                    r'not.*callable'
                ],
                'solutions': [
                    "Check variable types and ensure compatibility",
                    "Add type checking and validation",
                    "Use proper type conversion when needed"
                ]
            },
            'attribute_error': {
                'patterns': [
                    r'attribute.*error',
                    r'has.*no.*attribute',
                    r'object.*has.*no'
                ],
                'solutions': [
                    "Verify the object has the expected attributes",
                    "Add null/None checks before accessing attributes",
                    "Check object initialization and state"
                ]
            }
        }
        
        # Feedback processing statistics
        self.stats = {
            'total_feedback_processed': 0,
            'feedback_by_type': defaultdict(int),
            'feedback_by_severity': defaultdict(int),
            'improvement_success_rate': 0.0,
            'common_issues': Counter()
        }
    
    def process_quality_feedback(
        self,
        generated_code: str,
        quality_score: float,
        threshold: float,
        detailed_metrics: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """Process quality-related feedback and generate improvement suggestions.
        
        Args:
            generated_code: The generated code that needs improvement
            quality_score: Current quality score
            threshold: Required quality threshold
            detailed_metrics: Detailed quality metrics if available
            
        Returns:
            List of improvement suggestions
        """
        feedback_items = []
        
        # Create feedback items based on quality gaps
        quality_gap = threshold - quality_score
        
        if quality_gap > 0.3:
            feedback_items.append(FeedbackItem(
                feedback_type=FeedbackType.QUALITY_FEEDBACK,
                severity=FeedbackSeverity.CRITICAL,
                message=f"Quality score {quality_score:.2f} significantly below threshold {threshold:.2f}",
                category="overall_quality"
            ))
        elif quality_gap > 0.1:
            feedback_items.append(FeedbackItem(
                feedback_type=FeedbackType.QUALITY_FEEDBACK,
                severity=FeedbackSeverity.HIGH,
                message=f"Quality score {quality_score:.2f} below threshold {threshold:.2f}",
                category="overall_quality"
            ))
        
        # Add specific feedback based on detailed metrics
        if detailed_metrics:
            self._add_detailed_quality_feedback(feedback_items, detailed_metrics)
        
        # Process feedback and generate suggestions
        processed = self._process_feedback_items(feedback_items, generated_code)
        
        self._update_stats(feedback_items)
        
        return processed.improvement_suggestions
    
    def process_error_feedback(self, error_message: str) -> List[str]:
        """Process error feedback and generate solutions.
        
        Args:
            error_message: The error message to process
            
        Returns:
            List of suggested solutions
        """
        feedback_items = []
        
        # Categorize the error
        error_category = self._categorize_error(error_message)
        
        feedback_items.append(FeedbackItem(
            feedback_type=FeedbackType.ERROR_FEEDBACK,
            severity=FeedbackSeverity.CRITICAL,
            message=error_message,
            category=error_category
        ))
        
        # Generate specific solutions based on error type
        solutions = self._generate_error_solutions(error_message, error_category)
        
        processed = ProcessedFeedback(
            original_feedback=feedback_items,
            improvement_suggestions=solutions,
            prompt_enhancements=[
                f"Previous attempt failed with {error_category}: {error_message}",
                "Please address the following specific issues:",
                *solutions
            ],
            priority_fixes=solutions[:2],  # Top 2 priority fixes
            learning_points=[f"Avoid {error_category} by implementing proper error handling"],
            confidence_score=0.8,
            processing_timestamp=time.time()
        )
        
        self._update_stats(feedback_items)
        
        return processed.prompt_enhancements
    
    def process_validation_feedback(
        self,
        validation_results: Dict[str, Any],
        context: Dict[str, Any]
    ) -> List[str]:
        """Process validation feedback from external validators.
        
        Args:
            validation_results: Results from validation process
            context: Context information
            
        Returns:
            List of improvement suggestions
        """
        feedback_items = []
        
        # Process different types of validation results
        if 'test_failures' in validation_results:
            for failure in validation_results['test_failures']:
                feedback_items.append(FeedbackItem(
                    feedback_type=FeedbackType.VALIDATION_FEEDBACK,
                    severity=FeedbackSeverity.HIGH,
                    message=f"Test failure: {failure}",
                    category="test_failure"
                ))
        
        if 'lint_errors' in validation_results:
            for error in validation_results['lint_errors']:
                feedback_items.append(FeedbackItem(
                    feedback_type=FeedbackType.VALIDATION_FEEDBACK,
                    severity=FeedbackSeverity.MEDIUM,
                    message=f"Lint error: {error}",
                    category="code_style"
                ))
        
        if 'security_issues' in validation_results:
            for issue in validation_results['security_issues']:
                feedback_items.append(FeedbackItem(
                    feedback_type=FeedbackType.SECURITY_FEEDBACK,
                    severity=FeedbackSeverity.CRITICAL,
                    message=f"Security issue: {issue}",
                    category="security"
                ))
        
        processed = self._process_feedback_items(feedback_items, context.get('code', ''))
        
        self._update_stats(feedback_items)
        
        return processed.improvement_suggestions
    
    def process_user_feedback(
        self,
        user_comments: List[str],
        code_context: str
    ) -> ProcessedFeedback:
        """Process feedback from users or reviewers.
        
        Args:
            user_comments: List of user feedback comments
            code_context: The code being reviewed
            
        Returns:
            Processed feedback with actionable improvements
        """
        feedback_items = []
        
        for comment in user_comments:
            # Analyze sentiment and categorize feedback
            category = self._categorize_user_feedback(comment)
            severity = self._determine_feedback_severity(comment)
            
            feedback_items.append(FeedbackItem(
                feedback_type=FeedbackType.USER_FEEDBACK,
                severity=severity,
                message=comment,
                category=category
            ))
        
        processed = self._process_feedback_items(feedback_items, code_context)
        
        self._update_stats(feedback_items)
        
        return processed
    
    def _add_detailed_quality_feedback(
        self,
        feedback_items: List[FeedbackItem],
        metrics: Dict[str, Any]
    ) -> None:
        """Add detailed feedback based on quality metrics."""
        
        # Documentation feedback
        if metrics.get('documentation_score', 1.0) < 0.7:
            feedback_items.append(FeedbackItem(
                feedback_type=FeedbackType.QUALITY_FEEDBACK,
                severity=FeedbackSeverity.MEDIUM,
                message="Documentation coverage is below standards",
                category="documentation"
            ))
        
        # Maintainability feedback
        if metrics.get('maintainability_score', 1.0) < 0.7:
            feedback_items.append(FeedbackItem(
                feedback_type=FeedbackType.QUALITY_FEEDBACK,
                severity=FeedbackSeverity.HIGH,
                message="Code maintainability needs improvement",
                category="maintainability"
            ))
        
        # Security feedback
        if metrics.get('security_score', 1.0) < 0.8:
            feedback_items.append(FeedbackItem(
                feedback_type=FeedbackType.SECURITY_FEEDBACK,
                severity=FeedbackSeverity.CRITICAL,
                message="Security issues detected in the code",
                category="security"
            ))
        
        # Performance feedback
        if metrics.get('performance_score', 1.0) < 0.7:
            feedback_items.append(FeedbackItem(
                feedback_type=FeedbackType.PERFORMANCE_FEEDBACK,
                severity=FeedbackSeverity.MEDIUM,
                message="Performance optimizations needed",
                category="performance"
            ))
    
    def _process_feedback_items(
        self,
        feedback_items: List[FeedbackItem],
        code_context: str
    ) -> ProcessedFeedback:
        """Process a list of feedback items into actionable improvements."""
        
        improvement_suggestions = []
        prompt_enhancements = []
        priority_fixes = []
        learning_points = []
        
        # Group feedback by category
        feedback_by_category = defaultdict(list)
        for item in feedback_items:
            feedback_by_category[item.category].append(item)
        
        # Process each category
        for category, items in feedback_by_category.items():
            category_suggestions = self._generate_category_suggestions(category, items, code_context)
            improvement_suggestions.extend(category_suggestions)
            
            # Add to prompt enhancements
            if items:
                severity_levels = [item.severity for item in items]
                if FeedbackSeverity.CRITICAL in severity_levels:
                    prompt_enhancements.append(f"CRITICAL: Address {category} issues immediately")
                    priority_fixes.extend(category_suggestions[:2])
                elif FeedbackSeverity.HIGH in severity_levels:
                    prompt_enhancements.append(f"HIGH PRIORITY: Improve {category}")
                else:
                    prompt_enhancements.append(f"Consider improving {category}")
        
        # Generate learning points
        for item in feedback_items:
            if item.severity in [FeedbackSeverity.CRITICAL, FeedbackSeverity.HIGH]:
                learning_points.append(f"Learn from {item.category}: {item.message}")
        
        # Calculate confidence score based on feedback specificity
        confidence_score = self._calculate_confidence_score(feedback_items, improvement_suggestions)
        
        return ProcessedFeedback(
            original_feedback=feedback_items,
            improvement_suggestions=improvement_suggestions,
            prompt_enhancements=prompt_enhancements,
            priority_fixes=priority_fixes,
            learning_points=learning_points,
            confidence_score=confidence_score,
            processing_timestamp=time.time()
        )
    
    def _generate_category_suggestions(
        self,
        category: str,
        items: List[FeedbackItem],
        code_context: str
    ) -> List[str]:
        """Generate suggestions for a specific feedback category."""
        
        suggestions = []
        
        # Look for matching patterns in our knowledge base
        for main_category, subcategories in self.feedback_patterns.items():
            for subcategory, pattern_info in subcategories.items():
                # Check if any feedback messages match the patterns
                for item in items:
                    message_lower = item.message.lower()
                    for pattern in pattern_info['patterns']:
                        if re.search(pattern, message_lower):
                            suggestions.extend(pattern_info['suggestions'])
                            break
        
        # Add category-specific suggestions
        if category == 'documentation':
            suggestions.extend([
                "Add docstrings to all public functions and classes",
                "Include usage examples in documentation",
                "Document complex algorithms and business logic"
            ])
        elif category == 'maintainability':
            suggestions.extend([
                "Reduce function complexity by breaking into smaller functions",
                "Use meaningful variable and function names",
                "Remove duplicate code by extracting common functionality"
            ])
        elif category == 'security':
            suggestions.extend([
                "Validate all user inputs",
                "Use secure coding practices",
                "Implement proper authentication and authorization"
            ])
        elif category == 'performance':
            suggestions.extend([
                "Optimize algorithms and data structures",
                "Reduce unnecessary computations",
                "Use efficient libraries and built-in functions"
            ])
        
        # Remove duplicates while preserving order
        seen = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion not in seen:
                seen.add(suggestion)
                unique_suggestions.append(suggestion)
        
        return unique_suggestions[:5]  # Limit to top 5 suggestions
    
    def _categorize_error(self, error_message: str) -> str:
        """Categorize an error message."""
        error_lower = error_message.lower()
        
        for category, pattern_info in self.error_patterns.items():
            for pattern in pattern_info['patterns']:
                if re.search(pattern, error_lower):
                    return category
        
        return 'unknown_error'
    
    def _generate_error_solutions(self, error_message: str, category: str) -> List[str]:
        """Generate solutions for a specific error."""
        
        solutions = []
        
        # Get category-specific solutions
        if category in self.error_patterns:
            solutions.extend(self.error_patterns[category]['solutions'])
        
        # Add general debugging suggestions
        solutions.extend([
            "Review the code for syntax and logical errors",
            "Check variable names and scope",
            "Verify all dependencies are properly imported"
        ])
        
        return solutions[:3]  # Limit to top 3 solutions
    
    def _categorize_user_feedback(self, comment: str) -> str:
        """Categorize user feedback comment."""
        comment_lower = comment.lower()
        
        if any(word in comment_lower for word in ['bug', 'error', 'broken', 'fail']):
            return 'bug_report'
        elif any(word in comment_lower for word in ['slow', 'performance', 'optimize']):
            return 'performance'
        elif any(word in comment_lower for word in ['security', 'vulnerable', 'unsafe']):
            return 'security'
        elif any(word in comment_lower for word in ['unclear', 'confusing', 'document']):
            return 'clarity'
        elif any(word in comment_lower for word in ['feature', 'enhancement', 'improve']):
            return 'enhancement'
        else:
            return 'general'
    
    def _determine_feedback_severity(self, comment: str) -> FeedbackSeverity:
        """Determine the severity of user feedback."""
        comment_lower = comment.lower()
        
        if any(word in comment_lower for word in ['critical', 'urgent', 'broken', 'security']):
            return FeedbackSeverity.CRITICAL
        elif any(word in comment_lower for word in ['important', 'major', 'significant']):
            return FeedbackSeverity.HIGH
        elif any(word in comment_lower for word in ['minor', 'small', 'suggestion']):
            return FeedbackSeverity.LOW
        else:
            return FeedbackSeverity.MEDIUM
    
    def _calculate_confidence_score(
        self,
        feedback_items: List[FeedbackItem],
        suggestions: List[str]
    ) -> float:
        """Calculate confidence score for the processed feedback."""
        
        base_score = 0.5
        
        # Increase confidence based on feedback specificity
        specific_feedback = len([item for item in feedback_items if item.code_location])
        base_score += min(0.3, specific_feedback * 0.1)
        
        # Increase confidence based on number of actionable suggestions
        base_score += min(0.2, len(suggestions) * 0.02)
        
        # Decrease confidence for unknown categories
        unknown_feedback = len([item for item in feedback_items if item.category == 'unknown_error'])
        base_score -= min(0.2, unknown_feedback * 0.1)
        
        return max(0.0, min(1.0, base_score))
    
    def _update_stats(self, feedback_items: List[FeedbackItem]) -> None:
        """Update feedback processing statistics."""
        
        self.stats['total_feedback_processed'] += len(feedback_items)
        
        for item in feedback_items:
            self.stats['feedback_by_type'][item.feedback_type.value] += 1
            self.stats['feedback_by_severity'][item.severity.value] += 1
            self.stats['common_issues'][item.category] += 1
    
    def get_feedback_analytics(self) -> Dict[str, Any]:
        """Get analytics about processed feedback."""
        
        total_feedback = self.stats['total_feedback_processed']
        
        return {
            'total_feedback_processed': total_feedback,
            'feedback_by_type': dict(self.stats['feedback_by_type']),
            'feedback_by_severity': dict(self.stats['feedback_by_severity']),
            'most_common_issues': dict(self.stats['common_issues'].most_common(10)),
            'improvement_success_rate': self.stats['improvement_success_rate'],
            'avg_feedback_per_session': total_feedback / max(1, len(self.stats['feedback_by_type']))
        }
    
    def export_learning_data(self) -> Dict[str, Any]:
        """Export learning data for training or analysis."""
        
        return {
            'feedback_patterns': self.feedback_patterns,
            'error_patterns': self.error_patterns,
            'statistics': self.stats,
            'export_timestamp': time.time()
        }
    
    def import_learning_data(self, learning_data: Dict[str, Any]) -> None:
        """Import learning data from previous sessions."""
        
        if 'feedback_patterns' in learning_data:
            # Merge with existing patterns
            for category, patterns in learning_data['feedback_patterns'].items():
                if category not in self.feedback_patterns:
                    self.feedback_patterns[category] = {}
                self.feedback_patterns[category].update(patterns)
        
        if 'error_patterns' in learning_data:
            self.error_patterns.update(learning_data['error_patterns'])
        
        self.logger.info("Learning data imported successfully")
    
    def reset_stats(self) -> None:
        """Reset feedback processing statistics."""
        
        self.stats = {
            'total_feedback_processed': 0,
            'feedback_by_type': defaultdict(int),
            'feedback_by_severity': defaultdict(int),
            'improvement_success_rate': 0.0,
            'common_issues': Counter()
        }

