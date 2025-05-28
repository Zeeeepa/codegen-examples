#!/bin/bash

# Codegen AI Workflow Platform - Local Deployment Script
# This script sets up the complete platform locally using Docker Compose

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
PLATFORM_NAME="codegen-ai-platform"
COMPOSE_FILE="docker-compose.dev.yml"
ENV_FILE=".env.local"
DATA_DIR="./data"
LOGS_DIR="./logs"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to check prerequisites
check_prerequisites() {
    print_status "Checking prerequisites..."
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null && ! docker compose version &> /dev/null; then
        print_error "Docker Compose is not installed. Please install Docker Compose first."
        exit 1
    fi
    
    # Check if Docker daemon is running
    if ! docker info &> /dev/null; then
        print_error "Docker daemon is not running. Please start Docker first."
        exit 1
    fi
    
    print_success "All prerequisites met"
}

# Function to create necessary directories
create_directories() {
    print_status "Creating necessary directories..."
    
    mkdir -p "$DATA_DIR"/{postgres,redis,minio}
    mkdir -p "$LOGS_DIR"/{task-manager,webhook-orchestrator,codegen-agent,monitoring}
    
    print_success "Directories created"
}

# Function to generate environment file
generate_env_file() {
    print_status "Generating environment configuration..."
    
    if [[ -f "$ENV_FILE" ]]; then
        print_warning "Environment file already exists. Backing up..."
        cp "$ENV_FILE" "${ENV_FILE}.backup.$(date +%s)"
    fi
    
    cat > "$ENV_FILE" << EOF
# Codegen AI Workflow Platform - Local Environment Configuration
# Generated on $(date)

# Application Settings
ENVIRONMENT=local
DEBUG=true
LOG_LEVEL=info

# Database Configuration
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=codegen_platform
POSTGRES_USER=codegen
POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Redis Configuration
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=$(openssl rand -base64 32)

# MinIO Configuration (S3-compatible storage)
MINIO_HOST=minio
MINIO_PORT=9000
MINIO_ACCESS_KEY=codegen-access-key
MINIO_SECRET_KEY=$(openssl rand -base64 32)
MINIO_BUCKET=codegen-platform

# Task Manager Configuration
TASK_MANAGER_HOST=task-manager
TASK_MANAGER_PORT=8001
TASK_MANAGER_WORKERS=4

# Webhook Orchestrator Configuration
WEBHOOK_ORCHESTRATOR_HOST=webhook-orchestrator
WEBHOOK_ORCHESTRATOR_PORT=8002
WEBHOOK_SECRET=$(openssl rand -base64 32)

# Codegen Agent Configuration
CODEGEN_AGENT_HOST=codegen-agent
CODEGEN_AGENT_PORT=8003
CODEGEN_API_KEY=your-codegen-api-key-here

# Claude Code Configuration
CLAUDE_API_KEY=your-claude-api-key-here
CLAUDE_MODEL=claude-3-sonnet-20240229

# GitHub Integration
GITHUB_APP_ID=your-github-app-id
GITHUB_PRIVATE_KEY_PATH=/app/secrets/github-private-key.pem
GITHUB_WEBHOOK_SECRET=$(openssl rand -base64 32)

# Monitoring Configuration
PROMETHEUS_PORT=9090
GRAFANA_PORT=3000
GRAFANA_ADMIN_PASSWORD=$(openssl rand -base64 16)

# Security
JWT_SECRET=$(openssl rand -base64 64)
ENCRYPTION_KEY=$(openssl rand -base64 32)

# Network Configuration
PLATFORM_NETWORK=codegen-platform-network
EXTERNAL_PORT_TASK_MANAGER=8001
EXTERNAL_PORT_WEBHOOK_ORCHESTRATOR=8002
EXTERNAL_PORT_CODEGEN_AGENT=8003
EXTERNAL_PORT_DOCS=8080
EXTERNAL_PORT_GRAFANA=3000
EXTERNAL_PORT_PROMETHEUS=9090
EOF
    
    print_success "Environment file generated: $ENV_FILE"
    print_warning "Please update the API keys in $ENV_FILE before proceeding"
}

