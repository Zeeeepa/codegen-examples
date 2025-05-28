"""
Comprehensive Monitoring and Observability Integration

This module provides advanced monitoring integration with multiple observability platforms,
intelligent alerting, and comprehensive metrics collection for CI/CD pipelines.
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


class MonitoringPlatform(Enum):
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    DATADOG = "datadog"
    NEW_RELIC = "new_relic"
    SPLUNK = "splunk"
    ELASTIC = "elastic"
    JAEGER = "jaeger"
    ZIPKIN = "zipkin"


class MetricType(Enum):
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    SUMMARY = "summary"
    TIMER = "timer"


class AlertSeverity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class MetricDefinition:
    """Definition of a metric to be collected"""
    name: str
    type: MetricType
    description: str
    labels: List[str] = None
    unit: str = ""
    aggregation_window: str = "1m"
    retention_period: str = "30d"


@dataclass
class AlertRule:
    """Alert rule configuration"""
    name: str
    metric_name: str
    condition: str  # e.g., "> 0.05", "< 0.95"
    threshold: float
    duration: str = "5m"
    severity: AlertSeverity = AlertSeverity.WARNING
    description: str = ""
    runbook_url: Optional[str] = None
    notification_channels: List[str] = None


@dataclass
class Dashboard:
    """Dashboard configuration"""
    name: str
    description: str
    panels: List[Dict[str, Any]]
    tags: List[str] = None
    refresh_interval: str = "30s"
    time_range: str = "1h"


@dataclass
class MonitoringConfig:
    """Complete monitoring configuration"""
    application_name: str
    environment: str
    platforms: List[MonitoringPlatform]
    metrics: List[MetricDefinition]
    alerts: List[AlertRule]
    dashboards: List[Dashboard]
    custom_exporters: List[str] = None
    sampling_rate: float = 1.0
    retention_policy: str = "30d"


class MetricCollector(ABC):
    """Abstract base class for metric collectors"""
    
    @abstractmethod
    async def collect_metrics(self, config: MonitoringConfig) -> Dict[str, Any]:
        """Collect metrics from the platform"""
        pass
    
    @abstractmethod
    async def send_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Send a single metric"""
        pass


class PrometheusCollector(MetricCollector):
    """Prometheus metrics collector"""
    
    def __init__(self, endpoint: str = "http://localhost:9090"):
        self.endpoint = endpoint
        self.metrics_registry = {}
    
    async def collect_metrics(self, config: MonitoringConfig) -> Dict[str, Any]:
        """Collect metrics from Prometheus"""
        metrics_data = {}
        
        for metric_def in config.metrics:
            try:
                # Query Prometheus for metric data
                query = f"{metric_def.name}[{metric_def.aggregation_window}]"
                data = await self._query_prometheus(query)
                metrics_data[metric_def.name] = data
            except Exception as e:
                logger.error(f"Failed to collect metric {metric_def.name}: {str(e)}")
        
        return metrics_data
    
    async def send_metric(self, metric_name: str, value: float, labels: Dict[str, str] = None):
        """Send metric to Prometheus (via pushgateway)"""
        # This would integrate with Prometheus Pushgateway
        logger.info(f"Sending metric {metric_name}={value} with labels {labels}")
        await asyncio.sleep(0.1)  # Simulate network call
    
    async def _query_prometheus(self, query: str) -> Dict[str, Any]:
        """Query Prometheus API"""
        # Mock Prometheus query - replace with actual HTTP calls
        await asyncio.sleep(0.5)
        return {
            "status": "success",
            "data": {
                "resultType": "matrix",
                "result": [
                    {
                        "metric": {"__name__": "http_requests_total"},
                        "values": [[time.time(), "100"]]
                    }
                ]
            }
        }
    
    def create_prometheus_config(self, config: MonitoringConfig) -> str:
        """Generate Prometheus configuration"""
        prometheus_config = {
            "global": {
                "scrape_interval": "15s",
                "evaluation_interval": "15s"
            },
            "rule_files": [
                f"{config.application_name}_alerts.yml"
            ],
            "scrape_configs": [
                {
                    "job_name": f"{config.application_name}",
                    "static_configs": [
                        {
                            "targets": ["localhost:8080"]
                        }
                    ],
                    "metrics_path": "/metrics",
                    "scrape_interval": "30s"
                }
            ],
            "alerting": {
                "alertmanagers": [
                    {
                        "static_configs": [
                            {
                                "targets": ["localhost:9093"]
                            }
                        ]
                    }
                ]
            }
        }
        
        return json.dumps(prometheus_config, indent=2)


