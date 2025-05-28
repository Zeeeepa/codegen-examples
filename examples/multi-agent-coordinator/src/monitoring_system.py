#!/usr/bin/env python
"""
Monitoring System

This module implements comprehensive monitoring and observability for
multi-agent workflows with real-time metrics, alerting, and performance
analytics.
"""

import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Union, Tuple
from datetime import datetime, timedelta
import json
import threading
from collections import defaultdict, deque
import statistics
import psutil
import aiohttp


class MetricType(Enum):
    """Types of metrics collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"


class AlertSeverity(Enum):
    """Alert severity levels."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Metric:
    """Represents a single metric measurement."""
    name: str
    value: float
    metric_type: MetricType
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric to dictionary."""
        return {
            'name': self.name,
            'value': self.value,
            'type': self.metric_type.value,
            'tags': self.tags,
            'timestamp': self.timestamp.isoformat()
        }


@dataclass
class WorkflowMetrics:
    """Metrics for a workflow execution."""
    workflow_id: str
    status: str
    progress: float
    task_count: int
    running_tasks: int
    failed_tasks: int
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    resource_usage: Dict[str, float] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'workflow_id': self.workflow_id,
            'status': self.status,
            'progress': self.progress,
            'task_count': self.task_count,
            'running_tasks': self.running_tasks,
            'failed_tasks': self.failed_tasks,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration': self.duration,
            'resource_usage': self.resource_usage
        }


@dataclass
class Alert:
    """Represents an alert/notification."""
    id: str
    name: str
    severity: AlertSeverity
    message: str
    source: str
    tags: Dict[str, str] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    resolved_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'severity': self.severity.value,
            'message': self.message,
            'source': self.source,
            'tags': self.tags,
            'timestamp': self.timestamp.isoformat(),
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }


class AlertRule:
    """Defines conditions for triggering alerts."""
    
    def __init__(self, 
                 name: str,
                 condition: Callable[[Dict[str, Any]], bool],
                 severity: AlertSeverity,
                 message_template: str,
                 cooldown: int = 300):  # 5 minutes default cooldown
        self.name = name
        self.condition = condition
        self.severity = severity
        self.message_template = message_template
        self.cooldown = cooldown
        self.last_triggered: Optional[datetime] = None
    
    def should_trigger(self, metrics: Dict[str, Any]) -> bool:
        """Check if alert should be triggered."""
        # Check cooldown
        if (self.last_triggered and 
            datetime.now() - self.last_triggered < timedelta(seconds=self.cooldown)):
            return False
        
        return self.condition(metrics)
    
    def trigger(self, metrics: Dict[str, Any]) -> Alert:
        """Trigger the alert."""
        self.last_triggered = datetime.now()
        
        # Format message with metrics
        try:
            message = self.message_template.format(**metrics)
        except (KeyError, ValueError):
            message = self.message_template
        
        return Alert(
            id=str(uuid.uuid4()),
            name=self.name,
            severity=self.severity,
            message=message,
            source="monitoring_system",
            tags={'rule': self.name}
        )


class MetricsCollector:
    """Collects and aggregates metrics from various sources."""
    
    def __init__(self, collection_interval: int = 30):
        self.collection_interval = collection_interval
        self.metrics_buffer: deque = deque(maxlen=10000)
        self.aggregated_metrics: Dict[str, List[float]] = defaultdict(list)
        self.system_metrics: Dict[str, float] = {}
        
        # Background collection task
        self._collection_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start metrics collection."""
        self._collection_task = asyncio.create_task(self._collect_system_metrics())
        logging.info("MetricsCollector started")
    
    async def stop(self) -> None:
        """Stop metrics collection."""
        self._shutdown_event.set()
        if self._collection_task:
            self._collection_task.cancel()
        logging.info("MetricsCollector stopped")
    
    def record_metric(self, metric: Metric) -> None:
        """Record a metric measurement."""
        self.metrics_buffer.append(metric)
        
        # Update aggregated metrics
        key = f"{metric.name}_{metric.metric_type.value}"
        self.aggregated_metrics[key].append(metric.value)
        
        # Keep only recent values
        if len(self.aggregated_metrics[key]) > 1000:
            self.aggregated_metrics[key] = self.aggregated_metrics[key][-1000:]
    
    def get_metric_summary(self, metric_name: str, metric_type: MetricType) -> Dict[str, float]:
        """Get summary statistics for a metric."""
        key = f"{metric_name}_{metric_type.value}"
        values = self.aggregated_metrics.get(key, [])
        
        if not values:
            return {}
        
        return {
            'count': len(values),
            'sum': sum(values),
            'avg': statistics.mean(values),
            'min': min(values),
            'max': max(values),
            'median': statistics.median(values),
            'std_dev': statistics.stdev(values) if len(values) > 1 else 0.0
        }
    
    def get_recent_metrics(self, limit: int = 100) -> List[Metric]:
        """Get recent metrics."""
        return list(self.metrics_buffer)[-limit:]
    
    async def _collect_system_metrics(self) -> None:
        """Collect system-level metrics."""
        while not self._shutdown_event.is_set():
            try:
                # CPU usage
                cpu_percent = psutil.cpu_percent(interval=1)
                self.record_metric(Metric(
                    name="system.cpu.usage",
                    value=cpu_percent,
                    metric_type=MetricType.GAUGE,
                    tags={'host': 'localhost'}
                ))
                
                # Memory usage
                memory = psutil.virtual_memory()
                self.record_metric(Metric(
                    name="system.memory.usage",
                    value=memory.percent,
                    metric_type=MetricType.GAUGE,
                    tags={'host': 'localhost'}
                ))
                
                # Disk usage
                disk = psutil.disk_usage('/')
                disk_percent = (disk.used / disk.total) * 100
                self.record_metric(Metric(
                    name="system.disk.usage",
                    value=disk_percent,
                    metric_type=MetricType.GAUGE,
                    tags={'host': 'localhost', 'mount': '/'}
                ))
                
                # Network I/O
                network = psutil.net_io_counters()
                self.record_metric(Metric(
                    name="system.network.bytes_sent",
                    value=network.bytes_sent,
                    metric_type=MetricType.COUNTER,
                    tags={'host': 'localhost'}
                ))
                self.record_metric(Metric(
                    name="system.network.bytes_recv",
                    value=network.bytes_recv,
                    metric_type=MetricType.COUNTER,
                    tags={'host': 'localhost'}
                ))
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logging.error(f"Error collecting system metrics: {e}")
                await asyncio.sleep(60)


