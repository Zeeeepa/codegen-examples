#!/usr/bin/env python
"""
Workflow Templates

This module provides pre-defined workflow templates for common
multi-agent coordination scenarios.
"""

import uuid
from typing import Any, Dict, List, Optional
from datetime import datetime

from ..src.agent_registry import AgentType
from ..src.resource_manager import ResourceSpec, ResourceType, ResourceRequest


class WorkflowTemplate:
    """Base class for workflow templates."""
    
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
    
    def generate_workflow_config(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate workflow configuration from template."""
        raise NotImplementedError


class SoftwareDevelopmentWorkflow(WorkflowTemplate):
    """Template for complete software development workflow."""
    
    def __init__(self):
        super().__init__(
            name="Software Development Workflow",
            description="Complete software development lifecycle from planning to deployment"
        )
    
    def generate_workflow_config(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate software development workflow."""
        project_name = parameters.get('project_name', 'New Project')
        complexity = parameters.get('complexity', 'medium')  # low, medium, high
        
        # Adjust resources based on complexity
        complexity_multiplier = {'low': 0.5, 'medium': 1.0, 'high': 2.0}[complexity]
        
        tasks = [
            {
                'id': 'planning',
                'name': 'Project Planning',
                'agent_type': 'planner',
                'parameters': {
                    'project_name': project_name,
                    'requirements': parameters.get('requirements', ''),
                    'constraints': parameters.get('constraints', {})
                },
                'priority': 10,
                'timeout': 300,
                'resources': {
                    'cpu': 0.5 * complexity_multiplier,
                    'memory': 1.0 * complexity_multiplier
                }
            },
            {
                'id': 'architecture_design',
                'name': 'Architecture Design',
                'agent_type': 'planner',
                'parameters': {
                    'project_type': parameters.get('project_type', 'web_application'),
                    'scale': parameters.get('scale', 'medium')
                },
                'priority': 9,
                'timeout': 600,
                'resources': {
                    'cpu': 1.0 * complexity_multiplier,
                    'memory': 2.0 * complexity_multiplier
                }
            },
            {
                'id': 'backend_development',
                'name': 'Backend Development',
                'agent_type': 'coder',
                'parameters': {
                    'language': parameters.get('backend_language', 'python'),
                    'framework': parameters.get('backend_framework', 'fastapi'),
                    'features': parameters.get('backend_features', [])
                },
                'priority': 8,
                'timeout': 1800,
                'resources': {
                    'cpu': 2.0 * complexity_multiplier,
                    'memory': 4.0 * complexity_multiplier
                }
            },
            {
                'id': 'frontend_development',
                'name': 'Frontend Development',
                'agent_type': 'coder',
                'parameters': {
                    'language': parameters.get('frontend_language', 'typescript'),
                    'framework': parameters.get('frontend_framework', 'react'),
                    'features': parameters.get('frontend_features', [])
                },
                'priority': 8,
                'timeout': 1800,
                'resources': {
                    'cpu': 2.0 * complexity_multiplier,
                    'memory': 4.0 * complexity_multiplier
                }
            },
            {
                'id': 'backend_testing',
                'name': 'Backend Testing',
                'agent_type': 'tester',
                'parameters': {
                    'test_types': ['unit', 'integration', 'api'],
                    'coverage_threshold': 80
                },
                'priority': 7,
                'timeout': 900,
                'resources': {
                    'cpu': 1.5 * complexity_multiplier,
                    'memory': 3.0 * complexity_multiplier
                }
            },
            {
                'id': 'frontend_testing',
                'name': 'Frontend Testing',
                'agent_type': 'tester',
                'parameters': {
                    'test_types': ['unit', 'component', 'e2e'],
                    'coverage_threshold': 75
                },
                'priority': 7,
                'timeout': 900,
                'resources': {
                    'cpu': 1.5 * complexity_multiplier,
                    'memory': 3.0 * complexity_multiplier
                }
            },
            {
                'id': 'code_review',
                'name': 'Code Review',
                'agent_type': 'reviewer',
                'parameters': {
                    'review_criteria': ['security', 'performance', 'maintainability'],
                    'approval_threshold': 8.0
                },
                'priority': 6,
                'timeout': 600,
                'resources': {
                    'cpu': 1.0 * complexity_multiplier,
                    'memory': 2.0 * complexity_multiplier
                }
            },
            {
                'id': 'deployment',
                'name': 'Application Deployment',
                'agent_type': 'deployer',
                'parameters': {
                    'environment': parameters.get('deployment_environment', 'staging'),
                    'deployment_strategy': parameters.get('deployment_strategy', 'rolling')
                },
                'priority': 5,
                'timeout': 1200,
                'resources': {
                    'cpu': 1.0 * complexity_multiplier,
                    'memory': 2.0 * complexity_multiplier
                }
            }
        ]
        
        dependencies = [
            {'task': 'architecture_design', 'depends_on': 'planning'},
            {'task': 'backend_development', 'depends_on': 'architecture_design'},
            {'task': 'frontend_development', 'depends_on': 'architecture_design'},
            {'task': 'backend_testing', 'depends_on': 'backend_development'},
            {'task': 'frontend_testing', 'depends_on': 'frontend_development'},
            {'task': 'code_review', 'depends_on': 'backend_testing'},
            {'task': 'code_review', 'depends_on': 'frontend_testing'},
            {'task': 'deployment', 'depends_on': 'code_review'}
        ]
        
        return {
            'name': f"{project_name} Development Workflow",
            'description': f"Complete development workflow for {project_name}",
            'tasks_config': tasks,
            'dependencies': dependencies,
            'metadata': {
                'template': 'software_development',
                'complexity': complexity,
                'estimated_duration': self._estimate_duration(tasks, dependencies),
                'created_at': datetime.now().isoformat()
            }
        }
    
    def _estimate_duration(self, tasks: List[Dict], dependencies: List[Dict]) -> float:
        """Estimate total workflow duration."""
        # Simple estimation - in practice, would use critical path analysis
        return sum(task.get('timeout', 300) for task in tasks) * 0.7  # Assume some parallelization


class MLModelDevelopmentWorkflow(WorkflowTemplate):
    """Template for machine learning model development workflow."""
    
    def __init__(self):
        super().__init__(
            name="ML Model Development Workflow",
            description="End-to-end machine learning model development and deployment"
        )
    
    def generate_workflow_config(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate ML model development workflow."""
        model_name = parameters.get('model_name', 'ML Model')
        model_type = parameters.get('model_type', 'classification')
        
        tasks = [
            {
                'id': 'data_analysis',
                'name': 'Data Analysis and Exploration',
                'agent_type': 'custom',
                'parameters': {
                    'capability': 'data_preprocessing',
                    'dataset_path': parameters.get('dataset_path', ''),
                    'analysis_type': 'exploratory'
                },
                'priority': 10,
                'timeout': 900,
                'resources': {
                    'cpu': 2.0,
                    'memory': 8.0,
                    'gpu': 0.0
                }
            },
            {
                'id': 'data_preprocessing',
                'name': 'Data Preprocessing',
                'agent_type': 'custom',
                'parameters': {
                    'capability': 'data_preprocessing',
                    'preprocessing_steps': parameters.get('preprocessing_steps', [
                        'clean_missing_values',
                        'feature_engineering',
                        'data_splitting'
                    ])
                },
                'priority': 9,
                'timeout': 1200,
                'resources': {
                    'cpu': 4.0,
                    'memory': 16.0,
                    'gpu': 0.0
                }
            },
            {
                'id': 'model_training',
                'name': 'Model Training',
                'agent_type': 'custom',
                'parameters': {
                    'capability': 'model_training',
                    'model_type': model_type,
                    'hyperparameters': parameters.get('hyperparameters', {}),
                    'training_config': parameters.get('training_config', {})
                },
                'priority': 8,
                'timeout': 3600,
                'resources': {
                    'cpu': 8.0,
                    'memory': 32.0,
                    'gpu': 1.0
                }
            },
            {
                'id': 'model_evaluation',
                'name': 'Model Evaluation',
                'agent_type': 'tester',
                'parameters': {
                    'evaluation_metrics': parameters.get('evaluation_metrics', [
                        'accuracy', 'precision', 'recall', 'f1_score'
                    ]),
                    'validation_strategy': 'cross_validation'
                },
                'priority': 7,
                'timeout': 600,
                'resources': {
                    'cpu': 4.0,
                    'memory': 16.0,
                    'gpu': 0.5
                }
            },
            {
                'id': 'model_optimization',
                'name': 'Model Optimization',
                'agent_type': 'custom',
                'parameters': {
                    'capability': 'model_training',
                    'optimization_strategy': 'hyperparameter_tuning',
                    'optimization_budget': parameters.get('optimization_budget', 10)
                },
                'priority': 6,
                'timeout': 7200,
                'resources': {
                    'cpu': 16.0,
                    'memory': 64.0,
                    'gpu': 2.0
                }
            },
            {
                'id': 'model_validation',
                'name': 'Final Model Validation',
                'agent_type': 'reviewer',
                'parameters': {
                    'validation_criteria': ['performance', 'bias', 'interpretability'],
                    'approval_threshold': 0.85
                },
                'priority': 5,
                'timeout': 300,
                'resources': {
                    'cpu': 2.0,
                    'memory': 8.0,
                    'gpu': 0.0
                }
            },
            {
                'id': 'model_deployment',
                'name': 'Model Deployment',
                'agent_type': 'deployer',
                'parameters': {
                    'deployment_target': parameters.get('deployment_target', 'api_endpoint'),
                    'scaling_config': parameters.get('scaling_config', {})
                },
                'priority': 4,
                'timeout': 900,
                'resources': {
                    'cpu': 4.0,
                    'memory': 16.0,
                    'gpu': 0.0
                }
            }
        ]
        
        dependencies = [
            {'task': 'data_preprocessing', 'depends_on': 'data_analysis'},
            {'task': 'model_training', 'depends_on': 'data_preprocessing'},
            {'task': 'model_evaluation', 'depends_on': 'model_training'},
            {'task': 'model_optimization', 'depends_on': 'model_evaluation'},
            {'task': 'model_validation', 'depends_on': 'model_optimization'},
            {'task': 'model_deployment', 'depends_on': 'model_validation'}
        ]
        
        return {
            'name': f"{model_name} Development Workflow",
            'description': f"ML model development workflow for {model_name}",
            'tasks_config': tasks,
            'dependencies': dependencies,
            'metadata': {
                'template': 'ml_model_development',
                'model_type': model_type,
                'estimated_duration': self._estimate_duration(tasks, dependencies),
                'created_at': datetime.now().isoformat()
            }
        }
    
    def _estimate_duration(self, tasks: List[Dict], dependencies: List[Dict]) -> float:
        """Estimate total workflow duration."""
        return sum(task.get('timeout', 300) for task in tasks) * 0.8


class DataPipelineWorkflow(WorkflowTemplate):
    """Template for data pipeline development workflow."""
    
    def __init__(self):
        super().__init__(
            name="Data Pipeline Workflow",
            description="Data pipeline development and deployment workflow"
        )
    
    def generate_workflow_config(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate data pipeline workflow."""
        pipeline_name = parameters.get('pipeline_name', 'Data Pipeline')
        data_sources = parameters.get('data_sources', [])
        
        tasks = [
            {
                'id': 'pipeline_design',
                'name': 'Pipeline Architecture Design',
                'agent_type': 'planner',
                'parameters': {
                    'data_sources': data_sources,
                    'target_destinations': parameters.get('destinations', []),
                    'processing_requirements': parameters.get('processing_requirements', [])
                },
                'priority': 10,
                'timeout': 600,
                'resources': {'cpu': 1.0, 'memory': 2.0}
            },
            {
                'id': 'data_ingestion',
                'name': 'Data Ingestion Development',
                'agent_type': 'coder',
                'parameters': {
                    'ingestion_type': parameters.get('ingestion_type', 'batch'),
                    'data_formats': parameters.get('data_formats', ['json', 'csv'])
                },
                'priority': 9,
                'timeout': 1200,
                'resources': {'cpu': 2.0, 'memory': 4.0}
            },
            {
                'id': 'data_transformation',
                'name': 'Data Transformation Logic',
                'agent_type': 'coder',
                'parameters': {
                    'transformations': parameters.get('transformations', []),
                    'validation_rules': parameters.get('validation_rules', [])
                },
                'priority': 8,
                'timeout': 1800,
                'resources': {'cpu': 4.0, 'memory': 8.0}
            },
            {
                'id': 'pipeline_testing',
                'name': 'Pipeline Testing',
                'agent_type': 'tester',
                'parameters': {
                    'test_data': parameters.get('test_data_path', ''),
                    'test_scenarios': ['data_quality', 'performance', 'error_handling']
                },
                'priority': 7,
                'timeout': 900,
                'resources': {'cpu': 2.0, 'memory': 4.0}
            },
            {
                'id': 'pipeline_deployment',
                'name': 'Pipeline Deployment',
                'agent_type': 'deployer',
                'parameters': {
                    'deployment_platform': parameters.get('platform', 'kubernetes'),
                    'scheduling': parameters.get('scheduling', 'daily')
                },
                'priority': 6,
                'timeout': 600,
                'resources': {'cpu': 1.0, 'memory': 2.0}
            }
        ]
        
        dependencies = [
            {'task': 'data_ingestion', 'depends_on': 'pipeline_design'},
            {'task': 'data_transformation', 'depends_on': 'data_ingestion'},
            {'task': 'pipeline_testing', 'depends_on': 'data_transformation'},
            {'task': 'pipeline_deployment', 'depends_on': 'pipeline_testing'}
        ]
        
        return {
            'name': f"{pipeline_name} Development Workflow",
            'description': f"Data pipeline workflow for {pipeline_name}",
            'tasks_config': tasks,
            'dependencies': dependencies,
            'metadata': {
                'template': 'data_pipeline',
                'data_sources_count': len(data_sources),
                'estimated_duration': self._estimate_duration(tasks, dependencies),
                'created_at': datetime.now().isoformat()
            }
        }
    
    def _estimate_duration(self, tasks: List[Dict], dependencies: List[Dict]) -> float:
        """Estimate total workflow duration."""
        return sum(task.get('timeout', 300) for task in tasks) * 0.75


class InfrastructureProvisioningWorkflow(WorkflowTemplate):
    """Template for infrastructure provisioning workflow."""
    
    def __init__(self):
        super().__init__(
            name="Infrastructure Provisioning Workflow",
            description="Cloud infrastructure provisioning and configuration workflow"
        )
    
    def generate_workflow_config(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Generate infrastructure provisioning workflow."""
        environment = parameters.get('environment', 'staging')
        cloud_provider = parameters.get('cloud_provider', 'aws')
        
        tasks = [
            {
                'id': 'infrastructure_planning',
                'name': 'Infrastructure Planning',
                'agent_type': 'planner',
                'parameters': {
                    'cloud_provider': cloud_provider,
                    'environment': environment,
                    'requirements': parameters.get('requirements', {})
                },
                'priority': 10,
                'timeout': 300,
                'resources': {'cpu': 0.5, 'memory': 1.0}
            },
            {
                'id': 'network_setup',
                'name': 'Network Configuration',
                'agent_type': 'custom',
                'parameters': {
                    'capability': 'infrastructure_provisioning',
                    'component': 'network',
                    'vpc_config': parameters.get('vpc_config', {})
                },
                'priority': 9,
                'timeout': 600,
                'resources': {'cpu': 1.0, 'memory': 2.0}
            },
            {
                'id': 'compute_provisioning',
                'name': 'Compute Resources Provisioning',
                'agent_type': 'custom',
                'parameters': {
                    'capability': 'infrastructure_provisioning',
                    'component': 'compute',
                    'instance_config': parameters.get('instance_config', {})
                },
                'priority': 8,
                'timeout': 900,
                'resources': {'cpu': 1.5, 'memory': 3.0}
            },
            {
                'id': 'database_setup',
                'name': 'Database Setup',
                'agent_type': 'custom',
                'parameters': {
                    'capability': 'infrastructure_provisioning',
                    'component': 'database',
                    'database_config': parameters.get('database_config', {})
                },
                'priority': 7,
                'timeout': 1200,
                'resources': {'cpu': 2.0, 'memory': 4.0}
            },
            {
                'id': 'security_configuration',
                'name': 'Security Configuration',
                'agent_type': 'custom',
                'parameters': {
                    'capability': 'infrastructure_provisioning',
                    'component': 'security',
                    'security_policies': parameters.get('security_policies', [])
                },
                'priority': 6,
                'timeout': 600,
                'resources': {'cpu': 1.0, 'memory': 2.0}
            },
            {
                'id': 'monitoring_setup',
                'name': 'Monitoring and Logging Setup',
                'agent_type': 'custom',
                'parameters': {
                    'capability': 'infrastructure_provisioning',
                    'component': 'monitoring',
                    'monitoring_config': parameters.get('monitoring_config', {})
                },
                'priority': 5,
                'timeout': 450,
                'resources': {'cpu': 1.0, 'memory': 2.0}
            },
            {
                'id': 'infrastructure_testing',
                'name': 'Infrastructure Testing',
                'agent_type': 'tester',
                'parameters': {
                    'test_types': ['connectivity', 'security', 'performance'],
                    'test_scenarios': parameters.get('test_scenarios', [])
                },
                'priority': 4,
                'timeout': 600,
                'resources': {'cpu': 1.5, 'memory': 3.0}
            }
        ]
        
        dependencies = [
            {'task': 'network_setup', 'depends_on': 'infrastructure_planning'},
            {'task': 'compute_provisioning', 'depends_on': 'network_setup'},
            {'task': 'database_setup', 'depends_on': 'network_setup'},
            {'task': 'security_configuration', 'depends_on': 'compute_provisioning'},
            {'task': 'security_configuration', 'depends_on': 'database_setup'},
            {'task': 'monitoring_setup', 'depends_on': 'security_configuration'},
            {'task': 'infrastructure_testing', 'depends_on': 'monitoring_setup'}
        ]
        
        return {
            'name': f"{environment.title()} Infrastructure Provisioning",
            'description': f"Infrastructure provisioning workflow for {environment} environment",
            'tasks_config': tasks,
            'dependencies': dependencies,
            'metadata': {
                'template': 'infrastructure_provisioning',
                'cloud_provider': cloud_provider,
                'environment': environment,
                'estimated_duration': self._estimate_duration(tasks, dependencies),
                'created_at': datetime.now().isoformat()
            }
        }
    
    def _estimate_duration(self, tasks: List[Dict], dependencies: List[Dict]) -> float:
        """Estimate total workflow duration."""
        return sum(task.get('timeout', 300) for task in tasks) * 0.6  # High parallelization


# Template registry
WORKFLOW_TEMPLATES = {
    'software_development': SoftwareDevelopmentWorkflow(),
    'ml_model_development': MLModelDevelopmentWorkflow(),
    'data_pipeline': DataPipelineWorkflow(),
    'infrastructure_provisioning': InfrastructureProvisioningWorkflow()
}


def get_template(template_name: str) -> Optional[WorkflowTemplate]:
    """Get a workflow template by name."""
    return WORKFLOW_TEMPLATES.get(template_name)


def list_templates() -> List[Dict[str, str]]:
    """List all available workflow templates."""
    return [
        {
            'name': template_name,
            'title': template.name,
            'description': template.description
        }
        for template_name, template in WORKFLOW_TEMPLATES.items()
    ]


def create_workflow_from_template(template_name: str, parameters: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a workflow configuration from a template."""
    template = get_template(template_name)
    if not template:
        return None
    
    return template.generate_workflow_config(parameters)

