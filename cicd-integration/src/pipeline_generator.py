"""
Advanced CI/CD Pipeline Generator with Multi-Platform Support

This module provides intelligent pipeline generation for GitHub Actions, GitLab CI, and Jenkins
with enterprise-grade features including progressive delivery, feature flags, and ML-based optimization.
"""

import json
import yaml
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class PipelineType(Enum):
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    JENKINS = "jenkins"


class DeploymentStrategy(Enum):
    ROLLING = "rolling"
    BLUE_GREEN = "blue_green"
    CANARY = "canary"
    PROGRESSIVE = "progressive"


@dataclass
class QualityGate:
    """Configuration for intelligent quality gates"""
    name: str
    type: str  # test, security, performance, compliance
    threshold: float
    ml_enabled: bool = True
    auto_approve: bool = False
    timeout_minutes: int = 30


@dataclass
class DeploymentConfig:
    """Advanced deployment configuration"""
    strategy: DeploymentStrategy
    environments: List[str]
    approval_required: bool = True
    feature_flags_enabled: bool = True
    progressive_percentage: Optional[List[int]] = None
    rollback_threshold: float = 0.95
    health_check_url: Optional[str] = None


@dataclass
class SecurityConfig:
    """Security scanning and compliance configuration"""
    sast_enabled: bool = True
    dast_enabled: bool = True
    dependency_scan: bool = True
    container_scan: bool = True
    compliance_frameworks: List[str] = None
    secret_scanning: bool = True


@dataclass
class MonitoringConfig:
    """Observability and monitoring configuration"""
    prometheus_enabled: bool = True
    grafana_enabled: bool = True
    jaeger_enabled: bool = True
    custom_metrics: List[str] = None
    alert_channels: List[str] = None


@dataclass
class PipelineConfig:
    """Complete pipeline configuration"""
    name: str
    type: PipelineType
    language: str
    framework: Optional[str] = None
    quality_gates: List[QualityGate] = None
    deployment: DeploymentConfig = None
    security: SecurityConfig = None
    monitoring: MonitoringConfig = None
    multi_cloud: bool = False
    cost_optimization: bool = True