class GrafanaIntegration:
    """Grafana dashboard and alerting integration"""
    
    def __init__(self, api_url: str = "http://localhost:3000", api_key: str = ""):
        self.api_url = api_url
        self.api_key = api_key
    
    async def create_dashboard(self, dashboard: Dashboard, config: MonitoringConfig) -> str:
        """Create Grafana dashboard"""
        dashboard_json = {
            "dashboard": {
                "id": None,
                "title": dashboard.name,
                "description": dashboard.description,
                "tags": dashboard.tags or [],
                "timezone": "browser",
                "panels": self._convert_panels_to_grafana(dashboard.panels, config),
                "time": {
                    "from": f"now-{dashboard.time_range}",
                    "to": "now"
                },
                "refresh": dashboard.refresh_interval,
                "schemaVersion": 30,
                "version": 1
            },
            "overwrite": True
        }
        
        # Mock dashboard creation - replace with actual Grafana API calls
        await asyncio.sleep(1)
        dashboard_id = f"dashboard-{int(time.time())}"
        
        logger.info(f"Created Grafana dashboard: {dashboard.name} (ID: {dashboard_id})")
        return dashboard_id
    
    def _convert_panels_to_grafana(self, panels: List[Dict[str, Any]], config: MonitoringConfig) -> List[Dict[str, Any]]:
        """Convert panel definitions to Grafana format"""
        grafana_panels = []
        
        for i, panel in enumerate(panels):
            grafana_panel = {
                "id": i + 1,
                "title": panel.get("title", f"Panel {i + 1}"),
                "type": panel.get("type", "graph"),
                "gridPos": {
                    "h": panel.get("height", 8),
                    "w": panel.get("width", 12),
                    "x": (i % 2) * 12,
                    "y": (i // 2) * 8
                },
                "targets": [
                    {
                        "expr": panel.get("query", "up"),
                        "refId": "A"
                    }
                ],
                "yAxes": [
                    {
                        "label": panel.get("y_label", ""),
                        "min": panel.get("y_min"),
                        "max": panel.get("y_max")
                    }
                ]
            }
            grafana_panels.append(grafana_panel)
        
        return grafana_panels
    
    async def setup_alerting(self, alerts: List[AlertRule], config: MonitoringConfig):
        """Setup Grafana alerting rules"""
        for alert in alerts:
            alert_rule = {
                "alert": {
                    "name": alert.name,
                    "message": alert.description,
                    "frequency": "10s",
                    "conditions": [
                        {
                            "query": {
                                "queryType": "",
                                "refId": "A",
                                "model": {
                                    "expr": f"{alert.metric_name} {alert.condition}",
                                    "interval": "",
                                    "refId": "A"
                                }
                            },
                            "reducer": {
                                "type": "last",
                                "params": []
                            },
                            "evaluator": {
                                "params": [alert.threshold],
                                "type": "gt" if ">" in alert.condition else "lt"
                            }
                        }
                    ],
                    "executionErrorState": "alerting",
                    "noDataState": "no_data",
                    "for": alert.duration
                }
            }
            
            # Mock alert creation
            await asyncio.sleep(0.5)
            logger.info(f"Created Grafana alert: {alert.name}")


class DatadogIntegration:
    """Datadog monitoring integration"""
    
    def __init__(self, api_key: str = "", app_key: str = ""):
        self.api_key = api_key
        self.app_key = app_key
    
    async def send_metrics(self, metrics: List[Dict[str, Any]]):
        """Send metrics to Datadog"""
        # Mock Datadog API call
        await asyncio.sleep(0.5)
        logger.info(f"Sent {len(metrics)} metrics to Datadog")
    
    async def create_dashboard(self, dashboard: Dashboard, config: MonitoringConfig) -> str:
        """Create Datadog dashboard"""
        dashboard_payload = {
            "title": dashboard.name,
            "description": dashboard.description,
            "widgets": self._convert_panels_to_datadog(dashboard.panels),
            "layout_type": "ordered",
            "is_read_only": False,
            "notify_list": [],
            "template_variables": []
        }
        
        # Mock dashboard creation
        await asyncio.sleep(1)
        dashboard_id = f"datadog-dashboard-{int(time.time())}"
        
        logger.info(f"Created Datadog dashboard: {dashboard.name} (ID: {dashboard_id})")
        return dashboard_id
    
    def _convert_panels_to_datadog(self, panels: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Convert panels to Datadog widget format"""
        widgets = []
        
        for panel in panels:
            widget = {
                "definition": {
                    "type": "timeseries",
                    "requests": [
                        {
                            "q": panel.get("query", "avg:system.cpu.user{*}"),
                            "display_type": "line",
                            "style": {
                                "palette": "dog_classic",
                                "line_type": "solid",
                                "line_width": "normal"
                            }
                        }
                    ],
                    "title": panel.get("title", "Metric"),
                    "show_legend": True,
                    "legend_size": "0"
                }
            }
            widgets.append(widget)
        
        return widgets


class JaegerIntegration:
    """Jaeger distributed tracing integration"""
    
    def __init__(self, endpoint: str = "http://localhost:14268"):
        self.endpoint = endpoint
    
    async def send_trace(self, trace_data: Dict[str, Any]):
        """Send trace data to Jaeger"""
        # Mock trace sending
        await asyncio.sleep(0.2)
        logger.info(f"Sent trace to Jaeger: {trace_data.get('traceID', 'unknown')}")
    
    async def query_traces(self, service_name: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """Query traces from Jaeger"""
        # Mock trace query
        await asyncio.sleep(0.5)
        
        return [
            {
                "traceID": "abc123",
                "spans": [
                    {
                        "spanID": "span1",
                        "operationName": "http_request",
                        "startTime": int(start_time.timestamp() * 1000000),
                        "duration": 150000,  # microseconds
                        "tags": [
                            {"key": "http.method", "value": "GET"},
                            {"key": "http.status_code", "value": "200"}
                        ]
                    }
                ],
                "processes": {
                    "p1": {
                        "serviceName": service_name,
                        "tags": []
                    }
                }
            }
        ]


class AlertManager:
    """Manages alerts across multiple platforms"""
    
    def __init__(self):
        self.active_alerts = {}
        self.alert_history = []
        self.notification_channels = {}
    
    def register_notification_channel(self, name: str, handler):
        """Register notification channel handler"""
        self.notification_channels[name] = handler
        logger.info(f"Registered notification channel: {name}")
    
    async def process_alert(self, alert_data: Dict[str, Any]):
        """Process incoming alert"""
        alert_id = alert_data.get("alert_id", f"alert-{int(time.time())}")
        
        # Check if this is a new alert or update
        if alert_id not in self.active_alerts:
            # New alert
            self.active_alerts[alert_id] = {
                "id": alert_id,
                "name": alert_data.get("name", "Unknown Alert"),
                "severity": alert_data.get("severity", AlertSeverity.WARNING),
                "start_time": datetime.now(),
                "status": "firing",
                "description": alert_data.get("description", ""),
                "labels": alert_data.get("labels", {}),
                "annotations": alert_data.get("annotations", {})
            }
            
            # Send notifications
            await self._send_alert_notifications(self.active_alerts[alert_id])
            
        else:
            # Update existing alert
            if alert_data.get("status") == "resolved":
                self.active_alerts[alert_id]["status"] = "resolved"
                self.active_alerts[alert_id]["end_time"] = datetime.now()
                
                # Send resolution notification
                await self._send_resolution_notifications(self.active_alerts[alert_id])
                
                # Move to history
                self.alert_history.append(self.active_alerts[alert_id])
                del self.active_alerts[alert_id]
    
    async def _send_alert_notifications(self, alert: Dict[str, Any]):
        """Send alert notifications to configured channels"""
        message = f"""
        🚨 ALERT: {alert['name']}
        Severity: {alert['severity'].value if isinstance(alert['severity'], AlertSeverity) else alert['severity']}
        Description: {alert['description']}
        Time: {alert['start_time'].isoformat()}
        Labels: {alert['labels']}
        """
        
        for channel_name, handler in self.notification_channels.items():
            try:
                await handler(message, alert)
            except Exception as e:
                logger.error(f"Failed to send alert to {channel_name}: {str(e)}")
    
    async def _send_resolution_notifications(self, alert: Dict[str, Any]):
        """Send alert resolution notifications"""
        duration = alert.get('end_time', datetime.now()) - alert['start_time']
        
        message = f"""
        ✅ RESOLVED: {alert['name']}
        Duration: {duration.total_seconds():.2f} seconds
        Resolution Time: {alert.get('end_time', datetime.now()).isoformat()}
        """
        
        for channel_name, handler in self.notification_channels.items():
            try:
                await handler(message, alert)
            except Exception as e:
                logger.error(f"Failed to send resolution to {channel_name}: {str(e)}")


class MonitoringOrchestrator:
    """Orchestrates monitoring across multiple platforms"""
    
    def __init__(self):
        self.collectors = {}
        self.integrations = {}
        self.alert_manager = AlertManager()
        self.monitoring_configs = {}
    
    def register_collector(self, platform: MonitoringPlatform, collector: MetricCollector):
        """Register metric collector for platform"""
        self.collectors[platform] = collector
        logger.info(f"Registered collector for {platform.value}")
    
    def register_integration(self, platform: MonitoringPlatform, integration):
        """Register platform integration"""
        self.integrations[platform] = integration
        logger.info(f"Registered integration for {platform.value}")
    
    async def setup_monitoring(self, config: MonitoringConfig) -> Dict[str, Any]:
        """Setup monitoring for application"""
        self.monitoring_configs[config.application_name] = config
        setup_results = {}
        
        for platform in config.platforms:
            try:
                if platform == MonitoringPlatform.PROMETHEUS:
                    result = await self._setup_prometheus(config)
                elif platform == MonitoringPlatform.GRAFANA:
                    result = await self._setup_grafana(config)
                elif platform == MonitoringPlatform.DATADOG:
                    result = await self._setup_datadog(config)
                elif platform == MonitoringPlatform.JAEGER:
                    result = await self._setup_jaeger(config)
                else:
                    result = {"status": "not_implemented"}
                
                setup_results[platform.value] = result
                
            except Exception as e:
                logger.error(f"Failed to setup {platform.value}: {str(e)}")
                setup_results[platform.value] = {"status": "failed", "error": str(e)}
        
        # Setup alerting
        await self._setup_alerting(config)
        
        logger.info(f"Monitoring setup completed for {config.application_name}")
        return setup_results
    
    async def _setup_prometheus(self, config: MonitoringConfig) -> Dict[str, Any]:
        """Setup Prometheus monitoring"""
        if MonitoringPlatform.PROMETHEUS not in self.collectors:
            return {"status": "no_collector"}
        
        collector = self.collectors[MonitoringPlatform.PROMETHEUS]
        
        # Generate Prometheus configuration
        if hasattr(collector, 'create_prometheus_config'):
            prometheus_config = collector.create_prometheus_config(config)
            
            # Write configuration file (in real implementation)
            # with open(f"/etc/prometheus/{config.application_name}.yml", "w") as f:
            #     f.write(prometheus_config)
        
        return {"status": "configured", "scrape_targets": 1}
    
    async def _setup_grafana(self, config: MonitoringConfig) -> Dict[str, Any]:
        """Setup Grafana dashboards"""
        if MonitoringPlatform.GRAFANA not in self.integrations:
            return {"status": "no_integration"}
        
        grafana = self.integrations[MonitoringPlatform.GRAFANA]
        dashboard_ids = []
        
        for dashboard in config.dashboards:
            dashboard_id = await grafana.create_dashboard(dashboard, config)
            dashboard_ids.append(dashboard_id)
        
        # Setup alerting
        await grafana.setup_alerting(config.alerts, config)
        
        return {"status": "configured", "dashboards": dashboard_ids}
    
    async def _setup_datadog(self, config: MonitoringConfig) -> Dict[str, Any]:
        """Setup Datadog monitoring"""
        if MonitoringPlatform.DATADOG not in self.integrations:
            return {"status": "no_integration"}
        
        datadog = self.integrations[MonitoringPlatform.DATADOG]
        dashboard_ids = []
        
        for dashboard in config.dashboards:
            dashboard_id = await datadog.create_dashboard(dashboard, config)
            dashboard_ids.append(dashboard_id)
        
        return {"status": "configured", "dashboards": dashboard_ids}
    
    async def _setup_jaeger(self, config: MonitoringConfig) -> Dict[str, Any]:
        """Setup Jaeger tracing"""
        if MonitoringPlatform.JAEGER not in self.integrations:
            return {"status": "no_integration"}
        
        # Jaeger setup is typically done via environment variables or config files
        return {"status": "configured", "endpoint": "http://localhost:14268"}
    
    async def _setup_alerting(self, config: MonitoringConfig):
        """Setup alerting rules"""
        for alert in config.alerts:
            # Register alert with alert manager
            await self.alert_manager.process_alert({
                "alert_id": f"{config.application_name}-{alert.name}",
                "name": alert.name,
                "severity": alert.severity,
                "description": alert.description,
                "status": "configured"
            })
    
    async def collect_all_metrics(self, application_name: str) -> Dict[str, Any]:
        """Collect metrics from all configured platforms"""
        if application_name not in self.monitoring_configs:
            return {"error": "Application not configured"}
        
        config = self.monitoring_configs[application_name]
        all_metrics = {}
        
        for platform in config.platforms:
            if platform in self.collectors:
                try:
                    metrics = await self.collectors[platform].collect_metrics(config)
                    all_metrics[platform.value] = metrics
                except Exception as e:
                    logger.error(f"Failed to collect metrics from {platform.value}: {str(e)}")
                    all_metrics[platform.value] = {"error": str(e)}
        
        return all_metrics
    
    def generate_monitoring_report(self, application_name: str) -> Dict[str, Any]:
        """Generate comprehensive monitoring report"""
        if application_name not in self.monitoring_configs:
            return {"error": "Application not configured"}
        
        config = self.monitoring_configs[application_name]
        
        # Get active alerts
        active_alerts = [
            alert for alert in self.alert_manager.active_alerts.values()
            if application_name in alert.get('labels', {}).get('application', '')
        ]
        
        # Get recent alert history
        recent_alerts = [
            alert for alert in self.alert_manager.alert_history[-10:]
            if application_name in alert.get('labels', {}).get('application', '')
        ]
        
        return {
            "application_name": application_name,
            "environment": config.environment,
            "platforms": [p.value for p in config.platforms],
            "metrics_count": len(config.metrics),
            "alerts_count": len(config.alerts),
            "dashboards_count": len(config.dashboards),
            "active_alerts": len(active_alerts),
            "recent_alerts": len(recent_alerts),
            "sampling_rate": config.sampling_rate,
            "retention_policy": config.retention_policy
        }


# Example usage and configuration
def create_sample_monitoring_config() -> MonitoringConfig:
    """Create sample monitoring configuration"""
    return MonitoringConfig(
        application_name="enterprise-app",
        environment="production",
        platforms=[
            MonitoringPlatform.PROMETHEUS,
            MonitoringPlatform.GRAFANA,
            MonitoringPlatform.JAEGER
        ],
        metrics=[
            MetricDefinition(
                name="http_requests_total",
                type=MetricType.COUNTER,
                description="Total HTTP requests",
                labels=["method", "status", "endpoint"],
                unit="requests"
            ),
            MetricDefinition(
                name="http_request_duration_seconds",
                type=MetricType.HISTOGRAM,
                description="HTTP request duration",
                labels=["method", "endpoint"],
                unit="seconds"
            ),
            MetricDefinition(
                name="application_errors_total",
                type=MetricType.COUNTER,
                description="Total application errors",
                labels=["error_type", "severity"],
                unit="errors"
            )
        ],
        alerts=[
            AlertRule(
                name="High Error Rate",
                metric_name="application_errors_total",
                condition="> 0.05",
                threshold=0.05,
                duration="5m",
                severity=AlertSeverity.CRITICAL,
                description="Application error rate is above 5%",
                notification_channels=["slack", "pagerduty"]
            ),
            AlertRule(
                name="High Response Time",
                metric_name="http_request_duration_seconds",
                condition="> 1.0",
                threshold=1.0,
                duration="10m",
                severity=AlertSeverity.WARNING,
                description="HTTP response time is above 1 second",
                notification_channels=["slack"]
            )
        ],
        dashboards=[
            Dashboard(
                name="Application Overview",
                description="Main application metrics dashboard",
                panels=[
                    {
                        "title": "Request Rate",
                        "query": "rate(http_requests_total[5m])",
                        "type": "graph",
                        "y_label": "Requests/sec"
                    },
                    {
                        "title": "Error Rate",
                        "query": "rate(application_errors_total[5m])",
                        "type": "graph",
                        "y_label": "Errors/sec"
                    },
                    {
                        "title": "Response Time",
                        "query": "histogram_quantile(0.95, http_request_duration_seconds_bucket)",
                        "type": "graph",
                        "y_label": "Seconds"
                    }
                ],
                tags=["application", "production"]
            )
        ],
        sampling_rate=1.0,
        retention_policy="30d"
    )


async def slack_notification_handler(message: str, alert: Dict[str, Any]):
    """Example Slack notification handler"""
    logger.info(f"Sending to Slack: {message}")
    # Implement actual Slack API call here


async def main():
    """Example usage of the monitoring integration"""
    # Create monitoring configuration
    config = create_sample_monitoring_config()
    
    # Create orchestrator
    orchestrator = MonitoringOrchestrator()
    
    # Register collectors and integrations
    orchestrator.register_collector(MonitoringPlatform.PROMETHEUS, PrometheusCollector())
    orchestrator.register_integration(MonitoringPlatform.GRAFANA, GrafanaIntegration())
    orchestrator.register_integration(MonitoringPlatform.JAEGER, JaegerIntegration())
    
    # Register notification channels
    orchestrator.alert_manager.register_notification_channel("slack", slack_notification_handler)
    
    # Setup monitoring
    setup_results = await orchestrator.setup_monitoring(config)
    print(f"Monitoring setup results: {json.dumps(setup_results, indent=2)}")
    
    # Collect metrics
    metrics = await orchestrator.collect_all_metrics("enterprise-app")
    print(f"Collected metrics: {json.dumps(metrics, indent=2)}")
    
    # Generate report
    report = orchestrator.generate_monitoring_report("enterprise-app")
    print(f"Monitoring report: {json.dumps(report, indent=2)}")


if __name__ == "__main__":
    asyncio.run(main())

