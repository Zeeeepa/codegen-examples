# PostgreSQL Database Schema for AI-Powered Development Workflow System

This directory contains the complete database implementation for the AI-powered development workflow system, providing robust task storage, execution tracking, and PR management capabilities.

## 🏗️ Architecture Overview

The database schema is designed to support:

- **Task Management**: Flexible task storage with JSONB metadata
- **Execution Tracking**: Detailed execution history across multiple agent types
- **PR Lifecycle Management**: Complete pull request workflow tracking
- **Audit Trails**: Comprehensive logging of all workflow operations
- **High Availability**: Connection pooling, failover, and monitoring
- **Performance**: Advanced indexing and query optimization

## 📁 Directory Structure

```
database/
├── schema/                 # Database schema definitions
│   ├── 001_initial_schema.sql    # Core tables and types
│   ├── 002_indexes.sql           # Advanced indexing strategies
│   └── 003_constraints.sql       # Constraints and business logic
├── migrations/             # Migration and rollback tools
│   ├── migrate.py               # Migration execution system
│   └── rollback.py              # Safe rollback operations
├── config/                # Configuration and connection management
│   ├── database.py              # Connection pooling and management
│   ├── connection_pool.py       # Enterprise connection pooling
│   └── database.yaml            # Configuration settings
├── tests/                 # Comprehensive test suite
│   ├── test_schema.py           # Schema and constraint tests
│   └── test_performance.py     # Performance and scalability tests
└── README.md              # This documentation
```

## 🚀 Quick Start

### 1. Database Setup

```bash
# Create database
createdb workflow_db

# Run migrations
cd database/migrations
python migrate.py migrate --config ../config/database.yaml
```

### 2. Configuration

Copy and customize the configuration file:

```bash
cp database/config/database.yaml database/config/database.local.yaml
# Edit database.local.yaml with your settings
```

### 3. Initialize Connection Pool

```python
from database.config.database import get_database_manager

# Initialize database manager
db_manager = get_database_manager("database/config/database.local.yaml")
db_manager.initialize_sync()

# Get connection pool
pool = db_manager.get_sync_pool()

# Execute queries
result = pool.execute_query("SELECT COUNT(*) FROM tasks")
```

## 📊 Database Schema

### Core Tables

#### Projects
Stores top-level project information and repository details.

