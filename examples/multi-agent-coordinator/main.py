#!/usr/bin/env python
"""
Multi-Agent Coordination System Example

This example demonstrates the complete multi-agent coordination system
with workflow orchestration, resource management, and monitoring.
"""

import asyncio
import logging
import time
from typing import Dict, Any

from src.workflow_engine import WorkflowEngine
from src.agent_registry import AgentRegistry
from src.resource_manager import ResourceManager, ResourceNode, ResourceType
from src.monitoring_system import MonitoringSystem
from agents.base_agent import (
    create_planner_agent,
    create_coder_agent,
    create_tester_agent,
    create_reviewer_agent,
    create_deployer_agent,
    create_ml_engineer_agent,
    create_devops_engineer_agent
)
from workflows.workflow_templates import create_workflow_from_template


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MultiAgentCoordinator:
    """Main coordinator class that orchestrates the entire system."""
    
    def __init__(self):
        """Initialize the multi-agent coordination system."""
        # Initialize core components
        self.monitoring_system = MonitoringSystem()
        self.resource_manager = ResourceManager(enable_ml_optimization=True)
        self.agent_registry = AgentRegistry(enable_auto_scaling=True)
        self.workflow_engine = WorkflowEngine(
            agent_registry=self.agent_registry,
            resource_manager=self.resource_manager,
            monitoring_system=self.monitoring_system
        )
        
        # System state
        self.is_running = False
        self.agents = {}
        self.workflows = {}
    
    async def initialize(self) -> None:
        """Initialize the coordination system."""
        logger.info("Initializing Multi-Agent Coordination System...")
        
        # Start monitoring system
        await self.monitoring_system.start()
        
        # Setup resource nodes
        await self._setup_resource_nodes()
        
        # Register agents
        await self._register_agents()
        
        # Setup monitoring webhooks (example)
        # self.monitoring_system.add_webhook_url("https://your-webhook-url.com/alerts")
        
        self.is_running = True
        logger.info("Multi-Agent Coordination System initialized successfully")
    
    async def _setup_resource_nodes(self) -> None:
        """Setup resource nodes for the system."""
        # Main compute node
        main_node = ResourceNode(
            id="main_compute",
            name="Main Compute Node",
            location="datacenter_1",
            resources={
                ResourceType.CPU: 16.0,
                ResourceType.MEMORY: 64.0,
                ResourceType.GPU: 2.0,
                ResourceType.STORAGE: 1000.0,
                ResourceType.NETWORK: 10.0
            },
            capabilities={"general_compute", "ml_training", "web_hosting"}
        )
        await self.resource_manager.register_node(main_node)
        
        # ML-specific node
        ml_node = ResourceNode(
            id="ml_compute",
            name="ML Compute Node",
            location="datacenter_1",
            resources={
                ResourceType.CPU: 32.0,
                ResourceType.MEMORY: 128.0,
                ResourceType.GPU: 8.0,
                ResourceType.STORAGE: 2000.0,
                ResourceType.NETWORK: 25.0
            },
            capabilities={"ml_training", "gpu_compute", "data_processing"}
        )
        await self.resource_manager.register_node(ml_node)
        
        # Edge compute node
        edge_node = ResourceNode(
            id="edge_compute",
            name="Edge Compute Node",
            location="edge_location_1",
            resources={
                ResourceType.CPU: 8.0,
                ResourceType.MEMORY: 32.0,
                ResourceType.GPU: 1.0,
                ResourceType.STORAGE: 500.0,
                ResourceType.NETWORK: 5.0
            },
            capabilities={"edge_compute", "low_latency", "iot_processing"}
        )
        await self.resource_manager.register_node(edge_node)
        
        logger.info("Resource nodes registered successfully")
    
    async def _register_agents(self) -> None:
        """Register agents with the system."""
        # Create and register different types of agents
        agents_to_create = [
            ("planner_1", create_planner_agent, "Primary Planner Agent"),
            ("planner_2", create_planner_agent, "Secondary Planner Agent"),
            ("coder_1", create_coder_agent, "Backend Coder Agent"),
            ("coder_2", create_coder_agent, "Frontend Coder Agent"),
            ("tester_1", create_tester_agent, "Unit Tester Agent"),
            ("tester_2", create_tester_agent, "Integration Tester Agent"),
            ("reviewer_1", create_reviewer_agent, "Code Reviewer Agent"),
            ("deployer_1", create_deployer_agent, "Production Deployer Agent"),
            ("ml_engineer_1", create_ml_engineer_agent, "ML Engineer Agent"),
            ("devops_1", create_devops_engineer_agent, "DevOps Engineer Agent")
        ]
        
        for agent_id, agent_factory, agent_name in agents_to_create:
            agent = agent_factory(agent_name)
            await self.agent_registry.register_agent(agent)
            self.agents[agent_id] = agent
            logger.info(f"Registered agent: {agent_id} ({agent_name})")
        
        logger.info(f"Registered {len(self.agents)} agents successfully")
    
    async def create_workflow(self, template_name: str, parameters: Dict[str, Any]) -> str:
        """Create a workflow from a template."""
        if not self.is_running:
            raise RuntimeError("System not initialized")
        
        # Generate workflow configuration from template
        workflow_config = create_workflow_from_template(template_name, parameters)
        if not workflow_config:
            raise ValueError(f"Unknown template: {template_name}")
        
        # Create workflow
        workflow_id = await self.workflow_engine.create_workflow(
            name=workflow_config['name'],
            description=workflow_config['description'],
            tasks_config=workflow_config['tasks_config'],
            dependencies=workflow_config.get('dependencies', []),
            metadata=workflow_config.get('metadata', {})
        )
        
        self.workflows[workflow_id] = {
            'template': template_name,
            'parameters': parameters,
            'created_at': time.time()
        }
        
        logger.info(f"Created workflow {workflow_id} from template {template_name}")
        return workflow_id
    
    async def execute_workflow(self, workflow_id: str) -> bool:
        """Execute a workflow."""
        if workflow_id not in self.workflows:
            raise ValueError(f"Workflow {workflow_id} not found")
        
        logger.info(f"Starting execution of workflow {workflow_id}")
        success = await self.workflow_engine.execute_workflow(workflow_id)
        
        if success:
            logger.info(f"Workflow {workflow_id} completed successfully")
        else:
            logger.error(f"Workflow {workflow_id} failed")
        
        return success
    
    async def get_system_status(self) -> Dict[str, Any]:
        """Get comprehensive system status."""
        return {
            'system_running': self.is_running,
            'monitoring': await self.monitoring_system.health_check(),
            'resources': self.resource_manager.get_resource_status(),
            'agents': await self.agent_registry.get_registry_status(),
            'workflows': {
                'total': len(self.workflows),
                'active': len(self.workflow_engine.active_workflows)
            },
            'timestamp': time.time()
        }
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the system."""
        logger.info("Shutting down Multi-Agent Coordination System...")
        
        self.is_running = False
        
        # Shutdown components in reverse order
        await self.workflow_engine.shutdown()
        await self.agent_registry.shutdown()
        await self.resource_manager.shutdown()
        await self.monitoring_system.stop()
        
        logger.info("Multi-Agent Coordination System shutdown complete")


async def run_software_development_example():
    """Example: Software development workflow."""
    coordinator = MultiAgentCoordinator()
    
    try:
        # Initialize system
        await coordinator.initialize()
        
        # Create software development workflow
        workflow_id = await coordinator.create_workflow(
            template_name='software_development',
            parameters={
                'project_name': 'E-commerce API',
                'complexity': 'medium',
                'requirements': 'Build a REST API for e-commerce platform',
                'backend_language': 'python',
                'backend_framework': 'fastapi',
                'frontend_language': 'typescript',
                'frontend_framework': 'react',
                'deployment_environment': 'staging'
            }
        )
        
        # Execute workflow
        success = await coordinator.execute_workflow(workflow_id)
        
        # Get final status
        status = await coordinator.get_system_status()
        logger.info(f"Final system status: {status}")
        
        return success
        
    finally:
        await coordinator.shutdown()


async def run_ml_development_example():
    """Example: ML model development workflow."""
    coordinator = MultiAgentCoordinator()
    
    try:
        # Initialize system
        await coordinator.initialize()
        
        # Create ML development workflow
        workflow_id = await coordinator.create_workflow(
            template_name='ml_model_development',
            parameters={
                'model_name': 'Customer Churn Prediction',
                'model_type': 'classification',
                'dataset_path': '/data/customer_data.csv',
                'preprocessing_steps': [
                    'handle_missing_values',
                    'feature_scaling',
                    'categorical_encoding',
                    'feature_selection'
                ],
                'evaluation_metrics': ['accuracy', 'precision', 'recall', 'f1_score', 'auc'],
                'deployment_target': 'api_endpoint'
            }
        )
        
        # Execute workflow
        success = await coordinator.execute_workflow(workflow_id)
        
        # Monitor workflow progress
        for i in range(10):  # Check status 10 times
            await asyncio.sleep(30)  # Wait 30 seconds between checks
            workflow_status = await coordinator.workflow_engine.get_workflow_status(workflow_id)
            if workflow_status:
                logger.info(f"Workflow progress: {workflow_status['progress']:.1%}")
                if workflow_status['status'] in ['completed', 'failed']:
                    break
        
        return success
        
    finally:
        await coordinator.shutdown()


async def run_infrastructure_example():
    """Example: Infrastructure provisioning workflow."""
    coordinator = MultiAgentCoordinator()
    
    try:
        # Initialize system
        await coordinator.initialize()
        
        # Create infrastructure provisioning workflow
        workflow_id = await coordinator.create_workflow(
            template_name='infrastructure_provisioning',
            parameters={
                'environment': 'production',
                'cloud_provider': 'aws',
                'requirements': {
                    'high_availability': True,
                    'auto_scaling': True,
                    'backup_strategy': 'daily'
                },
                'vpc_config': {
                    'cidr_block': '10.0.0.0/16',
                    'availability_zones': 3
                },
                'instance_config': {
                    'instance_type': 't3.large',
                    'min_instances': 2,
                    'max_instances': 10
                },
                'database_config': {
                    'engine': 'postgresql',
                    'instance_class': 'db.t3.medium',
                    'multi_az': True
                }
            }
        )
        
        # Execute workflow
        success = await coordinator.execute_workflow(workflow_id)
        
        return success
        
    finally:
        await coordinator.shutdown()


async def run_parallel_workflows_example():
    """Example: Running multiple workflows in parallel."""
    coordinator = MultiAgentCoordinator()
    
    try:
        # Initialize system
        await coordinator.initialize()
        
        # Create multiple workflows
        workflows = []
        
        # Software development workflow
        sw_workflow_id = await coordinator.create_workflow(
            template_name='software_development',
            parameters={
                'project_name': 'Microservice A',
                'complexity': 'low',
                'backend_language': 'python'
            }
        )
        workflows.append(sw_workflow_id)
        
        # Data pipeline workflow
        dp_workflow_id = await coordinator.create_workflow(
            template_name='data_pipeline',
            parameters={
                'pipeline_name': 'Analytics Pipeline',
                'data_sources': ['database', 'api', 'files'],
                'ingestion_type': 'streaming'
            }
        )
        workflows.append(dp_workflow_id)
        
        # ML development workflow
        ml_workflow_id = await coordinator.create_workflow(
            template_name='ml_model_development',
            parameters={
                'model_name': 'Recommendation Engine',
                'model_type': 'collaborative_filtering'
            }
        )
        workflows.append(ml_workflow_id)
        
        # Execute all workflows in parallel
        tasks = [
            coordinator.execute_workflow(workflow_id)
            for workflow_id in workflows
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Report results
        for i, (workflow_id, result) in enumerate(zip(workflows, results)):
            if isinstance(result, Exception):
                logger.error(f"Workflow {workflow_id} failed: {result}")
            else:
                logger.info(f"Workflow {workflow_id} {'succeeded' if result else 'failed'}")
        
        return all(isinstance(r, bool) and r for r in results)
        
    finally:
        await coordinator.shutdown()


async def main():
    """Main function to run examples."""
    logger.info("Starting Multi-Agent Coordination System Examples")
    
    examples = [
        ("Software Development", run_software_development_example),
        ("ML Model Development", run_ml_development_example),
        ("Infrastructure Provisioning", run_infrastructure_example),
        ("Parallel Workflows", run_parallel_workflows_example)
    ]
    
    for example_name, example_func in examples:
        logger.info(f"\n{'='*50}")
        logger.info(f"Running Example: {example_name}")
        logger.info(f"{'='*50}")
        
        try:
            start_time = time.time()
            success = await example_func()
            duration = time.time() - start_time
            
            logger.info(f"Example '{example_name}' {'succeeded' if success else 'failed'} "
                       f"in {duration:.2f} seconds")
        
        except Exception as e:
            logger.error(f"Example '{example_name}' failed with error: {e}")
        
        # Wait between examples
        await asyncio.sleep(2)
    
    logger.info("\nAll examples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())

