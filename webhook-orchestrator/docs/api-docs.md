# Webhook Orchestrator API Documentation

## Overview

The Webhook Orchestrator is a robust FastAPI-based service designed to handle GitHub webhook events, coordinate workflow execution, and manage communication between system components. It provides advanced features including retry logic, circuit breakers, distributed tracing, and comprehensive monitoring.

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   GitHub        │    │   Webhook       │    │   Celery        │
│   Webhooks      │───▶│   Orchestrator  │───▶│   Workers       │
│                 │    │   (FastAPI)     │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │                        │
                                ▼                        ▼
                       ┌─────────────────┐    ┌─────────────────┐
                       │   PostgreSQL    │    │   Codegen       │
                       │   Database      │    │   Agent         │
                       └─────────────────┘    └─────────────────┘
```

## Features

### 🔒 Security
- **HMAC-SHA256 signature verification** for GitHub webhooks
- **Replay attack protection** with delivery ID tracking
- **Rate limiting** to prevent abuse
- **Payload size validation** to prevent DoS attacks

### 🔄 Resilience
- **Exponential backoff retry logic** with configurable strategies
- **Circuit breaker patterns** for external service dependencies
- **Graceful error handling** with detailed error reporting
- **Health checks** for all system components

### 📊 Observability
- **Prometheus metrics** for comprehensive monitoring
- **Distributed tracing** with OpenTelemetry and Jaeger
- **Structured logging** with correlation IDs
- **Real-time dashboards** with Grafana integration

### ⚡ Performance
- **Async processing** with FastAPI and asyncio
- **Background task queuing** with Celery and Redis
- **Database connection pooling** for optimal performance
- **Horizontal scaling** support with load balancing

## API Endpoints

### Webhook Processing

#### POST `/api/v1/webhooks/github`
Process GitHub webhook events.

**Headers:**
- `X-GitHub-Delivery`: Unique delivery ID
- `X-GitHub-Event`: Event type (pull_request, check_run, etc.)
- `X-Hub-Signature-256`: HMAC-SHA256 signature
- `Content-Type`: application/json

**Request Body:**
GitHub webhook payload (varies by event type)

**Response:**
```json
{
  "status": "accepted",
  "delivery_id": "12345678-1234-1234-1234-123456789012",
  "event_type": "pull_request",
  "result": {
    "status": "queued",
    "task_id": "task-uuid",
    "action": "opened"
  }
}
```

**Status Codes:**
- `200`: Webhook processed successfully
- `400`: Invalid payload or headers
- `401`: Invalid signature
- `409`: Duplicate/replayed request
- `413`: Payload too large
- `500`: Internal server error

### Webhook Event Management

#### GET `/api/v1/webhooks/events`
List webhook events with filtering and pagination.

**Query Parameters:**
- `limit`: Number of events to return (default: 50, max: 1000)
- `offset`: Number of events to skip (default: 0)
- `event_type`: Filter by event type
- `processed`: Filter by processing status

**Response:**
```json
[
  {
    "id": 1,
    "delivery_id": "12345678-1234-1234-1234-123456789012",
    "event_type": "pull_request",
    "processed": true,
    "created_at": "2023-12-01T10:00:00Z",
    "error_message": null
  }
]
```

#### GET `/api/v1/webhooks/events/{event_id}`
Get detailed webhook event information.

**Response:**
```json
{
  "id": 1,
  "delivery_id": "12345678-1234-1234-1234-123456789012",
  "event_type": "pull_request",
  "source": "github",
  "payload": { /* GitHub webhook payload */ },
  "headers": { /* Request headers */ },
  "processed": true,
  "processing_started_at": "2023-12-01T10:00:00Z",
  "processing_completed_at": "2023-12-01T10:00:05Z",
  "error_message": null,
  "retry_count": 0,
  "created_at": "2023-12-01T10:00:00Z",
  "updated_at": "2023-12-01T10:00:05Z"
}
```

#### POST `/api/v1/webhooks/events/{event_id}/reprocess`
Reprocess a failed webhook event.

**Response:**
```json
{
  "status": "reprocessing",
  "task_id": "celery-task-uuid",
  "event_id": 1
}
```

### Workflow Task Management

#### GET `/api/v1/tasks`
List workflow tasks with filtering and pagination.

**Query Parameters:**
- `limit`: Number of tasks to return (default: 50, max: 1000)
- `offset`: Number of tasks to skip (default: 0)
- `status`: Filter by task status
- `task_type`: Filter by task type
- `repository`: Filter by repository

**Response:**
```json
[
  {
    "id": 1,
    "task_id": "task-uuid",
    "task_type": "pull_request_analysis",
    "status": "completed",
    "repository": "owner/repo",
    "pr_number": 123,
    "created_at": "2023-12-01T10:00:00Z",
    "completed_at": "2023-12-01T10:00:30Z",
    "error_message": null,
    "codegen_task_url": "https://codegen.sh/tasks/codegen-task-id"
  }
]
```

#### GET `/api/v1/tasks/{task_id}`
Get detailed workflow task information including execution history.

**Response:**
```json
{
  "id": 1,
  "task_id": "task-uuid",
  "webhook_event_id": 1,
  "task_type": "pull_request_analysis",
  "status": "completed",
  "priority": 0,
  "repository": "owner/repo",
  "pr_number": 123,
  "branch": "feature-branch",
  "commit_sha": "abc123def456",
  "config": { /* Task configuration */ },
  "input_data": { /* Input data */ },
  "output_data": { /* Output data */ },
  "started_at": "2023-12-01T10:00:00Z",
  "completed_at": "2023-12-01T10:00:30Z",
  "error_message": null,
  "retry_count": 0,
  "max_retries": 3,
  "codegen_task_id": "codegen-task-id",
  "codegen_task_url": "https://codegen.sh/tasks/codegen-task-id",
  "created_at": "2023-12-01T10:00:00Z",
  "updated_at": "2023-12-01T10:00:30Z",
  "executions": [
    {
      "id": 1,
      "execution_id": "execution-uuid",
      "status": "completed",
      "started_at": "2023-12-01T10:00:00Z",
      "completed_at": "2023-12-01T10:00:30Z",
      "duration_ms": 30000,
      "error_message": null
    }
  ]
}
```

#### POST `/api/v1/tasks/{task_id}/retry`
Retry a failed workflow task.

**Response:**
```json
{
  "status": "retrying",
  "celery_task_id": "celery-task-uuid",
  "task_id": "task-uuid"
}
```

### System Monitoring

#### GET `/health`
Comprehensive health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2023-12-01T10:00:00Z",
  "checks": {
    "database": "healthy",
    "celery": "healthy",
    "github_api": "healthy"
  },
  "uptime": 3600.0
}
```

