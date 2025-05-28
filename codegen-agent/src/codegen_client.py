#!/usr/bin/env python
"""
Advanced Codegen Client with Context Awareness

This module provides an enhanced Codegen client that leverages comprehensive context
for intelligent code generation with retry logic and feedback integration.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple, Callable
from enum import Enum
import hashlib

from codegen import Agent, Codebase
from .context_engine import ContextEngine, TaskContext, TeamContext
from .retry_logic import RetryManager, RetryStrategy
from .quality_assessor import QualityAssessor
from .feedback_processor import FeedbackProcessor


class GenerationMode(Enum):
    """Code generation modes."""
    FEATURE_DEVELOPMENT = "feature_development"
    BUG_FIXING = "bug_fixing"
    REFACTORING = "refactoring"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    OPTIMIZATION = "optimization"


@dataclass
class GenerationRequest:
    """Request for code generation."""
    
    mode: GenerationMode
    description: str
    target_files: List[str]
    requirements: List[str]
    constraints: List[str]
    context_hints: Dict[str, Any]
    priority: str = "medium"
    max_retries: int = 3
    quality_threshold: float = 0.8


@dataclass
class GenerationResult:
    """Result of code generation."""
    
    success: bool
    generated_code: Optional[str]
    files_modified: List[str]
    quality_score: float
    feedback: List[str]
    retry_count: int
    execution_time: float
    task_url: Optional[str]
    error_message: Optional[str] = None


class AdvancedCodegenClient:
    """Advanced Codegen client with comprehensive context awareness."""
    
    def __init__(
        self,
        api_token: str,
        org_id: int = 1,
        cache_dir: str = ".codegen_cache",
        enable_learning: bool = True
    ):
        """Initialize the advanced Codegen client.
        
        Args:
            api_token: Codegen API token
            org_id: Organization ID
            cache_dir: Directory for caching
            enable_learning: Whether to enable learning from successful patterns
        """
        self.api_token = api_token
        self.org_id = org_id
        self.enable_learning = enable_learning
        
        # Initialize components
        self.context_engine = ContextEngine(cache_dir)
        self.retry_manager = RetryManager()
        self.quality_assessor = QualityAssessor()
        self.feedback_processor = FeedbackProcessor()
        
        # Learning and pattern storage
        self.successful_patterns = {}
        self.failed_patterns = {}
        
        # Logging
        self.logger = logging.getLogger(__name__)
        
        # Performance metrics
        self.metrics = {
            'total_requests': 0,
            'successful_requests': 0,
            'avg_quality_score': 0.0,
            'avg_retry_count': 0.0,
            'avg_execution_time': 0.0
        }
    
    def generate_code(
        self,
        request: GenerationRequest,
        repo_path: str,
        team_context: Optional[TeamContext] = None,
        validation_callback: Optional[Callable] = None
    ) -> GenerationResult:
        """Generate code with comprehensive context awareness and retry logic.
        
        Args:
            request: Generation request details
            repo_path: Path to the repository
            team_context: Team preferences and guidelines
            validation_callback: Optional callback for custom validation
            
        Returns:
            Generation result with quality metrics and feedback
        """
        start_time = time.time()
        self.metrics['total_requests'] += 1
        
        self.logger.info(f"Starting code generation: {request.mode.value}")
        
        try:
            # 1. Gather comprehensive context
            task_context = TaskContext(
                task_type=request.mode.value,
                description=request.description,
                requirements=request.requirements,
                constraints=request.constraints,
                target_files=request.target_files,
                related_issues=[],
                priority=request.priority,
                estimated_complexity="medium"
            )
            
            context = self.context_engine.gather_comprehensive_context(
                repo_path, task_context, team_context
            )
            
            # 2. Generate enhanced prompt
            prompt = self._generate_enhanced_prompt(request, context)
            
            # 3. Execute generation with retry logic
            result = self._execute_with_retry(
                prompt, request, context, validation_callback
            )
            
            # 4. Update metrics and learning
            execution_time = time.time() - start_time
            result.execution_time = execution_time
            
            if result.success:
                self.metrics['successful_requests'] += 1
                if self.enable_learning:
                    self._learn_from_success(request, context, result)
            else:
                if self.enable_learning:
                    self._learn_from_failure(request, context, result)
            
            # Update running averages
            self._update_metrics(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Code generation failed: {e}")
            return GenerationResult(
                success=False,
                generated_code=None,
                files_modified=[],
                quality_score=0.0,
                feedback=[f"Generation failed: {str(e)}"],
                retry_count=0,
                execution_time=time.time() - start_time,
                task_url=None,
                error_message=str(e)
            )
    
    def _generate_enhanced_prompt(
        self,
        request: GenerationRequest,
        context: Dict[str, Any]
    ) -> str:
        """Generate an enhanced prompt using comprehensive context."""
        
        # Load mode-specific prompt template
        template = self._load_prompt_template(request.mode)
        
        # Extract key context elements
        codebase_context = context.get('codebase', {})
        team_context = context.get('team', {})
        quality_context = context.get('quality', {})
        
        # Build context-aware prompt
        prompt_parts = [
            f"# {request.mode.value.title()} Task",
            f"## Description\n{request.description}",
            "",
            "## Codebase Context",
            f"- Repository: {codebase_context.get('repo_name', 'Unknown')}",
            f"- Languages: {', '.join(codebase_context.get('programming_languages', []))}",
            f"- Architecture: {', '.join(codebase_context.get('architectural_patterns', []))}",
            f"- Naming Convention: {codebase_context.get('naming_conventions', {}).get('dominant_convention', 'mixed')}",
            "",
            "## Quality Standards",
            f"- Documentation Coverage: {quality_context.get('documentation_coverage', 0):.1f}%",
            f"- Test Coverage: {quality_context.get('test_coverage_estimate', 0):.1f}%",
            f"- Maintainability Score: {quality_context.get('maintainability_score', 0):.1f}/100",
            ""
        ]
        
        # Add requirements and constraints
        if request.requirements:
            prompt_parts.extend([
                "## Requirements",
                *[f"- {req}" for req in request.requirements],
                ""
            ])
        
        if request.constraints:
            prompt_parts.extend([
                "## Constraints",
                *[f"- {constraint}" for constraint in request.constraints],
                ""
            ])
        
        # Add team preferences
        if team_context.get('inferred_coding_standards'):
            standards = team_context['inferred_coding_standards']
            prompt_parts.extend([
                "## Coding Standards",
                f"- Naming: {standards.get('naming_convention', 'consistent with codebase')}",
                f"- Documentation: {'Required' if standards.get('documentation_required') else 'Optional'}",
                ""
            ])
        
        # Add target files context
        if request.target_files:
            prompt_parts.extend([
                "## Target Files",
                *[f"- {file}" for file in request.target_files],
                ""
            ])
        
        # Add mode-specific instructions
        prompt_parts.extend([
            "## Instructions",
            template,
            "",
            "## Success Criteria",
            "- Code follows established patterns and conventions",
            "- Maintains or improves code quality metrics",
            "- Includes appropriate tests and documentation",
            "- Handles edge cases and error conditions",
            "- Is production-ready and maintainable"
        ])
        
        # Add learning from previous patterns
        if self.enable_learning:
            similar_patterns = self._find_similar_patterns(request, context)
            if similar_patterns:
                prompt_parts.extend([
                    "",
                    "## Learned Patterns",
                    "Based on previous successful implementations:",
                    *[f"- {pattern}" for pattern in similar_patterns[:3]]
                ])
        
        return "\n".join(prompt_parts)
    
    def _load_prompt_template(self, mode: GenerationMode) -> str:
        """Load mode-specific prompt template."""
        templates = {
            GenerationMode.FEATURE_DEVELOPMENT: """