```sql
CREATE TABLE projects (
    id UUID PRIMARY KEY,
    name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    repository_url VARCHAR(500),
    repository_name VARCHAR(255),
    default_branch VARCHAR(100) DEFAULT 'main',
    settings JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Tasks
Core task management with flexible JSONB metadata.

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY,
    project_id UUID NOT NULL REFERENCES projects(id),
    parent_task_id UUID REFERENCES tasks(id),
    title VARCHAR(500) NOT NULL,
    description TEXT,
    status task_status DEFAULT 'pending',
    priority INTEGER DEFAULT 0,
    requirements JSONB DEFAULT '{}',
    dependencies JSONB DEFAULT '[]',
    context JSONB DEFAULT '{}',
    tags JSONB DEFAULT '[]',
    assigned_agent agent_type,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

#### Task Executions
Tracks individual execution attempts with detailed metrics.

```sql
CREATE TABLE task_executions (
    id UUID PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id),
    agent_type agent_type NOT NULL,
    execution_status execution_status DEFAULT 'queued',
    input_context JSONB DEFAULT '{}',
    output_results JSONB DEFAULT '{}',
    error_details JSONB DEFAULT '{}',
    started_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    memory_usage_mb INTEGER,
    cpu_time_ms INTEGER
);
```

#### Pull Requests
PR lifecycle management with validation tracking.

```sql
CREATE TABLE pull_requests (
    id UUID PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    project_id UUID NOT NULL REFERENCES projects(id),
    pr_number INTEGER,
    repository_url VARCHAR(500) NOT NULL,
    branch_name VARCHAR(255) NOT NULL,
    title VARCHAR(500) NOT NULL,
    status pr_status DEFAULT 'draft',
    validation_results JSONB DEFAULT '{}',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

### JSONB Schema Examples

#### Task Requirements
```json
{
  "type": "feature",
  "priority": 1,
  "complexity": "medium",
  "estimated_hours": 8,
  "dependencies": ["task_123", "external_api"],
  "acceptance_criteria": [
    "Implement user authentication",
    "Add input validation",
    "Write unit tests"
  ]
}
```

#### Execution Context
```json
{
  "agent_config": {
    "model": "gpt-4",
    "temperature": 0.7,
    "max_tokens": 4000
  },
  "files": ["src/auth.py", "tests/test_auth.py"],
  "repository": {
    "branch": "feature/auth",
    "commit": "abc123def456"
  },
  "environment": "development"
}
```

## 🔍 Advanced Features

### 1. JSONB Indexing and Queries

The schema includes advanced GIN indexes for efficient JSONB queries:

```sql
-- Query by requirement type
SELECT * FROM tasks WHERE requirements->>'type' = 'feature';

-- Query by tag containment
SELECT * FROM tasks WHERE tags ? 'frontend';

-- Complex containment queries
SELECT * FROM tasks WHERE requirements @> '{"type": "feature", "priority": 1}';
```

### 2. Full-Text Search

```sql
-- Search tasks by title and description
SELECT * FROM tasks WHERE to_tsvector('english', title || ' ' || description) 
@@ to_tsquery('english', 'authentication & security');
```

### 3. Performance Views

Pre-built views for common analytics:

```sql
-- Active tasks summary
SELECT * FROM active_tasks;

-- Task execution performance
SELECT * FROM task_execution_summary;

-- PR validation status
SELECT * FROM pr_validation_status;
```

## ⚡ Performance Optimization

### Indexing Strategy

1. **Primary Indexes**: Core foreign keys and status fields
2. **Composite Indexes**: Multi-column indexes for common query patterns
3. **JSONB Indexes**: GIN indexes for flexible JSON queries
4. **Partial Indexes**: Indexes on filtered subsets for efficiency
5. **Text Search Indexes**: Full-text search capabilities

### Query Optimization

- Use prepared statements for repeated queries
- Leverage connection pooling for concurrent access
- Monitor slow queries with built-in logging
- Regular VACUUM and ANALYZE operations

### Connection Pooling

The system includes enterprise-grade connection pooling with:

- Load balancing across multiple database endpoints
- Health checking and automatic failover
- Connection lifecycle management
- Performance monitoring and metrics

## 🔒 Security Features

### Data Protection

- SSL/TLS encryption for connections
- Parameterized queries to prevent SQL injection
- Role-based access control
- Audit logging for all operations

### Constraints and Validation

- Business logic enforcement through triggers
- Data integrity constraints
- JSONB schema validation
- Circular dependency prevention

## 📈 Monitoring and Maintenance

### Health Monitoring

```python
# Check database health
health_status = db_manager.health_check()
print(health_status)

# Get performance statistics
stats = db_manager.get_comprehensive_stats()
print(f"Total queries: {stats['sync_pool']['queries_executed']}")
```

### Maintenance Operations

```bash
# Run database migrations
python migrate.py migrate

# Check migration status
python migrate.py status

# Rollback to specific version
python rollback.py rollback --version 001

# Clean up old data
python cleanup.py --days 90
```

## 🧪 Testing

### Schema Tests

```bash
# Run schema integrity tests
pytest database/tests/test_schema.py -v
```

### Performance Tests

```bash
# Run performance benchmarks
pytest database/tests/test_performance.py -v -s
```

### Load Testing

```bash
# Run concurrent access tests
pytest database/tests/test_performance.py::TestDatabasePerformance::test_concurrent_access_performance -v
```

## 🔧 Configuration

### Environment Variables

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=workflow_db
export DB_USER=postgres
export DB_PASSWORD=your_password
export DB_SSL_MODE=prefer
export DB_MIN_CONNECTIONS=5
export DB_MAX_CONNECTIONS=20
```

### YAML Configuration

See `database/config/database.yaml` for comprehensive configuration options including:

- Connection settings
- Performance tuning
- High availability setup
- Monitoring configuration
- Security settings

## 🚨 Troubleshooting

### Common Issues

1. **Connection Pool Exhaustion**
   ```python
   # Monitor pool usage
   stats = pool.get_stats()
   print(f"Active connections: {stats['active_connections']}")
   ```

2. **Slow Queries**
   ```sql
   -- Check slow query log
   SELECT query, mean_time, calls FROM pg_stat_statements 
   ORDER BY mean_time DESC LIMIT 10;
   ```

3. **Index Usage**
   ```sql
   -- Check index usage
   SELECT * FROM index_usage_stats WHERE usage_category = 'UNUSED';
   ```

### Performance Tuning

1. **Analyze Query Plans**
   ```sql
   EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM tasks WHERE status = 'pending';
   ```

2. **Update Statistics**
   ```sql
   ANALYZE tasks;
   ```

3. **Vacuum Operations**
   ```sql
   VACUUM ANALYZE tasks;
   ```

## 📚 Additional Resources

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [JSONB Performance Tips](https://www.postgresql.org/docs/current/datatype-json.html)
- [Connection Pooling Best Practices](https://wiki.postgresql.org/wiki/Number_Of_Database_Connections)
- [Index Optimization Guide](https://www.postgresql.org/docs/current/indexes.html)

## 🤝 Contributing

When contributing to the database schema:

1. **Always create migrations** for schema changes
2. **Add appropriate indexes** for new query patterns
3. **Include tests** for new functionality
4. **Update documentation** for schema changes
5. **Consider performance impact** of changes

## 📄 License

This database schema is part of the AI-Powered Development Workflow System and follows the same licensing terms as the main project.

