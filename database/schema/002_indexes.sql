-- Advanced Indexing Strategies for AI-Powered Development Workflow System
-- Optimized for JSONB queries, performance, and concurrent access patterns

-- ============================================================================
-- PRIMARY INDEXES FOR CORE QUERIES
-- ============================================================================

-- Projects indexes
CREATE INDEX idx_projects_name_trgm ON projects USING gin (name gin_trgm_ops);
CREATE INDEX idx_projects_repository_name ON projects (repository_name) WHERE archived_at IS NULL;
CREATE INDEX idx_projects_active ON projects (created_at DESC) WHERE archived_at IS NULL;

-- Tasks indexes - Core performance critical
CREATE INDEX idx_tasks_project_status ON tasks (project_id, status);
CREATE INDEX idx_tasks_status_priority ON tasks (status, priority DESC) WHERE status IN ('pending', 'in_progress');
CREATE INDEX idx_tasks_assigned_agent ON tasks (assigned_agent, assigned_at DESC) WHERE assigned_agent IS NOT NULL;
CREATE INDEX idx_tasks_parent_child ON tasks (parent_task_id) WHERE parent_task_id IS NOT NULL;
CREATE INDEX idx_tasks_due_date ON tasks (due_date) WHERE due_date IS NOT NULL AND status NOT IN ('completed', 'cancelled');
CREATE INDEX idx_tasks_created_at ON tasks (created_at DESC);
CREATE INDEX idx_tasks_updated_at ON tasks (updated_at DESC);

-- Task executions indexes
CREATE INDEX idx_task_executions_task_status ON task_executions (task_id, execution_status);
CREATE INDEX idx_task_executions_agent_type ON task_executions (agent_type, started_at DESC);
CREATE INDEX idx_task_executions_status_started ON task_executions (execution_status, started_at DESC);
CREATE INDEX idx_task_executions_duration ON task_executions (duration DESC) WHERE duration IS NOT NULL;
CREATE INDEX idx_task_executions_recent ON task_executions (created_at DESC);

-- Pull requests indexes
CREATE INDEX idx_pull_requests_project_status ON pull_requests (project_id, status);
CREATE INDEX idx_pull_requests_task_id ON pull_requests (task_id) WHERE task_id IS NOT NULL;
CREATE INDEX idx_pull_requests_repository_pr ON pull_requests (repository_url, pr_number);
CREATE INDEX idx_pull_requests_branch ON pull_requests (repository_url, branch_name);
CREATE INDEX idx_pull_requests_status_updated ON pull_requests (status, updated_at DESC);
CREATE INDEX idx_pull_requests_created_at ON pull_requests (created_at DESC);

-- Validations indexes
CREATE INDEX idx_validations_pr_type_result ON validations (pr_id, validation_type, result);
CREATE INDEX idx_validations_execution_type ON validations (task_execution_id, validation_type) WHERE task_execution_id IS NOT NULL;
CREATE INDEX idx_validations_result_score ON validations (result, score DESC) WHERE score IS NOT NULL;
CREATE INDEX idx_validations_type_completed ON validations (validation_type, completed_at DESC);

-- Workflow events indexes
CREATE INDEX idx_workflow_events_category_type ON workflow_events (event_category, event_type);
CREATE INDEX idx_workflow_events_occurred_at ON workflow_events (occurred_at DESC);
CREATE INDEX idx_workflow_events_project_occurred ON workflow_events (project_id, occurred_at DESC) WHERE project_id IS NOT NULL;
CREATE INDEX idx_workflow_events_task_occurred ON workflow_events (task_id, occurred_at DESC) WHERE task_id IS NOT NULL;
CREATE INDEX idx_workflow_events_actor ON workflow_events (actor, occurred_at DESC) WHERE actor IS NOT NULL;

-- Agent configurations indexes
CREATE INDEX idx_agent_configurations_project_type ON agent_configurations (project_id, agent_type);
CREATE INDEX idx_agent_configurations_active ON agent_configurations (agent_type, is_active) WHERE is_active = true;
CREATE INDEX idx_agent_configurations_health ON agent_configurations (health_status, last_health_check DESC);

-- Dependencies indexes
CREATE INDEX idx_dependencies_dependent_task ON dependencies (dependent_task_id, is_satisfied);
CREATE INDEX idx_dependencies_dependency_task ON dependencies (dependency_task_id);
CREATE INDEX idx_dependencies_unsatisfied ON dependencies (dependency_type, is_satisfied) WHERE is_satisfied = false;

-- ============================================================================
-- ADVANCED JSONB INDEXES FOR COMPLEX QUERIES
-- ============================================================================

-- Tasks JSONB indexes for requirements, dependencies, and context
CREATE INDEX idx_tasks_requirements_gin ON tasks USING gin (requirements);
CREATE INDEX idx_tasks_dependencies_gin ON tasks USING gin (dependencies);
CREATE INDEX idx_tasks_context_gin ON tasks USING gin (context);
CREATE INDEX idx_tasks_tags_gin ON tasks USING gin (tags);

