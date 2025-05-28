# PostgreSQL Database Optimization Guide

This guide provides comprehensive optimization strategies for the AI-powered development workflow database, covering performance tuning, scalability, and operational best practices.

## 🎯 Performance Optimization Strategies

### 1. Advanced Indexing Strategies

#### JSONB Query Optimization

```sql
-- Create specialized indexes for common JSONB query patterns
CREATE INDEX idx_tasks_requirements_type_priority ON tasks 
USING gin ((requirements->'type'), (requirements->'priority'));

-- Composite JSONB indexes for complex queries
CREATE INDEX idx_tasks_context_files_branch ON tasks 
USING gin ((context->'files'), (context->'repository'->'branch'));

-- Expression indexes for computed values
CREATE INDEX idx_tasks_estimated_completion ON tasks 
((created_at + (requirements->>'estimated_hours')::interval));
```

#### Partial Indexes for Hot Data

```sql
-- Index only active tasks for faster dashboard queries
CREATE INDEX idx_tasks_active_priority ON tasks (priority DESC, created_at DESC) 
WHERE status IN ('pending', 'in_progress', 'validation');

-- Index recent executions for monitoring
CREATE INDEX idx_executions_recent_performance ON task_executions 
(agent_type, execution_status, duration) 
WHERE completed_at > NOW() - INTERVAL '7 days';

-- Index failed items for debugging
CREATE INDEX idx_validations_recent_failures ON validations 
(validation_type, pr_id, completed_at DESC) 
WHERE result = 'failed' AND completed_at > NOW() - INTERVAL '24 hours';
```

#### Covering Indexes

```sql
-- Include frequently accessed columns in indexes
CREATE INDEX idx_tasks_project_status_covering ON tasks 
(project_id, status) INCLUDE (title, priority, assigned_agent, updated_at);

-- Covering index for execution summaries
CREATE INDEX idx_executions_task_covering ON task_executions 
(task_id, execution_status) INCLUDE (agent_type, duration, memory_usage_mb);
```

### 2. Partitioning Strategies

#### Time-Based Partitioning for Large Tables

```sql
-- Partition workflow_events by month
CREATE TABLE workflow_events_partitioned (
    LIKE workflow_events INCLUDING ALL
) PARTITION BY RANGE (occurred_at);

-- Create monthly partitions
CREATE TABLE workflow_events_2024_01 PARTITION OF workflow_events_partitioned
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE workflow_events_2024_02 PARTITION OF workflow_events_partitioned
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

-- Automatic partition creation function
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    end_date date;
BEGIN
    partition_name := table_name || '_' || to_char(start_date, 'YYYY_MM');
    end_date := start_date + interval '1 month';
    
    EXECUTE format('CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;
```

#### Hash Partitioning for High-Volume Tables

```sql
-- Partition task_executions by hash for even distribution
CREATE TABLE task_executions_partitioned (
    LIKE task_executions INCLUDING ALL
) PARTITION BY HASH (task_id);

-- Create hash partitions
CREATE TABLE task_executions_p0 PARTITION OF task_executions_partitioned
FOR VALUES WITH (modulus 4, remainder 0);

CREATE TABLE task_executions_p1 PARTITION OF task_executions_partitioned
FOR VALUES WITH (modulus 4, remainder 1);

CREATE TABLE task_executions_p2 PARTITION OF task_executions_partitioned
FOR VALUES WITH (modulus 4, remainder 2);

CREATE TABLE task_executions_p3 PARTITION OF task_executions_partitioned
FOR VALUES WITH (modulus 4, remainder 3);
```

### 3. Query Optimization Techniques

#### Optimized Aggregation Queries

```sql
-- Use window functions for running totals
SELECT 
    project_id,
    created_at::date as date,
    COUNT(*) as daily_tasks,
    SUM(COUNT(*)) OVER (PARTITION BY project_id ORDER BY created_at::date) as cumulative_tasks
FROM tasks
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY project_id, created_at::date
ORDER BY project_id, date;

-- Efficient percentile calculations
SELECT 
    agent_type,
    percentile_cont(0.5) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM duration)) as median_duration,
    percentile_cont(0.95) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM duration)) as p95_duration,
    percentile_cont(0.99) WITHIN GROUP (ORDER BY EXTRACT(EPOCH FROM duration)) as p99_duration
FROM task_executions
WHERE execution_status = 'completed' AND completed_at > NOW() - INTERVAL '7 days'
GROUP BY agent_type;
```

#### Materialized Views for Complex Analytics

