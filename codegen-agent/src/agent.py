#!/usr/bin/env python
"""
Main Agent Orchestrator

This module provides the main orchestrator for the Advanced Codegen Agent,
integrating all components and providing a unified interface.
"""

import logging
import os
import time
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable

from .context_engine import ContextEngine, TaskContext, TeamContext
from .codegen_client import AdvancedCodegenClient, GenerationRequest, GenerationResult, GenerationMode
from .retry_logic import RetryManager, RetryConfig
from .quality_assessor import QualityAssessor
from .feedback_processor import FeedbackProcessor


class AdvancedCodegenAgent:
    """
    Main orchestrator for the Advanced Codegen Agent.
    
    This class integrates all components and provides a unified interface
    for context-aware code generation with intelligent retry logic and
    quality assessment.
    """
    
    def __init__(
        self,
        api_token: str,
        org_id: int = 1,
        config_path: Optional[str] = None,
        cache_dir: str = ".codegen_cache"
    ):
        """Initialize the Advanced Codegen Agent.
        
        Args:
            api_token: Codegen API token
            org_id: Organization ID
            config_path: Path to configuration file
            cache_dir: Directory for caching
        """
        self.api_token = api_token
        self.org_id = org_id
        self.cache_dir = cache_dir
        
        # Load configuration
        self.config = self._load_config(config_path)
        
        # Setup logging
        self._setup_logging()
        self.logger = logging.getLogger(__name__)
        
        # Initialize components
        self.context_engine = ContextEngine(cache_dir)
        self.codegen_client = AdvancedCodegenClient(
            api_token=api_token,
            org_id=org_id,
            cache_dir=cache_dir,
            enable_learning=self.config.get('agent', {}).get('learning', {}).get('enabled', True)
        )
        self.quality_assessor = QualityAssessor()
        self.feedback_processor = FeedbackProcessor()
        
        # Performance tracking
        self.session_stats = {
            'requests_processed': 0,
            'successful_generations': 0,
            'failed_generations': 0,
            'total_execution_time': 0.0,
            'avg_quality_score': 0.0,
            'session_start_time': time.time()
        }
        
        self.logger.info("Advanced Codegen Agent initialized successfully")
    
    def generate_feature(
        self,
        description: str,
        requirements: List[str],
        repo_path: str,
        feature_type: str = "general",
        constraints: Optional[List[str]] = None,
        team_context: Optional[TeamContext] = None,
        quality_threshold: float = 0.8,
        validation_callback: Optional[Callable] = None
    ) -> GenerationResult:
        """Generate a new feature with comprehensive context awareness.
        
        Args:
            description: Feature description
            requirements: List of feature requirements
            repo_path: Path to the repository
            feature_type: Type of feature (web, api, data, etc.)
            constraints: Optional constraints
            team_context: Team preferences and guidelines
            quality_threshold: Minimum quality threshold
            validation_callback: Optional validation callback
            
        Returns:
            Generation result with quality metrics
        """
        self.logger.info(f"Starting feature generation: {description}")
        
        try:
            # Create generation request
            request = GenerationRequest(
                mode=GenerationMode.FEATURE_DEVELOPMENT,
                description=description,
                target_files=[],  # Will be determined during generation
                requirements=requirements,
                constraints=constraints or [],
                context_hints={'feature_type': feature_type},
                quality_threshold=quality_threshold
            )
            
            # Generate code
            result = self.codegen_client.generate_code(
                request=request,
                repo_path=repo_path,
                team_context=team_context,
                validation_callback=validation_callback
            )
            
            # Update session statistics
            self._update_session_stats(result)
            
            self.logger.info(f"Feature generation completed: success={result.success}, quality={result.quality_score:.2f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Feature generation failed: {e}")
            self.session_stats['failed_generations'] += 1
            raise
    
    def fix_bug(
        self,
        bug_description: str,
        repo_path: str,
        bug_type: str = "general",
        error_logs: Optional[List[str]] = None,
        reproduction_steps: Optional[List[str]] = None,
        team_context: Optional[TeamContext] = None,
        quality_threshold: float = 0.8
    ) -> GenerationResult:
        """Fix a bug with systematic debugging approach.
        
        Args:
            bug_description: Description of the bug
            repo_path: Path to the repository
            bug_type: Type of bug (performance, security, logic, etc.)
            error_logs: Optional error logs
            reproduction_steps: Optional reproduction steps
            team_context: Team preferences and guidelines
            quality_threshold: Minimum quality threshold
            
        Returns:
            Generation result with fix details
        """
        self.logger.info(f"Starting bug fix: {bug_description}")
        
        try:
            # Create generation request
            request = GenerationRequest(
                mode=GenerationMode.BUG_FIXING,
                description=bug_description,
                target_files=[],
                requirements=[],
                constraints=[],
                context_hints={
                    'bug_type': bug_type,
                    'error_logs': error_logs or [],
                    'reproduction_steps': reproduction_steps or []
                },
                quality_threshold=quality_threshold
            )
            
            # Generate fix
            result = self.codegen_client.generate_code(
                request=request,
                repo_path=repo_path,
                team_context=team_context
            )
            
            # Update session statistics
            self._update_session_stats(result)
            
            self.logger.info(f"Bug fix completed: success={result.success}, quality={result.quality_score:.2f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Bug fix failed: {e}")
            self.session_stats['failed_generations'] += 1
            raise
    
    def refactor_code(
        self,
        refactoring_description: str,
        target_files: List[str],
        repo_path: str,
        refactoring_type: str = "general",
        current_issues: Optional[List[str]] = None,
        target_improvements: Optional[List[str]] = None,
        team_context: Optional[TeamContext] = None,
        quality_threshold: float = 0.8
    ) -> GenerationResult:
        """Refactor code for improved quality and maintainability.
        
        Args:
            refactoring_description: Description of refactoring goals
            target_files: Files to refactor
            repo_path: Path to the repository
            refactoring_type: Type of refactoring (legacy, performance, security)
            current_issues: Current code issues to address
            target_improvements: Target improvements
            team_context: Team preferences and guidelines
            quality_threshold: Minimum quality threshold
            
        Returns:
            Generation result with refactoring details
        """
        self.logger.info(f"Starting code refactoring: {refactoring_description}")
        
        try:
            # Create generation request
            request = GenerationRequest(
                mode=GenerationMode.REFACTORING,
                description=refactoring_description,
                target_files=target_files,
                requirements=target_improvements or [],
                constraints=[],
                context_hints={
                    'refactoring_type': refactoring_type,
                    'current_issues': current_issues or [],
                    'target_improvements': target_improvements or []
                },
                quality_threshold=quality_threshold
            )
            
            # Generate refactored code
            result = self.codegen_client.generate_code(
                request=request,
                repo_path=repo_path,
                team_context=team_context
            )
            
            # Update session statistics
            self._update_session_stats(result)
            
            self.logger.info(f"Code refactoring completed: success={result.success}, quality={result.quality_score:.2f}")
            return result
            
        except Exception as e:
            self.logger.error(f"Code refactoring failed: {e}")
            self.session_stats['failed_generations'] += 1
            raise
    
    def assess_code_quality(
        self,
        code: str,
        repo_path: str,
        language: Optional[str] = None
    ) -> Dict[str, Any]:
        """Assess the quality of given code.
        
        Args:
            code: Code to assess
            repo_path: Path to the repository for context
            language: Programming language (auto-detected if not provided)
            
        Returns:
            Detailed quality assessment
        """
        self.logger.info("Starting code quality assessment")
        
        try:
            # Gather context for assessment
            task_context = TaskContext(
                task_type="quality_assessment",
                description="Code quality assessment",
                requirements=[],
                constraints=[],
                target_files=[],
                related_issues=[],
                priority="medium",
                estimated_complexity="low"
            )
            
            context = self.context_engine.gather_comprehensive_context(
                repo_path=repo_path,
                task_context=task_context,
                use_cache=True
            )
            
            # Perform quality assessment
            metrics = self.quality_assessor.get_detailed_metrics(code, context)
            
            self.logger.info(f"Quality assessment completed: score={metrics.overall_score:.2f}")
            
            return {
                'overall_score': metrics.overall_score,
                'detailed_metrics': {
                    'readability': metrics.readability_score,
                    'maintainability': metrics.maintainability_score,
                    'correctness': metrics.correctness_score,
                    'performance': metrics.performance_score,
                    'security': metrics.security_score,
                    'documentation': metrics.documentation_score,
                    'testing': metrics.testing_score
                },
                'recommendations': metrics.recommendations,
                'critical_issues': metrics.critical_issues,
                'complexity_metrics': metrics.complexity_metrics,
                'security_issues': metrics.security_issues,
                'performance_issues': metrics.performance_issues
            }
            
        except Exception as e:
            self.logger.error(f"Quality assessment failed: {e}")
            raise
    
    def get_session_statistics(self) -> Dict[str, Any]:
        """Get statistics for the current session.
        
        Returns:
            Session statistics and performance metrics
        """
        session_duration = time.time() - self.session_stats['session_start_time']
        
        # Get component metrics
        codegen_metrics = self.codegen_client.get_metrics()
        
        return {
            'session': {
                'duration_seconds': session_duration,
                'requests_processed': self.session_stats['requests_processed'],
                'successful_generations': self.session_stats['successful_generations'],
                'failed_generations': self.session_stats['failed_generations'],
                'success_rate': (
                    self.session_stats['successful_generations'] / 
                    max(1, self.session_stats['requests_processed'])
                ),
                'avg_execution_time': (
                    self.session_stats['total_execution_time'] / 
                    max(1, self.session_stats['requests_processed'])
                ),
                'avg_quality_score': self.session_stats['avg_quality_score']
            },
            'codegen_client': codegen_metrics,
            'feedback_analytics': self.feedback_processor.get_feedback_analytics()
        }
    
    def export_learning_data(self) -> Dict[str, Any]:
        """Export learning data for analysis or transfer.
        
        Returns:
            Comprehensive learning data
        """
        return {
            'feedback_data': self.feedback_processor.export_learning_data(),
            'session_stats': self.session_stats,
            'config': self.config,
            'export_timestamp': time.time()
        }
    
    def import_learning_data(self, learning_data: Dict[str, Any]) -> None:
        """Import learning data from previous sessions.
        
        Args:
            learning_data: Learning data to import
        """
        if 'feedback_data' in learning_data:
            self.feedback_processor.import_learning_data(learning_data['feedback_data'])
        
        self.logger.info("Learning data imported successfully")
    
    def _load_config(self, config_path: Optional[str]) -> Dict[str, Any]:
        """Load configuration from file or use defaults.
        
        Args:
            config_path: Path to configuration file
            
        Returns:
            Configuration dictionary
        """
        if config_path and Path(config_path).exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                return config
            except Exception as e:
                print(f"Warning: Failed to load config from {config_path}: {e}")
        
        # Try to load from default locations
        default_paths = [
            "config/agent_config.yaml",
            "codegen-agent/config/agent_config.yaml",
            os.path.expanduser("~/.codegen/agent_config.yaml")
        ]
        
        for path in default_paths:
            if Path(path).exists():
                try:
                    with open(path, 'r') as f:
                        config = yaml.safe_load(f)
                    return config
                except Exception:
                    continue
        
        # Return minimal default config
        return {
            'agent': {
                'learning': {'enabled': True},
                'quality': {'threshold': 0.8},
                'retry': {'max_retries': 3}
            }
        }
    
    def _setup_logging(self) -> None:
        """Setup logging configuration."""
        log_config = self.config.get('logging', {})
        
        # Create logs directory if it doesn't exist
        log_file = log_config.get('file', 'logs/codegen_agent.log')
        log_dir = Path(log_file).parent
        log_dir.mkdir(exist_ok=True)
        
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_config.get('level', 'INFO')),
            format=log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s'),
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
    
    def _update_session_stats(self, result: GenerationResult) -> None:
        """Update session statistics with generation result.
        
        Args:
            result: Generation result to process
        """
        self.session_stats['requests_processed'] += 1
        
        if result.success:
            self.session_stats['successful_generations'] += 1
        else:
            self.session_stats['failed_generations'] += 1
        
        self.session_stats['total_execution_time'] += result.execution_time
        
        # Update running average of quality scores
        total_requests = self.session_stats['requests_processed']
        current_avg = self.session_stats['avg_quality_score']
        self.session_stats['avg_quality_score'] = (
            (current_avg * (total_requests - 1) + result.quality_score) / total_requests
        )


def create_agent_from_config(config_path: str, api_token: str, org_id: int = 1) -> AdvancedCodegenAgent:
    """Create an agent instance from configuration file.
    
    Args:
        config_path: Path to configuration file
        api_token: Codegen API token
        org_id: Organization ID
        
    Returns:
        Configured agent instance
    """
    return AdvancedCodegenAgent(
        api_token=api_token,
        org_id=org_id,
        config_path=config_path
    )


def create_agent_with_defaults(api_token: str, org_id: int = 1) -> AdvancedCodegenAgent:
    """Create an agent instance with default configuration.
    
    Args:
        api_token: Codegen API token
        org_id: Organization ID
        
    Returns:
        Agent instance with default configuration
    """
    return AdvancedCodegenAgent(
        api_token=api_token,
        org_id=org_id
    )

