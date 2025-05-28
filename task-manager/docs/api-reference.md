# Enhanced Task Manager MCP Server API Reference

## Overview

The Enhanced Task Manager MCP Server provides a comprehensive set of tools for intelligent task management, natural language processing, dependency analysis, and workflow automation. This document describes all available MCP tools and their usage.

## Available Tools

### Task Management

#### `create_task`

Create a new task with optional natural language parsing.

**Parameters:**
- `title` (string, required): Task title
- `description` (string, optional): Task description
- `natural_language_input` (string, optional): Natural language description for parsing
- `project_id` (string, optional): Project UUID
- `priority` (enum, optional): low | medium | high | critical (default: medium)
- `complexity` (enum, optional): simple | moderate | complex | epic (default: moderate)
- `estimated_hours` (number, optional): Estimated hours to complete
- `assignee` (string, optional): Task assignee
- `tags` (array, optional): Array of tag strings
- `due_date` (string, optional): ISO datetime string
- `auto_parse` (boolean, optional): Enable automatic NLP parsing (default: true)

**Example:**
```json
{
  "title": "Implement user authentication",
  "natural_language_input": "Create a secure login system with JWT tokens, password hashing, and email verification. Should integrate with our existing user database and support OAuth providers like Google and GitHub. High priority task that needs to be completed in 2 weeks.",
  "auto_parse": true
}
```

**Response:**
```json
{
  "success": true,
  "task": {
    "id": "uuid",
    "title": "Implement user authentication",
    "status": "pending",
    "priority": "high",
    "complexity": "complex",
    "estimated_hours": 40,
    "tags": ["authentication", "security", "backend"]
  },
  "parsed_requirements": {
    "acceptance_criteria": ["Secure login system", "JWT token support", "Email verification"],
    "technical_requirements": ["Password hashing", "OAuth integration"],
    "workflow_triggers": [{"type": "codegen", "config": {...}}]
  }
}
```

#### `update_task`

Update an existing task.

**Parameters:**
- `task_id` (string, required): Task UUID
- `title` (string, optional): New title
- `description` (string, optional): New description
- `status` (enum, optional): pending | in_progress | blocked | review | completed | cancelled | failed
- `priority` (enum, optional): low | medium | high | critical
- `complexity` (enum, optional): simple | moderate | complex | epic
- `estimated_hours` (number, optional): Updated estimate
- `actual_hours` (number, optional): Actual time spent
- `assignee` (string, optional): New assignee
- `tags` (array, optional): Updated tags
- `due_date` (string, optional): New due date

**Example:**
```json
{
  "task_id": "uuid",
  "status": "in_progress",
  "actual_hours": 15
}
```

#### `get_task`

Retrieve task details by ID.

**Parameters:**
- `task_id` (string, required): Task UUID

**Response:**
```json
{
  "success": true,
  "task": {
    "id": "uuid",
    "title": "Task title",
    "description": "Task description",
    "status": "in_progress",
    "priority": "high",
    "complexity": "moderate",
    "estimated_hours": 8,
    "actual_hours": 5,
    "assignee": "john.doe",
    "tags": ["frontend", "react"],
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-02T00:00:00Z",
    "due_date": "2024-01-15T00:00:00Z"
  },
  "dependencies": [
    {
      "id": "uuid",
      "depends_on_task_id": "uuid",
      "dependency_type": "blocks"
    }
  ]
}
```

#### `search_tasks`

Search and filter tasks.

**Parameters:**
- `query` (string, optional): Full-text search query
- `project_id` (string, optional): Filter by project
- `status` (string, optional): Filter by status
- `priority` (string, optional): Filter by priority
- `assignee` (string, optional): Filter by assignee
- `limit` (number, optional): Maximum results (default: 10)
- `offset` (number, optional): Pagination offset (default: 0)

**Example:**
```json
{
  "query": "authentication security",
  "status": "pending",
  "limit": 5
}
```

### Dependency Management

#### `add_dependency`

Add a dependency between tasks.

**Parameters:**
- `task_id` (string, required): Task that depends on another
- `depends_on_task_id` (string, required): Task that is depended upon
- `dependency_type` (string, optional): Type of dependency (default: "blocks")

**Example:**
```json
{
  "task_id": "uuid-task-a",
  "depends_on_task_id": "uuid-task-b",
  "dependency_type": "blocks"
}
```

#### `remove_dependency`

Remove a dependency between tasks.

**Parameters:**
- `task_id` (string, required): Task UUID
- `depends_on_task_id` (string, required): Dependency task UUID

#### `analyze_dependencies`

Analyze task dependencies and generate insights.

**Parameters:**
- `project_id` (string, optional): Analyze specific project (optional)

**Response:**
```json
{
  "success": true,
  "analysis": {
    "hasCycles": false,
    "cycles": [],
    "criticalPath": ["uuid1", "uuid2", "uuid3"],
    "parallelizable": [["uuid4", "uuid5"], ["uuid6", "uuid7"]],
    "bottlenecks": ["uuid2"],
    "estimatedDuration": 120,
    "riskFactors": [
      {
        "type": "single_point_of_failure",
        "severity": "high",
        "description": "Task blocks 5 other tasks",
        "affectedTasks": ["uuid2", "uuid8", "uuid9"]
      }
    ]
  },
  "graph_stats": {
    "nodes": 15,
    "edges": 23
  }
}
```

