-- Enhanced Task Manager Database Schema
-- PostgreSQL schema for task management with dependency tracking and workflow integration

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Task status enum
CREATE TYPE task_status AS ENUM (
    'pending',
    'in_progress',
    'blocked',
    'review',
    'completed',
    'cancelled',
    'failed'
);

-- Task priority enum
CREATE TYPE task_priority AS ENUM (
    'low',
    'medium',
    'high',
    'critical'
);

-- Task complexity enum
CREATE TYPE task_complexity AS ENUM (
    'simple',
    'moderate',
    'complex',
    'epic'
);

-- Workflow trigger type enum
CREATE TYPE workflow_trigger_type AS ENUM (
    'codegen',
    'claude_code',
    'webhook',
    'manual',
    'scheduled'
);

-- Projects table
CREATE TABLE projects (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    repository_url VARCHAR(500),
    branch_name VARCHAR(100) DEFAULT 'main',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Tasks table
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    project_id UUID REFERENCES projects(id) ON DELETE CASCADE,
    title VARCHAR(500) NOT NULL,
    description TEXT,
    natural_language_input TEXT, -- Original user input
    parsed_requirements JSONB, -- Structured requirements from NLP
    status task_status DEFAULT 'pending',
    priority task_priority DEFAULT 'medium',
    complexity task_complexity DEFAULT 'moderate',
    estimated_hours DECIMAL(5,2),
    actual_hours DECIMAL(5,2),
    assignee VARCHAR(255),
    tags TEXT[],
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    due_date TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    metadata JSONB DEFAULT '{}'::jsonb,
    
    -- Full-text search
    search_vector tsvector GENERATED ALWAYS AS (
        to_tsvector('english', 
            COALESCE(title, '') || ' ' || 
            COALESCE(description, '') || ' ' || 
            COALESCE(natural_language_input, '')
        )
    ) STORED
);

-- Task dependencies table (for dependency graph)
CREATE TABLE task_dependencies (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    depends_on_task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    dependency_type VARCHAR(50) DEFAULT 'blocks', -- blocks, requires, suggests
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    -- Prevent self-dependencies and duplicates
    CONSTRAINT no_self_dependency CHECK (task_id != depends_on_task_id),
    CONSTRAINT unique_dependency UNIQUE (task_id, depends_on_task_id)
);

-- Workflow triggers table
CREATE TABLE workflow_triggers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    trigger_type workflow_trigger_type NOT NULL,
    trigger_config JSONB NOT NULL, -- Configuration for the specific trigger
    status VARCHAR(50) DEFAULT 'pending', -- pending, triggered, completed, failed
    triggered_at TIMESTAMP WITH TIME ZONE,
    completed_at TIMESTAMP WITH TIME ZONE,
    result JSONB, -- Result data from the workflow
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    max_retries INTEGER DEFAULT 3,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Task history/audit log
CREATE TABLE task_history (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    old_value TEXT,
    new_value TEXT,
    changed_by VARCHAR(255),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    change_reason TEXT
);

-- Task comments/notes
CREATE TABLE task_comments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    author VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    comment_type VARCHAR(50) DEFAULT 'note', -- note, system, ai_analysis
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Task files/artifacts
CREATE TABLE task_artifacts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    file_path VARCHAR(1000) NOT NULL,
    file_type VARCHAR(100), -- code, documentation, test, config
    content_hash VARCHAR(64), -- SHA-256 hash for change detection
    size_bytes BIGINT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    metadata JSONB DEFAULT '{}'::jsonb
);

