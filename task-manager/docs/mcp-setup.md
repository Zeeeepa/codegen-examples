# Enhanced Task Manager MCP Server Setup Guide

## Overview

The Enhanced Task Manager MCP Server extends the claude-task-master architecture with PostgreSQL integration, natural language processing, and Codegen workflow triggers. This guide will help you set up and configure the server for use with AI editors like Cursor, Windsurf, and others.

## Prerequisites

- Node.js 18+ 
- PostgreSQL 12+
- npm or yarn package manager
- AI editor with MCP support (Cursor, Windsurf, etc.)

## Installation

### 1. Clone and Install Dependencies

```bash
git clone <repository-url>
cd task-manager
npm install
```

### 2. Database Setup

#### Create PostgreSQL Database

```sql
-- Connect to PostgreSQL as superuser
CREATE DATABASE task_manager;
CREATE USER task_manager_user WITH PASSWORD 'your_secure_password';
GRANT ALL PRIVILEGES ON DATABASE task_manager TO task_manager_user;
```

#### Initialize Database Schema

```bash
# Run the schema creation script
psql -h localhost -U task_manager_user -d task_manager -f src/database/schema.sql
```

### 3. Environment Configuration

Create a `.env` file in the task-manager directory:

```env
# Database Configuration
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=task_manager
DATABASE_USER=task_manager_user
DATABASE_PASSWORD=your_secure_password
DATABASE_SSL=false
DATABASE_MAX_CONNECTIONS=20
DATABASE_IDLE_TIMEOUT=30000
DATABASE_CONNECTION_TIMEOUT=2000

# Codegen API Configuration
CODEGEN_API_URL=https://api.codegen.sh
CODEGEN_API_KEY=your_codegen_api_key

# Claude Code API Configuration
CLAUDE_CODE_API_URL=https://api.claude-code.com
CLAUDE_CODE_API_KEY=your_claude_code_api_key

# Server Configuration
LOG_LEVEL=info
NODE_ENV=production
```

### 4. Build the Project

```bash
npm run build
```

## MCP Configuration

### For Cursor

Add the following to your Cursor MCP configuration file (`~/.cursor/mcp_servers.json`):

```json
{
  "mcpServers": {
    "enhanced-task-manager": {
      "command": "node",
      "args": ["/path/to/task-manager/dist/index.js"],
      "env": {
        "DATABASE_HOST": "localhost",
        "DATABASE_PORT": "5432",
        "DATABASE_NAME": "task_manager",
        "DATABASE_USER": "task_manager_user",
        "DATABASE_PASSWORD": "your_secure_password",
        "CODEGEN_API_URL": "https://api.codegen.sh",
        "CODEGEN_API_KEY": "your_codegen_api_key",
        "CLAUDE_CODE_API_URL": "https://api.claude-code.com",
        "CLAUDE_CODE_API_KEY": "your_claude_code_api_key"
      }
    }
  }
}
```

### For Windsurf

Add to your Windsurf configuration:

```json
{
  "mcp": {
    "servers": {
      "enhanced-task-manager": {
        "command": "node",
        "args": ["/path/to/task-manager/dist/index.js"],
        "env": {
          "DATABASE_HOST": "localhost",
          "DATABASE_PORT": "5432",
          "DATABASE_NAME": "task_manager",
          "DATABASE_USER": "task_manager_user",
          "DATABASE_PASSWORD": "your_secure_password",
          "CODEGEN_API_URL": "https://api.codegen.sh",
          "CODEGEN_API_KEY": "your_codegen_api_key",
          "CLAUDE_CODE_API_URL": "https://api.claude-code.com",
          "CLAUDE_CODE_API_KEY": "your_claude_code_api_key"
        }
      }
    }
  }
}
```

### For VS Code with MCP Extension

Add to your VS Code settings.json:

```json
{
  "mcp.servers": {
    "enhanced-task-manager": {
      "command": "node",
      "args": ["/path/to/task-manager/dist/index.js"],
      "env": {
        "DATABASE_HOST": "localhost",
        "DATABASE_PORT": "5432",
        "DATABASE_NAME": "task_manager",
        "DATABASE_USER": "task_manager_user",
        "DATABASE_PASSWORD": "your_secure_password",
        "CODEGEN_API_URL": "https://api.codegen.sh",
        "CODEGEN_API_KEY": "your_codegen_api_key",
        "CLAUDE_CODE_API_URL": "https://api.claude-code.com",
        "CLAUDE_CODE_API_KEY": "your_claude_code_api_key"
      }
    }
  }
}
```

## Testing the Setup

### 1. Test Database Connection

```bash
npm run test:db
```

### 2. Test MCP Server

```bash
# Start the server in development mode
npm run dev

# In another terminal, test with MCP client
echo '{"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}' | node dist/index.js
```

### 3. Test in AI Editor

Open your AI editor and try these commands:

```
Create a new task: "Implement user authentication with JWT tokens"
```

```
List all pending tasks
```

```
Analyze dependencies for project
```

## Configuration Options

### Database Configuration

- `DATABASE_HOST`: PostgreSQL host (default: localhost)
- `DATABASE_PORT`: PostgreSQL port (default: 5432)
- `DATABASE_NAME`: Database name
- `DATABASE_USER`: Database user
- `DATABASE_PASSWORD`: Database password
- `DATABASE_SSL`: Enable SSL connection (default: false)

### Workflow Configuration

- `CODEGEN_API_URL`: Codegen API endpoint
- `CODEGEN_API_KEY`: Codegen API key
- `CLAUDE_CODE_API_URL`: Claude Code API endpoint
- `CLAUDE_CODE_API_KEY`: Claude Code API key

### Server Configuration

- `LOG_LEVEL`: Logging level (error, warn, info, debug)
- `NODE_ENV`: Environment (development, production)

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify credentials and database exists
   - Check firewall settings

2. **MCP Server Not Starting**
   - Verify Node.js version (18+)
   - Check environment variables
   - Review logs in `logs/error.log`

3. **API Keys Invalid**
   - Verify Codegen API key is valid
   - Check Claude Code API access
   - Ensure proper permissions

### Debug Mode

Enable debug logging:

```env
LOG_LEVEL=debug
```

### Health Check

The server provides a health check endpoint:

```bash
curl http://localhost:3000/health
```

## Security Considerations

1. **Database Security**
   - Use strong passwords
   - Enable SSL in production
   - Restrict database access

2. **API Keys**
   - Store securely (use environment variables)
   - Rotate regularly
   - Limit permissions

3. **Network Security**
   - Use HTTPS in production
   - Configure firewalls
   - Monitor access logs

## Performance Tuning

### Database Optimization

```sql
-- Add indexes for better performance
CREATE INDEX CONCURRENTLY idx_tasks_status_priority ON tasks(status, priority);
CREATE INDEX CONCURRENTLY idx_tasks_assignee_status ON tasks(assignee, status);
```

### Connection Pooling

Adjust pool settings in configuration:

```env
DATABASE_MAX_CONNECTIONS=50
DATABASE_IDLE_TIMEOUT=60000
```

## Backup and Recovery

### Database Backup

```bash
# Create backup
pg_dump -h localhost -U task_manager_user task_manager > backup.sql

# Restore backup
psql -h localhost -U task_manager_user task_manager < backup.sql
```

### Configuration Backup

Backup your MCP configuration and environment files regularly.

## Support

For issues and questions:

1. Check the logs in `logs/` directory
2. Review the API documentation
3. Submit issues to the project repository
4. Join the community Discord/Slack

## Next Steps

- Review the [API Reference](api-reference.md)
- Explore advanced features
- Set up monitoring and alerting
- Configure automated backups