#### `get_ready_tasks`

Get tasks ready to start (no incomplete dependencies).

**Parameters:**
- `project_id` (string, optional): Filter by project
- `assignee` (string, optional): Filter by assignee

**Response:**
```json
{
  "success": true,
  "ready_tasks": [
    {
      "id": "uuid",
      "title": "Setup development environment",
      "priority": "high",
      "complexity": "simple",
      "estimated_hours": 4
    }
  ],
  "count": 1
}
```

#### `suggest_task_ordering`

Get suggested optimal task execution order.

**Parameters:**
- `project_id` (string, optional): Analyze specific project

**Response:**
```json
{
  "success": true,
  "suggested_order": [
    {
      "id": "uuid1",
      "title": "Setup database schema",
      "priority": "critical"
    },
    {
      "id": "uuid2", 
      "title": "Implement user model",
      "priority": "high"
    }
  ],
  "task_ids": ["uuid1", "uuid2", "uuid3"]
}
```

### Workflow Management

#### `create_workflow_trigger`

Create a workflow trigger for a task.

**Parameters:**
- `task_id` (string, required): Task UUID
- `trigger_type` (enum, required): codegen | claude_code | webhook | manual | scheduled
- `config` (object, required): Trigger-specific configuration

**Codegen Trigger Config:**
```json
{
  "task_id": "uuid",
  "trigger_type": "codegen",
  "config": {
    "auto_trigger": false,
    "review_required": true,
    "repository_url": "https://github.com/user/repo",
    "branch_name": "feature/auth",
    "target_files": ["src/auth/", "tests/auth/"],
    "agent_instructions": "Implement secure authentication with best practices",
    "timeout_minutes": 30
  }
}
```

**Claude Code Trigger Config:**
```json
{
  "task_id": "uuid",
  "trigger_type": "claude_code",
  "config": {
    "validation_type": "full",
    "auto_fix": true,
    "test_coverage_required": true,
    "security_scan": true,
    "performance_check": false
  }
}
```

**Webhook Trigger Config:**
```json
{
  "task_id": "uuid",
  "trigger_type": "webhook",
  "config": {
    "endpoint": "https://api.example.com/webhook",
    "method": "POST",
    "headers": {"X-API-Key": "secret"},
    "authentication": {
      "type": "bearer",
      "token": "bearer_token"
    }
  }
}
```

**Scheduled Trigger Config:**
```json
{
  "task_id": "uuid",
  "trigger_type": "scheduled",
  "config": {
    "cron_expression": "0 9 * * 1",
    "timezone": "UTC",
    "max_executions": 10
  }
}
```

#### `execute_workflow_trigger`

Execute a workflow trigger.

**Parameters:**
- `trigger_id` (string, required): Trigger UUID

**Response:**
```json
{
  "success": true,
  "result": {
    "success": true,
    "data": {
      "agent_id": "uuid",
      "task_url": "https://codegen.sh/tasks/uuid"
    },
    "execution_time_ms": 1500,
    "metadata": {
      "agent_id": "uuid",
      "task_url": "https://codegen.sh/tasks/uuid"
    }
  }
}
```

### Natural Language Processing

#### `parse_natural_language`

Parse natural language input into structured requirements.

**Parameters:**
- `input` (string, required): Natural language description
- `context` (object, optional): Additional parsing context

**Context Object:**
```json
{
  "project_context": "E-commerce platform development",
  "existing_tasks": [
    {"id": "uuid", "title": "Setup database", "description": "..."}
  ],
  "user_preferences": {
    "defaultPriority": "medium",
    "defaultComplexity": "moderate",
    "preferredWorkflows": ["codegen", "claude_code"]
  }
}
```

**Example:**
```json
{
  "input": "We need to build a shopping cart feature that allows users to add items, update quantities, and proceed to checkout. It should integrate with our payment system and send confirmation emails. This is urgent and needs to be done by next Friday.",
  "context": {
    "project_context": "E-commerce platform",
    "user_preferences": {
      "defaultPriority": "medium"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "parsed_requirements": {
    "title": "Build shopping cart feature",
    "description": "Shopping cart with add items, update quantities, checkout integration",
    "priority": "critical",
    "complexity": "complex",
    "estimated_hours": 32,
    "tags": ["frontend", "backend", "payment", "email"],
    "dependencies": [],
    "acceptance_criteria": [
      "Users can add items to cart",
      "Users can update quantities",
      "Checkout integration works",
      "Payment system integration",
      "Confirmation emails sent"
    ],
    "technical_requirements": [
      "Payment system integration",
      "Email service integration"
    ],
    "files_to_modify": [],
    "workflow_triggers": [
      {
        "type": "codegen",
        "config": {"auto_trigger": true, "review_required": true}
      }
    ]
  },
  "complexity_analysis": {
    "score": 75,
    "factors": {
      "description_length": 15,
      "technical_requirements": 20,
      "acceptance_criteria": 40
    },
    "recommendation": "complex"
  }
}
```