**Status Codes:**
- `200`: System is healthy or degraded but functional
- `503`: System is unhealthy

#### GET `/metrics`
Prometheus metrics endpoint.

**Response:**
Prometheus-formatted metrics including:
- `webhook_events_total`: Total webhook events received
- `webhook_processing_duration_seconds`: Webhook processing time
- `workflow_tasks_total`: Total workflow tasks created
- `workflow_task_duration_seconds`: Task execution time
- `celery_queue_size`: Current queue sizes
- `github_api_requests_total`: GitHub API request count
- `codegen_agent_tasks_total`: Codegen agent tasks triggered

#### GET `/api/v1/metrics`
JSON-formatted system metrics.

**Response:**
```json
{
  "webhook_events_total": 1000,
  "workflow_tasks_total": 800,
  "task_executions_total": 850,
  "tasks_by_status": {
    "completed": 700,
    "failed": 50,
    "running": 30,
    "pending": 20
  },
  "events_by_type": {
    "pull_request": 600,
    "check_run": 200,
    "check_suite": 150,
    "push": 50
  },
  "avg_processing_time_ms": 2500.0
}
```

### Administrative

#### POST `/api/v1/admin/cleanup`
Trigger cleanup of old data.

**Response:**
```json
{
  "status": "cleanup_triggered",
  "task_id": "cleanup-task-uuid"
}
```

#### GET `/api/v1/admin/stats`
Get administrative statistics.

**Response:**
```json
{
  "recent_activity": {
    "webhooks_24h": 100,
    "tasks_24h": 80
  },
  "error_rates": {
    "failed_webhooks_24h": 5,
    "failed_tasks_24h": 3,
    "webhook_error_rate": 5.0,
    "task_error_rate": 3.75
  }
}
```

## Event Types

### Supported GitHub Events

#### Pull Request Events
- `opened`: New pull request created
- `synchronize`: Pull request updated with new commits
- `reopened`: Pull request reopened
- `ready_for_review`: Draft pull request marked ready
- `closed`: Pull request closed (monitoring only)

#### Check Events
- `check_run.completed`: Individual check completed
- `check_suite.completed`: Check suite completed

#### Push Events
- `push`: Code pushed to main/master branch

#### Installation Events
- `installation`: App installed/uninstalled
- `installation_repositories`: Repository access changed
- `ping`: Webhook test event

