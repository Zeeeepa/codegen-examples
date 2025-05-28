"""
Claude Code Integration & Validation Engine

Main orchestrator for comprehensive PR validation, debugging, and iterative improvement.
Provides enterprise-grade security, performance optimization, and multi-platform CI/CD support.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
import json
import uuid

from .claude_client import ClaudeClient
from .error_analyzer import ErrorAnalyzer
from .fix_suggester import FixSuggester
from .learning_engine import LearningEngine
from .security.container_manager import ContainerManager
from .security.security_scanner import SecurityScanner
from .platforms.platform_manager import PlatformManager
from .ml.error_classifier import ErrorClassifier
from .monitoring.metrics_collector import MetricsCollector


class ValidationStatus(Enum):
    """Validation status enumeration."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"


class ValidationSeverity(Enum):
    """Issue severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass
class ValidationIssue:
    """Represents a validation issue found during analysis."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: str = ""
    severity: ValidationSeverity = ValidationSeverity.MEDIUM
    message: str = ""
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    column: Optional[int] = None
    rule_id: Optional[str] = None
    category: str = "general"
    confidence: float = 1.0
    suggested_fix: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """Complete validation result with issues, fixes, and metadata."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ValidationStatus = ValidationStatus.PENDING
    issues: List[ValidationIssue] = field(default_factory=list)
    fixes: List[Dict[str, Any]] = field(default_factory=list)
    execution_time: float = 0.0
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def critical_issues(self) -> List[ValidationIssue]:
        """Get critical severity issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.CRITICAL]
    
    @property
    def high_issues(self) -> List[ValidationIssue]:
        """Get high severity issues."""
        return [issue for issue in self.issues if issue.severity == ValidationSeverity.HIGH]
    
    @property
    def success_rate(self) -> float:
        """Calculate validation success rate."""
        if not self.issues:
            return 1.0
        critical_count = len(self.critical_issues)
        high_count = len(self.high_issues)
        total_issues = len(self.issues)
        
        # Weight critical and high issues more heavily
        weighted_issues = critical_count * 3 + high_count * 2 + (total_issues - critical_count - high_count)
        max_weight = total_issues * 3
        
        return max(0.0, 1.0 - (weighted_issues / max_weight)) if max_weight > 0 else 1.0


