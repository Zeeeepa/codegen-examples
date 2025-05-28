# 📚 Codegen AI Workflow Platform - Documentation & Deployment System

A comprehensive documentation and deployment guide system that provides complete setup instructions, API documentation, troubleshooting guides, and automated deployment scripts for the entire AI workflow platform.

## 🎯 Overview

This documentation system implements a complete knowledge base and deployment automation for the Codegen AI Workflow Platform, featuring:

- **Interactive API Documentation** - OpenAPI/Swagger with live testing capabilities
- **One-Click Deployment** - Automated scripts for AWS, GCP, Azure, and local environments
- **Step-by-Step Tutorials** - Comprehensive guides with working examples
- **Troubleshooting Tools** - Diagnostic utilities and recovery procedures
- **Architecture Documentation** - System design and component interactions
- **Configuration Management** - Environment-specific settings and templates

## 🚀 Quick Start

### Prerequisites

- Docker & Docker Compose
- Node.js 18+ (for documentation website)
- Python 3.9+ (for diagnostic tools)
- Git

### Local Deployment

1. **Clone and navigate to the documentation system:**
   ```bash
   git clone https://github.com/Zeeeepa/codegen-examples.git
   cd codegen-examples/documentation-system
   ```

2. **Run the automated deployment:**
   ```bash
   ./deployment/scripts/deploy_local.sh
   ```

3. **Access the documentation:**
   - 📚 Documentation Website: http://localhost:8080
   - 🔧 Task Manager API: http://localhost:8001
   - 📊 Monitoring Dashboard: http://localhost:3000

## 📁 Directory Structure

```
documentation-system/
├── docs-website/              # Interactive documentation website
│   ├── src/
│   │   ├── pages/            # Documentation pages
│   │   ├── components/       # React components
│   │   └── utils/           # Utilities and helpers
│   └── package.json
├── api-docs/                 # OpenAPI specifications
│   ├── openapi/             # API spec files
│   ├── generators/          # Documentation generators
│   └── examples/            # Code examples
├── deployment/              # Deployment automation
│   ├── scripts/            # Deployment scripts
│   ├── terraform/          # Infrastructure as Code
│   ├── kubernetes/         # K8s manifests
│   ├── docker/            # Docker configurations
│   └── configs/           # Configuration templates
├── tutorials/              # Step-by-step guides
│   ├── getting-started/   # Beginner tutorials
│   ├── advanced/         # Advanced topics
│   ├── integrations/     # Integration guides
│   └── examples/         # Example configurations
├── troubleshooting/       # Diagnostic tools and guides
│   ├── diagnostic-tools/ # Health check scripts
│   ├── common-issues/   # Issue resolution guides
│   └── recovery-procedures/ # Disaster recovery
├── architecture/         # System design documentation
│   ├── system-design/   # Architecture overviews
│   ├── diagrams/       # System diagrams
│   └── specifications/ # Technical specifications
└── automation/          # Documentation automation
    ├── doc-generation/ # Auto-generated docs
    ├── deployment-automation/ # Deployment tools
    └── maintenance/   # Maintenance scripts
```

## 🛠️ Features

### Interactive Documentation Website

- **Modern React/Next.js Interface** - Fast, responsive, and accessible
- **Live API Testing** - Test endpoints directly from the documentation
- **Advanced Search** - Full-text search with intelligent filtering
- **Code Examples** - Copy-paste ready examples in multiple languages
- **Interactive Tutorials** - Step-by-step guided workflows

### Deployment Automation

- **Multi-Cloud Support** - AWS, GCP, Azure, and local deployment
- **Infrastructure as Code** - Terraform modules for reproducible deployments
- **Container Orchestration** - Docker Compose and Kubernetes configurations
- **Environment Management** - Automated configuration for dev/staging/prod
- **Health Monitoring** - Built-in health checks and monitoring setup

### Comprehensive Documentation

- **API Reference** - Complete OpenAPI 3.0 specifications
- **Architecture Guides** - System design and component interactions
- **Tutorial Library** - From basic setup to advanced customization
- **Troubleshooting** - Common issues and diagnostic procedures
- **Best Practices** - Production deployment and security guidelines

## 🔧 Development

### Running the Documentation Website Locally

```bash
cd docs-website
npm install
npm run dev
```

The website will be available at http://localhost:3000

### Building for Production

```bash
cd docs-website
npm run build
npm run start
```

### Running Diagnostic Tools

```bash
# System health check
python3 troubleshooting/diagnostic-tools/system_health_check.py

# Connectivity test
python3 troubleshooting/diagnostic-tools/connectivity_test.py

# Performance analysis
python3 troubleshooting/diagnostic-tools/performance_analyzer.py
```