-- Specific JSONB path indexes for common query patterns
CREATE INDEX idx_tasks_requirements_priority ON tasks USING gin ((requirements->'priority'));
CREATE INDEX idx_tasks_requirements_type ON tasks USING gin ((requirements->'type'));
CREATE INDEX idx_tasks_context_files ON tasks USING gin ((context->'files'));
CREATE INDEX idx_tasks_context_repository ON tasks USING gin ((context->'repository'));

-- Task executions JSONB indexes
CREATE INDEX idx_task_executions_input_gin ON task_executions USING gin (input_context);
CREATE INDEX idx_task_executions_output_gin ON task_executions USING gin (output_results);
CREATE INDEX idx_task_executions_errors_gin ON task_executions USING gin (error_details);

-- Specific execution context indexes
CREATE INDEX idx_task_executions_input_agent_config ON task_executions USING gin ((input_context->'agent_config'));
CREATE INDEX idx_task_executions_output_artifacts ON task_executions USING gin ((output_results->'artifacts'));
CREATE INDEX idx_task_executions_error_type ON task_executions USING gin ((error_details->'error_type'));

-- Pull requests JSONB indexes
CREATE INDEX idx_pull_requests_validation_gin ON pull_requests USING gin (validation_results);
CREATE INDEX idx_pull_requests_reviews_gin ON pull_requests USING gin (review_comments);

-- Specific PR validation indexes
CREATE INDEX idx_pull_requests_validation_status ON pull_requests USING gin ((validation_results->'status'));
CREATE INDEX idx_pull_requests_validation_scores ON pull_requests USING gin ((validation_results->'scores'));

-- Validations JSONB indexes
CREATE INDEX idx_validations_details_gin ON validations USING gin (details);
CREATE INDEX idx_validations_suggestions_gin ON validations USING gin (suggestions);

-- Workflow events JSONB indexes
CREATE INDEX idx_workflow_events_data_gin ON workflow_events USING gin (event_data);
CREATE INDEX idx_workflow_events_metadata_gin ON workflow_events USING gin (metadata);

-- Agent configurations JSONB indexes
CREATE INDEX idx_agent_configurations_config_gin ON agent_configurations USING gin (configuration);
CREATE INDEX idx_agent_configurations_capabilities_gin ON agent_configurations USING gin (capabilities);

-- ============================================================================
-- COMPOSITE INDEXES FOR COMPLEX QUERIES
-- ============================================================================

-- Task management dashboard queries
CREATE INDEX idx_tasks_dashboard ON tasks (project_id, status, priority DESC, updated_at DESC);
CREATE INDEX idx_tasks_agent_workload ON tasks (assigned_agent, status, created_at DESC) WHERE assigned_agent IS NOT NULL;

-- Execution performance analysis
CREATE INDEX idx_executions_performance ON task_executions (agent_type, execution_status, duration DESC, started_at DESC);
CREATE INDEX idx_executions_resource_usage ON task_executions (memory_usage_mb DESC, cpu_time_ms DESC, completed_at DESC) WHERE execution_status = 'completed';

-- PR workflow tracking
CREATE INDEX idx_pr_workflow ON pull_requests (project_id, status, created_at DESC, updated_at DESC);
CREATE INDEX idx_pr_validation_tracking ON validations (pr_id, validation_type, result, completed_at DESC);

-- Audit and monitoring
CREATE INDEX idx_workflow_events_monitoring ON workflow_events (event_category, occurred_at DESC, actor);
CREATE INDEX idx_workflow_events_error_tracking ON workflow_events (event_type, occurred_at DESC) WHERE event_data ? 'error';

-- ============================================================================
-- PARTIAL INDEXES FOR SPECIFIC USE CASES
-- ============================================================================

-- Active/pending items only
CREATE INDEX idx_tasks_active_only ON tasks (project_id, priority DESC, created_at DESC) 
    WHERE status IN ('pending', 'in_progress', 'validation');

CREATE INDEX idx_executions_running_only ON task_executions (agent_type, started_at DESC) 
    WHERE execution_status IN ('queued', 'running');

CREATE INDEX idx_pr_open_only ON pull_requests (project_id, updated_at DESC) 
    WHERE status IN ('draft', 'open', 'review_requested');

-- Failed items for debugging
CREATE INDEX idx_tasks_failed_only ON tasks (project_id, updated_at DESC) 
    WHERE status = 'failed';

CREATE INDEX idx_executions_failed_only ON task_executions (task_id, agent_type, completed_at DESC) 
    WHERE execution_status = 'failed';

CREATE INDEX idx_validations_failed_only ON validations (pr_id, validation_type, completed_at DESC) 
    WHERE result = 'failed';