class ValidationEngine:
    """
    Main validation engine that orchestrates comprehensive PR validation.
    
    Features:
    - Secure containerized code execution
    - ML-powered error analysis and fix suggestions
    - Multi-platform CI/CD integration
    - Real-time collaboration and progress tracking
    - Continuous learning from validation patterns
    """
    
    def __init__(
        self,
        claude_api_key: str,
        database_url: str,
        redis_url: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """Initialize the validation engine with required dependencies."""
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        
        # Initialize core components
        self.claude_client = ClaudeClient(
            api_key=claude_api_key,
            model=self.config.get("claude_model", "claude-3-5-sonnet-20241022"),
            max_tokens=self.config.get("claude_max_tokens", 4096)
        )
        
        self.error_analyzer = ErrorAnalyzer(
            claude_client=self.claude_client,
            config=self.config.get("error_analyzer", {})
        )
        
        self.fix_suggester = FixSuggester(
            claude_client=self.claude_client,
            config=self.config.get("fix_suggester", {})
        )
        
        self.learning_engine = LearningEngine(
            database_url=database_url,
            config=self.config.get("learning_engine", {})
        )
        
        self.container_manager = ContainerManager(
            runtime=self.config.get("container_runtime", "gvisor"),
            config=self.config.get("container_manager", {})
        )
        
        self.security_scanner = SecurityScanner(
            config=self.config.get("security_scanner", {})
        )
        
        self.platform_manager = PlatformManager(
            config=self.config.get("platform_manager", {})
        )
        
        self.error_classifier = ErrorClassifier(
            model_path=self.config.get("ml_model_path", "./ml-models"),
            config=self.config.get("error_classifier", {})
        )
        
        self.metrics_collector = MetricsCollector(
            redis_url=redis_url,
            config=self.config.get("metrics_collector", {})
        )
        
        # Validation pipeline configuration
        self.max_execution_time = self.config.get("max_execution_time", 300)
        self.enable_learning = self.config.get("enable_learning", True)
        self.confidence_threshold = self.config.get("confidence_threshold", 0.8)
        
    async def validate_pr(
        self,
        repo_url: str,
        pr_number: int,
        branch: str,
        validation_types: Optional[List[str]] = None,
        custom_config: Optional[Dict[str, Any]] = None
    ) -> ValidationResult:
        """
        Validate a pull request with comprehensive analysis.
        
        Args:
            repo_url: Repository URL
            pr_number: Pull request number
            branch: Branch name to validate
            validation_types: Specific validation types to run
            custom_config: Custom configuration for this validation
            
        Returns:
            ValidationResult with issues, fixes, and metadata
        """
        start_time = time.time()
        result = ValidationResult()
        
        try:
            self.logger.info(f"Starting validation for PR #{pr_number} on {repo_url}")
            result.status = ValidationStatus.RUNNING
            
            # Collect metrics
            await self.metrics_collector.record_validation_start(repo_url, pr_number)
            
            # Clone repository in secure container
            container_id = await self.container_manager.create_container(
                image="claude-validation:latest",
                command=["sleep", "infinity"],
                limits={
                    "memory": self.config.get("max_memory_mb", 1024) * 1024 * 1024,
                    "cpu": self.config.get("max_cpu_cores", 2),
                    "timeout": self.max_execution_time
                }
            )
            
            try:
                # Clone repository
                await self.container_manager.exec_command(
                    container_id,
                    ["git", "clone", "--depth", "1", "-b", branch, repo_url, "/workspace"]
                )
                
                # Run validation pipeline
                validation_tasks = []
                
                if not validation_types or "code_quality" in validation_types:
                    validation_tasks.append(self._run_code_quality_validation(container_id))
                
                if not validation_types or "security" in validation_types:
                    validation_tasks.append(self._run_security_validation(container_id))
                
                if not validation_types or "testing" in validation_types:
                    validation_tasks.append(self._run_testing_validation(container_id))
                
                if not validation_types or "performance" in validation_types:
                    validation_tasks.append(self._run_performance_validation(container_id))
                
                # Execute validations in parallel
                validation_results = await asyncio.gather(*validation_tasks, return_exceptions=True)
                
                # Aggregate results
                for validation_result in validation_results:
                    if isinstance(validation_result, Exception):
                        self.logger.error(f"Validation task failed: {validation_result}")
                        result.issues.append(ValidationIssue(
                            type="validation_error",
                            severity=ValidationSeverity.HIGH,
                            message=f"Validation task failed: {str(validation_result)}",
                            category="system"
                        ))
                    else:
                        result.issues.extend(validation_result)
                
                # Analyze errors with ML
                if result.issues:
                    analyzed_issues = await self.error_analyzer.analyze_issues(result.issues)
                    result.issues = analyzed_issues
                    
                    # Generate fix suggestions
                    fixes = await self.fix_suggester.suggest_fixes(result.issues)
                    result.fixes = fixes
                
                # Learn from validation results
                if self.enable_learning:
                    await self.learning_engine.record_validation(result)
                
                # Determine final status
                if result.critical_issues:
                    result.status = ValidationStatus.FAILED
                elif result.high_issues:
                    result.status = ValidationStatus.FAILED
                else:
                    result.status = ValidationStatus.SUCCESS
                    
            finally:
                # Cleanup container
                await self.container_manager.remove_container(container_id)
                
        except asyncio.TimeoutError:
            result.status = ValidationStatus.TIMEOUT
            self.logger.error(f"Validation timed out for PR #{pr_number}")
            
        except Exception as e:
            result.status = ValidationStatus.ERROR
            result.issues.append(ValidationIssue(
                type="system_error",
                severity=ValidationSeverity.CRITICAL,
                message=f"Validation engine error: {str(e)}",
                category="system"
            ))
            self.logger.error(f"Validation failed for PR #{pr_number}: {e}")
            
        finally:
            result.execution_time = time.time() - start_time
            
            # Record metrics
            await self.metrics_collector.record_validation_complete(
                repo_url, pr_number, result.status, result.execution_time
            )
            
        return result
    
    async def _run_code_quality_validation(self, container_id: str) -> List[ValidationIssue]:
        """Run code quality validation (linting, formatting, complexity)."""
        issues = []
        
        try:
            # Run ESLint for JavaScript/TypeScript
            eslint_result = await self.container_manager.exec_command(
                container_id,
                ["npx", "eslint", "/workspace", "--format", "json"],
                capture_output=True
            )
            
            if eslint_result.stdout:
                eslint_data = json.loads(eslint_result.stdout)
                for file_result in eslint_data:
                    for message in file_result.get("messages", []):
                        issues.append(ValidationIssue(
                            type="code_quality",
                            severity=self._map_eslint_severity(message.get("severity", 1)),
                            message=message.get("message", ""),
                            file_path=file_result.get("filePath", "").replace("/workspace/", ""),
                            line_number=message.get("line"),
                            column=message.get("column"),
                            rule_id=message.get("ruleId"),
                            category="linting"
                        ))
            
            # Run Pylint for Python
            pylint_result = await self.container_manager.exec_command(
                container_id,
                ["pylint", "/workspace", "--output-format", "json"],
                capture_output=True
            )
            
            if pylint_result.stdout:
                pylint_data = json.loads(pylint_result.stdout)
                for message in pylint_data:
                    issues.append(ValidationIssue(
                        type="code_quality",
                        severity=self._map_pylint_severity(message.get("type", "warning")),
                        message=message.get("message", ""),
                        file_path=message.get("path", "").replace("/workspace/", ""),
                        line_number=message.get("line"),
                        column=message.get("column"),
                        rule_id=message.get("message-id"),
                        category="linting"
                    ))
                    
        except Exception as e:
            self.logger.error(f"Code quality validation failed: {e}")
            issues.append(ValidationIssue(
                type="validation_error",
                severity=ValidationSeverity.MEDIUM,
                message=f"Code quality validation failed: {str(e)}",
                category="system"
            ))
            
        return issues
    
    async def _run_security_validation(self, container_id: str) -> List[ValidationIssue]:
        """Run security validation (SAST, dependency scanning)."""
        return await self.security_scanner.scan_container(container_id)
    
    async def _run_testing_validation(self, container_id: str) -> List[ValidationIssue]:
        """Run testing validation (unit, integration tests)."""
        issues = []
        
        try:
            # Run Jest tests for JavaScript/TypeScript
            jest_result = await self.container_manager.exec_command(
                container_id,
                ["npm", "test", "--", "--json"],
                capture_output=True,
                cwd="/workspace"
            )
            
            if jest_result.stdout:
                jest_data = json.loads(jest_result.stdout)
                if not jest_data.get("success", True):
                    for test_result in jest_data.get("testResults", []):
                        for assertion in test_result.get("assertionResults", []):
                            if assertion.get("status") == "failed":
                                issues.append(ValidationIssue(
                                    type="test_failure",
                                    severity=ValidationSeverity.HIGH,
                                    message=assertion.get("failureMessages", ["Test failed"])[0],
                                    file_path=test_result.get("name", "").replace("/workspace/", ""),
                                    category="testing"
                                ))
            
            # Run pytest for Python
            pytest_result = await self.container_manager.exec_command(
                container_id,
                ["python", "-m", "pytest", "/workspace", "--json-report", "--json-report-file=/tmp/pytest.json"],
                capture_output=True
            )
            
            pytest_json_result = await self.container_manager.exec_command(
                container_id,
                ["cat", "/tmp/pytest.json"],
                capture_output=True
            )
            
            if pytest_json_result.stdout:
                pytest_data = json.loads(pytest_json_result.stdout)
                for test in pytest_data.get("tests", []):
                    if test.get("outcome") == "failed":
                        issues.append(ValidationIssue(
                            type="test_failure",
                            severity=ValidationSeverity.HIGH,
                            message=test.get("call", {}).get("longrepr", "Test failed"),
                            file_path=test.get("nodeid", "").split("::")[0],
                            category="testing"
                        ))
                        
        except Exception as e:
            self.logger.error(f"Testing validation failed: {e}")
            issues.append(ValidationIssue(
                type="validation_error",
                severity=ValidationSeverity.MEDIUM,
                message=f"Testing validation failed: {str(e)}",
                category="system"
            ))
            
        return issues
    
    async def _run_performance_validation(self, container_id: str) -> List[ValidationIssue]:
        """Run performance validation (memory, CPU profiling)."""
        issues = []
        
        try:
            # Run memory profiling
            memory_result = await self.container_manager.exec_command(
                container_id,
                ["python", "-m", "memory_profiler", "/workspace/main.py"],
                capture_output=True
            )
            
            # Analyze memory usage patterns
            if memory_result.stdout:
                lines = memory_result.stdout.split('\n')
                for line in lines:
                    if 'MiB' in line and float(line.split()[1]) > 100:  # Memory threshold
                        issues.append(ValidationIssue(
                            type="performance",
                            severity=ValidationSeverity.MEDIUM,
                            message=f"High memory usage detected: {line.strip()}",
                            category="performance"
                        ))
                        
        except Exception as e:
            self.logger.error(f"Performance validation failed: {e}")
            
        return issues
    
    def _map_eslint_severity(self, severity: int) -> ValidationSeverity:
        """Map ESLint severity to ValidationSeverity."""
        if severity == 2:
            return ValidationSeverity.HIGH
        elif severity == 1:
            return ValidationSeverity.MEDIUM
        else:
            return ValidationSeverity.LOW
    
    def _map_pylint_severity(self, severity: str) -> ValidationSeverity:
        """Map Pylint severity to ValidationSeverity."""
        severity_map = {
            "error": ValidationSeverity.HIGH,
            "warning": ValidationSeverity.MEDIUM,
            "refactor": ValidationSeverity.LOW,
            "convention": ValidationSeverity.LOW,
            "info": ValidationSeverity.INFO
        }
        return severity_map.get(severity.lower(), ValidationSeverity.MEDIUM)
    
    async def get_validation_history(
        self,
        repo_url: str,
        limit: int = 100
    ) -> List[ValidationResult]:
        """Get validation history for a repository."""
        return await self.learning_engine.get_validation_history(repo_url, limit)
    
    async def get_validation_metrics(
        self,
        repo_url: str,
        time_range: str = "7d"
    ) -> Dict[str, Any]:
        """Get validation metrics for a repository."""
        return await self.metrics_collector.get_metrics(repo_url, time_range)
    
    async def shutdown(self):
        """Gracefully shutdown the validation engine."""
        await self.container_manager.cleanup()
        await self.learning_engine.close()
        await self.metrics_collector.close()