## 📖 Documentation Sections

### Getting Started
- [Quick Start Guide](tutorials/getting-started/quick-start.md)
- [Installation Instructions](tutorials/getting-started/installation.md)
- [First Workflow Tutorial](tutorials/getting-started/first-workflow.md)

### API Reference
- [Task Manager API](api-docs/openapi/task-manager.yaml)
- [Webhook Orchestrator API](api-docs/openapi/webhook-orchestrator.yaml)
- [Codegen Agent API](api-docs/openapi/codegen-agent.yaml)
- [Interactive API Explorer](docs-website/src/components/ApiExplorer.tsx)

### Deployment Guides
- [Local Development](deployment/scripts/deploy_local.sh)
- [AWS Deployment](deployment/scripts/deploy_aws.sh)
- [Kubernetes Deployment](deployment/kubernetes/)
- [Docker Compose](deployment/docker/docker-compose.dev.yml)

### Architecture
- [System Overview](architecture/system-design/overview.md)
- [Component Architecture](architecture/system-design/component-architecture.md)
- [Data Flow](architecture/system-design/data-flow.md)
- [Security Model](architecture/system-design/security-model.md)

### Troubleshooting
- [Common Issues](troubleshooting/common-issues/)
- [Diagnostic Tools](troubleshooting/diagnostic-tools/)
- [Recovery Procedures](troubleshooting/recovery-procedures/)

## 🔍 Health Monitoring

The system includes comprehensive health monitoring:

```bash
# Run full system health check
./troubleshooting/diagnostic-tools/system_health_check.py

# Check specific components
./troubleshooting/diagnostic-tools/connectivity_test.py --service task-manager

# Performance analysis
./troubleshooting/diagnostic-tools/performance_analyzer.py --duration 60
```

## 🚀 Deployment Options

### Local Development
```bash
./deployment/scripts/deploy_local.sh
```

### AWS Cloud
```bash
./deployment/scripts/deploy_aws.sh --region us-west-2 --environment production
```

### Google Cloud Platform
```bash
./deployment/scripts/deploy_gcp.sh --project my-project --zone us-central1-a
```

### Azure
```bash
./deployment/scripts/deploy_azure.sh --resource-group codegen-rg --location eastus
```

### Kubernetes
```bash
kubectl apply -f deployment/kubernetes/manifests/
```

## 🔐 Security

The platform includes enterprise-grade security features:

- **Authentication & Authorization** - JWT-based API security
- **Secrets Management** - Encrypted configuration and key storage
- **Network Security** - TLS encryption and network isolation
- **Audit Logging** - Comprehensive activity tracking
- **Vulnerability Scanning** - Automated security assessments

## 📊 Monitoring & Observability

Built-in monitoring stack includes:

- **Prometheus** - Metrics collection and alerting
- **Grafana** - Visualization and dashboards
- **Health Checks** - Automated service monitoring
- **Log Aggregation** - Centralized logging with structured data
- **Performance Metrics** - Response times, throughput, and resource usage

## 🤝 Contributing

We welcome contributions! Please see our [Contributing Guide](../CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests and documentation
5. Submit a pull request

### Documentation Updates

- Update relevant markdown files
- Test the documentation website locally
- Ensure all links work correctly
- Update API specifications if needed

## 📄 License

This project is licensed under the Apache 2.0 License - see the [LICENSE](../LICENSE) file for details.

## 🆘 Support

- **📖 Documentation**: Full documentation at http://localhost:8080
- **🐛 Issues**: Report bugs on [GitHub Issues](https://github.com/Zeeeepa/codegen-examples/issues)
- **💬 Community**: Join our [Discord community](https://discord.gg/codegen)
- **📧 Enterprise Support**: Contact support@codegen.sh

## 🗺️ Roadmap

### Upcoming Features

- **Multi-language SDKs** - Python, JavaScript, Go, and Rust clients
- **Advanced Workflows** - Visual workflow builder and templates
- **Enterprise Features** - SSO, RBAC, and compliance tools
- **AI Enhancements** - Improved agent capabilities and coordination
- **Performance Optimizations** - Caching, scaling, and efficiency improvements

### Version History

- **v1.0.0** - Initial release with core documentation and deployment
- **v1.1.0** - Enhanced API documentation and monitoring
- **v1.2.0** - Multi-cloud deployment support
- **v2.0.0** - Interactive tutorials and advanced troubleshooting

---

**Built with ❤️ by the Codegen Team**

For the latest updates and announcements, follow us on [Twitter](https://twitter.com/codegensh) and [LinkedIn](https://linkedin.com/company/codegen).

