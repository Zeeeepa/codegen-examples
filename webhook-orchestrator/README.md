# 🔗 Webhook Orchestrator FastAPI Service

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)](https://fastapi.tiangolo.com/)
[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](docker/Dockerfile)

A robust, production-ready webhook orchestrator built with FastAPI that handles GitHub events, coordinates workflow execution, and manages communication between system components with advanced features including retry logic, circuit breakers, distributed tracing, and comprehensive monitoring.

## 🎯 Features

### 🔒 **Advanced Security**
- **HMAC-SHA256 signature verification** for GitHub webhooks
- **Replay attack protection** with delivery ID tracking and timestamp validation
- **Rate limiting** with configurable thresholds and burst handling
- **Payload size validation** to prevent DoS attacks
- **Input sanitization** and validation with Pydantic models

### 🔄 **Resilience & Reliability**
- **Exponential backoff retry logic** with multiple strategies (exponential, linear, fixed, Fibonacci)
- **Circuit breaker patterns** for external service dependencies
- **Graceful error handling** with detailed error reporting and correlation IDs
- **Health checks** for all system components with dependency monitoring
- **Automatic failover** and recovery mechanisms

### 📊 **Observability & Monitoring**
- **Prometheus metrics** for comprehensive system monitoring
- **Distributed tracing** with OpenTelemetry and Jaeger integration
- **Structured logging** with correlation IDs and contextual information
- **Real-time dashboards** with Grafana integration
- **Custom metrics** for business logic monitoring

### ⚡ **Performance & Scalability**
- **Async processing** with FastAPI and asyncio for high concurrency
- **Background task queuing** with Celery and Redis for scalable processing
- **Database connection pooling** for optimal database performance
- **Horizontal scaling** support with load balancing
- **Auto-scaling** capabilities with Kubernetes HPA

### 🔧 **Developer Experience**
- **Comprehensive API documentation** with OpenAPI/Swagger
- **Type safety** with Pydantic models and Python type hints
- **Extensive testing** with pytest and async test support
- **Docker containerization** for consistent deployments
- **Development tools** integration (linting, formatting, testing)

## 🏗️ Architecture

```mermaid
graph TB
    A[GitHub Webhooks] --> B[Nginx Load Balancer]
    B --> C[FastAPI Application]
    C --> D[PostgreSQL Database]
    C --> E[Redis Cache/Queue]
    E --> F[Celery Workers]
    F --> G[Codegen Agent]
    F --> H[GitHub API]
    
    C --> I[Prometheus Metrics]
    I --> J[Grafana Dashboard]
    
    C --> K[Jaeger Tracing]
    
    subgraph "Monitoring Stack"
        I
        J
        K
    end
    
    subgraph "Processing Layer"
        F
        G
        H
    end
    
    subgraph "Storage Layer"
        D
        E
    end
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (recommended)

### 1. Clone and Setup

```bash
git clone <repository-url>
cd webhook-orchestrator

# Copy environment configuration
cp .env.example .env
# Edit .env with your configuration
```

### 2. Docker Deployment (Recommended)

```bash
# Start all services
docker-compose up -d

# Check service health
curl http://localhost:8000/health

# View logs
docker-compose logs -f webhook-orchestrator
```

### 3. Manual Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
alembic upgrade head

# Start services
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. Verify Installation

- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health
- **Metrics**: http://localhost:8000/metrics
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Flower Monitoring**: http://localhost:5555

## 📋 Configuration

### Environment Variables

Key configuration options:

```bash
# GitHub Integration
GITHUB_WEBHOOK_SECRET=your-webhook-secret
GITHUB_TOKEN=your-github-token

# Codegen Integration
CODEGEN_TOKEN=your-codegen-token
CODEGEN_ORG_ID=1

# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/db

# Security
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=yourdomain.com,localhost

# Monitoring
ENABLE_METRICS=true
ENABLE_TRACING=true
JAEGER_ENDPOINT=http://jaeger:14268
```

See [.env.example](.env.example) for complete configuration options.

### GitHub Webhook Setup

1. Go to your GitHub repository settings
2. Navigate to Webhooks
3. Add webhook with URL: `https://your-domain.com/api/v1/webhooks/github`
4. Select events: Pull requests, Check runs, Check suites, Pushes
5. Set content type to `application/json`
6. Add your webhook secret

## 🔄 Supported Events

### GitHub Events

| Event Type | Actions | Description |
|------------|---------|-------------|
| `pull_request` | opened, synchronize, reopened, ready_for_review | Triggers PR analysis and code generation |
| `check_run` | completed (with failures) | Triggers failure analysis and fixes |
| `check_suite` | completed (with failures) | Triggers comprehensive failure analysis |
| `push` | to main/master branches | Triggers push analysis and monitoring |
| `installation` | created, deleted | Manages app installation events |
| `ping` | - | Webhook connectivity test |

### Workflow Tasks

| Task Type | Purpose | Triggers |
|-----------|---------|----------|
| `pull_request_analysis` | Analyze PR changes and determine actions | New/updated PRs |
| `check_failure_analysis` | Analyze and fix failed check runs | Failed tests, linting, builds |
| `check_suite_failure_analysis` | Comprehensive failure analysis | Failed check suites |
| `push_analysis` | Monitor main branch changes | Pushes to main/master |
| `codegen_trigger` | Trigger Codegen agent | Based on analysis results |

## 🔧 API Reference

### Webhook Endpoints

#### POST `/api/v1/webhooks/github`
Process GitHub webhook events.

**Headers:**
- `X-GitHub-Delivery`: Unique delivery ID
- `X-GitHub-Event`: Event type
- `X-Hub-Signature-256`: HMAC signature

**Response:**
```json
{
  "status": "accepted",
  "delivery_id": "12345678-1234-1234-1234-123456789012",
  "event_type": "pull_request",
  "result": {
    "status": "queued",
    "task_id": "task-uuid"
  }
}
```

### Management Endpoints

#### GET `/api/v1/tasks`
List workflow tasks with filtering.

**Query Parameters:**
- `limit`: Number of tasks (default: 50, max: 1000)
- `offset`: Skip tasks (default: 0)
- `status`: Filter by status
- `task_type`: Filter by type
- `repository`: Filter by repository

#### GET `/health`
Comprehensive health check.

```json
{
  "status": "healthy",
  "checks": {
    "database": "healthy",
    "celery": "healthy",
    "github_api": "healthy"
  },
  "uptime": 3600.0
}
```

#### GET `/metrics`
Prometheus metrics endpoint.

See [API Documentation](docs/api-docs.md) for complete API reference.

## 📊 Monitoring

### Key Metrics

- **Webhook Processing**: Event volume, latency, error rates
- **Task Execution**: Queue sizes, execution times, retry rates
- **System Health**: Resource usage, connection pools, API quotas
- **Business Metrics**: Codegen triggers, PR analysis results

### Dashboards

The included Grafana dashboards provide:

1. **System Overview**: High-level system health and performance
2. **Webhook Processing**: Detailed webhook processing metrics
3. **Task Execution**: Celery task monitoring and queue analysis
4. **Error Analysis**: Error rates, failure patterns, and debugging info

### Alerting

Recommended alerts:

- High error rate (>5% webhook failures)
- Queue backlog (>100 pending tasks)
- High latency (>30s average processing time)
- Service unavailability
- Resource exhaustion

## 🧪 Testing

### Running Tests

```bash
# Install test dependencies
pip install pytest pytest-asyncio pytest-cov

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/test_webhooks.py -v
pytest tests/test_tasks.py -v
```

### Test Categories

- **Unit Tests**: Individual component testing
- **Integration Tests**: End-to-end workflow testing
- **Performance Tests**: Load and stress testing
- **Security Tests**: Vulnerability and penetration testing

## 🚀 Deployment

### Docker Deployment

```bash
# Production deployment
docker-compose -f docker-compose.prod.yml up -d

# Scale workers
docker-compose up -d --scale celery-worker=4
```

### Kubernetes Deployment

```bash
# Apply configurations
kubectl apply -f k8s/

# Check status
kubectl get pods -n webhook-orchestrator

# Scale deployment
kubectl scale deployment webhook-orchestrator --replicas=5
```

See [Deployment Guide](docs/deployment.md) for detailed deployment instructions.

## 🔒 Security

### Security Features

- **Webhook signature verification** with HMAC-SHA256
- **Replay attack protection** with delivery ID tracking
- **Rate limiting** to prevent abuse
- **Input validation** with Pydantic models
- **Secure defaults** for all configurations

### Security Best Practices

1. **Use HTTPS** for all webhook endpoints
2. **Rotate secrets** regularly
3. **Monitor for suspicious activity**
4. **Keep dependencies updated**
5. **Implement proper access controls**

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Set up pre-commit hooks
pre-commit install

# Run linting
black app/ tests/
isort app/ tests/
flake8 app/ tests/

# Run type checking
mypy app/
```

## 📚 Documentation

- [API Documentation](docs/api-docs.md) - Complete API reference
- [Deployment Guide](docs/deployment.md) - Production deployment instructions
- [Architecture Overview](docs/architecture.md) - System design and components
- [Configuration Reference](docs/configuration.md) - All configuration options

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Errors**
   - Check DATABASE_URL configuration
   - Verify PostgreSQL is running and accessible
   - Check connection pool settings

2. **Celery Worker Issues**
   - Verify Redis connectivity
   - Check worker logs for errors
   - Monitor queue sizes

3. **Webhook Signature Failures**
   - Verify GITHUB_WEBHOOK_SECRET matches GitHub configuration
   - Check webhook payload format
   - Monitor for replay attacks

### Debug Commands

```bash
# Check service health
curl http://localhost:8000/health

# View application logs
docker-compose logs -f webhook-orchestrator

# Check Celery worker status
docker-compose exec celery-worker celery -A app.tasks.celery_app inspect active

# Monitor metrics
curl http://localhost:8000/metrics
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FastAPI](https://fastapi.tiangolo.com/) for the excellent web framework
- [Celery](https://docs.celeryproject.org/) for distributed task processing
- [OpenTelemetry](https://opentelemetry.io/) for observability standards
- [Prometheus](https://prometheus.io/) for monitoring and alerting
- [Grafana](https://grafana.com/) for visualization and dashboards

## 📞 Support

- 📧 Email: support@example.com
- 💬 Discord: [Join our community](https://discord.gg/example)
- 📖 Documentation: [docs.example.com](https://docs.example.com)
- 🐛 Issues: [GitHub Issues](https://github.com/example/webhook-orchestrator/issues)

---

**Built with ❤️ for the developer community**