### Task Types

#### Analysis Tasks
- `pull_request_analysis`: Analyze PR changes and determine actions
- `check_failure_analysis`: Analyze failed check runs
- `check_suite_failure_analysis`: Analyze failed check suites
- `push_analysis`: Analyze push events to main branch

#### Action Tasks
- `codegen_trigger`: Trigger Codegen agent for code generation/fixes

## Configuration

### Environment Variables

#### Required
- `DATABASE_URL`: PostgreSQL connection string
- `GITHUB_WEBHOOK_SECRET`: GitHub webhook secret for signature verification
- `CODEGEN_TOKEN`: Codegen API token
- `CODEGEN_ORG_ID`: Codegen organization ID
- `SECRET_KEY`: Application secret key

#### Optional
- `REDIS_URL`: Redis connection string (default: redis://localhost:6379/0)
- `CELERY_BROKER_URL`: Celery broker URL (default: redis://localhost:6379/1)
- `GITHUB_TOKEN`: GitHub API token for enhanced functionality
- `JAEGER_ENDPOINT`: Jaeger tracing endpoint
- `LOG_LEVEL`: Logging level (default: INFO)
- `ENABLE_METRICS`: Enable Prometheus metrics (default: true)
- `ENABLE_TRACING`: Enable distributed tracing (default: true)

### Rate Limiting

Default rate limits:
- Webhook endpoints: 10 requests/second with burst of 20
- API endpoints: 100 requests/minute with burst of 50
- Health check: No rate limiting

### Retry Configuration

Default retry settings:
- Maximum retries: 3
- Backoff strategy: Exponential with base delay of 1 second
- Maximum delay: 300 seconds (5 minutes)
- Circuit breaker: 5 failures trigger open state, 30-second recovery timeout

## Error Handling

### Error Response Format

```json
{
  "error": "Error description",
  "status_code": 400,
  "path": "/api/v1/webhooks/github",
  "correlation_id": "trace-id-12345"
}
```

### Common Error Scenarios

1. **Invalid Signature (401)**
   - Webhook signature verification failed
   - Check `GITHUB_WEBHOOK_SECRET` configuration

2. **Payload Too Large (413)**
   - Webhook payload exceeds size limit
   - Default limit: 1MB

3. **Rate Limited (429)**
   - Too many requests from same IP
   - Implement exponential backoff in client

4. **Service Unavailable (503)**
   - System health check failed
   - Check dependent services (database, Redis, etc.)

## Monitoring and Alerting

### Key Metrics to Monitor

1. **Webhook Processing**
   - `webhook_events_total`: Event volume
   - `webhook_processing_duration_seconds`: Processing latency
   - `webhook_errors_total`: Error rate

2. **Task Execution**
   - `workflow_tasks_total`: Task volume
   - `workflow_task_duration_seconds`: Task execution time
   - `workflow_task_retries_total`: Retry frequency

3. **System Health**
   - `celery_queue_size`: Queue backlog
   - `database_connections_active`: Database load
   - `github_api_rate_limit_remaining`: API quota

### Recommended Alerts

1. **High Error Rate**: >5% webhook processing failures
2. **Queue Backlog**: >100 pending tasks
3. **High Latency**: >30s average processing time
4. **Service Down**: Health check failures
5. **Rate Limit**: <100 GitHub API requests remaining

## Security Considerations

### Webhook Security
- Always verify HMAC-SHA256 signatures
- Implement replay attack protection
- Use HTTPS for webhook endpoints
- Validate payload structure and size

### API Security
- Implement authentication for administrative endpoints
- Use rate limiting to prevent abuse
- Sanitize all input data
- Log security events for audit

### Infrastructure Security
- Use secure database connections (SSL/TLS)
- Encrypt sensitive configuration values
- Implement network segmentation
- Regular security updates for dependencies

## Deployment

### Docker Deployment
```bash
# Build and start all services
docker-compose up -d

# Scale workers
docker-compose up -d --scale celery-worker=4

# View logs
docker-compose logs -f webhook-orchestrator
```

### Kubernetes Deployment
See `k8s/` directory for Kubernetes manifests including:
- Deployment configurations
- Service definitions
- ConfigMaps and Secrets
- Horizontal Pod Autoscaler
- Ingress configuration

### Production Checklist
- [ ] Configure SSL/TLS certificates
- [ ] Set up monitoring and alerting
- [ ] Configure log aggregation
- [ ] Implement backup strategy
- [ ] Set up CI/CD pipeline
- [ ] Configure auto-scaling
- [ ] Test disaster recovery procedures

