# Quick Start Guide

Welcome to the Codegen AI Workflow Platform! This guide will help you get up and running in under 10 minutes.

## Prerequisites

Before you begin, ensure you have the following installed:

- **Docker** (version 20.10 or later)
- **Docker Compose** (version 2.0 or later)
- **Git** (for cloning the repository)
- **curl** (for testing API endpoints)

### System Requirements

- **CPU**: 2+ cores recommended
- **RAM**: 4GB minimum, 8GB recommended
- **Disk**: 10GB free space
- **OS**: Linux, macOS, or Windows with WSL2

## Step 1: Clone the Repository

```bash
git clone https://github.com/Zeeeepa/codegen-examples.git
cd codegen-examples/documentation-system
```

## Step 2: Run the Local Deployment Script

The platform includes an automated deployment script that sets up everything for you:

```bash
./deployment/scripts/deploy_local.sh
```

This script will:
- ✅ Check prerequisites
- 🏗️ Create necessary directories
- ⚙️ Generate environment configuration
- 🐳 Build and start Docker containers
- 🔍 Perform health checks

### What Gets Deployed

The local deployment includes:

| Service | Port | Description |
|---------|------|-------------|
| **Task Manager** | 8001 | Core task orchestration API |
| **Webhook Orchestrator** | 8002 | GitHub webhook handling |
| **Codegen Agent** | 8003 | AI agent coordination |
| **Documentation** | 8080 | This documentation site |
| **Grafana** | 3000 | Monitoring dashboard |
| **Prometheus** | 9090 | Metrics collection |
| **MinIO Console** | 9001 | Object storage management |

## Step 3: Configure API Keys

After deployment, you'll need to configure your API keys:

1. **Edit the environment file:**
   ```bash
   nano .env.local
   ```

2. **Update the following keys:**
   ```env
   # Required: Get from https://codegen.sh/token
   CODEGEN_API_KEY=your-codegen-api-key-here
   
   # Required: Get from https://console.anthropic.com
   CLAUDE_API_KEY=your-claude-api-key-here
   
   # Optional: For GitHub integration
   GITHUB_APP_ID=your-github-app-id
   GITHUB_PRIVATE_KEY_PATH=/app/secrets/github-private-key.pem
   ```

3. **Restart the services:**
   ```bash
   docker-compose -f deployment/docker/docker-compose.dev.yml restart
   ```

## Step 4: Verify Installation

### Check Service Health

Run the built-in health check tool:

```bash
python3 troubleshooting/diagnostic-tools/system_health_check.py
```

Expected output:
```
================================================================================
CODEGEN AI WORKFLOW PLATFORM - HEALTH CHECK REPORT
================================================================================
Overall Status: HEALTHY
Components Checked: 12

STATUS SUMMARY:
  ✅ Healthy:  12
  ⚠️  Warning:  0
  ❌ Critical: 0
  ❓ Unknown:  0
```

### Test API Endpoints

Test the core services:

```bash
# Task Manager API
curl http://localhost:8001/health

# Webhook Orchestrator
curl http://localhost:8002/health

# Codegen Agent
curl http://localhost:8003/health
```

### Access Web Interfaces

Open these URLs in your browser:

- **📚 Documentation**: http://localhost:8080
- **📊 Grafana Dashboard**: http://localhost:3000
  - Username: `admin`
  - Password: Check `.env.local` for `GRAFANA_ADMIN_PASSWORD`
- **💾 MinIO Console**: http://localhost:9001

## Step 5: Create Your First Workflow

### Using the API

Create a simple task using the Task Manager API:

```bash
curl -X POST http://localhost:8001/tasks \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_API_KEY" \
  -d '{
    "title": "My First AI Workflow",
    "description": "Create a simple Python script that prints Hello World",
    "priority": 3,
    "metadata": {
      "type": "code_generation",
      "language": "python"
    }
  }'
```

### Using the Python SDK

```python
import asyncio
from codegen import CodegenClient

async def create_workflow():
    client = CodegenClient(api_key="YOUR_API_KEY")
    
    # Create a new task
    task = await client.tasks.create(
        title="My First AI Workflow",
        description="Create a simple Python script that prints Hello World",
        priority=3,
        metadata={
            "type": "code_generation",
            "language": "python"
        }
    )
    
    print(f"Created task: {task.id}")
    return task

# Run the workflow
task = asyncio.run(create_workflow())
```

## Step 6: Monitor Your Workflow

### View Task Status

Check your task status:

```bash
curl http://localhost:8001/tasks/{task_id} \
  -H "Authorization: Bearer YOUR_API_KEY"
```

### Monitor in Grafana

1. Open http://localhost:3000
2. Navigate to **Dashboards** → **Codegen Platform Overview**
3. View real-time metrics for:
   - Task execution rates
   - API response times
   - System resource usage
   - Error rates

## Next Steps

Congratulations! You now have a fully functional Codegen AI Workflow Platform. Here's what to explore next:

### 🎯 Immediate Next Steps

1. **[Configure GitHub Integration](../integrations/github-setup.md)** - Automate code reviews and PR management
2. **[Create Custom Agents](../advanced/custom-agents.md)** - Build specialized AI agents for your use cases
3. **[Set Up Monitoring](../integrations/monitoring-setup.md)** - Configure alerts and dashboards

### 📚 Learn More

- **[API Reference](../../api-docs/openapi/task-manager.yaml)** - Complete API documentation
- **[Architecture Overview](../../architecture/system-design/overview.md)** - Understand the system design
- **[Troubleshooting Guide](../../troubleshooting/common-issues/)** - Common issues and solutions

### 🚀 Production Deployment

Ready for production? Check out our deployment guides:

- **[AWS Deployment](../../deployment/aws/)** - Deploy to Amazon Web Services
- **[Kubernetes Deployment](../../deployment/kubernetes/)** - Container orchestration
- **[Security Configuration](../../architecture/system-design/security-model.md)** - Production security setup

## Troubleshooting

### Common Issues

**Services not starting?**
```bash
# Check Docker daemon
docker info

# View service logs
docker-compose -f deployment/docker/docker-compose.dev.yml logs -f
```

**API keys not working?**
```bash
# Verify environment file
cat .env.local | grep API_KEY

# Restart services after updating keys
docker-compose -f deployment/docker/docker-compose.dev.yml restart
```

**Port conflicts?**
```bash
# Check what's using the ports
netstat -tulpn | grep :8001

# Update ports in .env.local if needed
```

### Getting Help

- **📖 Documentation**: Browse the full documentation at http://localhost:8080
- **🐛 Issues**: Report bugs on [GitHub Issues](https://github.com/Zeeeepa/codegen-examples/issues)
- **💬 Community**: Join our [Discord community](https://discord.gg/codegen)
- **📧 Support**: Email support@codegen.sh for enterprise support

---

**🎉 You're all set!** Your Codegen AI Workflow Platform is ready to automate your development workflows with the power of AI.