### Project Management

#### `create_project`

Create a new project.

**Parameters:**
- `name` (string, required): Project name
- `description` (string, optional): Project description
- `repository_url` (string, optional): Repository URL
- `branch_name` (string, optional): Default branch (default: "main")

**Example:**
```json
{
  "name": "E-commerce Platform",
  "description": "Modern e-commerce platform with React frontend and Node.js backend",
  "repository_url": "https://github.com/company/ecommerce",
  "branch_name": "main"
}
```

#### `list_projects`

List all projects.

**Response:**
```json
{
  "success": true,
  "projects": [
    {
      "id": "uuid",
      "name": "E-commerce Platform",
      "description": "Modern e-commerce platform",
      "repository_url": "https://github.com/company/ecommerce",
      "branch_name": "main",
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-02T00:00:00Z"
    }
  ],
  "count": 1
}
```

### Analytics

#### `get_task_statistics`

Get task statistics and analytics.

**Parameters:**
- `project_id` (string, optional): Filter by project

**Response:**
```json
{
  "success": true,
  "statistics": {
    "total": 50,
    "by_status": {
      "pending": 15,
      "in_progress": 10,
      "completed": 20,
      "blocked": 3,
      "cancelled": 2
    },
    "by_priority": {
      "low": 10,
      "medium": 25,
      "high": 12,
      "critical": 3
    },
    "by_complexity": {
      "simple": 20,
      "moderate": 18,
      "complex": 10,
      "epic": 2
    },
    "avg_completion_time": 24.5
  }
}
```

## Error Handling

All tools return errors in the standard MCP format:

```json
{
  "error": {
    "code": -32602,
    "message": "Invalid params",
    "data": {
      "details": "Task ID is required"
    }
  }
}
```

### Common Error Codes

- `-32600`: Invalid Request
- `-32601`: Method Not Found
- `-32602`: Invalid Params
- `-32603`: Internal Error

## Usage Examples

### Creating a Complex Task with Dependencies

```javascript
// 1. Create the main task
const mainTask = await callTool('create_task', {
  title: "Implement user dashboard",
  natural_language_input: "Create a comprehensive user dashboard with analytics, settings, and profile management. Should be responsive and accessible.",
  auto_parse: true
});

// 2. Create dependency tasks
const authTask = await callTool('create_task', {
  title: "Setup authentication system",
  priority: "critical"
});

// 3. Add dependency
await callTool('add_dependency', {
  task_id: mainTask.task.id,
  depends_on_task_id: authTask.task.id
});

// 4. Create workflow trigger
await callTool('create_workflow_trigger', {
  task_id: mainTask.task.id,
  trigger_type: "codegen",
  config: {
    auto_trigger: false,
    review_required: true,
    target_files: ["src/dashboard/", "src/components/dashboard/"]
  }
});
```

### Analyzing Project Dependencies

```javascript
// Get dependency analysis
const analysis = await callTool('analyze_dependencies', {
  project_id: "project-uuid"
});

// Get ready tasks
const readyTasks = await callTool('get_ready_tasks', {
  project_id: "project-uuid",
  assignee: "john.doe"
});

// Get suggested ordering
const ordering = await callTool('suggest_task_ordering', {
  project_id: "project-uuid"
});
```

### Natural Language Task Creation

```javascript
// Parse complex requirements
const parsed = await callTool('parse_natural_language', {
  input: "Build a real-time chat system with WebSocket support, message history, file sharing, and emoji reactions. Should handle 1000+ concurrent users and integrate with our existing user system.",
  context: {
    project_context: "Social media platform",
    user_preferences: {
      defaultPriority: "high",
      preferredWorkflows: ["codegen", "claude_code"]
    }
  }
});

// Create task from parsed requirements
const task = await callTool('create_task', {
  title: parsed.parsed_requirements.title,
  description: parsed.parsed_requirements.description,
  priority: parsed.parsed_requirements.priority,
  complexity: parsed.parsed_requirements.complexity,
  estimated_hours: parsed.parsed_requirements.estimated_hours,
  tags: parsed.parsed_requirements.tags,
  auto_parse: false // Already parsed
});
```

## Best Practices

1. **Use Natural Language Parsing**: Enable `auto_parse` for better task analysis
2. **Set Realistic Estimates**: Use the complexity analysis to guide time estimates
3. **Manage Dependencies**: Regularly analyze dependencies to avoid bottlenecks
4. **Monitor Workflows**: Set up appropriate triggers for automation
5. **Track Progress**: Use task statistics to monitor project health
6. **Plan Ahead**: Use suggested ordering to optimize task execution

## Rate Limits

- Task creation: 100 requests/minute
- Dependency analysis: 10 requests/minute
- Workflow triggers: 50 executions/hour
- Natural language parsing: 200 requests/hour

## Support

For API questions and issues:
- Check server logs for detailed error information
- Review the setup guide for configuration issues
- Submit bug reports with reproduction steps