Create a new feature implementation that:
1. Follows the existing codebase architecture and patterns
2. Includes comprehensive error handling and validation
3. Provides clear, well-documented interfaces
4. Includes unit tests with good coverage
5. Considers performance and scalability implications
6. Maintains backward compatibility where applicable
            """.strip(),
            
            GenerationMode.BUG_FIXING: """
Fix the identified bug by:
1. Analyzing the root cause thoroughly
2. Implementing a minimal, targeted fix
3. Adding tests to prevent regression
4. Ensuring the fix doesn't introduce new issues
5. Documenting the fix and its rationale
6. Considering edge cases and error scenarios
            """.strip(),
            
            GenerationMode.REFACTORING: """
Refactor the code to:
1. Improve readability and maintainability
2. Reduce complexity and technical debt
3. Enhance performance where possible
4. Maintain existing functionality exactly
5. Update tests to reflect changes
6. Follow established design patterns
            """.strip(),
            
            GenerationMode.TESTING: """
Create comprehensive tests that:
1. Cover all critical functionality and edge cases
2. Follow the project's testing conventions
3. Are maintainable and well-documented
4. Include both positive and negative test cases
5. Test error conditions and boundary values
6. Provide clear, descriptive test names
            """.strip(),
            
            GenerationMode.DOCUMENTATION: """
