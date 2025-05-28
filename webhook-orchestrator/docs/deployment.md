# Webhook Orchestrator Deployment Guide

## Overview

This guide covers deployment strategies for the Webhook Orchestrator, from local development to production-ready deployments with high availability and scalability.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Kubernetes Deployment](#kubernetes-deployment)
4. [Production Considerations](#production-considerations)
5. [Monitoring and Observability](#monitoring-and-observability)
6. [Security Configuration](#security-configuration)
7. [Scaling and Performance](#scaling-and-performance)
8. [Troubleshooting](#troubleshooting)

## Local Development

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker and Docker Compose (optional)

### Setup

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd webhook-orchestrator
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize database:**
   ```bash
   alembic upgrade head
   ```

6. **Start services:**
   ```bash
   # Terminal 1: FastAPI server
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   
   # Terminal 2: Celery worker
   celery -A app.tasks.celery_app worker --loglevel=info
   
   # Terminal 3: Celery beat (optional)
   celery -A app.tasks.celery_app beat --loglevel=info
   ```

### Development Environment Variables

```bash
# .env file for development
DEBUG=true
ENVIRONMENT=development
LOG_LEVEL=DEBUG

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/webhook_orchestrator

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2

# GitHub
GITHUB_WEBHOOK_SECRET=your-webhook-secret
GITHUB_TOKEN=your-github-token

# Codegen
CODEGEN_TOKEN=your-codegen-token
CODEGEN_ORG_ID=1

# Security
SECRET_KEY=your-secret-key

# Monitoring
ENABLE_METRICS=true
ENABLE_TRACING=true
JAEGER_ENDPOINT=http://localhost:14268
```

## Docker Deployment

### Quick Start

1. **Create environment file:**
   ```bash
   cp docker/.env.example docker/.env
   # Edit docker/.env with your configuration
   ```

2. **Start all services:**
   ```bash
   cd docker
   docker-compose up -d
   ```

3. **Verify deployment:**
   ```bash
   # Check service health
   curl http://localhost:8000/health
   
   # View logs
   docker-compose logs -f webhook-orchestrator
   ```

### Docker Compose Services

The Docker Compose setup includes:

- **webhook-orchestrator**: Main FastAPI application
- **celery-worker**: Background task processing (2 replicas)
- **celery-beat**: Periodic task scheduler
- **celery-flower**: Task monitoring UI
- **postgres**: PostgreSQL database
- **redis**: Redis for caching and task queue
- **prometheus**: Metrics collection
- **grafana**: Metrics visualization
- **jaeger**: Distributed tracing
- **nginx**: Reverse proxy and load balancer

### Service URLs

- **Main Application**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Grafana Dashboard**: http://localhost:3000 (admin/admin)
- **Flower Monitoring**: http://localhost:5555
- **Jaeger Tracing**: http://localhost:16686
- **Prometheus**: http://localhost:9090

### Docker Environment Variables

```bash
# docker/.env
# Production settings
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO

# Database
POSTGRES_DB=webhook_orchestrator
POSTGRES_USER=webhook_user
POSTGRES_PASSWORD=secure-password
DATABASE_URL=postgresql+asyncpg://webhook_user:secure-password@postgres:5432/webhook_orchestrator

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# GitHub
GITHUB_WEBHOOK_SECRET=your-webhook-secret
GITHUB_TOKEN=your-github-token

# Codegen
CODEGEN_TOKEN=your-codegen-token
CODEGEN_ORG_ID=1

# Security
SECRET_KEY=your-very-secure-secret-key

# Monitoring
ENABLE_METRICS=true
ENABLE_TRACING=true
JAEGER_ENDPOINT=http://jaeger:14268

# Grafana
GRAFANA_PASSWORD=secure-grafana-password
```

### Scaling with Docker Compose

```bash
# Scale Celery workers
docker-compose up -d --scale celery-worker=4

# Scale main application (behind load balancer)
docker-compose up -d --scale webhook-orchestrator=3
```

## Kubernetes Deployment

### Prerequisites

- Kubernetes cluster (1.20+)
- kubectl configured
- Helm 3+ (optional but recommended)

### Namespace Setup

```bash
kubectl create namespace webhook-orchestrator
kubectl config set-context --current --namespace=webhook-orchestrator
```

### ConfigMap and Secrets

1. **Create ConfigMap:**
   ```yaml
   # k8s/configmap.yaml
   apiVersion: v1
   kind: ConfigMap
   metadata:
     name: webhook-orchestrator-config
   data:
     ENVIRONMENT: "production"
     LOG_LEVEL: "INFO"
     ENABLE_METRICS: "true"
     ENABLE_TRACING: "true"
     DATABASE_URL: "postgresql+asyncpg://webhook_user:$(POSTGRES_PASSWORD)@postgres:5432/webhook_orchestrator"
     REDIS_URL: "redis://redis:6379/0"
     CELERY_BROKER_URL: "redis://redis:6379/1"
     CELERY_RESULT_BACKEND: "redis://redis:6379/2"
   ```

2. **Create Secrets:**
   ```bash
   kubectl create secret generic webhook-orchestrator-secrets \
     --from-literal=SECRET_KEY=your-secret-key \
     --from-literal=GITHUB_WEBHOOK_SECRET=your-webhook-secret \
     --from-literal=GITHUB_TOKEN=your-github-token \
     --from-literal=CODEGEN_TOKEN=your-codegen-token \
     --from-literal=POSTGRES_PASSWORD=your-db-password
   ```

### Database Deployment

```yaml
# k8s/postgres.yaml
apiVersion: apps/v1
kind: StatefulSet
metadata:
  name: postgres
spec:
  serviceName: postgres
  replicas: 1
  selector:
    matchLabels:
      app: postgres
  template:
    metadata:
      labels:
        app: postgres
    spec:
      containers:
      - name: postgres
        image: postgres:15-alpine
        env:
        - name: POSTGRES_DB
          value: webhook_orchestrator
        - name: POSTGRES_USER
          value: webhook_user
        - name: POSTGRES_PASSWORD
          valueFrom:
            secretKeyRef:
              name: webhook-orchestrator-secrets
              key: POSTGRES_PASSWORD
        ports:
        - containerPort: 5432
        volumeMounts:
        - name: postgres-storage
          mountPath: /var/lib/postgresql/data
  volumeClaimTemplates:
  - metadata:
      name: postgres-storage
    spec:
      accessModes: ["ReadWriteOnce"]
      resources:
        requests:
          storage: 20Gi
---
apiVersion: v1
kind: Service
metadata:
  name: postgres
spec:
  selector:
    app: postgres
  ports:
  - port: 5432
    targetPort: 5432
```

### Redis Deployment

```yaml
# k8s/redis.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis
  template:
    metadata:
      labels:
        app: redis
    spec:
      containers:
      - name: redis
        image: redis:7-alpine
        command: ["redis-server", "--appendonly", "yes"]
        ports:
        - containerPort: 6379
        volumeMounts:
        - name: redis-storage
          mountPath: /data
      volumes:
      - name: redis-storage
        persistentVolumeClaim:
          claimName: redis-pvc
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: redis-pvc
spec:
  accessModes:
    - ReadWriteOnce
  resources:
    requests:
      storage: 10Gi
---
apiVersion: v1
kind: Service
metadata:
  name: redis
spec:
  selector:
    app: redis
  ports:
  - port: 6379
    targetPort: 6379
```

### Application Deployment

```yaml
# k8s/webhook-orchestrator.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: webhook-orchestrator
spec:
  replicas: 3
  selector:
    matchLabels:
      app: webhook-orchestrator
  template:
    metadata:
      labels:
        app: webhook-orchestrator
    spec:
      containers:
      - name: webhook-orchestrator
        image: webhook-orchestrator:latest
        ports:
        - containerPort: 8000
        envFrom:
        - configMapRef:
            name: webhook-orchestrator-config
        - secretRef:
            name: webhook-orchestrator-secrets
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
---
apiVersion: v1
kind: Service
metadata:
  name: webhook-orchestrator
spec:
  selector:
    app: webhook-orchestrator
  ports:
  - port: 80
    targetPort: 8000
  type: ClusterIP
```

### Celery Workers Deployment

```yaml
# k8s/celery-worker.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
spec:
  replicas: 4
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: celery-worker
        image: webhook-orchestrator:latest
        command: ["celery", "-A", "app.tasks.celery_app", "worker", "--loglevel=info", "--concurrency=4"]
        envFrom:
        - configMapRef:
            name: webhook-orchestrator-config
        - secretRef:
            name: webhook-orchestrator-secrets
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### Horizontal Pod Autoscaler

```yaml
# k8s/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: webhook-orchestrator-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: webhook-orchestrator
  minReplicas: 3
  maxReplicas: 10
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
---
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: celery-worker-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: celery-worker
  minReplicas: 2
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 80
```

### Ingress Configuration

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: webhook-orchestrator-ingress
  annotations:
    nginx.ingress.kubernetes.io/rate-limit: "100"
    nginx.ingress.kubernetes.io/rate-limit-window: "1m"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
spec:
  tls:
  - hosts:
    - webhook-orchestrator.yourdomain.com
    secretName: webhook-orchestrator-tls
  rules:
  - host: webhook-orchestrator.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: webhook-orchestrator
            port:
              number: 80
```

### Deployment Commands

```bash
# Apply all configurations
kubectl apply -f k8s/

# Check deployment status
kubectl get pods
kubectl get services
kubectl get ingress

# View logs
kubectl logs -f deployment/webhook-orchestrator
kubectl logs -f deployment/celery-worker

# Scale deployments
kubectl scale deployment webhook-orchestrator --replicas=5
kubectl scale deployment celery-worker --replicas=8
```

## Production Considerations

### High Availability

1. **Database High Availability:**
   - Use PostgreSQL with streaming replication
   - Consider managed database services (AWS RDS, Google Cloud SQL)
   - Implement automated backups and point-in-time recovery

2. **Redis High Availability:**
   - Use Redis Sentinel or Redis Cluster
   - Consider managed Redis services (AWS ElastiCache, Google Memorystore)
   - Implement data persistence with AOF and RDB

3. **Application High Availability:**
   - Deploy across multiple availability zones
   - Use load balancers with health checks
   - Implement graceful shutdown handling

### Performance Optimization

1. **Database Optimization:**
   ```sql
   -- Recommended PostgreSQL settings
   shared_buffers = 256MB
   effective_cache_size = 1GB
   work_mem = 4MB
   maintenance_work_mem = 64MB
   max_connections = 200
   ```

2. **Connection Pooling:**
   ```python
   # Database connection pool settings
   DATABASE_POOL_SIZE=20
   DATABASE_MAX_OVERFLOW=30
   DATABASE_POOL_TIMEOUT=30
   DATABASE_POOL_RECYCLE=3600
   ```

3. **Celery Optimization:**
   ```python
   # Celery worker settings
   CELERY_WORKER_CONCURRENCY=4
   CELERY_WORKER_PREFETCH_MULTIPLIER=1
   CELERY_TASK_ACKS_LATE=True
   CELERY_WORKER_MAX_TASKS_PER_CHILD=1000
   ```

### Security Hardening

1. **Network Security:**
   - Use private subnets for databases
   - Implement security groups/firewall rules
   - Enable VPC flow logs

2. **Application Security:**
   - Use HTTPS everywhere
   - Implement proper authentication
   - Regular security updates
   - Vulnerability scanning

3. **Secrets Management:**
   - Use Kubernetes secrets or external secret managers
   - Rotate secrets regularly
   - Encrypt secrets at rest

### Backup and Recovery

1. **Database Backups:**
   ```bash
   # Automated PostgreSQL backup
   pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME | gzip > backup_$(date +%Y%m%d_%H%M%S).sql.gz
   ```

2. **Configuration Backups:**
   ```bash
   # Backup Kubernetes configurations
   kubectl get all -o yaml > k8s-backup-$(date +%Y%m%d).yaml
   ```

3. **Disaster Recovery Plan:**
   - Document recovery procedures
   - Test recovery regularly
   - Implement cross-region backups

## Monitoring and Observability

### Prometheus Configuration

```yaml
# monitoring/prometheus-config.yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
- job_name: 'webhook-orchestrator'
  kubernetes_sd_configs:
  - role: pod
  relabel_configs:
  - source_labels: [__meta_kubernetes_pod_label_app]
    action: keep
    regex: webhook-orchestrator
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_scrape]
    action: keep
    regex: true
  - source_labels: [__meta_kubernetes_pod_annotation_prometheus_io_path]
    action: replace
    target_label: __metrics_path__
    regex: (.+)
```

### Grafana Dashboards

Key metrics to monitor:

1. **Application Metrics:**
   - Request rate and latency
   - Error rate
   - Active connections

2. **Task Metrics:**
   - Queue size
   - Task execution time
   - Task failure rate

3. **Infrastructure Metrics:**
   - CPU and memory usage
   - Database connections
   - Redis memory usage

### Alerting Rules

```yaml
# monitoring/alert-rules.yaml
groups:
- name: webhook-orchestrator
  rules:
  - alert: HighErrorRate
    expr: rate(webhook_errors_total[5m]) > 0.05
    for: 2m
    labels:
      severity: warning
    annotations:
      summary: High error rate detected
      
  - alert: QueueBacklog
    expr: celery_queue_size > 100
    for: 5m
    labels:
      severity: warning
    annotations:
      summary: Large queue backlog detected
      
  - alert: ServiceDown
    expr: up{job="webhook-orchestrator"} == 0
    for: 1m
    labels:
      severity: critical
    annotations:
      summary: Webhook orchestrator service is down
```

## Security Configuration

### SSL/TLS Configuration

1. **Certificate Management:**
   ```bash
   # Using cert-manager for automatic certificate management
   kubectl apply -f https://github.com/jetstack/cert-manager/releases/download/v1.8.0/cert-manager.yaml
   ```

2. **Ingress TLS:**
   ```yaml
   apiVersion: networking.k8s.io/v1
   kind: Ingress
   metadata:
     annotations:
       cert-manager.io/cluster-issuer: "letsencrypt-prod"
   spec:
     tls:
     - hosts:
       - webhook-orchestrator.yourdomain.com
       secretName: webhook-orchestrator-tls
   ```

### Network Policies

```yaml
# security/network-policy.yaml
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: webhook-orchestrator-netpol
spec:
  podSelector:
    matchLabels:
      app: webhook-orchestrator
  policyTypes:
  - Ingress
  - Egress
  ingress:
  - from:
    - namespaceSelector:
        matchLabels:
          name: ingress-nginx
    ports:
    - protocol: TCP
      port: 8000
  egress:
  - to:
    - podSelector:
        matchLabels:
          app: postgres
    ports:
    - protocol: TCP
      port: 5432
  - to:
    - podSelector:
        matchLabels:
          app: redis
    ports:
    - protocol: TCP
      port: 6379
```

### Pod Security Standards

```yaml
# security/pod-security-policy.yaml
apiVersion: v1
kind: Pod
metadata:
  name: webhook-orchestrator
spec:
  securityContext:
    runAsNonRoot: true
    runAsUser: 1000
    fsGroup: 1000
  containers:
  - name: webhook-orchestrator
    securityContext:
      allowPrivilegeEscalation: false
      readOnlyRootFilesystem: true
      capabilities:
        drop:
        - ALL
```

## Scaling and Performance

### Horizontal Scaling

1. **Application Scaling:**
   - Use HPA based on CPU/memory
   - Consider custom metrics (queue size, request rate)
   - Implement graceful shutdown

2. **Database Scaling:**
   - Read replicas for read-heavy workloads
   - Connection pooling
   - Query optimization

3. **Cache Scaling:**
   - Redis clustering
   - Cache warming strategies
   - TTL optimization

### Vertical Scaling

1. **Resource Requests and Limits:**
   ```yaml
   resources:
     requests:
       memory: "512Mi"
       cpu: "500m"
     limits:
       memory: "1Gi"
       cpu: "1000m"
   ```

2. **JVM Tuning (if applicable):**
   ```bash
   # Java application tuning
   JAVA_OPTS="-Xms512m -Xmx1g -XX:+UseG1GC"
   ```

### Performance Testing

1. **Load Testing:**
   ```bash
   # Using Apache Bench
   ab -n 1000 -c 10 http://localhost:8000/health
   
   # Using wrk
   wrk -t12 -c400 -d30s http://localhost:8000/api/v1/webhooks/github
   ```

2. **Stress Testing:**
   ```bash
   # Using Kubernetes job for load testing
   kubectl apply -f load-test-job.yaml
   ```

## Troubleshooting

### Common Issues

1. **Database Connection Issues:**
   ```bash
   # Check database connectivity
   kubectl exec -it deployment/webhook-orchestrator -- python -c "
   from app.core.database import db_manager
   import asyncio
   asyncio.run(db_manager.initialize())
   print('Database connection successful')
   "
   ```

2. **Celery Worker Issues:**
   ```bash
   # Check Celery worker status
   kubectl exec -it deployment/celery-worker -- celery -A app.tasks.celery_app inspect active
   
   # Check queue status
   kubectl exec -it deployment/celery-worker -- celery -A app.tasks.celery_app inspect reserved
   ```

3. **Memory Issues:**
   ```bash
   # Check memory usage
   kubectl top pods
   
   # Check for memory leaks
   kubectl exec -it deployment/webhook-orchestrator -- python -c "
   import psutil
   process = psutil.Process()
   print(f'Memory usage: {process.memory_info().rss / 1024 / 1024:.2f} MB')
   "
   ```

### Debugging Commands

```bash
# View application logs
kubectl logs -f deployment/webhook-orchestrator --tail=100

# Debug pod issues
kubectl describe pod <pod-name>

# Check resource usage
kubectl top nodes
kubectl top pods

# Access pod shell
kubectl exec -it <pod-name> -- /bin/bash

# Port forward for local debugging
kubectl port-forward deployment/webhook-orchestrator 8000:8000

# Check service endpoints
kubectl get endpoints

# View events
kubectl get events --sort-by=.metadata.creationTimestamp
```

### Performance Debugging

1. **Application Profiling:**
   ```python
   # Add profiling to application
   import cProfile
   import pstats
   
   profiler = cProfile.Profile()
   profiler.enable()
   # ... application code ...
   profiler.disable()
   stats = pstats.Stats(profiler)
   stats.sort_stats('cumulative').print_stats(10)
   ```

2. **Database Query Analysis:**
   ```sql
   -- Enable query logging in PostgreSQL
   ALTER SYSTEM SET log_statement = 'all';
   SELECT pg_reload_conf();
   
   -- Analyze slow queries
   SELECT query, mean_time, calls 
   FROM pg_stat_statements 
   ORDER BY mean_time DESC 
   LIMIT 10;
   ```

3. **Memory Profiling:**
   ```python
   # Memory profiling with memory_profiler
   from memory_profiler import profile
   
   @profile
   def webhook_handler():
       # ... handler code ...
   ```

### Log Analysis

```bash
# Aggregate logs from all pods
kubectl logs -l app=webhook-orchestrator --tail=1000 | grep ERROR

# Search for specific patterns
kubectl logs -l app=webhook-orchestrator | grep "webhook_processing_error"

# Export logs for analysis
kubectl logs deployment/webhook-orchestrator --since=1h > webhook-logs.txt
```

This deployment guide provides comprehensive coverage of deploying the Webhook Orchestrator from development to production environments with proper security, monitoring, and scaling considerations.