```sql
-- Daily task metrics materialized view
CREATE MATERIALIZED VIEW daily_task_metrics AS
SELECT 
    date_trunc('day', created_at) as date,
    project_id,
    COUNT(*) as tasks_created,
    COUNT(CASE WHEN status = 'completed' THEN 1 END) as tasks_completed,
    AVG(priority) as avg_priority,
    COUNT(CASE WHEN assigned_agent = 'codegen' THEN 1 END) as codegen_tasks,
    COUNT(CASE WHEN assigned_agent = 'claude_code' THEN 1 END) as claude_tasks
FROM tasks
GROUP BY date_trunc('day', created_at), project_id;

-- Create unique index for concurrent refresh
CREATE UNIQUE INDEX idx_daily_task_metrics_date_project 
ON daily_task_metrics (date, project_id);

-- Refresh schedule (run via cron)
-- 0 1 * * * psql -d workflow_db -c "REFRESH MATERIALIZED VIEW CONCURRENTLY daily_task_metrics;"
```

### 4. Connection Pool Optimization

#### Advanced Pool Configuration

```python
# High-performance connection pool setup
from database.config.connection_pool import EnterpriseConnectionPool, DatabaseEndpoint

# Master-replica configuration
master_endpoint = DatabaseEndpoint(
    host="master-db.example.com",
    port=5432,
    database="workflow_db",
    username="app_user",
    password="secure_password",
    is_read_only=False,
    priority=1,
    weight=1,
    max_connections=20
)

replica_endpoints = [
    DatabaseEndpoint(
        host="replica1-db.example.com",
        port=5432,
        database="workflow_db",
        username="app_user",
        password="secure_password",
        is_read_only=True,
        priority=2,
        weight=2,
        max_connections=15
    ),
    DatabaseEndpoint(
        host="replica2-db.example.com",
        port=5432,
        database="workflow_db",
        username="app_user",
        password="secure_password",
        is_read_only=True,
        priority=2,
        weight=1,
        max_connections=15
    )
]

# Create enterprise pool with load balancing
pool = EnterpriseConnectionPool(
    endpoints=[master_endpoint] + replica_endpoints,
    min_connections_per_endpoint=3,
    max_connections_per_endpoint=20,
    load_balancing_strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
    health_check_interval=30,
    retry_attempts=3,
    retry_delay=1.0
)

pool.initialize()
```

## 🏗️ High Availability Configuration

### 1. Replication Setup

#### Streaming Replication Configuration

```bash
# Primary server postgresql.conf
wal_level = replica
max_wal_senders = 3
max_replication_slots = 3
synchronous_commit = on
synchronous_standby_names = 'replica1,replica2'

# Replica server postgresql.conf
hot_standby = on
max_standby_streaming_delay = 30s
wal_receiver_status_interval = 10s
hot_standby_feedback = on
```

#### Automatic Failover with Patroni

```yaml
# patroni.yml configuration
scope: workflow-cluster
namespace: /workflow/
name: workflow-db-1

restapi:
  listen: 0.0.0.0:8008
  connect_address: 10.0.1.10:8008

etcd:
  hosts: 10.0.1.20:2379,10.0.1.21:2379,10.0.1.22:2379

bootstrap:
  dcs:
    ttl: 30
    loop_wait: 10
    retry_timeout: 30
    maximum_lag_on_failover: 1048576
    postgresql:
      use_pg_rewind: true
      parameters:
        max_connections: 100
        shared_buffers: 256MB
        effective_cache_size: 1GB
        maintenance_work_mem: 64MB
        checkpoint_completion_target: 0.7
        wal_buffers: 16MB
        default_statistics_target: 100
        random_page_cost: 1.1
        effective_io_concurrency: 200

postgresql:
  listen: 0.0.0.0:5432
  connect_address: 10.0.1.10:5432
  data_dir: /var/lib/postgresql/data
  pgpass: /tmp/pgpass
  authentication:
    replication:
      username: replicator
      password: repl_password
    superuser:
      username: postgres
      password: postgres_password
```

### 2. Load Balancing with PgBouncer

```ini
# pgbouncer.ini
[databases]
workflow_db = host=localhost port=5432 dbname=workflow_db
workflow_db_ro = host=replica1.example.com port=5432 dbname=workflow_db

[pgbouncer]
listen_port = 6432
listen_addr = *
auth_type = md5
auth_file = /etc/pgbouncer/userlist.txt
logfile = /var/log/pgbouncer/pgbouncer.log
pidfile = /var/run/pgbouncer/pgbouncer.pid
admin_users = admin
stats_users = stats, admin

# Connection pooling
pool_mode = transaction
max_client_conn = 100
default_pool_size = 20
min_pool_size = 5
reserve_pool_size = 5
reserve_pool_timeout = 5
max_db_connections = 50
max_user_connections = 50

# Performance tuning
server_reset_query = DISCARD ALL
server_check_query = SELECT 1
server_check_delay = 30
```