Create clear, comprehensive documentation that:
1. Explains the purpose and functionality
2. Provides usage examples and code samples
3. Documents all parameters and return values
4. Includes common use cases and patterns
5. Follows the project's documentation style
6. Is accessible to the target audience
            """.strip(),
            
            GenerationMode.OPTIMIZATION: """
Optimize the code for:
1. Better performance and efficiency
2. Reduced resource consumption
3. Improved scalability
4. Maintained functionality and correctness
5. Clear documentation of optimizations
6. Benchmarks to validate improvements
            """.strip()
        }
        
        return templates.get(mode, "Generate high-quality code following best practices.")
    
    def _execute_with_retry(
        self,
        prompt: str,
        request: GenerationRequest,
        context: Dict[str, Any],
        validation_callback: Optional[Callable]
    ) -> GenerationResult:
        """Execute code generation with intelligent retry logic."""
        
        retry_strategy = RetryStrategy(
            max_retries=request.max_retries,
            base_delay=2.0,
            max_delay=30.0,
            exponential_base=2.0
        )
        
        last_error = None
        retry_count = 0
        
        for attempt in range(request.max_retries + 1):
            try:
                self.logger.info(f"Generation attempt {attempt + 1}/{request.max_retries + 1}")
                
                # Create agent and run task
                agent = Agent(token=self.api_token, org_id=self.org_id)
                task = agent.run(prompt)
                
                # Wait for completion with timeout
                result = self._wait_for_completion(agent, task, timeout=300)
                
                if not result['success']:
                    raise Exception(f"Task failed: {result.get('error', 'Unknown error')}")
                
                # Extract generated code
                generated_code = result.get('result', '')
                
                # Assess quality
                quality_score = self.quality_assessor.assess_quality(
                    generated_code, context, request
                )
                
                # Custom validation if provided
                if validation_callback:
                    validation_result = validation_callback(generated_code, context)
                    if not validation_result.get('valid', True):
                        raise Exception(f"Validation failed: {validation_result.get('message', 'Unknown validation error')}")
                
                # Check if quality meets threshold
                if quality_score >= request.quality_threshold:
                    return GenerationResult(
                        success=True,
                        generated_code=generated_code,
                        files_modified=self._extract_modified_files(generated_code),
                        quality_score=quality_score,
                        feedback=self._generate_feedback(generated_code, quality_score),
                        retry_count=retry_count,
                        execution_time=0.0,  # Will be set by caller
                        task_url=result.get('web_url')
                    )
                else:
                    # Quality too low, prepare for retry
                    feedback = self.feedback_processor.process_quality_feedback(
                        generated_code, quality_score, request.quality_threshold
                    )
                    
                    # Update prompt with feedback for next attempt
                    prompt = self._enhance_prompt_with_feedback(prompt, feedback)
                    
                    if attempt < request.max_retries:
                        retry_count += 1
                        delay = retry_strategy.get_delay(attempt)
                        self.logger.info(f"Quality score {quality_score:.2f} below threshold {request.quality_threshold:.2f}, retrying in {delay:.1f}s")
                        time.sleep(delay)
                        continue
                    else:
                        # Max retries reached, return best attempt
                        return GenerationResult(
                            success=False,
                            generated_code=generated_code,
                            files_modified=self._extract_modified_files(generated_code),
                            quality_score=quality_score,
                            feedback=[f"Quality score {quality_score:.2f} below threshold {request.quality_threshold:.2f}"],
                            retry_count=retry_count,
                            execution_time=0.0,
                            task_url=result.get('web_url'),
                            error_message="Quality threshold not met after maximum retries"
                        )
                
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt + 1} failed: {e}")
                
                if attempt < request.max_retries:
                    retry_count += 1
                    
                    # Process error feedback
                    error_feedback = self.feedback_processor.process_error_feedback(str(e))
                    prompt = self._enhance_prompt_with_feedback(prompt, error_feedback)
                    
                    delay = retry_strategy.get_delay(attempt)
                    self.logger.info(f"Retrying in {delay:.1f}s")
                    time.sleep(delay)
                else:
                    # Max retries reached
                    break
        
        # All retries failed
        return GenerationResult(
            success=False,
            generated_code=None,
            files_modified=[],
            quality_score=0.0,
            feedback=[f"All attempts failed. Last error: {str(last_error)}"],
            retry_count=retry_count,
            execution_time=0.0,
            task_url=None,
            error_message=str(last_error)
        )
    
    def _wait_for_completion(self, agent: Agent, task: Any, timeout: int = 300) -> Dict[str, Any]:
        """Wait for task completion with timeout."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                status = agent.get_status()
                
                if status.get('status') == 'completed':
                    return {
                        'success': True,
                        'result': status.get('result'),
                        'web_url': status.get('web_url')
                    }
                elif status.get('status') == 'failed':
                    return {
                        'success': False,
                        'error': status.get('result', 'Task failed'),
                        'web_url': status.get('web_url')
                    }
                
                time.sleep(2)
                
            except Exception as e:
                self.logger.warning(f"Error checking task status: {e}")
                time.sleep(5)
        
        return {
            'success': False,
            'error': 'Task timed out',
            'web_url': None
        }
    
    def _extract_modified_files(self, generated_code: str) -> List[str]:
        """Extract list of files that would be modified by the generated code."""
        # Simple heuristic - look for file paths in the code
        files = []
        lines = generated_code.split('\n')
        
        for line in lines:
            # Look for common file path patterns
            if any(keyword in line.lower() for keyword in ['file:', 'path:', 'create', 'modify', 'update']):
                # Extract potential file paths
                words = line.split()
                for word in words:
                    if '.' in word and '/' in word and not word.startswith('http'):
                        files.append(word.strip('"`\''))
        
        return list(set(files))
    
    def _generate_feedback(self, generated_code: str, quality_score: float) -> List[str]:
        """Generate feedback about the generated code."""
        feedback = []
        
        if quality_score >= 0.9:
            feedback.append("Excellent code quality - well structured and documented")
        elif quality_score >= 0.8:
            feedback.append("Good code quality - meets standards with minor improvements possible")
        elif quality_score >= 0.7:
            feedback.append("Acceptable code quality - some improvements recommended")
        else:
            feedback.append("Code quality below standards - significant improvements needed")
        
        # Add specific feedback based on code analysis
        if 'def ' in generated_code or 'function ' in generated_code:
            feedback.append("Functions detected - ensure proper documentation and error handling")
        
        if 'class ' in generated_code:
            feedback.append("Classes detected - verify proper encapsulation and interface design")
        
        if 'test' in generated_code.lower():
            feedback.append("Tests included - good practice for maintainability")
        
        return feedback
    
    def _enhance_prompt_with_feedback(self, original_prompt: str, feedback: List[str]) -> str:
        """Enhance prompt with feedback from previous attempts."""
        if not feedback:
            return original_prompt
        
        feedback_section = "\n\n## Feedback from Previous Attempt\n"
        feedback_section += "Please address the following issues:\n"
        feedback_section += "\n".join(f"- {item}" for item in feedback)
        
        return original_prompt + feedback_section
    
    def _learn_from_success(
        self,
        request: GenerationRequest,
        context: Dict[str, Any],
        result: GenerationResult
    ) -> None:
        """Learn from successful generation patterns."""
        pattern_key = self._generate_pattern_key(request, context)
        
        if pattern_key not in self.successful_patterns:
            self.successful_patterns[pattern_key] = []
        
        self.successful_patterns[pattern_key].append({
            'quality_score': result.quality_score,
            'retry_count': result.retry_count,
            'timestamp': time.time(),
            'context_summary': context.get('compressed', ''),
            'feedback': result.feedback
        })
        
        # Keep only recent successful patterns (last 10)
        self.successful_patterns[pattern_key] = self.successful_patterns[pattern_key][-10:]
    
    def _learn_from_failure(
        self,
        request: GenerationRequest,
        context: Dict[str, Any],
        result: GenerationResult
    ) -> None:
        """Learn from failed generation patterns."""
        pattern_key = self._generate_pattern_key(request, context)
        
        if pattern_key not in self.failed_patterns:
            self.failed_patterns[pattern_key] = []
        
        self.failed_patterns[pattern_key].append({
            'error_message': result.error_message,
            'retry_count': result.retry_count,
            'timestamp': time.time(),
            'context_summary': context.get('compressed', ''),
            'feedback': result.feedback
        })
        
        # Keep only recent failed patterns (last 5)
        self.failed_patterns[pattern_key] = self.failed_patterns[pattern_key][-5:]
    
    def _find_similar_patterns(
        self,
        request: GenerationRequest,
        context: Dict[str, Any]
    ) -> List[str]:
        """Find similar successful patterns for learning."""
        current_key = self._generate_pattern_key(request, context)
        similar_patterns = []
        
        # Look for exact matches first
        if current_key in self.successful_patterns:
            patterns = self.successful_patterns[current_key]
            for pattern in patterns[-3:]:  # Last 3 successful patterns
                if pattern['quality_score'] >= 0.8:
                    similar_patterns.extend(pattern['feedback'])
        
        # Look for similar mode patterns
        for key, patterns in self.successful_patterns.items():
            if request.mode.value in key and key != current_key:
                for pattern in patterns[-2:]:  # Last 2 from similar modes
                    if pattern['quality_score'] >= 0.9:
                        similar_patterns.extend(pattern['feedback'][:1])
        
        return list(set(similar_patterns))
    
    def _generate_pattern_key(self, request: GenerationRequest, context: Dict[str, Any]) -> str:
        """Generate a key for pattern matching."""
        codebase = context.get('codebase', {})
        key_elements = [
            request.mode.value,
            '_'.join(codebase.get('programming_languages', [])[:2]),
            '_'.join(codebase.get('architectural_patterns', [])[:2])
        ]
        return '_'.join(filter(None, key_elements))
    
    def _update_metrics(self, result: GenerationResult) -> None:
        """Update performance metrics."""
        total = self.metrics['total_requests']
        
        # Update running averages
        self.metrics['avg_quality_score'] = (
            (self.metrics['avg_quality_score'] * (total - 1) + result.quality_score) / total
        )
        
        self.metrics['avg_retry_count'] = (
            (self.metrics['avg_retry_count'] * (total - 1) + result.retry_count) / total
        )
        
        self.metrics['avg_execution_time'] = (
            (self.metrics['avg_execution_time'] * (total - 1) + result.execution_time) / total
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        success_rate = (
            self.metrics['successful_requests'] / self.metrics['total_requests']
            if self.metrics['total_requests'] > 0 else 0
        )
        
        return {
            **self.metrics,
            'success_rate': success_rate,
            'learned_patterns': len(self.successful_patterns),
            'failed_patterns': len(self.failed_patterns)
        }
    
    def clear_learning_data(self) -> None:
        """Clear learned patterns (useful for testing or reset)."""
        self.successful_patterns.clear()
        self.failed_patterns.clear()
        self.logger.info("Learning data cleared")

