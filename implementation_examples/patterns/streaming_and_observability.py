#!/usr/bin/env python
"""
Streaming and Observability Patterns

This module demonstrates advanced patterns for streaming responses and comprehensive
observability in Codegen SDK integrations, including metrics collection, distributed
tracing, and real-time monitoring.
"""

import asyncio
import time
import json
import uuid
from typing import Iterator, Dict, Any, Optional, List, Callable
from dataclasses import dataclass, field
from datetime import datetime, timezone
from contextlib import contextmanager
import logging
from abc import ABC, abstractmethod

# Simulated streaming and observability components
# In a real implementation, these would integrate with actual services


@dataclass
class MetricPoint:
    """Represents a single metric measurement"""
    name: str
    value: float
    timestamp: datetime
    tags: Dict[str, str] = field(default_factory=dict)
    unit: str = ""


@dataclass
class SpanContext:
    """Distributed tracing span context"""
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    baggage: Dict[str, str] = field(default_factory=dict)


@dataclass
class Span:
    """Distributed tracing span"""
    context: SpanContext
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    tags: Dict[str, Any] = field(default_factory=dict)
    logs: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "ok"  # ok, error, timeout


class MetricsCollector(ABC):
    """Abstract base class for metrics collection"""
    
    @abstractmethod
    def record_counter(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        """Record a counter metric"""
        pass
    
    @abstractmethod
    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a gauge metric"""
        pass
    
    @abstractmethod
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        """Record a histogram metric"""
        pass
    
    @abstractmethod
    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        """Record a timer metric"""
        pass


class PrometheusMetricsCollector(MetricsCollector):
    """Prometheus-compatible metrics collector"""
    
    def __init__(self):
        self.metrics = []
        self.logger = logging.getLogger(__name__)
    
    def record_counter(self, name: str, value: float = 1, tags: Dict[str, str] = None):
        metric = MetricPoint(
            name=f"{name}_total",
            value=value,
            timestamp=datetime.now(timezone.utc),
            tags=tags or {},
            unit="count"
        )
        self.metrics.append(metric)
        self.logger.debug(f"Counter: {name} = {value}")
    
    def record_gauge(self, name: str, value: float, tags: Dict[str, str] = None):
        metric = MetricPoint(
            name=name,
            value=value,
            timestamp=datetime.now(timezone.utc),
            tags=tags or {},
            unit="gauge"
        )
        self.metrics.append(metric)
        self.logger.debug(f"Gauge: {name} = {value}")
    
    def record_histogram(self, name: str, value: float, tags: Dict[str, str] = None):
        metric = MetricPoint(
            name=f"{name}_histogram",
            value=value,
            timestamp=datetime.now(timezone.utc),
            tags=tags or {},
            unit="histogram"
        )
        self.metrics.append(metric)
        self.logger.debug(f"Histogram: {name} = {value}")
    
    def record_timer(self, name: str, duration: float, tags: Dict[str, str] = None):
        metric = MetricPoint(
            name=f"{name}_duration_seconds",
            value=duration,
            timestamp=datetime.now(timezone.utc),
            tags=tags or {},
            unit="seconds"
        )
        self.metrics.append(metric)
        self.logger.debug(f"Timer: {name} = {duration}s")
    
    def get_metrics_export(self) -> str:
        """Export metrics in Prometheus format"""
        lines = []
        for metric in self.metrics:
            tags_str = ",".join([f'{k}="{v}"' for k, v in metric.tags.items()])
            if tags_str:
                line = f'{metric.name}{{{tags_str}}} {metric.value}'
            else:
                line = f'{metric.name} {metric.value}'
            lines.append(line)
        return "\n".join(lines)


class Tracer:
    """Distributed tracing implementation"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.spans = []
        self.active_spans = {}
        self.logger = logging.getLogger(__name__)
    
    def start_span(self, operation_name: str, parent_context: Optional[SpanContext] = None) -> Span:
        """Start a new tracing span"""
        trace_id = parent_context.trace_id if parent_context else str(uuid.uuid4())
        span_id = str(uuid.uuid4())
        parent_span_id = parent_context.span_id if parent_context else None
        
        context = SpanContext(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id
        )
        
        span = Span(
            context=context,
            operation_name=operation_name,
            start_time=datetime.now(timezone.utc)
        )
        
        span.tags["service.name"] = self.service_name
        self.spans.append(span)
        self.active_spans[span_id] = span
        
        self.logger.debug(f"Started span: {operation_name} (trace: {trace_id}, span: {span_id})")
        return span
    
    def finish_span(self, span: Span, status: str = "ok"):
        """Finish a tracing span"""
        span.end_time = datetime.now(timezone.utc)
        span.status = status
        
        if span.context.span_id in self.active_spans:
            del self.active_spans[span.context.span_id]
        
        duration = (span.end_time - span.start_time).total_seconds()
        self.logger.debug(f"Finished span: {span.operation_name} ({duration:.3f}s, status: {status})")
    
    @contextmanager
    def span(self, operation_name: str, parent_context: Optional[SpanContext] = None):
        """Context manager for automatic span lifecycle"""
        span = self.start_span(operation_name, parent_context)
        try:
            yield span
            self.finish_span(span, "ok")
        except Exception as e:
            span.tags["error"] = True
            span.tags["error.message"] = str(e)
            self.finish_span(span, "error")
            raise


class StreamingResponse:
    """Simulated streaming response for agent tasks"""
    
    def __init__(self, task_id: str, total_chunks: int = 10):
        self.task_id = task_id
        self.total_chunks = total_chunks
        self.current_chunk = 0
        self.is_complete = False
        self.error = None
    
    def __iter__(self) -> Iterator[Dict[str, Any]]:
        """Iterate over streaming chunks"""
        while not self.is_complete and self.current_chunk < self.total_chunks:
            self.current_chunk += 1
            
            # Simulate processing time
            time.sleep(0.5)
            
            # Simulate occasional errors
            if self.current_chunk == 7 and self.task_id.endswith("error"):
                self.error = "Simulated processing error"
                yield {
                    "type": "error",
                    "task_id": self.task_id,
                    "error": self.error,
                    "chunk": self.current_chunk,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                return
            
            # Generate chunk content
            chunk_content = f"Processing step {self.current_chunk}/{self.total_chunks}..."
            if self.current_chunk == self.total_chunks:
                chunk_content = "Task completed successfully!"
                self.is_complete = True
            
            yield {
                "type": "chunk" if not self.is_complete else "complete",
                "task_id": self.task_id,
                "content": chunk_content,
                "chunk": self.current_chunk,
                "total_chunks": self.total_chunks,
                "progress": self.current_chunk / self.total_chunks,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }


class ObservableStreamingAgent:
    """Agent with streaming capabilities and comprehensive observability"""
    
    def __init__(self, token: str, org_id: int, service_name: str = "codegen-agent"):
        self.token = token
        self.org_id = org_id
        self.service_name = service_name
        
        # Initialize observability components
        self.metrics = PrometheusMetricsCollector()
        self.tracer = Tracer(service_name)
        self.logger = logging.getLogger(__name__)
        
        # Performance tracking
        self.request_count = 0
        self.error_count = 0
        self.total_execution_time = 0.0
    
    def run_streaming(self, prompt: str, context: Optional[Dict[str, Any]] = None) -> Iterator[Dict[str, Any]]:
        """Run agent task with streaming response and full observability"""
        
        task_id = str(uuid.uuid4())
        self.request_count += 1
        
        # Start distributed tracing
        with self.tracer.span("agent_run_streaming") as span:
            span.tags.update({
                "task_id": task_id,
                "prompt_length": len(prompt),
                "org_id": self.org_id,
                "has_context": context is not None
            })
            
            # Record metrics
            self.metrics.record_counter("agent_requests", tags={
                "service": self.service_name,
                "org_id": str(self.org_id)
            })
            
            start_time = time.time()
            
            try:
                # Log request details
                self.logger.info(f"Starting streaming task {task_id}", extra={
                    "task_id": task_id,
                    "prompt_length": len(prompt),
                    "context_keys": list(context.keys()) if context else []
                })
                
                # Simulate streaming response
                streaming_response = StreamingResponse(task_id)
                
                chunk_count = 0
                for chunk in streaming_response:
                    chunk_count += 1
                    
                    # Add observability to each chunk
                    chunk["trace_id"] = span.context.trace_id
                    chunk["span_id"] = span.context.span_id
                    
                    # Record chunk metrics
                    self.metrics.record_counter("agent_chunks", tags={
                        "service": self.service_name,
                        "task_id": task_id,
                        "chunk_type": chunk["type"]
                    })
                    
                    # Log chunk processing
                    self.logger.debug(f"Processed chunk {chunk_count} for task {task_id}")
                    
                    yield chunk
                    
                    # Handle errors
                    if chunk["type"] == "error":
                        self.error_count += 1
                        self.metrics.record_counter("agent_errors", tags={
                            "service": self.service_name,
                            "error_type": "processing_error"
                        })
                        span.tags["error"] = True
                        span.tags["error.message"] = chunk["error"]
                        break
                
                # Record completion metrics
                execution_time = time.time() - start_time
                self.total_execution_time += execution_time
                
                self.metrics.record_timer("agent_execution_time", execution_time, tags={
                    "service": self.service_name,
                    "status": "error" if streaming_response.error else "success"
                })
                
                self.metrics.record_histogram("agent_chunks_per_task", chunk_count, tags={
                    "service": self.service_name
                })
                
                # Update span with final metrics
                span.tags.update({
                    "execution_time": execution_time,
                    "chunk_count": chunk_count,
                    "success": streaming_response.error is None
                })
                
                self.logger.info(f"Completed streaming task {task_id}", extra={
                    "task_id": task_id,
                    "execution_time": execution_time,
                    "chunk_count": chunk_count,
                    "success": streaming_response.error is None
                })
                
            except Exception as e:
                self.error_count += 1
                execution_time = time.time() - start_time
                
                self.metrics.record_counter("agent_errors", tags={
                    "service": self.service_name,
                    "error_type": "exception"
                })
                
                self.logger.error(f"Task {task_id} failed with exception: {e}", extra={
                    "task_id": task_id,
                    "execution_time": execution_time,
                    "error": str(e)
                })
                
                # Yield error response
                yield {
                    "type": "error",
                    "task_id": task_id,
                    "error": str(e),
                    "trace_id": span.context.trace_id,
                    "span_id": span.context.span_id,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }
                
                raise
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get current health and performance metrics"""
        avg_execution_time = (self.total_execution_time / self.request_count 
                             if self.request_count > 0 else 0)
        error_rate = (self.error_count / self.request_count * 100 
                     if self.request_count > 0 else 0)
        
        return {
            "service_name": self.service_name,
            "uptime_seconds": time.time(),  # Simplified uptime
            "total_requests": self.request_count,
            "total_errors": self.error_count,
            "error_rate_percent": error_rate,
            "average_execution_time": avg_execution_time,
            "status": "healthy" if error_rate < 10 else "degraded"
        }
    
    def export_metrics(self) -> str:
        """Export metrics in Prometheus format"""
        # Add current health metrics
        health = self.get_health_metrics()
        self.metrics.record_gauge("agent_total_requests", health["total_requests"])
        self.metrics.record_gauge("agent_error_rate", health["error_rate_percent"])
        self.metrics.record_gauge("agent_avg_execution_time", health["average_execution_time"])
        
        return self.metrics.get_metrics_export()
    
    def export_traces(self) -> List[Dict[str, Any]]:
        """Export traces in JSON format"""
        traces = []
        for span in self.tracer.spans:
            trace_data = {
                "trace_id": span.context.trace_id,
                "span_id": span.context.span_id,
                "parent_span_id": span.context.parent_span_id,
                "operation_name": span.operation_name,
                "start_time": span.start_time.isoformat(),
                "end_time": span.end_time.isoformat() if span.end_time else None,
                "duration_ms": ((span.end_time - span.start_time).total_seconds() * 1000 
                               if span.end_time else None),
                "tags": span.tags,
                "logs": span.logs,
                "status": span.status
            }
            traces.append(trace_data)
        
        return traces


class RealTimeMonitor:
    """Real-time monitoring and alerting system"""
    
    def __init__(self, agent: ObservableStreamingAgent):
        self.agent = agent
        self.alert_thresholds = {
            "error_rate": 10.0,  # 10%
            "avg_execution_time": 30.0,  # 30 seconds
            "request_rate": 100  # requests per minute
        }
        self.alerts = []
        self.logger = logging.getLogger(__name__)
    
    def check_health(self) -> Dict[str, Any]:
        """Check system health and generate alerts"""
        health = self.agent.get_health_metrics()
        alerts = []
        
        # Check error rate
        if health["error_rate_percent"] > self.alert_thresholds["error_rate"]:
            alert = {
                "type": "error_rate_high",
                "severity": "warning",
                "message": f"Error rate is {health['error_rate_percent']:.1f}%, above threshold of {self.alert_thresholds['error_rate']}%",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "value": health["error_rate_percent"],
                "threshold": self.alert_thresholds["error_rate"]
            }
            alerts.append(alert)
            self.logger.warning(alert["message"])
        
        # Check execution time
        if health["average_execution_time"] > self.alert_thresholds["avg_execution_time"]:
            alert = {
                "type": "execution_time_high",
                "severity": "warning",
                "message": f"Average execution time is {health['average_execution_time']:.1f}s, above threshold of {self.alert_thresholds['avg_execution_time']}s",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "value": health["average_execution_time"],
                "threshold": self.alert_thresholds["avg_execution_time"]
            }
            alerts.append(alert)
            self.logger.warning(alert["message"])
        
        self.alerts.extend(alerts)
        
        return {
            "health": health,
            "alerts": alerts,
            "status": "healthy" if not alerts else "warning"
        }
    
    def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data"""
        health_check = self.check_health()
        
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "service": self.agent.service_name,
            "health": health_check["health"],
            "alerts": self.alerts[-10:],  # Last 10 alerts
            "metrics_summary": {
                "total_requests": health_check["health"]["total_requests"],
                "error_rate": health_check["health"]["error_rate_percent"],
                "avg_response_time": health_check["health"]["average_execution_time"],
                "status": health_check["status"]
            },
            "recent_traces": self.agent.export_traces()[-5:]  # Last 5 traces
        }


# Example usage and demonstration
async def main():
    """Demonstrate streaming and observability patterns"""
    import os
    
    # Setup logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Initialize observable streaming agent
    token = os.getenv("CODEGEN_TOKEN", "demo-token")
    agent = ObservableStreamingAgent(token=token, org_id=1, service_name="demo-agent")
    
    # Initialize monitoring
    monitor = RealTimeMonitor(agent)
    
    print("=== Streaming and Observability Demo ===")
    
    # Example 1: Successful streaming task
    print("\n1. Successful Streaming Task:")
    async for chunk in agent.run_streaming("Create a Python function for sorting"):
        print(f"  Chunk {chunk['chunk']}: {chunk['content'][:50]}...")
        if chunk['type'] == 'complete':
            break
    
    # Example 2: Task with simulated error
    print("\n2. Task with Error:")
    try:
        async for chunk in agent.run_streaming("This will error", {"task_suffix": "error"}):
            print(f"  Chunk {chunk['chunk']}: {chunk.get('content', chunk.get('error', ''))[:50]}...")
            if chunk['type'] == 'error':
                break
    except Exception as e:
        print(f"  Caught exception: {e}")
    
    # Example 3: Multiple concurrent tasks
    print("\n3. Multiple Concurrent Tasks:")
    tasks = [
        "Create a REST API endpoint",
        "Generate unit tests",
        "Write documentation"
    ]
    
    for i, task in enumerate(tasks):
        print(f"  Starting task {i+1}: {task}")
        chunk_count = 0
        async for chunk in agent.run_streaming(task):
            chunk_count += 1
            if chunk_count <= 2:  # Show first 2 chunks
                print(f"    Chunk {chunk['chunk']}: {chunk['content'][:40]}...")
            if chunk['type'] in ['complete', 'error']:
                break
    
    # Example 4: Health monitoring
    print("\n4. Health Monitoring:")
    dashboard_data = monitor.get_dashboard_data()
    print(f"  Service Status: {dashboard_data['metrics_summary']['status']}")
    print(f"  Total Requests: {dashboard_data['metrics_summary']['total_requests']}")
    print(f"  Error Rate: {dashboard_data['metrics_summary']['error_rate']:.1f}%")
    print(f"  Avg Response Time: {dashboard_data['metrics_summary']['avg_response_time']:.2f}s")
    
    if dashboard_data['alerts']:
        print(f"  Active Alerts: {len(dashboard_data['alerts'])}")
        for alert in dashboard_data['alerts'][-3:]:  # Show last 3 alerts
            print(f"    - {alert['type']}: {alert['message']}")
    
    # Example 5: Metrics export
    print("\n5. Metrics Export (Prometheus format):")
    metrics_export = agent.export_metrics()
    print("  Sample metrics:")
    for line in metrics_export.split('\n')[:5]:  # Show first 5 metrics
        print(f"    {line}")
    
    # Example 6: Trace export
    print("\n6. Distributed Traces:")
    traces = agent.export_traces()
    print(f"  Total traces: {len(traces)}")
    if traces:
        latest_trace = traces[-1]
        print(f"  Latest trace: {latest_trace['operation_name']} ({latest_trace['duration_ms']:.1f}ms)")
        print(f"    Status: {latest_trace['status']}")
        print(f"    Tags: {latest_trace['tags']}")


if __name__ == "__main__":
    asyncio.run(main())