## 📊 Performance Monitoring Setup

### 1. PostgreSQL Statistics Collection

```sql
-- Enable pg_stat_statements extension
CREATE EXTENSION IF NOT EXISTS pg_stat_statements;

-- Configure in postgresql.conf
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.max = 10000
pg_stat_statements.track = all
pg_stat_statements.track_utility = on
pg_stat_statements.save = on

-- Query performance monitoring view
CREATE VIEW slow_queries AS
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    stddev_time,
    rows,
    100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0) AS hit_percent
FROM pg_stat_statements
WHERE mean_time > 100  -- Queries taking more than 100ms on average
ORDER BY mean_time DESC;
```

### 2. Custom Monitoring Functions

```sql
-- Database health check function
CREATE OR REPLACE FUNCTION database_health_check()
RETURNS TABLE(
    metric_name text,
    metric_value numeric,
    status text,
    threshold numeric
) AS $$
BEGIN
    -- Connection usage
    RETURN QUERY
    SELECT 
        'active_connections'::text,
        (SELECT count(*) FROM pg_stat_activity WHERE state = 'active')::numeric,
        CASE WHEN (SELECT count(*) FROM pg_stat_activity WHERE state = 'active') > 50 
             THEN 'WARNING' ELSE 'OK' END::text,
        50::numeric;
    
    -- Database size
    RETURN QUERY
    SELECT 
        'database_size_mb'::text,
        (pg_database_size(current_database()) / 1024 / 1024)::numeric,
        CASE WHEN (pg_database_size(current_database()) / 1024 / 1024) > 10000 
             THEN 'WARNING' ELSE 'OK' END::text,
        10000::numeric;
    
    -- Slow queries
    RETURN QUERY
    SELECT 
        'slow_queries_count'::text,
        (SELECT count(*) FROM pg_stat_statements WHERE mean_time > 1000)::numeric,
        CASE WHEN (SELECT count(*) FROM pg_stat_statements WHERE mean_time > 1000) > 10 
             THEN 'WARNING' ELSE 'OK' END::text,
        10::numeric;
    
    -- Cache hit ratio
    RETURN QUERY
    SELECT 
        'cache_hit_ratio'::text,
        (SELECT 100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)) 
         FROM pg_stat_database WHERE datname = current_database())::numeric,
        CASE WHEN (SELECT 100.0 * sum(blks_hit) / (sum(blks_hit) + sum(blks_read)) 
                   FROM pg_stat_database WHERE datname = current_database()) < 95 
             THEN 'WARNING' ELSE 'OK' END::text,
        95::numeric;
END;
$$ LANGUAGE plpgsql;
```

### 3. Alerting Setup

```python
# Database monitoring script
import psycopg2
import smtplib
from email.mime.text import MIMEText
from datetime import datetime

def check_database_health():
    """Check database health and send alerts if needed"""
    conn = psycopg2.connect(
        host="localhost",
        database="workflow_db",
        user="monitor_user",
        password="monitor_password"
    )
    
    with conn.cursor() as cursor:
        cursor.execute("SELECT * FROM database_health_check()")
        metrics = cursor.fetchall()
        
        alerts = []
        for metric_name, metric_value, status, threshold in metrics:
            if status == 'WARNING':
                alerts.append(f"{metric_name}: {metric_value} (threshold: {threshold})")
        
        if alerts:
            send_alert("Database Health Warning", "\n".join(alerts))
    
    conn.close()

def send_alert(subject, message):
    """Send email alert"""
    msg = MIMEText(message)
    msg['Subject'] = f"[DB Alert] {subject}"
    msg['From'] = "db-monitor@example.com"
    msg['To'] = "admin@example.com"
    
    smtp = smtplib.SMTP('localhost')
    smtp.send_message(msg)
    smtp.quit()

if __name__ == "__main__":
    check_database_health()
```

## 🧹 Data Archival and Cleanup

### 1. Automated Data Archival

```sql
-- Archive old completed tasks
CREATE OR REPLACE FUNCTION archive_old_tasks()
RETURNS integer AS $$
DECLARE
    archived_count integer;
BEGIN
    -- Archive tasks completed more than 90 days ago
    WITH archived_tasks AS (
        DELETE FROM tasks 
        WHERE status = 'completed' 
        AND completed_at < NOW() - INTERVAL '90 days'
        RETURNING *
    )
    INSERT INTO tasks_archive SELECT * FROM archived_tasks;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    
    -- Log archival operation
    INSERT INTO workflow_events (
        event_type, event_category, action, description, event_data
    ) VALUES (
        'data_archival', 'system', 'archive_tasks',
        'Archived old completed tasks',
        jsonb_build_object('archived_count', archived_count)
    );
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- Schedule via cron: 0 2 * * 0 (weekly on Sunday at 2 AM)
```