class AlertManager:
    """Manages alerts and notifications."""
    
    def __init__(self):
        self.alert_rules: List[AlertRule] = []
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.notification_handlers: List[Callable[[Alert], None]] = []
        
        # Background alert processing
        self._alert_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
    
    async def start(self) -> None:
        """Start alert manager."""
        self._alert_task = asyncio.create_task(self._process_alerts())
        logging.info("AlertManager started")
    
    async def stop(self) -> None:
        """Stop alert manager."""
        self._shutdown_event.set()
        if self._alert_task:
            self._alert_task.cancel()
        logging.info("AlertManager stopped")
    
    def add_rule(self, rule: AlertRule) -> None:
        """Add an alert rule."""
        self.alert_rules.append(rule)
        logging.info(f"Added alert rule: {rule.name}")
    
    def add_notification_handler(self, handler: Callable[[Alert], None]) -> None:
        """Add a notification handler."""
        self.notification_handlers.append(handler)
    
    async def check_alerts(self, metrics: Dict[str, Any]) -> List[Alert]:
        """Check all alert rules against current metrics."""
        triggered_alerts = []
        
        for rule in self.alert_rules:
            if rule.should_trigger(metrics):
                alert = rule.trigger(metrics)
                triggered_alerts.append(alert)
                
                # Store active alert
                self.active_alerts[alert.id] = alert
                self.alert_history.append(alert)
                
                # Send notifications
                for handler in self.notification_handlers:
                    try:
                        await self._call_handler(handler, alert)
                    except Exception as e:
                        logging.error(f"Error in notification handler: {e}")
                
                logging.warning(f"Alert triggered: {alert.name} - {alert.message}")
        
        return triggered_alerts
    
    async def _call_handler(self, handler: Callable, alert: Alert) -> None:
        """Call notification handler (async or sync)."""
        if asyncio.iscoroutinefunction(handler):
            await handler(alert)
        else:
            handler(alert)
    
    def resolve_alert(self, alert_id: str) -> bool:
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            del self.active_alerts[alert_id]
            logging.info(f"Resolved alert: {alert.name}")
            return True
        return False
    
    def get_active_alerts(self) -> List[Alert]:
        """Get all active alerts."""
        return list(self.active_alerts.values())
    
    def get_alert_history(self, limit: int = 100) -> List[Alert]:
        """Get alert history."""
        return list(self.alert_history)[-limit:]
    
    async def _process_alerts(self) -> None:
        """Background alert processing."""
        while not self._shutdown_event.is_set():
            try:
                # Auto-resolve old alerts (could be configurable)
                current_time = datetime.now()
                alerts_to_resolve = []
                
                for alert_id, alert in self.active_alerts.items():
                    # Auto-resolve alerts older than 1 hour
                    if current_time - alert.timestamp > timedelta(hours=1):
                        alerts_to_resolve.append(alert_id)
                
                for alert_id in alerts_to_resolve:
                    self.resolve_alert(alert_id)
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logging.error(f"Error in alert processing: {e}")
                await asyncio.sleep(120)


