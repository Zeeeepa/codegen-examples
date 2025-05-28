"""
Automated Rollback System with Intelligent Decision Making

This module implements sophisticated rollback mechanisms with automated triggers,
health monitoring, and intelligent recovery strategies for failed deployments.
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
from datetime import datetime, timedelta
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class RollbackTrigger(Enum):
    MANUAL = "manual"
    HEALTH_CHECK_FAILURE = "health_check_failure"
    ERROR_RATE_THRESHOLD = "error_rate_threshold"
    RESPONSE_TIME_THRESHOLD = "response_time_threshold"
    RESOURCE_EXHAUSTION = "resource_exhaustion"
    SECURITY_INCIDENT = "security_incident"
    COMPLIANCE_VIOLATION = "compliance_violation"
    BUSINESS_METRIC_DEGRADATION = "business_metric_degradation"


class RollbackStrategy(Enum):
    IMMEDIATE = "immediate"
    GRADUAL = "gradual"
    CANARY_ROLLBACK = "canary_rollback"
    BLUE_GREEN_SWITCH = "blue_green_switch"
    FEATURE_FLAG_DISABLE = "feature_flag_disable"
    TRAFFIC_DRAIN = "traffic_drain"


class RollbackStatus(Enum):
    PENDING = "pending"
    INITIATED = "initiated"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    PARTIAL = "partial"


@dataclass
class HealthMetric:
    """Health metric for monitoring"""
    name: str
    value: float
    threshold: float
    unit: str
    timestamp: datetime
    critical: bool = False


@dataclass
class RollbackCondition:
    """Condition that can trigger a rollback"""
    name: str
    metric_name: str
    operator: str  # >, <, >=, <=, ==, !=
    threshold: float
    duration_seconds: int = 60
    critical: bool = False
    enabled: bool = True


@dataclass
class RollbackConfig:
    """Configuration for rollback system"""
    application_name: str
    environment: str
    conditions: List[RollbackCondition]
    strategy: RollbackStrategy
    auto_rollback_enabled: bool = True
    confirmation_required: bool = False
    max_rollback_attempts: int = 3
    rollback_timeout_minutes: int = 15
    notification_channels: List[str] = None
    preserve_data: bool = True


@dataclass
class RollbackEvent:
    """Rollback event record"""
    id: str
    application_name: str
    environment: str
    trigger: RollbackTrigger
    strategy: RollbackStrategy
    status: RollbackStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    triggered_by: str = "system"
    reason: str = ""
    metrics_at_trigger: List[HealthMetric] = None
    rollback_version: Optional[str] = None
    success: bool = False
    error_message: Optional[str] = None


class HealthMonitor:
    """Monitors application health and triggers rollbacks"""
    
    def __init__(self, rollback_config: RollbackConfig):
        self.config = rollback_config
        self.metrics_history = []
        self.active_alerts = {}
        self.monitoring_active = False
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        self.monitoring_active = True
        logger.info(f"Starting health monitoring for {self.config.application_name}")
        
        while self.monitoring_active:
            try:
                # Collect current metrics
                current_metrics = await self._collect_metrics()
                self.metrics_history.append(current_metrics)
                
                # Keep only recent metrics (last hour)
                cutoff_time = datetime.now() - timedelta(hours=1)
                self.metrics_history = [
                    metrics for metrics in self.metrics_history
                    if any(metric.timestamp > cutoff_time for metric in metrics)
                ]
                
                # Check rollback conditions
                triggered_conditions = await self._check_rollback_conditions(current_metrics)
                
                if triggered_conditions and self.config.auto_rollback_enabled:
                    await self._trigger_rollback(triggered_conditions, current_metrics)
                
                # Wait before next check
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Error in health monitoring: {str(e)}")
                await asyncio.sleep(60)  # Wait longer on error
    
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        logger.info(f"Stopped health monitoring for {self.config.application_name}")
    
    async def _collect_metrics(self) -> List[HealthMetric]:
        """Collect current health metrics"""
        # This would integrate with actual monitoring systems like Prometheus, DataDog, etc.
        await asyncio.sleep(1)  # Simulate metric collection time
        
        # Mock metrics - replace with actual implementation
        current_time = datetime.now()
        return [
            HealthMetric(
                name="error_rate",
                value=2.5,  # 2.5% error rate
                threshold=5.0,
                unit="percentage",
                timestamp=current_time
            ),
            HealthMetric(
                name="response_time_p95",
                value=450.0,  # 450ms
                threshold=1000.0,
                unit="milliseconds",
                timestamp=current_time
            ),
            HealthMetric(
                name="cpu_utilization",
                value=85.0,  # 85% CPU
                threshold=90.0,
                unit="percentage",
                timestamp=current_time,
                critical=True
            ),
            HealthMetric(
                name="memory_utilization",
                value=78.0,  # 78% memory
                threshold=85.0,
                unit="percentage",
                timestamp=current_time
            ),
            HealthMetric(
                name="active_connections",
                value=1250.0,
                threshold=2000.0,
                unit="count",
                timestamp=current_time
            )
        ]
    
    async def _check_rollback_conditions(self, current_metrics: List[HealthMetric]) -> List[RollbackCondition]:
        """Check if any rollback conditions are met"""
        triggered_conditions = []
        
        for condition in self.config.conditions:
            if not condition.enabled:
                continue
            
            # Find matching metric
            metric = next((m for m in current_metrics if m.name == condition.metric_name), None)
            if not metric:
                continue
            
            # Check condition
            if self._evaluate_condition(metric.value, condition.operator, condition.threshold):
                # Check if condition has been met for required duration
                if await self._condition_met_for_duration(condition, current_metrics):
                    triggered_conditions.append(condition)
                    logger.warning(f"Rollback condition triggered: {condition.name}")
        
        return triggered_conditions
    
    def _evaluate_condition(self, value: float, operator: str, threshold: float) -> bool:
        """Evaluate a rollback condition"""
        if operator == ">":
            return value > threshold
        elif operator == "<":
            return value < threshold
        elif operator == ">=":
            return value >= threshold
        elif operator == "<=":
            return value <= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        else:
            logger.error(f"Unknown operator: {operator}")
            return False
    
    async def _condition_met_for_duration(self, condition: RollbackCondition, current_metrics: List[HealthMetric]) -> bool:
        """Check if condition has been met for the required duration"""
        # Check historical metrics to see if condition has been consistently met
        cutoff_time = datetime.now() - timedelta(seconds=condition.duration_seconds)
        
        # For simplicity, assume condition is met if current metrics trigger it
        # In a real implementation, you would check historical data
        return True
    
    async def _trigger_rollback(self, conditions: List[RollbackCondition], metrics: List[HealthMetric]):
        """Trigger automatic rollback"""
        logger.critical(f"Triggering automatic rollback for {self.config.application_name}")
        
        # Determine trigger type based on conditions
        trigger = RollbackTrigger.HEALTH_CHECK_FAILURE
        if any(c.metric_name == "error_rate" for c in conditions):
            trigger = RollbackTrigger.ERROR_RATE_THRESHOLD
        elif any(c.metric_name == "response_time_p95" for c in conditions):
            trigger = RollbackTrigger.RESPONSE_TIME_THRESHOLD
        elif any(c.critical for c in conditions):
            trigger = RollbackTrigger.RESOURCE_EXHAUSTION
        
        # Create rollback event
        rollback_event = RollbackEvent(
            id=f"rollback-{self.config.application_name}-{int(time.time())}",
            application_name=self.config.application_name,
            environment=self.config.environment,
            trigger=trigger,
            strategy=self.config.strategy,
            status=RollbackStatus.INITIATED,
            start_time=datetime.now(),
            triggered_by="health_monitor",
            reason=f"Conditions triggered: {[c.name for c in conditions]}",
            metrics_at_trigger=metrics
        )
        
        # Execute rollback
        rollback_executor = RollbackExecutor(self.config)
        await rollback_executor.execute_rollback(rollback_event)


class RollbackExecutor:
    """Executes rollback operations using different strategies"""
    
    def __init__(self, config: RollbackConfig):
        self.config = config
        self.rollback_history = []
    
    async def execute_rollback(self, rollback_event: RollbackEvent) -> RollbackEvent:
        """Execute rollback using the configured strategy"""
        logger.info(f"Executing rollback {rollback_event.id} using {rollback_event.strategy.value} strategy")
        
        try:
            rollback_event.status = RollbackStatus.IN_PROGRESS
            
            # Execute strategy-specific rollback
            if rollback_event.strategy == RollbackStrategy.IMMEDIATE:
                await self._execute_immediate_rollback(rollback_event)
            elif rollback_event.strategy == RollbackStrategy.GRADUAL:
                await self._execute_gradual_rollback(rollback_event)
            elif rollback_event.strategy == RollbackStrategy.CANARY_ROLLBACK:
                await self._execute_canary_rollback(rollback_event)
            elif rollback_event.strategy == RollbackStrategy.BLUE_GREEN_SWITCH:
                await self._execute_blue_green_rollback(rollback_event)
            elif rollback_event.strategy == RollbackStrategy.FEATURE_FLAG_DISABLE:
                await self._execute_feature_flag_rollback(rollback_event)
            elif rollback_event.strategy == RollbackStrategy.TRAFFIC_DRAIN:
                await self._execute_traffic_drain_rollback(rollback_event)
            else:
                raise ValueError(f"Unknown rollback strategy: {rollback_event.strategy}")
            
            # Verify rollback success
            if await self._verify_rollback_success(rollback_event):
                rollback_event.status = RollbackStatus.COMPLETED
                rollback_event.success = True
                logger.info(f"Rollback {rollback_event.id} completed successfully")
            else:
                rollback_event.status = RollbackStatus.PARTIAL
                logger.warning(f"Rollback {rollback_event.id} partially successful")
            
        except Exception as e:
            logger.error(f"Rollback {rollback_event.id} failed: {str(e)}")
            rollback_event.status = RollbackStatus.FAILED
            rollback_event.error_message = str(e)
        
        finally:
            rollback_event.end_time = datetime.now()
            self.rollback_history.append(rollback_event)
            
            # Send notifications
            await self._send_rollback_notifications(rollback_event)
        
        return rollback_event
    
    async def _execute_immediate_rollback(self, rollback_event: RollbackEvent):
        """Execute immediate rollback to previous version"""
        logger.info("Executing immediate rollback")
        
        # Stop current deployment
        await self._stop_current_deployment()
        
        # Deploy previous version
        previous_version = await self._get_previous_stable_version()
        rollback_event.rollback_version = previous_version
        
        await self._deploy_version(previous_version)
        
        # Update load balancer
        await self._update_load_balancer_to_previous()
        
        logger.info("Immediate rollback completed")
    
    async def _execute_gradual_rollback(self, rollback_event: RollbackEvent):
        """Execute gradual rollback with traffic shifting"""
        logger.info("Executing gradual rollback")
        
        # Get previous version
        previous_version = await self._get_previous_stable_version()
        rollback_event.rollback_version = previous_version
        
        # Deploy previous version alongside current
        await self._deploy_version(previous_version, parallel=True)
        
        # Gradually shift traffic
        traffic_percentages = [10, 25, 50, 75, 100]
        for percentage in traffic_percentages:
            logger.info(f"Shifting {percentage}% traffic to previous version")
            await self._shift_traffic_to_previous(percentage)
            
            # Monitor for a short period
            await asyncio.sleep(30)
            
            # Check if rollback is working
            if not await self._check_rollback_health():
                raise Exception("Rollback health check failed")
        
        # Remove current version
        await self._remove_current_version()
        
        logger.info("Gradual rollback completed")
    
    async def _execute_canary_rollback(self, rollback_event: RollbackEvent):
        """Execute canary-style rollback"""
        logger.info("Executing canary rollback")
        
        # Deploy previous version as canary
        previous_version = await self._get_previous_stable_version()
        rollback_event.rollback_version = previous_version
        
        await self._deploy_canary_version(previous_version)
        
        # Test canary with small traffic
        await self._route_canary_traffic(5)  # 5% traffic
        
        # Monitor canary health
        if await self._monitor_canary_health(duration_seconds=120):
            # Promote canary to full deployment
            await self._promote_canary_to_full()
        else:
            raise Exception("Canary rollback health check failed")
        
        logger.info("Canary rollback completed")
    
    async def _execute_blue_green_rollback(self, rollback_event: RollbackEvent):
        """Execute blue-green rollback"""
        logger.info("Executing blue-green rollback")
        
        # Switch traffic back to blue environment (previous version)
        await self._switch_traffic_to_blue()
        
        # Verify blue environment health
        if not await self._verify_blue_environment_health():
            raise Exception("Blue environment health check failed")
        
        # Mark green environment for cleanup
        await self._mark_green_for_cleanup()
        
        logger.info("Blue-green rollback completed")
    
    async def _execute_feature_flag_rollback(self, rollback_event: RollbackEvent):
        """Execute rollback by disabling feature flags"""
        logger.info("Executing feature flag rollback")
        
        # Get problematic feature flags
        problematic_flags = await self._identify_problematic_features()
        
        # Disable feature flags gradually
        for flag in problematic_flags:
            logger.info(f"Disabling feature flag: {flag}")
            await self._disable_feature_flag(flag)
            
            # Wait and monitor
            await asyncio.sleep(10)
            
            # Check if issue is resolved
            if await self._check_rollback_health():
                logger.info(f"Issue resolved by disabling {flag}")
                break
        
        logger.info("Feature flag rollback completed")
    
    async def _execute_traffic_drain_rollback(self, rollback_event: RollbackEvent):
        """Execute rollback by draining traffic"""
        logger.info("Executing traffic drain rollback")
        
        # Gradually reduce traffic to problematic instances
        traffic_percentages = [90, 75, 50, 25, 0]
        
        for percentage in traffic_percentages:
            logger.info(f"Reducing traffic to {percentage}%")
            await self._set_traffic_percentage(percentage)
            
            # Wait and monitor
            await asyncio.sleep(30)
            
            # Check if issue is resolved
            if await self._check_rollback_health():
                logger.info(f"Issue resolved at {percentage}% traffic")
                break
        
        # Deploy previous version to drained instances
        previous_version = await self._get_previous_stable_version()
        rollback_event.rollback_version = previous_version
        
        await self._deploy_to_drained_instances(previous_version)
        
        # Gradually restore traffic
        for percentage in reversed(traffic_percentages):
            if percentage > 0:
                logger.info(f"Restoring traffic to {percentage}%")
                await self._set_traffic_percentage(percentage)
                await asyncio.sleep(30)
        
        logger.info("Traffic drain rollback completed")
    
    async def _verify_rollback_success(self, rollback_event: RollbackEvent) -> bool:
        """Verify that rollback was successful"""
        logger.info("Verifying rollback success")
        
        # Wait for system to stabilize
        await asyncio.sleep(60)
        
        # Check health metrics
        health_monitor = HealthMonitor(self.config)
        current_metrics = await health_monitor._collect_metrics()
        
        # Verify all conditions are now within acceptable ranges
        for condition in self.config.conditions:
            metric = next((m for m in current_metrics if m.name == condition.metric_name), None)
            if metric:
                if health_monitor._evaluate_condition(metric.value, condition.operator, condition.threshold):
                    logger.warning(f"Condition {condition.name} still triggered after rollback")
                    return False
        
        logger.info("Rollback verification successful")
        return True
    
    async def _send_rollback_notifications(self, rollback_event: RollbackEvent):
        """Send notifications about rollback status"""
        if not self.config.notification_channels:
            return
        
        message = f"""
        Rollback Event: {rollback_event.id}
        Application: {rollback_event.application_name}
        Environment: {rollback_event.environment}
        Status: {rollback_event.status.value}
        Trigger: {rollback_event.trigger.value}
        Strategy: {rollback_event.strategy.value}
        Success: {rollback_event.success}
        Duration: {(rollback_event.end_time - rollback_event.start_time).total_seconds() if rollback_event.end_time else 'N/A'} seconds
        """
        
        for channel in self.config.notification_channels:
            await self._send_notification(channel, message)
    
    # Helper methods (these would integrate with actual infrastructure)
    
    async def _stop_current_deployment(self):
        """Stop current deployment"""
        await asyncio.sleep(1)
    
    async def _get_previous_stable_version(self) -> str:
        """Get previous stable version"""
        await asyncio.sleep(0.5)
        return "v1.2.2"  # Mock previous version
    
    async def _deploy_version(self, version: str, parallel: bool = False):
        """Deploy specific version"""
        await asyncio.sleep(2)
    
    async def _update_load_balancer_to_previous(self):
        """Update load balancer to route to previous version"""
        await asyncio.sleep(1)
    
    async def _shift_traffic_to_previous(self, percentage: int):
        """Shift traffic percentage to previous version"""
        await asyncio.sleep(1)
    
    async def _check_rollback_health(self) -> bool:
        """Check if rollback improved health"""
        await asyncio.sleep(1)
        return True  # Mock health check
    
    async def _remove_current_version(self):
        """Remove current problematic version"""
        await asyncio.sleep(1)
    
    async def _deploy_canary_version(self, version: str):
        """Deploy version as canary"""
        await asyncio.sleep(2)
    
    async def _route_canary_traffic(self, percentage: int):
        """Route traffic percentage to canary"""
        await asyncio.sleep(1)
    
    async def _monitor_canary_health(self, duration_seconds: int) -> bool:
        """Monitor canary health for specified duration"""
        await asyncio.sleep(duration_seconds / 10)  # Simulate monitoring
        return True
    
    async def _promote_canary_to_full(self):
        """Promote canary to full deployment"""
        await asyncio.sleep(1)
    
    async def _switch_traffic_to_blue(self):
        """Switch traffic to blue environment"""
        await asyncio.sleep(1)
    
    async def _verify_blue_environment_health(self) -> bool:
        """Verify blue environment health"""
        await asyncio.sleep(1)
        return True
    
    async def _mark_green_for_cleanup(self):
        """Mark green environment for cleanup"""
        await asyncio.sleep(0.5)
    
    async def _identify_problematic_features(self) -> List[str]:
        """Identify problematic feature flags"""
        await asyncio.sleep(1)
        return ["new_ui_feature", "experimental_algorithm"]
    
    async def _disable_feature_flag(self, flag_name: str):
        """Disable specific feature flag"""
        await asyncio.sleep(0.5)
    
    async def _set_traffic_percentage(self, percentage: int):
        """Set traffic percentage to current version"""
        await asyncio.sleep(1)
    
    async def _deploy_to_drained_instances(self, version: str):
        """Deploy version to drained instances"""
        await asyncio.sleep(2)
    
    async def _send_notification(self, channel: str, message: str):
        """Send notification to specified channel"""
        logger.info(f"Sending notification to {channel}: {message}")


class RollbackOrchestrator:
    """Orchestrates rollback operations and manages rollback policies"""
    
    def __init__(self):
        self.active_monitors = {}
        self.rollback_configs = {}
        self.rollback_history = []
    
    def register_application(self, config: RollbackConfig):
        """Register application for rollback monitoring"""
        self.rollback_configs[config.application_name] = config
        
        # Start health monitoring
        monitor = HealthMonitor(config)
        self.active_monitors[config.application_name] = monitor
        
        # Start monitoring in background
        asyncio.create_task(monitor.start_monitoring())
        
        logger.info(f"Registered application {config.application_name} for rollback monitoring")
    
    def unregister_application(self, application_name: str):
        """Unregister application from rollback monitoring"""
        if application_name in self.active_monitors:
            self.active_monitors[application_name].stop_monitoring()
            del self.active_monitors[application_name]
        
        if application_name in self.rollback_configs:
            del self.rollback_configs[application_name]
        
        logger.info(f"Unregistered application {application_name} from rollback monitoring")
    
    async def manual_rollback(self, application_name: str, reason: str = "Manual rollback") -> RollbackEvent:
        """Trigger manual rollback"""
        if application_name not in self.rollback_configs:
            raise ValueError(f"Application {application_name} not registered")
        
        config = self.rollback_configs[application_name]
        
        # Create rollback event
        rollback_event = RollbackEvent(
            id=f"manual-rollback-{application_name}-{int(time.time())}",
            application_name=application_name,
            environment=config.environment,
            trigger=RollbackTrigger.MANUAL,
            strategy=config.strategy,
            status=RollbackStatus.INITIATED,
            start_time=datetime.now(),
            triggered_by="manual",
            reason=reason
        )
        
        # Execute rollback
        executor = RollbackExecutor(config)
        result = await executor.execute_rollback(rollback_event)
        
        self.rollback_history.append(result)
        return result
    
    def get_rollback_status(self, application_name: str) -> Dict[str, Any]:
        """Get rollback status for application"""
        if application_name not in self.rollback_configs:
            return {"error": "Application not registered"}
        
        config = self.rollback_configs[application_name]
        monitor = self.active_monitors.get(application_name)
        
        # Get recent rollback events
        recent_rollbacks = [
            event for event in self.rollback_history
            if event.application_name == application_name and
            event.start_time > datetime.now() - timedelta(days=7)
        ]
        
        return {
            "application_name": application_name,
            "environment": config.environment,
            "auto_rollback_enabled": config.auto_rollback_enabled,
            "monitoring_active": monitor.monitoring_active if monitor else False,
            "recent_rollbacks": len(recent_rollbacks),
            "last_rollback": recent_rollbacks[-1].start_time.isoformat() if recent_rollbacks else None,
            "rollback_conditions": len(config.conditions)
        }
    
    def generate_rollback_report(self, application_name: str, days: int = 30) -> Dict[str, Any]:
        """Generate comprehensive rollback report"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        app_rollbacks = [
            event for event in self.rollback_history
            if event.application_name == application_name and event.start_time > cutoff_date
        ]
        
        if not app_rollbacks:
            return {"message": "No rollbacks found for the specified period"}
        
        # Calculate statistics
        total_rollbacks = len(app_rollbacks)
        successful_rollbacks = len([r for r in app_rollbacks if r.success])
        failed_rollbacks = total_rollbacks - successful_rollbacks
        
        # Group by trigger
        trigger_counts = {}
        for rollback in app_rollbacks:
            trigger = rollback.trigger.value
            trigger_counts[trigger] = trigger_counts.get(trigger, 0) + 1
        
        # Calculate average rollback time
        completed_rollbacks = [r for r in app_rollbacks if r.end_time]
        avg_rollback_time = 0
        if completed_rollbacks:
            total_time = sum((r.end_time - r.start_time).total_seconds() for r in completed_rollbacks)
            avg_rollback_time = total_time / len(completed_rollbacks)
        
        return {
            "application_name": application_name,
            "report_period_days": days,
            "total_rollbacks": total_rollbacks,
            "successful_rollbacks": successful_rollbacks,
            "failed_rollbacks": failed_rollbacks,
            "success_rate": (successful_rollbacks / total_rollbacks * 100) if total_rollbacks > 0 else 0,
            "trigger_breakdown": trigger_counts,
            "average_rollback_time_seconds": avg_rollback_time,
            "rollback_events": [asdict(event) for event in app_rollbacks]
        }


