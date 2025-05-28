"""
Test suite for Pipeline Generator module

This module contains comprehensive tests for the pipeline generation functionality,
including unit tests, integration tests, and validation tests.
"""

import pytest
import json
import yaml
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.pipeline_generator import (
    PipelineGenerator,
    PipelineConfig,
    PipelineType,
    DeploymentStrategy,
    QualityGate,
    DeploymentConfig,
    SecurityConfig,
    MonitoringConfig,
    create_sample_config
)


class TestPipelineGenerator:
    """Test cases for PipelineGenerator class"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.generator = PipelineGenerator()
        self.sample_config = create_sample_config()
    
    def test_pipeline_generator_initialization(self):
        """Test pipeline generator initialization"""
        assert self.generator is not None
        assert hasattr(self.generator, 'templates')
        assert hasattr(self.generator, 'ml_models')
    
    def test_github_actions_pipeline_generation(self):
        """Test GitHub Actions pipeline generation"""
        config = PipelineConfig(
            name="test-app",
            type=PipelineType.GITHUB_ACTIONS,
            language="python",
            framework="fastapi"
        )
        
        pipeline = self.generator.generate_github_actions_pipeline(config)
        
        # Validate pipeline structure
        assert "name" in pipeline
        assert "on" in pipeline
        assert "env" in pipeline
        assert "jobs" in pipeline
        
        # Validate job structure
        assert "build-test" in pipeline["jobs"]
        build_job = pipeline["jobs"]["build-test"]
        assert "runs-on" in build_job
        assert "steps" in build_job
        assert "outputs" in build_job
        
        # Validate environment variables
        assert "REGISTRY" in pipeline["env"]
        assert "IMAGE_NAME" in pipeline["env"]
        assert "DEPLOYMENT_STRATEGY" in pipeline["env"]
    
    def test_gitlab_ci_pipeline_generation(self):
        """Test GitLab CI pipeline generation"""
        config = PipelineConfig(
            name="test-app",
            type=PipelineType.GITLAB_CI,
            language="python"
        )
        
        pipeline = self.generator.generate_gitlab_ci_pipeline(config)
        
        # Validate pipeline structure
        assert "stages" in pipeline
        assert "variables" in pipeline
        assert "before_script" in pipeline
        
        # Validate stages
        expected_stages = ["build", "test", "security", "deploy", "monitor"]
        assert pipeline["stages"] == expected_stages
        
        # Validate build job
        assert "build" in pipeline
        build_job = pipeline["build"]
        assert "stage" in build_job
        assert build_job["stage"] == "build"
    
    def test_jenkins_pipeline_generation(self):
        """Test Jenkins pipeline generation"""
        config = PipelineConfig(
            name="test-app",
            type=PipelineType.JENKINS,
            language="python"
        )
        
        jenkinsfile = self.generator.generate_jenkins_pipeline(config)
        
        # Validate Jenkinsfile structure
        assert isinstance(jenkinsfile, str)
        assert "pipeline {" in jenkinsfile
        assert "agent any" in jenkinsfile
        assert "environment {" in jenkinsfile
        assert "stages {" in jenkinsfile
        
        # Validate stages
        assert "stage('Checkout')" in jenkinsfile
        assert "stage('Build')" in jenkinsfile
        assert "stage('Security Scanning')" in jenkinsfile
        assert "stage('Quality Gates')" in jenkinsfile
    
    def test_pipeline_with_quality_gates(self):
        """Test pipeline generation with quality gates"""
        quality_gates = [
            QualityGate(
                name="Code Coverage",
                type="test",
                threshold=80.0,
                ml_enabled=True,
                timeout_minutes=15
            ),
            QualityGate(
                name="Security Scan",
                type="security",
                threshold=95.0,
                ml_enabled=True,
                timeout_minutes=20
            )
        ]
        
        config = PipelineConfig(
            name="test-app",
            type=PipelineType.GITHUB_ACTIONS,
            language="python",
            quality_gates=quality_gates
        )
        
        pipeline = self.generator.generate_github_actions_pipeline(config)
        
        # Validate quality gates are included
        build_job = pipeline["jobs"]["build-test"]
        steps = build_job["steps"]
        
        # Find quality gate step
        quality_gate_step = None
        for step in steps:
            if isinstance(step, dict) and step.get("name") == "Quality Gates":
                quality_gate_step = step
                break
        
        assert quality_gate_step is not None
        assert "steps" in quality_gate_step
    
    def test_pipeline_with_deployment_config(self):
        """Test pipeline generation with deployment configuration"""
        deployment_config = DeploymentConfig(
            strategy=DeploymentStrategy.CANARY,
            environments=["staging", "production"],
            approval_required=True,
            feature_flags_enabled=True,
            rollback_threshold=0.95
        )
        
        config = PipelineConfig(
            name="test-app",
            type=PipelineType.GITHUB_ACTIONS,
            language="python",
            deployment=deployment_config
        )
        
        pipeline = self.generator.generate_github_actions_pipeline(config)
        
        # Validate deployment jobs are created
        for env in deployment_config.environments:
            job_name = f"deploy-{env}"
            assert job_name in pipeline["jobs"]
            
            deploy_job = pipeline["jobs"][job_name]
            assert "environment" in deploy_job
            assert deploy_job["environment"] == env
    
    def test_pipeline_with_security_config(self):
        """Test pipeline generation with security configuration"""
        security_config = SecurityConfig(
            sast_enabled=True,
            dast_enabled=True,
            dependency_scan=True,
            container_scan=True,
            secret_scanning=True
        )
        
        config = PipelineConfig(
            name="test-app",
            type=PipelineType.GITHUB_ACTIONS,
            language="python",
            security=security_config
        )
        
        pipeline = self.generator.generate_github_actions_pipeline(config)
        
        # Validate security scanning steps
        build_job = pipeline["jobs"]["build-test"]
        steps = build_job["steps"]
        
        # Find security scanning step
        security_step = None
        for step in steps:
            if isinstance(step, dict) and "Security Scanning" in step.get("name", ""):
                security_step = step
                break
        
        assert security_step is not None
    
    def test_pipeline_with_monitoring_config(self):
        """Test pipeline generation with monitoring configuration"""
        monitoring_config = MonitoringConfig(
            prometheus_enabled=True,
            grafana_enabled=True,
            jaeger_enabled=True,
            custom_metrics=["business_metrics"],
            alert_channels=["slack", "email"]
        )
        
        config = PipelineConfig(
            name="test-app",
            type=PipelineType.GITHUB_ACTIONS,
            language="python",
            monitoring=monitoring_config
        )
        
        pipeline = self.generator.generate_github_actions_pipeline(config)
        
        # Validate monitoring job is created
        assert "setup-monitoring" in pipeline["jobs"]
        monitoring_job = pipeline["jobs"]["setup-monitoring"]
        assert "steps" in monitoring_job
    
    def test_progressive_delivery_pipeline(self):
        """Test progressive delivery pipeline generation"""
        deployment_config = DeploymentConfig(
            strategy=DeploymentStrategy.PROGRESSIVE,
            environments=["staging", "production"],
            progressive_percentage=[10, 25, 50, 100],
            feature_flags_enabled=True
        )
        
        config = PipelineConfig(
            name="test-app",
            type=PipelineType.GITHUB_ACTIONS,
            language="python",
            deployment=deployment_config
        )
        
        pipeline = self.generator.generate_github_actions_pipeline(config)
        
        # Validate progressive delivery job
        assert "progressive-delivery" in pipeline["jobs"]
        progressive_job = pipeline["jobs"]["progressive-delivery"]
        assert "needs" in progressive_job
        assert "deploy-staging" in progressive_job["needs"]
    
    def test_multi_cloud_pipeline(self):
        """Test multi-cloud pipeline generation"""
        config = PipelineConfig(
            name="test-app",
            type=PipelineType.GITHUB_ACTIONS,
            language="python",
            multi_cloud=True,
            cost_optimization=True
        )
        
        pipeline = self.generator.generate_github_actions_pipeline(config)
        
        # Validate multi-cloud environment variables
        assert "DEPLOYMENT_STRATEGY" in pipeline["env"]
        
        # Validate that the pipeline includes multi-cloud considerations
        build_job = pipeline["jobs"]["build-test"]
        assert "steps" in build_job
    
    def test_sample_config_creation(self):
        """Test sample configuration creation"""
        config = create_sample_config()
        
        assert config.name == "enterprise-app"
        assert config.type == PipelineType.GITHUB_ACTIONS
        assert config.language == "python"
        assert config.framework == "fastapi"
        
        # Validate quality gates
        assert len(config.quality_gates) == 3
        assert config.quality_gates[0].name == "Code Coverage"
        assert config.quality_gates[1].name == "Security Scan"
        assert config.quality_gates[2].name == "Performance Test"
        
        # Validate deployment config
        assert config.deployment.strategy == DeploymentStrategy.PROGRESSIVE
        assert "staging" in config.deployment.environments
        assert "production" in config.deployment.environments
        
        # Validate security config
        assert config.security.sast_enabled is True
        assert config.security.dast_enabled is True
        
        # Validate monitoring config
        assert config.monitoring.prometheus_enabled is True
        assert config.monitoring.grafana_enabled is True


class TestPipelineConfigValidation:
    """Test cases for pipeline configuration validation"""
    
    def test_valid_pipeline_config(self):
        """Test valid pipeline configuration"""
        config = PipelineConfig(
            name="test-app",
            type=PipelineType.GITHUB_ACTIONS,
            language="python"
        )
        
        assert config.name == "test-app"
        assert config.type == PipelineType.GITHUB_ACTIONS
        assert config.language == "python"
    
    def test_invalid_pipeline_type(self):
        """Test invalid pipeline type handling"""
        with pytest.raises(ValueError):
            PipelineConfig(
                name="test-app",
                type="invalid_type",  # This should raise an error
                language="python"
            )
    
    def test_quality_gate_validation(self):
        """Test quality gate validation"""
        # Valid quality gate
        gate = QualityGate(
            name="Test Gate",
            type="test",
            threshold=80.0,
            ml_enabled=True
        )
        
        assert gate.name == "Test Gate"
        assert gate.threshold == 80.0
        assert gate.ml_enabled is True
    
    def test_deployment_config_validation(self):
        """Test deployment configuration validation"""
        config = DeploymentConfig(
            strategy=DeploymentStrategy.CANARY,
            environments=["staging", "production"],
            rollback_threshold=0.95
        )
        
        assert config.strategy == DeploymentStrategy.CANARY
        assert len(config.environments) == 2
        assert config.rollback_threshold == 0.95


class TestPipelineIntegration:
    """Integration tests for pipeline generation"""
    
    @pytest.fixture
    def mock_context(self):
        """Mock context for testing"""
        return {
            "project_name": "test-project",
            "branch": "main",
            "commit_sha": "abc123",
            "build_number": "1234"
        }
    
    def test_end_to_end_pipeline_generation(self, mock_context):
        """Test end-to-end pipeline generation"""
        generator = PipelineGenerator()
        config = create_sample_config()
        
        # Generate all pipeline types
        github_pipeline = generator.generate_github_actions_pipeline(config)
        gitlab_pipeline = generator.generate_gitlab_ci_pipeline(config)
        jenkins_pipeline = generator.generate_jenkins_pipeline(config)
        
        # Validate all pipelines are generated
        assert github_pipeline is not None
        assert gitlab_pipeline is not None
        assert jenkins_pipeline is not None
        
        # Validate GitHub Actions pipeline
        assert "jobs" in github_pipeline
        assert len(github_pipeline["jobs"]) > 0
        
        # Validate GitLab CI pipeline
        assert "stages" in gitlab_pipeline
        assert len(gitlab_pipeline["stages"]) > 0
        
        # Validate Jenkins pipeline
        assert "pipeline {" in jenkins_pipeline
        assert "stages {" in jenkins_pipeline
    
    def test_pipeline_serialization(self):
        """Test pipeline serialization to YAML/JSON"""
        generator = PipelineGenerator()
        config = create_sample_config()
        
        # Generate GitHub Actions pipeline
        pipeline = generator.generate_github_actions_pipeline(config)
        
        # Test JSON serialization
        json_str = json.dumps(pipeline, indent=2)
        assert json_str is not None
        
        # Test YAML serialization
        yaml_str = yaml.dump(pipeline, default_flow_style=False)
        assert yaml_str is not None
        
        # Validate round-trip
        parsed_pipeline = yaml.safe_load(yaml_str)
        assert parsed_pipeline["name"] == pipeline["name"]
    
    @patch('src.pipeline_generator.PipelineGenerator._load_templates')
    def test_template_loading(self, mock_load_templates):
        """Test template loading functionality"""
        mock_load_templates.return_value = None
        
        generator = PipelineGenerator()
        mock_load_templates.assert_called_once()
    
    def test_error_handling(self):
        """Test error handling in pipeline generation"""
        generator = PipelineGenerator()
        
        # Test with invalid configuration
        invalid_config = PipelineConfig(
            name="",  # Empty name should be handled gracefully
            type=PipelineType.GITHUB_ACTIONS,
            language="python"
        )
        
        # Should not raise an exception
        pipeline = generator.generate_github_actions_pipeline(invalid_config)
        assert pipeline is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