### 2. Partition Maintenance

```sql
-- Automatic partition management
CREATE OR REPLACE FUNCTION maintain_partitions()
RETURNS void AS $$
DECLARE
    current_month date;
    next_month date;
    partition_name text;
BEGIN
    current_month := date_trunc('month', CURRENT_DATE);
    next_month := current_month + interval '1 month';
    
    -- Create next month's partition if it doesn't exist
    partition_name := 'workflow_events_' || to_char(next_month, 'YYYY_MM');
    
    IF NOT EXISTS (
        SELECT 1 FROM pg_class WHERE relname = partition_name
    ) THEN
        PERFORM create_monthly_partition('workflow_events_partitioned', next_month);
    END IF;
    
    -- Drop partitions older than 1 year
    FOR partition_name IN 
        SELECT schemaname||'.'||tablename 
        FROM pg_tables 
        WHERE tablename LIKE 'workflow_events_____'
        AND tablename < 'workflow_events_' || to_char(CURRENT_DATE - interval '1 year', 'YYYY_MM')
    LOOP
        EXECUTE 'DROP TABLE ' || partition_name;
    END LOOP;
END;
$$ LANGUAGE plpgsql;
```

## 🔧 Maintenance Procedures

### 1. Regular Maintenance Tasks

```bash
#!/bin/bash
# daily_maintenance.sh

# Update table statistics
psql -d workflow_db -c "ANALYZE;"

# Vacuum tables with high update frequency
psql -d workflow_db -c "VACUUM ANALYZE tasks;"
psql -d workflow_db -c "VACUUM ANALYZE task_executions;"
psql -d workflow_db -c "VACUUM ANALYZE workflow_events;"

# Refresh materialized views
psql -d workflow_db -c "REFRESH MATERIALIZED VIEW CONCURRENTLY daily_task_metrics;"

# Check for unused indexes
psql -d workflow_db -c "
SELECT schemaname, tablename, indexname, idx_scan
FROM pg_stat_user_indexes 
WHERE idx_scan = 0 AND schemaname = 'public'
ORDER BY schemaname, tablename, indexname;
"

# Check database size growth
psql -d workflow_db -c "
SELECT 
    pg_size_pretty(pg_database_size(current_database())) as database_size,
    pg_size_pretty(pg_total_relation_size('tasks')) as tasks_size,
    pg_size_pretty(pg_total_relation_size('task_executions')) as executions_size,
    pg_size_pretty(pg_total_relation_size('workflow_events')) as events_size;
"
```

### 2. Performance Tuning Checklist

```sql
-- Weekly performance review queries

-- 1. Check slow queries
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    (100.0 * shared_blks_hit / nullif(shared_blks_hit + shared_blks_read, 0)) AS hit_percent
FROM pg_stat_statements 
WHERE mean_time > 100
ORDER BY mean_time DESC 
LIMIT 10;

-- 2. Check index usage
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as size
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

-- 3. Check table bloat
SELECT 
    schemaname,
    tablename,
    n_tup_ins,
    n_tup_upd,
    n_tup_del,
    n_dead_tup,
    last_vacuum,
    last_autovacuum,
    last_analyze,
    last_autoanalyze
FROM pg_stat_user_tables 
WHERE schemaname = 'public'
ORDER BY n_dead_tup DESC;

-- 4. Check connection usage
SELECT 
    state,
    count(*) as connections,
    max(now() - state_change) as max_duration
FROM pg_stat_activity 
WHERE datname = current_database()
GROUP BY state;
```

## 📈 Scaling Strategies

### 1. Horizontal Scaling

- **Read Replicas**: Distribute read queries across multiple replicas
- **Sharding**: Partition data across multiple databases by project or date
- **Connection Pooling**: Use PgBouncer or similar for connection management
- **Caching Layer**: Implement Redis for frequently accessed data

### 2. Vertical Scaling

- **Memory**: Increase shared_buffers and effective_cache_size
- **CPU**: Optimize parallel query execution
- **Storage**: Use SSDs and optimize I/O patterns
- **Network**: Ensure sufficient bandwidth for replication

### 3. Application-Level Optimizations

- **Query Optimization**: Use prepared statements and efficient queries
- **Batch Operations**: Group multiple operations into transactions
- **Async Processing**: Use background jobs for heavy operations
- **Caching**: Cache frequently accessed data at application level

This optimization guide provides a comprehensive foundation for maintaining high-performance, scalable database operations in the AI-powered development workflow system.