# Example usage and configuration
def create_sample_rollback_config() -> RollbackConfig:
    """Create sample rollback configuration"""
    return RollbackConfig(
        application_name="enterprise-app",
        environment="production",
        conditions=[
            RollbackCondition(
                name="High Error Rate",
                metric_name="error_rate",
                operator=">",
                threshold=5.0,
                duration_seconds=120,
                critical=True
            ),
            RollbackCondition(
                name="High Response Time",
                metric_name="response_time_p95",
                operator=">",
                threshold=1000.0,
                duration_seconds=180,
                critical=False
            ),
            RollbackCondition(
                name="High CPU Usage",
                metric_name="cpu_utilization",
                operator=">",
                threshold=90.0,
                duration_seconds=300,
                critical=True
            )
        ],
        strategy=RollbackStrategy.GRADUAL,
        auto_rollback_enabled=True,
        confirmation_required=False,
        max_rollback_attempts=3,
        rollback_timeout_minutes=15,
        notification_channels=["slack", "email", "pagerduty"],
        preserve_data=True
    )


async def main():
    """Example usage of the rollback system"""
    # Create rollback configuration
    config = create_sample_rollback_config()
    
    # Create orchestrator
    orchestrator = RollbackOrchestrator()
    
    # Register application
    orchestrator.register_application(config)
    
    # Simulate running for a while
    await asyncio.sleep(10)
    
    # Trigger manual rollback
    rollback_result = await orchestrator.manual_rollback(
        "enterprise-app",
        "Testing manual rollback functionality"
    )
    
    print(f"Manual rollback completed: {rollback_result.success}")
    
    # Generate report
    report = orchestrator.generate_rollback_report("enterprise-app", days=1)
    print(f"Rollback report: {json.dumps(report, indent=2, default=str)}")
    
    # Cleanup
    orchestrator.unregister_application("enterprise-app")


if __name__ == "__main__":
    asyncio.run(main())

