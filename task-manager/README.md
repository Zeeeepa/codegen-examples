# 🎛️ Enhanced Task Manager MCP Server

An intelligent task management system that extends the claude-task-master architecture with PostgreSQL integration, natural language processing, and Codegen workflow automation.

## ✨ Features

### 🧠 **Intelligent Task Management**
- **Natural Language Processing**: Convert plain English descriptions into structured tasks
- **Smart Priority & Complexity Analysis**: Automatic assessment based on content analysis
- **Dependency Graph Management**: Visual dependency tracking with cycle detection
- **Ready Task Detection**: Identify tasks ready to start based on dependencies

### 🔄 **Workflow Automation**
- **Codegen Integration**: Automatic code generation triggers
- **Claude Code Validation**: Automated code review and testing
- **Webhook Support**: Custom workflow integrations
- **Scheduled Tasks**: Cron-based task automation
- **Manual Approval Workflows**: Human-in-the-loop processes

### 📊 **Advanced Analytics**
- **Dependency Analysis**: Critical path, bottlenecks, and parallelization opportunities
- **Risk Assessment**: Identify potential project risks and blockers
- **Performance Metrics**: Task completion times and team productivity
- **Project Statistics**: Comprehensive reporting and insights

### 🔌 **MCP Protocol Support**
- **Multi-Editor Compatibility**: Works with Cursor, Windsurf, VS Code, and more
- **Real-time Communication**: Seamless integration with AI assistants
- **Extensible Tool Set**: 15+ specialized tools for task management

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- PostgreSQL 12+
- AI editor with MCP support

### Installation

1. **Clone and Install**
   ```bash
   git clone <repository-url>
   cd task-manager
   npm install
   ```

2. **Database Setup**
   ```bash
   # Create PostgreSQL database
   createdb task_manager
   
   # Run schema
   psql -d task_manager -f src/database/schema.sql
   ```

3. **Configuration**
   ```bash
   cp .env.example .env
   # Edit .env with your database and API credentials
   ```

4. **Build and Start**
   ```bash
   npm run build
   npm start
   ```

### MCP Configuration

Add to your AI editor's MCP configuration:

**Cursor** (`~/.cursor/mcp_servers.json`):
```json
{
  "mcpServers": {
    "enhanced-task-manager": {
      "command": "node",
      "args": ["/path/to/task-manager/dist/index.js"],
      "env": {
        "DATABASE_HOST": "localhost",
        "DATABASE_NAME": "task_manager",
        "DATABASE_USER": "your_user",
        "DATABASE_PASSWORD": "your_password",
        "CODEGEN_API_KEY": "your_codegen_key",
        "CLAUDE_CODE_API_KEY": "your_claude_code_key"
      }
    }
  }
}
```

## 🛠️ Usage Examples

### Creating Tasks with Natural Language

```
Create a task: "Build a user authentication system with JWT tokens, password hashing, and email verification. This is high priority and should integrate with our existing user database."
```

The system will automatically:
- Parse requirements into structured data
- Assign appropriate priority and complexity
- Extract technical requirements
- Suggest workflow triggers
- Identify potential dependencies

### Dependency Analysis

```
Analyze dependencies for the current project
```

Get insights on:
- Critical path identification
- Bottleneck detection
- Parallelizable task groups
- Risk factor assessment
- Estimated project duration

### Workflow Automation

```
Create a Codegen trigger for task "implement-auth" with auto-review enabled
```

Automatically trigger code generation when tasks are ready, with built-in review processes.

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   AI Editors    │    │   MCP Server     │    │   PostgreSQL    │
│                 │    │                  │    │                 │
│ • Cursor        │◄──►│ • Task Parser    │◄──►│ • Tasks         │
│ • Windsurf      │    │ • Dependency     │    │ • Dependencies  │
│ • VS Code       │    │   Analyzer       │    │ • Workflows     │
│ • Others        │    │ • Workflow       │    │ • Analytics     │
│                 │    │   Manager        │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │   External APIs  │
                       │                  │
                       │ • Codegen API    │
                       │ • Claude Code    │
                       │ • Webhooks       │
                       │ • Schedulers     │
                       └──────────────────┘
```

## 📚 Available Tools

### Task Management
- `create_task` - Create tasks with NLP parsing
- `update_task` - Update task properties
- `get_task` - Retrieve task details
- `search_tasks` - Search and filter tasks

### Dependency Management
- `add_dependency` - Create task dependencies
- `remove_dependency` - Remove dependencies
- `analyze_dependencies` - Comprehensive dependency analysis
- `get_ready_tasks` - Find tasks ready to start
- `suggest_task_ordering` - Optimal execution order

### Workflow Automation
- `create_workflow_trigger` - Setup automation triggers
- `execute_workflow_trigger` - Manual trigger execution

### Natural Language Processing
- `parse_natural_language` - Convert text to structured requirements

### Project Management
- `create_project` - Create new projects
- `list_projects` - List all projects
- `get_task_statistics` - Analytics and reporting

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_HOST` | PostgreSQL host | localhost |
| `DATABASE_PORT` | PostgreSQL port | 5432 |
| `DATABASE_NAME` | Database name | task_manager |
| `CODEGEN_API_KEY` | Codegen API key | - |
| `CLAUDE_CODE_API_KEY` | Claude Code API key | - |
| `LOG_LEVEL` | Logging level | info |

### Feature Flags

| Flag | Description | Default |
|------|-------------|---------|
| `AUTO_PARSE_NATURAL_LANGUAGE` | Enable automatic NLP | true |
| `ENABLE_WORKFLOW_TRIGGERS` | Enable automation | true |
| `ENABLE_DEPENDENCY_ANALYSIS` | Enable analysis | true |
| `MAX_TASKS_PER_PROJECT` | Task limit per project | 10000 |

## 🧪 Testing

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Run specific test file
npm test -- test-mcp-server.ts
```

## 📖 Documentation

- [Setup Guide](docs/mcp-setup.md) - Detailed installation and configuration
- [API Reference](docs/api-reference.md) - Complete tool documentation
- [Architecture Guide](docs/architecture.md) - System design and patterns

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: Submit bug reports and feature requests
- **Documentation**: Check the docs/ directory
- **Community**: Join our Discord/Slack for discussions

## 🔮 Roadmap

### v1.1 - Enhanced Intelligence
- [ ] Machine learning-based task estimation
- [ ] Automated dependency inference
- [ ] Smart task prioritization
- [ ] Team workload balancing

### v1.2 - Advanced Integrations
- [ ] Jira/Asana synchronization
- [ ] GitHub Issues integration
- [ ] Slack/Teams notifications
- [ ] Calendar integration

### v1.3 - Enterprise Features
- [ ] Multi-tenant support
- [ ] Advanced security controls
- [ ] Audit logging
- [ ] Performance monitoring

## 🏆 Key Benefits

### For Development Teams
- **Reduced Planning Overhead**: Natural language task creation
- **Better Coordination**: Visual dependency management
- **Automated Workflows**: Seamless CI/CD integration
- **Data-Driven Decisions**: Comprehensive analytics

### For Project Managers
- **Risk Mitigation**: Early bottleneck detection
- **Resource Optimization**: Parallel task identification
- **Progress Tracking**: Real-time project insights
- **Stakeholder Communication**: Clear dependency visualization

### For AI Assistants
- **Structured Context**: Rich task metadata for better assistance
- **Workflow Integration**: Seamless automation triggers
- **Natural Interaction**: Plain English task management
- **Extensible Platform**: Easy integration with existing tools

---

Built with ❤️ for the AI-powered development workflow ecosystem.