# Function to create Docker Compose file
create_compose_file() {
    print_status "Creating Docker Compose configuration..."
    
    cat > "$COMPOSE_FILE" << 'EOF'
version: '3.8'

services:
  # PostgreSQL Database
  postgres:
    image: postgres:15-alpine
    container_name: codegen-postgres
    environment:
      POSTGRES_DB: ${POSTGRES_DB}
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./deployment/configs/postgres/init.sql:/docker-entrypoint-initdb.d/init.sql
    ports:
      - "5432:5432"
    networks:
      - codegen-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Redis Cache
  redis:
    image: redis:7-alpine
    container_name: codegen-redis
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - ./data/redis:/data
    ports:
      - "6379:6379"
    networks:
      - codegen-network
    healthcheck:
      test: ["CMD", "redis-cli", "--raw", "incr", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # MinIO S3-compatible storage
  minio:
    image: minio/minio:latest
    container_name: codegen-minio
    command: server /data --console-address ":9001"
    environment:
      MINIO_ACCESS_KEY: ${MINIO_ACCESS_KEY}
      MINIO_SECRET_KEY: ${MINIO_SECRET_KEY}
    volumes:
      - ./data/minio:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    networks:
      - codegen-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 20s
      retries: 3

  # Task Manager Service
  task-manager:
    build:
      context: ../../
      dockerfile: deployment/docker/Dockerfiles/task-manager.Dockerfile
    container_name: codegen-task-manager
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
      - LOG_LEVEL=${LOG_LEVEL}
    volumes:
      - ./logs/task-manager:/app/logs
      - ./deployment/configs/task-manager:/app/config
    ports:
      - "${EXTERNAL_PORT_TASK_MANAGER}:8001"
    networks:
      - codegen-network
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8001/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Webhook Orchestrator Service
  webhook-orchestrator:
    build:
      context: ../../
      dockerfile: deployment/docker/Dockerfiles/webhook-orchestrator.Dockerfile
    container_name: codegen-webhook-orchestrator
    environment:
      - DATABASE_URL=postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@postgres:5432/${POSTGRES_DB}
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379
      - WEBHOOK_SECRET=${WEBHOOK_SECRET}
      - TASK_MANAGER_URL=http://task-manager:8001
    volumes:
      - ./logs/webhook-orchestrator:/app/logs
      - ./deployment/configs/webhook-orchestrator:/app/config
    ports:
      - "${EXTERNAL_PORT_WEBHOOK_ORCHESTRATOR}:8002"
    networks:
      - codegen-network
    depends_on:
      task-manager:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8002/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Codegen Agent Service
  codegen-agent:
    build:
      context: ../../
      dockerfile: deployment/docker/Dockerfiles/codegen-agent.Dockerfile
    container_name: codegen-codegen-agent
    environment:
      - CODEGEN_API_KEY=${CODEGEN_API_KEY}
      - CLAUDE_API_KEY=${CLAUDE_API_KEY}
      - TASK_MANAGER_URL=http://task-manager:8001
      - WEBHOOK_ORCHESTRATOR_URL=http://webhook-orchestrator:8002
    volumes:
      - ./logs/codegen-agent:/app/logs
      - ./deployment/configs/codegen-agent:/app/config
    ports:
      - "${EXTERNAL_PORT_CODEGEN_AGENT}:8003"
    networks:
      - codegen-network
    depends_on:
      webhook-orchestrator:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8003/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Documentation Website
  docs-website:
    build:
      context: ../../documentation-system/docs-website
      dockerfile: ../../deployment/docker/Dockerfiles/docs-website.Dockerfile
    container_name: codegen-docs
    ports:
      - "${EXTERNAL_PORT_DOCS}:3000"
    networks:
      - codegen-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Prometheus Monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: codegen-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--web.console.libraries=/etc/prometheus/console_libraries'
      - '--web.console.templates=/etc/prometheus/consoles'
      - '--web.enable-lifecycle'
    volumes:
      - ./deployment/configs/monitoring-configs/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./data/prometheus:/prometheus
    ports:
      - "${EXTERNAL_PORT_PROMETHEUS}:9090"
    networks:
      - codegen-network

  # Grafana Dashboard
  grafana:
    image: grafana/grafana:latest
    container_name: codegen-grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
    volumes:
      - ./data/grafana:/var/lib/grafana
      - ./deployment/configs/monitoring-configs/grafana:/etc/grafana/provisioning
    ports:
      - "${EXTERNAL_PORT_GRAFANA}:3000"
    networks:
      - codegen-network
    depends_on:
      - prometheus

networks:
  codegen-network:
    driver: bridge
    name: ${PLATFORM_NETWORK}

volumes:
  postgres_data:
  redis_data:
  minio_data:
  prometheus_data:
  grafana_data:
EOF
    
    print_success "Docker Compose file created: $COMPOSE_FILE"
}

# Function to start services
start_services() {
    print_status "Starting Codegen AI Workflow Platform..."
    
    # Pull latest images
    print_status "Pulling Docker images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" pull
    
    # Build custom images
    print_status "Building custom images..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" build
    
    # Start services
    print_status "Starting services..."
    docker-compose -f "$COMPOSE_FILE" --env-file "$ENV_FILE" up -d
    
    # Wait for services to be healthy
    print_status "Waiting for services to be ready..."
    sleep 30
    
    # Check service health
    check_service_health
}

# Function to check service health
check_service_health() {
    print_status "Checking service health..."
    
    services=("postgres" "redis" "minio" "task-manager" "webhook-orchestrator" "codegen-agent" "docs-website")
    
    for service in "${services[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up (healthy)"; then
            print_success "$service is healthy"
        else
            print_warning "$service is not healthy yet"
        fi
    done
}

# Function to display access information
display_access_info() {
    print_success "Codegen AI Workflow Platform is running!"
    echo
    echo "Access URLs:"
    echo "  📚 Documentation:        http://localhost:8080"
    echo "  🔧 Task Manager API:     http://localhost:8001"
    echo "  🔗 Webhook Orchestrator: http://localhost:8002"
    echo "  🤖 Codegen Agent:        http://localhost:8003"
    echo "  📊 Grafana Dashboard:    http://localhost:3000 (admin/$(grep GRAFANA_ADMIN_PASSWORD $ENV_FILE | cut -d'=' -f2))"
    echo "  📈 Prometheus:           http://localhost:9090"
    echo "  💾 MinIO Console:        http://localhost:9001"
    echo
    echo "Useful commands:"
    echo "  View logs:     docker-compose -f $COMPOSE_FILE logs -f [service-name]"
    echo "  Stop platform: docker-compose -f $COMPOSE_FILE down"
    echo "  Restart:       docker-compose -f $COMPOSE_FILE restart [service-name]"
    echo
    print_warning "Remember to update API keys in $ENV_FILE for full functionality"
}

# Function to show usage
show_usage() {
    echo "Usage: $0 [OPTIONS]"
    echo
    echo "Options:"
    echo "  -h, --help     Show this help message"
    echo "  --stop         Stop the platform"
    echo "  --restart      Restart the platform"
    echo "  --logs         Show logs for all services"
    echo "  --status       Show status of all services"
    echo "  --clean        Stop and remove all containers, networks, and volumes"
    echo
}

# Function to stop services
stop_services() {
    print_status "Stopping Codegen AI Workflow Platform..."
    docker-compose -f "$COMPOSE_FILE" down
    print_success "Platform stopped"
}

# Function to restart services
restart_services() {
    print_status "Restarting Codegen AI Workflow Platform..."
    docker-compose -f "$COMPOSE_FILE" restart
    print_success "Platform restarted"
}

# Function to show logs
show_logs() {
    docker-compose -f "$COMPOSE_FILE" logs -f
}

# Function to show status
show_status() {
    docker-compose -f "$COMPOSE_FILE" ps
}

# Function to clean up
clean_up() {
    print_warning "This will remove all containers, networks, and volumes. Are you sure? (y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        print_status "Cleaning up..."
        docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
        docker system prune -f
        print_success "Cleanup completed"
    else
        print_status "Cleanup cancelled"
    fi
}

# Main execution
main() {
    case "${1:-}" in
        -h|--help)
            show_usage
            exit 0
            ;;
        --stop)
            stop_services
            exit 0
            ;;
        --restart)
            restart_services
            exit 0
            ;;
        --logs)
            show_logs
            exit 0
            ;;
        --status)
            show_status
            exit 0
            ;;
        --clean)
            clean_up
            exit 0
            ;;
        "")
            # Default: deploy
            ;;
        *)
            print_error "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
    
    print_status "Starting Codegen AI Workflow Platform local deployment..."
    
    check_prerequisites
    create_directories
    generate_env_file
    create_compose_file
    start_services
    display_access_info
}

# Run main function with all arguments
main "$@"