-- Recent activity indexes
CREATE INDEX idx_tasks_recent_activity ON tasks (updated_at DESC) 
    WHERE updated_at > NOW() - INTERVAL '7 days';

CREATE INDEX idx_executions_recent_activity ON task_executions (completed_at DESC) 
    WHERE completed_at > NOW() - INTERVAL '24 hours';

-- ============================================================================
-- TEXT SEARCH INDEXES
-- ============================================================================

-- Full-text search capabilities
CREATE INDEX idx_tasks_title_search ON tasks USING gin (to_tsvector('english', title));
CREATE INDEX idx_tasks_description_search ON tasks USING gin (to_tsvector('english', description));
CREATE INDEX idx_tasks_combined_search ON tasks USING gin (to_tsvector('english', title || ' ' || COALESCE(description, '')));

CREATE INDEX idx_pr_title_search ON pull_requests USING gin (to_tsvector('english', title));
CREATE INDEX idx_pr_description_search ON pull_requests USING gin (to_tsvector('english', description));

-- Trigram indexes for fuzzy matching
CREATE INDEX idx_tasks_title_trgm ON tasks USING gin (title gin_trgm_ops);
CREATE INDEX idx_pr_title_trgm ON pull_requests USING gin (title gin_trgm_ops);
CREATE INDEX idx_pr_branch_trgm ON pull_requests USING gin (branch_name gin_trgm_ops);

-- ============================================================================
-- SPECIALIZED INDEXES FOR ANALYTICS
-- ============================================================================

-- Time-series analysis indexes
CREATE INDEX idx_tasks_created_date_trunc ON tasks (date_trunc('day', created_at), status);
CREATE INDEX idx_executions_completed_date_trunc ON task_executions (date_trunc('hour', completed_at), execution_status) 
    WHERE completed_at IS NOT NULL;

-- Performance metrics indexes
CREATE INDEX idx_executions_duration_percentiles ON task_executions (agent_type, duration) 
    WHERE duration IS NOT NULL AND execution_status = 'completed';

CREATE INDEX idx_validations_score_distribution ON validations (validation_type, score) 
    WHERE score IS NOT NULL;

-- Resource utilization indexes
CREATE INDEX idx_executions_resource_analysis ON task_executions (agent_type, memory_usage_mb, cpu_time_ms, completed_at) 
    WHERE execution_status = 'completed' AND memory_usage_mb IS NOT NULL;

-- ============================================================================
-- MAINTENANCE AND MONITORING INDEXES
-- ============================================================================

-- Cleanup and archival support
CREATE INDEX idx_tasks_archival_candidates ON tasks (completed_at) 
    WHERE status IN ('completed', 'cancelled') AND completed_at < NOW() - INTERVAL '90 days';

CREATE INDEX idx_executions_archival_candidates ON task_executions (completed_at) 
    WHERE execution_status IN ('completed', 'failed') AND completed_at < NOW() - INTERVAL '30 days';

CREATE INDEX idx_workflow_events_archival_candidates ON workflow_events (occurred_at) 
    WHERE occurred_at < NOW() - INTERVAL '180 days';

-- Health monitoring indexes
CREATE INDEX idx_agent_health_monitoring ON agent_configurations (agent_type, health_status, last_health_check) 
    WHERE is_active = true;

-- ============================================================================
-- COMMENTS FOR INDEX DOCUMENTATION
-- ============================================================================

COMMENT ON INDEX idx_tasks_requirements_gin IS 'GIN index for flexible JSONB queries on task requirements';
COMMENT ON INDEX idx_tasks_dependencies_gin IS 'GIN index for complex dependency queries using JSONB operators';
COMMENT ON INDEX idx_tasks_context_gin IS 'GIN index for context-based task searches and filtering';
COMMENT ON INDEX idx_task_executions_input_gin IS 'GIN index for execution input context queries';
COMMENT ON INDEX idx_task_executions_output_gin IS 'GIN index for execution result and artifact searches';
COMMENT ON INDEX idx_pull_requests_validation_gin IS 'GIN index for PR validation result queries';
COMMENT ON INDEX idx_workflow_events_data_gin IS 'GIN index for event data analysis and filtering';

-- Index usage statistics view for monitoring
CREATE VIEW index_usage_stats AS
SELECT 
    schemaname,
    tablename,
    indexname,
    idx_tup_read,
    idx_tup_fetch,
    idx_scan,
    CASE 
        WHEN idx_scan = 0 THEN 'UNUSED'
        WHEN idx_scan < 100 THEN 'LOW_USAGE'
        WHEN idx_scan < 1000 THEN 'MODERATE_USAGE'
        ELSE 'HIGH_USAGE'
    END as usage_category
FROM pg_stat_user_indexes 
WHERE schemaname = 'public'
ORDER BY idx_scan DESC;