-- Indexes for performance
CREATE INDEX idx_tasks_project_id ON tasks(project_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_priority ON tasks(priority);
CREATE INDEX idx_tasks_assignee ON tasks(assignee);
CREATE INDEX idx_tasks_created_at ON tasks(created_at);
CREATE INDEX idx_tasks_search_vector ON tasks USING gin(search_vector);
CREATE INDEX idx_task_dependencies_task_id ON task_dependencies(task_id);
CREATE INDEX idx_task_dependencies_depends_on ON task_dependencies(depends_on_task_id);
CREATE INDEX idx_workflow_triggers_task_id ON workflow_triggers(task_id);
CREATE INDEX idx_workflow_triggers_status ON workflow_triggers(status);
CREATE INDEX idx_task_history_task_id ON task_history(task_id);
CREATE INDEX idx_task_comments_task_id ON task_comments(task_id);
CREATE INDEX idx_task_artifacts_task_id ON task_artifacts(task_id);

-- Functions for automatic timestamp updates
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers for automatic timestamp updates
CREATE TRIGGER update_projects_updated_at BEFORE UPDATE ON projects
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_tasks_updated_at BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_workflow_triggers_updated_at BEFORE UPDATE ON workflow_triggers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to detect circular dependencies
CREATE OR REPLACE FUNCTION check_circular_dependency()
RETURNS TRIGGER AS $$
BEGIN
    -- Use recursive CTE to check for circular dependencies
    WITH RECURSIVE dependency_path AS (
        -- Base case: direct dependency
        SELECT 
            NEW.task_id as start_task,
            NEW.depends_on_task_id as current_task,
            1 as depth,
            ARRAY[NEW.task_id, NEW.depends_on_task_id] as path
        
        UNION ALL
        
        -- Recursive case: follow the dependency chain
        SELECT 
            dp.start_task,
            td.depends_on_task_id,
            dp.depth + 1,
            dp.path || td.depends_on_task_id
        FROM dependency_path dp
        JOIN task_dependencies td ON dp.current_task = td.task_id
        WHERE dp.depth < 10 -- Prevent infinite recursion
          AND NOT (td.depends_on_task_id = ANY(dp.path)) -- Prevent cycles in path
    )
    SELECT 1 FROM dependency_path 
    WHERE current_task = start_task
    LIMIT 1;
    
    -- If we found a circular dependency, raise an error
    IF FOUND THEN
        RAISE EXCEPTION 'Circular dependency detected: task % would create a cycle', NEW.task_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to prevent circular dependencies
CREATE TRIGGER prevent_circular_dependencies
    BEFORE INSERT OR UPDATE ON task_dependencies
    FOR EACH ROW EXECUTE FUNCTION check_circular_dependency();

-- Function to automatically update task status based on dependencies
CREATE OR REPLACE FUNCTION update_task_status_on_dependency_change()
RETURNS TRIGGER AS $$
BEGIN
    -- If a dependency is completed, check if the dependent task can be unblocked
    IF TG_OP = 'UPDATE' AND OLD.status != 'completed' AND NEW.status = 'completed' THEN
        -- Find tasks that depend on this completed task
        UPDATE tasks SET status = 'pending'
        WHERE id IN (
            SELECT td.task_id 
            FROM task_dependencies td
            WHERE td.depends_on_task_id = NEW.id
              AND NOT EXISTS (
                  -- Check if there are other incomplete dependencies
                  SELECT 1 FROM task_dependencies td2
                  JOIN tasks t2 ON td2.depends_on_task_id = t2.id
                  WHERE td2.task_id = td.task_id 
                    AND t2.status NOT IN ('completed', 'cancelled')
              )
        ) AND status = 'blocked';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to update dependent task statuses
CREATE TRIGGER update_dependent_tasks_status
    AFTER UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_task_status_on_dependency_change();

-- Views for common queries
CREATE VIEW task_summary AS
SELECT 
    t.id,
    t.title,
    t.status,
    t.priority,
    t.complexity,
    t.estimated_hours,
    t.actual_hours,
    t.assignee,
    t.created_at,
    t.due_date,
    p.name as project_name,
    (SELECT COUNT(*) FROM task_dependencies WHERE task_id = t.id) as dependency_count,
    (SELECT COUNT(*) FROM task_dependencies WHERE depends_on_task_id = t.id) as dependent_count
FROM tasks t
LEFT JOIN projects p ON t.project_id = p.id;

CREATE VIEW dependency_graph AS
SELECT 
    td.task_id,
    t1.title as task_title,
    td.depends_on_task_id,
    t2.title as dependency_title,
    td.dependency_type,
    t1.status as task_status,
    t2.status as dependency_status
FROM task_dependencies td
JOIN tasks t1 ON td.task_id = t1.id
JOIN tasks t2 ON td.depends_on_task_id = t2.id;