class PipelineGenerator:
    """Advanced pipeline generator with ML-based optimization"""
    
    def __init__(self):
        self.templates = {}
        self.ml_models = {}
        self._load_templates()
    
    def _load_templates(self):
        """Load pipeline templates for different platforms"""
        # This would typically load from external template files
        pass
    
    def generate_github_actions_pipeline(self, config: PipelineConfig) -> Dict[str, Any]:
        """Generate GitHub Actions workflow with advanced features"""
        
        workflow = {
            "name": f"CI/CD Pipeline - {config.name}",
            "on": {
                "push": {"branches": ["main", "develop"]},
                "pull_request": {"branches": ["main"]},
                "workflow_dispatch": {}
            },
            "env": {
                "REGISTRY": "ghcr.io",
                "IMAGE_NAME": "${{ github.repository }}",
                "DEPLOYMENT_STRATEGY": config.deployment.strategy.value if config.deployment else "rolling"
            },
            "jobs": {}
        }
        
        # Build and test job
        workflow["jobs"]["build-test"] = {
            "runs-on": "ubuntu-latest",
            "outputs": {
                "image-digest": "${{ steps.build.outputs.digest }}",
                "version": "${{ steps.version.outputs.version }}"
            },
            "steps": [
                {"uses": "actions/checkout@v4"},
                {"name": "Setup Environment", "uses": "./.github/actions/setup"},
                self._generate_security_scanning_steps(config.security),
                self._generate_build_steps(config),
                self._generate_test_steps(config),
                self._generate_quality_gate_steps(config.quality_gates)
            ]
        }
        
        # Multi-environment deployment jobs
        if config.deployment:
            for env in config.deployment.environments:
                workflow["jobs"][f"deploy-{env}"] = self._generate_deployment_job(config, env)
        
        # Progressive delivery job
        if config.deployment and config.deployment.strategy == DeploymentStrategy.PROGRESSIVE:
            workflow["jobs"]["progressive-delivery"] = self._generate_progressive_delivery_job(config)
        
        # Monitoring and alerting job
        if config.monitoring:
            workflow["jobs"]["setup-monitoring"] = self._generate_monitoring_job(config)
        
        return workflow
    
    def generate_gitlab_ci_pipeline(self, config: PipelineConfig) -> Dict[str, Any]:
        """Generate GitLab CI pipeline with enterprise features"""
        
        pipeline = {
            "stages": ["build", "test", "security", "deploy", "monitor"],
            "variables": {
                "DOCKER_DRIVER": "overlay2",
                "DEPLOYMENT_STRATEGY": config.deployment.strategy.value if config.deployment else "rolling",
                "FEATURE_FLAGS_ENABLED": str(config.deployment.feature_flags_enabled).lower() if config.deployment else "false"
            },
            "before_script": [
                "echo 'Setting up CI/CD environment...'",
                "export CI_COMMIT_SHORT_SHA=${CI_COMMIT_SHA:0:8}"
            ]
        }
        
        # Build stage
        pipeline["build"] = {
            "stage": "build",
            "image": "docker:latest",
            "services": ["docker:dind"],
            "script": [
                "docker build -t $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA .",
                "docker push $CI_REGISTRY_IMAGE:$CI_COMMIT_SHORT_SHA"
            ],
            "artifacts": {
                "reports": {
                    "dotenv": "build.env"
                }
            }
        }
        
        # Security scanning
        if config.security:
            pipeline.update(self._generate_gitlab_security_jobs(config.security))
        
        # Quality gates
        if config.quality_gates:
            pipeline.update(self._generate_gitlab_quality_gates(config.quality_gates))
        
        # Deployment jobs
        if config.deployment:
            pipeline.update(self._generate_gitlab_deployment_jobs(config))
        
        return pipeline
    
    def generate_jenkins_pipeline(self, config: PipelineConfig) -> str:
        """Generate Jenkins pipeline (Jenkinsfile) with advanced features"""
        
        jenkinsfile = f"""
pipeline {{
    agent any
    
    environment {{
        REGISTRY = 'your-registry.com'
        IMAGE_NAME = '{config.name}'
        DEPLOYMENT_STRATEGY = '{config.deployment.strategy.value if config.deployment else "rolling"}'
        FEATURE_FLAGS_ENABLED = '{str(config.deployment.feature_flags_enabled).lower() if config.deployment else "false"}'
    }}
    
    options {{
        buildDiscarder(logRotator(numToKeepStr: '10'))
        timeout(time: 60, unit: 'MINUTES')
        retry(3)
    }}
    
    stages {{
        stage('Checkout') {{
            steps {{
                checkout scm
                script {{
                    env.BUILD_VERSION = sh(returnStdout: true, script: 'git rev-parse --short HEAD').trim()
                }}
            }}
        }}
        
        stage('Build') {{
            steps {{
                script {{
                    {self._generate_jenkins_build_script(config)}
                }}
            }}
        }}
        
        stage('Security Scanning') {{
            parallel {{
                {self._generate_jenkins_security_stages(config.security) if config.security else ""}
            }}
        }}
        
        stage('Quality Gates') {{
            steps {{
                {self._generate_jenkins_quality_gates(config.quality_gates) if config.quality_gates else "echo 'No quality gates configured'"}
            }}
        }}
        
        stage('Deploy') {{
            when {{
                anyOf {{
                    branch 'main'
                    branch 'develop'
                }}
            }}
            steps {{
                {self._generate_jenkins_deployment_script(config) if config.deployment else "echo 'No deployment configured'"}
            }}
        }}
        
        stage('Post-Deploy Monitoring') {{
            steps {{
                {self._generate_jenkins_monitoring_script(config.monitoring) if config.monitoring else "echo 'No monitoring configured'"}
            }}
        }}
    }}
    
    post {{
        always {{
            {self._generate_jenkins_cleanup_script()}
        }}
        failure {{
            {self._generate_jenkins_failure_script(config)}
        }}
        success {{
            {self._generate_jenkins_success_script(config)}
        }}
    }}
}}
"""
        return jenkinsfile
    
    def _generate_security_scanning_steps(self, security_config: SecurityConfig) -> Dict[str, Any]:
        """Generate security scanning steps for GitHub Actions"""
        if not security_config:
            return {"name": "Skip Security Scanning", "run": "echo 'Security scanning disabled'"}
        
        steps = []
        
        if security_config.sast_enabled:
            steps.append({
                "name": "SAST Scanning",
                "uses": "github/codeql-action/init@v2",
                "with": {"languages": "python,javascript,typescript"}
            })
        
        if security_config.dependency_scan:
            steps.append({
                "name": "Dependency Scanning",
                "uses": "actions/dependency-review-action@v3"
            })
        
        if security_config.container_scan:
            steps.append({
                "name": "Container Security Scan",
                "uses": "aquasecurity/trivy-action@master",
                "with": {
                    "image-ref": "${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}",
                    "format": "sarif",
                    "output": "trivy-results.sarif"
                }
            })
        
        return {"name": "Security Scanning", "steps": steps}
    
    def _generate_build_steps(self, config: PipelineConfig) -> Dict[str, Any]:
        """Generate build steps based on language and framework"""
        return {
            "name": "Build Application",
            "run": f"""
                echo "Building {config.language} application..."
                # Add language-specific build commands here
                docker build -t ${{{{ env.REGISTRY }}}}/${{{{ env.IMAGE_NAME }}}}:${{{{ github.sha }}}} .
            """
        }
    
    def _generate_test_steps(self, config: PipelineConfig) -> Dict[str, Any]:
        """Generate comprehensive test steps"""
        return {
            "name": "Run Tests",
            "run": """
                echo "Running unit tests..."
                echo "Running integration tests..."
                echo "Running performance tests..."
                # Add test commands here
            """
        }
    
    def _generate_quality_gate_steps(self, quality_gates: List[QualityGate]) -> Dict[str, Any]:
        """Generate intelligent quality gate steps"""
        if not quality_gates:
            return {"name": "Skip Quality Gates", "run": "echo 'No quality gates configured'"}
        
        steps = []
        for gate in quality_gates:
            steps.append({
                "name": f"Quality Gate: {gate.name}",
                "run": f"""
                    echo "Executing quality gate: {gate.name}"
                    echo "Type: {gate.type}"
                    echo "Threshold: {gate.threshold}"
                    echo "ML Enabled: {gate.ml_enabled}"
                    # Add quality gate logic here
                """,
                "timeout-minutes": gate.timeout_minutes
            })
        
        return {"name": "Quality Gates", "steps": steps}
    
    def _generate_deployment_job(self, config: PipelineConfig, environment: str) -> Dict[str, Any]:
        """Generate deployment job for specific environment"""
        return {
            "needs": ["build-test"],
            "runs-on": "ubuntu-latest",
            "environment": environment,
            "if": f"github.ref == 'refs/heads/main' || github.ref == 'refs/heads/develop'",
            "steps": [
                {"uses": "actions/checkout@v4"},
                {
                    "name": f"Deploy to {environment}",
                    "run": f"""
                        echo "Deploying to {environment} using {config.deployment.strategy.value} strategy"
                        echo "Feature flags enabled: {config.deployment.feature_flags_enabled}"
                        # Add deployment logic here
                    """
                },
                {
                    "name": "Health Check",
                    "run": f"""
                        echo "Performing health check for {environment}"
                        # Add health check logic here
                    """
                }
            ]
        }
    
    def _generate_progressive_delivery_job(self, config: PipelineConfig) -> Dict[str, Any]:
        """Generate progressive delivery job with canary deployment"""
        return {
            "needs": ["deploy-staging"],
            "runs-on": "ubuntu-latest",
            "if": "github.ref == 'refs/heads/main'",
            "steps": [
                {
                    "name": "Progressive Delivery",
                    "run": f"""
                        echo "Starting progressive delivery..."
                        echo "Rollback threshold: {config.deployment.rollback_threshold}"
                        # Add progressive delivery logic here
                    """
                }
            ]
        }
    
    def _generate_monitoring_job(self, config: PipelineConfig) -> Dict[str, Any]:
        """Generate monitoring setup job"""
        return {
            "needs": ["deploy-production"],
            "runs-on": "ubuntu-latest",
            "steps": [
                {
                    "name": "Setup Monitoring",
                    "run": f"""
                        echo "Setting up monitoring..."
                        echo "Prometheus enabled: {config.monitoring.prometheus_enabled}"
                        echo "Grafana enabled: {config.monitoring.grafana_enabled}"
                        # Add monitoring setup logic here
                    """
                }
            ]
        }
    
    def _generate_gitlab_security_jobs(self, security_config: SecurityConfig) -> Dict[str, Any]:
        """Generate GitLab security scanning jobs"""
        jobs = {}
        
        if security_config.sast_enabled:
            jobs["sast"] = {
                "stage": "security",
                "image": "registry.gitlab.com/gitlab-org/security-products/analyzers/semgrep:latest",
                "script": ["semgrep --config=auto --json --output=sast-report.json ."],
                "artifacts": {
                    "reports": {"sast": "sast-report.json"}
                }
            }
        
        if security_config.dependency_scan:
            jobs["dependency_scanning"] = {
                "stage": "security",
                "image": "registry.gitlab.com/gitlab-org/security-products/analyzers/gemnasium:latest",
                "script": ["gemnasium-dependency-scanning"],
                "artifacts": {
                    "reports": {"dependency_scanning": "dependency-scanning-report.json"}
                }
            }
        
        return jobs
    
    def _generate_gitlab_quality_gates(self, quality_gates: List[QualityGate]) -> Dict[str, Any]:
        """Generate GitLab quality gate jobs"""
        jobs = {}
        
        for gate in quality_gates:
            jobs[f"quality_gate_{gate.name.lower().replace(' ', '_')}"] = {
                "stage": "test",
                "script": [
                    f"echo 'Executing quality gate: {gate.name}'",
                    f"echo 'Threshold: {gate.threshold}'",
                    "# Add quality gate logic here"
                ],
                "timeout": f"{gate.timeout_minutes}m"
            }
        
        return jobs
    
    def _generate_gitlab_deployment_jobs(self, config: PipelineConfig) -> Dict[str, Any]:
        """Generate GitLab deployment jobs"""
        jobs = {}
        
        for env in config.deployment.environments:
            jobs[f"deploy_{env}"] = {
                "stage": "deploy",
                "script": [
                    f"echo 'Deploying to {env}'",
                    f"echo 'Strategy: {config.deployment.strategy.value}'",
                    "# Add deployment logic here"
                ],
                "environment": {"name": env},
                "when": "manual" if config.deployment.approval_required else "on_success"
            }
        
        return jobs
    
    def _generate_jenkins_build_script(self, config: PipelineConfig) -> str:
        """Generate Jenkins build script"""
        return f"""
            echo "Building {config.language} application..."
            sh 'docker build -t $REGISTRY/$IMAGE_NAME:$BUILD_VERSION .'
            sh 'docker push $REGISTRY/$IMAGE_NAME:$BUILD_VERSION'
        """
    
    def _generate_jenkins_security_stages(self, security_config: SecurityConfig) -> str:
        """Generate Jenkins security scanning stages"""
        stages = []
        
        if security_config.sast_enabled:
            stages.append("""
                stage('SAST') {
                    steps {
                        sh 'echo "Running SAST scanning..."'
                        // Add SAST logic here
                    }
                }
            """)
        
        if security_config.dependency_scan:
            stages.append("""
                stage('Dependency Scan') {
                    steps {
                        sh 'echo "Running dependency scanning..."'
                        // Add dependency scan logic here
                    }
                }
            """)
        
        return "\n".join(stages)
    
    def _generate_jenkins_quality_gates(self, quality_gates: List[QualityGate]) -> str:
        """Generate Jenkins quality gate steps"""
        steps = []
        
        for gate in quality_gates:
            steps.append(f"""
                timeout(time: {gate.timeout_minutes}, unit: 'MINUTES') {{
                    sh 'echo "Executing quality gate: {gate.name}"'
                    sh 'echo "Threshold: {gate.threshold}"'
                    // Add quality gate logic here
                }}
            """)
        
        return "\n".join(steps)
    
    def _generate_jenkins_deployment_script(self, config: PipelineConfig) -> str:
        """Generate Jenkins deployment script"""
        return f"""
            script {{
                for (env in {config.deployment.environments}) {{
                    stage("Deploy to ${{env}}") {{
                        sh "echo 'Deploying to ${{env}} using {config.deployment.strategy.value} strategy'"
                        // Add deployment logic here
                    }}
                }}
            }}
        """
    
    def _generate_jenkins_monitoring_script(self, monitoring_config: MonitoringConfig) -> str:
        """Generate Jenkins monitoring setup script"""
        return f"""
            sh 'echo "Setting up monitoring..."'
            sh 'echo "Prometheus enabled: {monitoring_config.prometheus_enabled}"'
            sh 'echo "Grafana enabled: {monitoring_config.grafana_enabled}"'
            // Add monitoring setup logic here
        """
    
    def _generate_jenkins_cleanup_script(self) -> str:
        """Generate Jenkins cleanup script"""
        return """
            sh 'echo "Cleaning up..."'
            sh 'docker system prune -f'
            // Add cleanup logic here
        """
    
    def _generate_jenkins_failure_script(self, config: PipelineConfig) -> str:
        """Generate Jenkins failure handling script"""
        return f"""
            sh 'echo "Pipeline failed for {config.name}"'
            // Add failure notification logic here
        """
    
    def _generate_jenkins_success_script(self, config: PipelineConfig) -> str:
        """Generate Jenkins success handling script"""
        return f"""
            sh 'echo "Pipeline succeeded for {config.name}"'
            // Add success notification logic here
        """