class PerformanceAnalyzer:
    """Analyzes performance trends and provides insights."""
    
    def __init__(self):
        self.performance_data: Dict[str, List[Tuple[datetime, float]]] = defaultdict(list)
        self.trend_analysis: Dict[str, Dict[str, Any]] = {}
        self.anomaly_detection: Dict[str, Any] = {}
    
    def record_performance_data(self, metric_name: str, value: float, timestamp: datetime = None) -> None:
        """Record performance data point."""
        if timestamp is None:
            timestamp = datetime.now()
        
        self.performance_data[metric_name].append((timestamp, value))
        
        # Keep only recent data (last 24 hours)
        cutoff_time = datetime.now() - timedelta(hours=24)
        self.performance_data[metric_name] = [
            (ts, val) for ts, val in self.performance_data[metric_name]
            if ts > cutoff_time
        ]
    
    def analyze_trends(self, metric_name: str) -> Dict[str, Any]:
        """Analyze trends for a metric."""
        data = self.performance_data.get(metric_name, [])
        if len(data) < 2:
            return {'trend': 'insufficient_data'}
        
        # Calculate trend
        values = [val for _, val in data]
        timestamps = [ts.timestamp() for ts, _ in data]
        
        # Simple linear regression for trend
        n = len(values)
        sum_x = sum(timestamps)
        sum_y = sum(values)
        sum_xy = sum(x * y for x, y in zip(timestamps, values))
        sum_x2 = sum(x * x for x in timestamps)
        
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x * sum_x)
        
        trend_direction = 'increasing' if slope > 0 else 'decreasing' if slope < 0 else 'stable'
        
        # Calculate statistics
        avg_value = statistics.mean(values)
        std_dev = statistics.stdev(values) if len(values) > 1 else 0.0
        
        analysis = {
            'trend': trend_direction,
            'slope': slope,
            'average': avg_value,
            'std_dev': std_dev,
            'min': min(values),
            'max': max(values),
            'data_points': len(values),
            'time_range': {
                'start': data[0][0].isoformat(),
                'end': data[-1][0].isoformat()
            }
        }
        
        self.trend_analysis[metric_name] = analysis
        return analysis
    
    def detect_anomalies(self, metric_name: str, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """Detect anomalies in metric data."""
        data = self.performance_data.get(metric_name, [])
        if len(data) < 10:  # Need sufficient data for anomaly detection
            return []
        
        values = [val for _, val in data]
        avg_value = statistics.mean(values)
        std_dev = statistics.stdev(values)
        
        anomalies = []
        for timestamp, value in data:
            # Z-score based anomaly detection
            z_score = abs(value - avg_value) / std_dev if std_dev > 0 else 0
            
            if z_score > threshold_std:
                anomalies.append({
                    'timestamp': timestamp.isoformat(),
                    'value': value,
                    'z_score': z_score,
                    'deviation': value - avg_value
                })
        
        return anomalies
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get overall performance summary."""
        summary = {}
        
        for metric_name in self.performance_data:
            trend_analysis = self.analyze_trends(metric_name)
            anomalies = self.detect_anomalies(metric_name)
            
            summary[metric_name] = {
                'trend_analysis': trend_analysis,
                'anomaly_count': len(anomalies),
                'recent_anomalies': anomalies[-5:] if anomalies else []
            }
        
        return summary


class MonitoringSystem:
    """
    Comprehensive monitoring system with features:
    - Real-time metrics collection and aggregation
    - Intelligent alerting with customizable rules
    - Performance trend analysis and anomaly detection
    - Workflow and agent health monitoring
    - Integration with external monitoring systems
    """
    
    def __init__(self, 
                 collection_interval: int = 30,
                 enable_system_metrics: bool = True,
                 enable_alerts: bool = True):
        """Initialize the monitoring system."""
        self.collection_interval = collection_interval
        self.enable_system_metrics = enable_system_metrics
        self.enable_alerts = enable_alerts
        
        # Components
        self.metrics_collector = MetricsCollector(collection_interval)
        self.alert_manager = AlertManager()
        self.performance_analyzer = PerformanceAnalyzer()
        
        # Workflow monitoring
        self.workflow_metrics: Dict[str, WorkflowMetrics] = {}
        self.agent_metrics: Dict[str, Dict[str, Any]] = defaultdict(dict)
        
        # External integrations
        self.webhook_urls: List[str] = []
        self.prometheus_enabled = False
        self.grafana_enabled = False
        
        # Background tasks
        self._background_tasks: List[asyncio.Task] = []
        self._shutdown_event = asyncio.Event()
        
        # Setup default alert rules
        self._setup_default_alerts()
        
        logging.info("MonitoringSystem initialized")
    
    def _setup_default_alerts(self) -> None:
        """Setup default alert rules."""
        # High CPU usage alert
        self.alert_manager.add_rule(AlertRule(
            name="high_cpu_usage",
            condition=lambda m: m.get('system.cpu.usage', 0) > 80,
            severity=AlertSeverity.WARNING,
            message_template="High CPU usage detected: {system.cpu.usage:.1f}%"
        ))
        
        # High memory usage alert
        self.alert_manager.add_rule(AlertRule(
            name="high_memory_usage",
            condition=lambda m: m.get('system.memory.usage', 0) > 85,
            severity=AlertSeverity.WARNING,
            message_template="High memory usage detected: {system.memory.usage:.1f}%"
        ))
        
        # Workflow failure alert
        self.alert_manager.add_rule(AlertRule(
            name="workflow_failure",
            condition=lambda m: m.get('workflow.failed_tasks', 0) > 0,
            severity=AlertSeverity.ERROR,
            message_template="Workflow {workflow_id} has {workflow.failed_tasks} failed tasks"
        ))
        
        # Agent offline alert
        self.alert_manager.add_rule(AlertRule(
            name="agent_offline",
            condition=lambda m: m.get('agent.status') == 'offline',
            severity=AlertSeverity.ERROR,
            message_template="Agent {agent_id} is offline"
        ))
    
    async def start(self) -> None:
        """Start the monitoring system."""
        # Start components
        await self.metrics_collector.start()
        
        if self.enable_alerts:
            await self.alert_manager.start()
        
        # Start background services
        monitor_task = asyncio.create_task(self._monitoring_loop())
        self._background_tasks.append(monitor_task)
        
        analysis_task = asyncio.create_task(self._analysis_loop())
        self._background_tasks.append(analysis_task)
        
        logging.info("MonitoringSystem started")
    
    async def stop(self) -> None:
        """Stop the monitoring system."""
        logging.info("Stopping MonitoringSystem...")
        
        # Signal shutdown
        self._shutdown_event.set()
        
        # Stop components
        await self.metrics_collector.stop()
        
        if self.enable_alerts:
            await self.alert_manager.stop()
        
        # Cancel background tasks
        for task in self._background_tasks:
            task.cancel()
        
        # Wait for tasks to complete
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        
        logging.info("MonitoringSystem stopped")
    
    async def record_workflow_metrics(self, metrics: WorkflowMetrics) -> None:
        """Record workflow metrics."""
        self.workflow_metrics[metrics.workflow_id] = metrics
        
        # Record individual metrics
        self.metrics_collector.record_metric(Metric(
            name="workflow.progress",
            value=metrics.progress,
            metric_type=MetricType.GAUGE,
            tags={'workflow_id': metrics.workflow_id, 'status': metrics.status}
        ))
        
        self.metrics_collector.record_metric(Metric(
            name="workflow.running_tasks",
            value=metrics.running_tasks,
            metric_type=MetricType.GAUGE,
            tags={'workflow_id': metrics.workflow_id}
        ))
        
        self.metrics_collector.record_metric(Metric(
            name="workflow.failed_tasks",
            value=metrics.failed_tasks,
            metric_type=MetricType.GAUGE,
            tags={'workflow_id': metrics.workflow_id}
        ))
        
        # Record performance data
        if metrics.duration:
            self.performance_analyzer.record_performance_data(
                f"workflow.{metrics.workflow_id}.duration",
                metrics.duration
            )
    
    async def record_agent_metrics(self, agent_id: str, metrics: Dict[str, Any]) -> None:
        """Record agent metrics."""
        self.agent_metrics[agent_id].update(metrics)
        
        # Record individual metrics
        for metric_name, value in metrics.items():
            if isinstance(value, (int, float)):
                self.metrics_collector.record_metric(Metric(
                    name=f"agent.{metric_name}",
                    value=value,
                    metric_type=MetricType.GAUGE,
                    tags={'agent_id': agent_id}
                ))
    
    def add_webhook_url(self, url: str) -> None:
        """Add webhook URL for notifications."""
        self.webhook_urls.append(url)
        
        # Add webhook notification handler
        async def webhook_handler(alert: Alert):
            await self._send_webhook_notification(url, alert)
        
        self.alert_manager.add_notification_handler(webhook_handler)
    
    async def _send_webhook_notification(self, url: str, alert: Alert) -> None:
        """Send alert notification via webhook."""
        try:
            async with aiohttp.ClientSession() as session:
                payload = {
                    'alert': alert.to_dict(),
                    'timestamp': datetime.now().isoformat(),
                    'source': 'multi_agent_coordinator'
                }
                
                async with session.post(url, json=payload, timeout=10) as response:
                    if response.status == 200:
                        logging.info(f"Webhook notification sent to {url}")
                    else:
                        logging.warning(f"Webhook notification failed: {response.status}")
        
        except Exception as e:
            logging.error(f"Error sending webhook notification: {e}")
    
    async def _monitoring_loop(self) -> None:
        """Main monitoring loop."""
        while not self._shutdown_event.is_set():
            try:
                # Collect current metrics
                current_metrics = {}
                
                # System metrics
                recent_metrics = self.metrics_collector.get_recent_metrics(10)
                for metric in recent_metrics:
                    current_metrics[metric.name] = metric.value
                
                # Workflow metrics
                for workflow_id, wf_metrics in self.workflow_metrics.items():
                    current_metrics[f'workflow.{workflow_id}.progress'] = wf_metrics.progress
                    current_metrics[f'workflow.{workflow_id}.failed_tasks'] = wf_metrics.failed_tasks
                    current_metrics['workflow_id'] = workflow_id
                
                # Agent metrics
                for agent_id, agent_data in self.agent_metrics.items():
                    for key, value in agent_data.items():
                        if isinstance(value, (int, float)):
                            current_metrics[f'agent.{agent_id}.{key}'] = value
                    current_metrics['agent_id'] = agent_id
                
                # Check alerts
                if self.enable_alerts:
                    await self.alert_manager.check_alerts(current_metrics)
                
                await asyncio.sleep(self.collection_interval)
                
            except Exception as e:
                logging.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(60)
    
    async def _analysis_loop(self) -> None:
        """Performance analysis loop."""
        while not self._shutdown_event.is_set():
            try:
                # Analyze performance trends
                for workflow_id in self.workflow_metrics:
                    duration_metric = f"workflow.{workflow_id}.duration"
                    if duration_metric in self.performance_analyzer.performance_data:
                        trend_analysis = self.performance_analyzer.analyze_trends(duration_metric)
                        
                        # Log significant trends
                        if trend_analysis.get('trend') == 'increasing':
                            logging.warning(f"Workflow {workflow_id} duration is increasing")
                
                await asyncio.sleep(300)  # Analyze every 5 minutes
                
            except Exception as e:
                logging.error(f"Error in analysis loop: {e}")
                await asyncio.sleep(600)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status."""
        # Get recent system metrics
        recent_metrics = self.metrics_collector.get_recent_metrics(5)
        system_metrics = {}
        
        for metric in recent_metrics:
            if metric.name.startswith('system.'):
                system_metrics[metric.name] = metric.value
        
        # Get workflow status
        workflow_status = {}
        for workflow_id, metrics in self.workflow_metrics.items():
            workflow_status[workflow_id] = {
                'status': metrics.status,
                'progress': metrics.progress,
                'running_tasks': metrics.running_tasks,
                'failed_tasks': metrics.failed_tasks
            }
        
        # Get agent status
        agent_status = {}
        for agent_id, metrics in self.agent_metrics.items():
            agent_status[agent_id] = metrics
        
        # Get active alerts
        active_alerts = self.alert_manager.get_active_alerts() if self.enable_alerts else []
        
        return {
            'timestamp': datetime.now().isoformat(),
            'system_metrics': system_metrics,
            'workflow_status': workflow_status,
            'agent_status': agent_status,
            'active_alerts': [alert.to_dict() for alert in active_alerts],
            'performance_summary': self.performance_analyzer.get_performance_summary()
        }
    
    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get metrics summary."""
        summary = {}
        
        # Get summaries for key metrics
        key_metrics = [
            ('system.cpu.usage', MetricType.GAUGE),
            ('system.memory.usage', MetricType.GAUGE),
            ('workflow.progress', MetricType.GAUGE),
            ('agent.tasks_completed', MetricType.COUNTER)
        ]
        
        for metric_name, metric_type in key_metrics:
            summary[metric_name] = self.metrics_collector.get_metric_summary(metric_name, metric_type)
        
        return summary
    
    def export_prometheus_metrics(self) -> str:
        """Export metrics in Prometheus format."""
        # This would generate Prometheus-compatible metrics
        # For now, return a simple format
        lines = []
        
        recent_metrics = self.metrics_collector.get_recent_metrics(100)
        for metric in recent_metrics:
            # Convert to Prometheus format
            metric_name = metric.name.replace('.', '_')
            tags = ','.join(f'{k}="{v}"' for k, v in metric.tags.items())
            
            if tags:
                line = f'{metric_name}{{{tags}}} {metric.value}'
            else:
                line = f'{metric_name} {metric.value}'
            
            lines.append(line)
        
        return '\n'.join(lines)
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform system health check."""
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        # Check metrics collector
        try:
            recent_metrics = self.metrics_collector.get_recent_metrics(1)
            health_status['components']['metrics_collector'] = {
                'status': 'healthy',
                'recent_metrics_count': len(recent_metrics)
            }
        except Exception as e:
            health_status['components']['metrics_collector'] = {
                'status': 'unhealthy',
                'error': str(e)
            }
            health_status['status'] = 'degraded'
        
        # Check alert manager
        if self.enable_alerts:
            try:
                active_alerts = self.alert_manager.get_active_alerts()
                health_status['components']['alert_manager'] = {
                    'status': 'healthy',
                    'active_alerts_count': len(active_alerts)
                }
            except Exception as e:
                health_status['components']['alert_manager'] = {
                    'status': 'unhealthy',
                    'error': str(e)
                }
                health_status['status'] = 'degraded'
        
        return health_status