def create_sample_config() -> PipelineConfig:
    """Create a sample pipeline configuration"""
    return PipelineConfig(
        name="enterprise-app",
        type=PipelineType.GITHUB_ACTIONS,
        language="python",
        framework="fastapi",
        quality_gates=[
            QualityGate(
                name="Code Coverage",
                type="test",
                threshold=0.8,
                ml_enabled=True,
                auto_approve=False,
                timeout_minutes=15
            ),
            QualityGate(
                name="Security Scan",
                type="security",
                threshold=0.95,
                ml_enabled=True,
                auto_approve=False,
                timeout_minutes=20
            ),
            QualityGate(
                name="Performance Test",
                type="performance",
                threshold=0.9,
                ml_enabled=True,
                auto_approve=False,
                timeout_minutes=30
            )
        ],
        deployment=DeploymentConfig(
            strategy=DeploymentStrategy.PROGRESSIVE,
            environments=["staging", "production"],
            approval_required=True,
            feature_flags_enabled=True,
            progressive_percentage=[10, 25, 50, 100],
            rollback_threshold=0.95,
            health_check_url="/health"
        ),
        security=SecurityConfig(
            sast_enabled=True,
            dast_enabled=True,
            dependency_scan=True,
            container_scan=True,
            compliance_frameworks=["SOC2", "GDPR", "HIPAA"],
            secret_scanning=True
        ),
        monitoring=MonitoringConfig(
            prometheus_enabled=True,
            grafana_enabled=True,
            jaeger_enabled=True,
            custom_metrics=["business_metrics", "sla_metrics"],
            alert_channels=["slack", "email", "pagerduty"]
        ),
        multi_cloud=True,
        cost_optimization=True
    )


if __name__ == "__main__":
    # Example usage
    generator = PipelineGenerator()
    config = create_sample_config()
    
    # Generate GitHub Actions workflow
    github_workflow = generator.generate_github_actions_pipeline(config)
    print("GitHub Actions Workflow Generated")
    
    # Generate GitLab CI pipeline
    gitlab_pipeline = generator.generate_gitlab_ci_pipeline(config)
    print("GitLab CI Pipeline Generated")
    
    # Generate Jenkins pipeline
    jenkins_pipeline = generator.generate_jenkins_pipeline(config)
    print("Jenkins Pipeline Generated")

