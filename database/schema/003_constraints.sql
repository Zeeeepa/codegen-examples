-- Advanced Constraints and Data Integrity Rules
-- Ensures data consistency, business logic enforcement, and referential integrity

-- ============================================================================
-- ENHANCED CHECK CONSTRAINTS
-- ============================================================================

-- Projects constraints
ALTER TABLE projects ADD CONSTRAINT check_project_name_format 
    CHECK (name ~ '^[a-zA-Z0-9][a-zA-Z0-9_-]*[a-zA-Z0-9]$' AND length(name) >= 2);

ALTER TABLE projects ADD CONSTRAINT check_repository_name_format 
    CHECK (repository_name IS NULL OR repository_name ~ '^[a-zA-Z0-9][a-zA-Z0-9._-]*[a-zA-Z0-9]$');

ALTER TABLE projects ADD CONSTRAINT check_default_branch_format 
    CHECK (default_branch ~ '^[a-zA-Z0-9][a-zA-Z0-9/_-]*[a-zA-Z0-9]$');

-- Tasks constraints
ALTER TABLE tasks ADD CONSTRAINT check_task_title_length 
    CHECK (length(trim(title)) >= 3 AND length(title) <= 500);

ALTER TABLE tasks ADD CONSTRAINT check_task_priority_range 
    CHECK (priority >= 0 AND priority <= 10);

ALTER TABLE tasks ADD CONSTRAINT check_estimated_duration_positive 
    CHECK (estimated_duration IS NULL OR estimated_duration > INTERVAL '0');

ALTER TABLE tasks ADD CONSTRAINT check_actual_duration_positive 
    CHECK (actual_duration IS NULL OR actual_duration > INTERVAL '0');

ALTER TABLE tasks ADD CONSTRAINT check_due_date_future 
    CHECK (due_date IS NULL OR due_date > created_at);

ALTER TABLE tasks ADD CONSTRAINT check_completion_timing 
    CHECK (
        (status != 'completed' AND completed_at IS NULL) OR
        (status = 'completed' AND completed_at IS NOT NULL AND completed_at >= created_at)
    );

ALTER TABLE tasks ADD CONSTRAINT check_assignment_consistency 
    CHECK (
        (assigned_agent IS NULL AND assigned_at IS NULL) OR
        (assigned_agent IS NOT NULL AND assigned_at IS NOT NULL)
    );

-- Task executions constraints
ALTER TABLE task_executions ADD CONSTRAINT check_execution_timing_logic 
    CHECK (
        (execution_status = 'queued' AND started_at IS NULL AND completed_at IS NULL) OR
        (execution_status = 'running' AND started_at IS NOT NULL AND completed_at IS NULL) OR
        (execution_status IN ('completed', 'failed', 'timeout', 'cancelled') AND started_at IS NOT NULL AND completed_at IS NOT NULL)
    );

ALTER TABLE task_executions ADD CONSTRAINT check_resource_usage_positive 
    CHECK (
        (memory_usage_mb IS NULL OR memory_usage_mb > 0) AND
        (cpu_time_ms IS NULL OR cpu_time_ms >= 0)
    );

ALTER TABLE task_executions ADD CONSTRAINT check_agent_instance_format 
    CHECK (agent_instance_id IS NULL OR length(trim(agent_instance_id)) >= 1);

-- Pull requests constraints
ALTER TABLE pull_requests ADD CONSTRAINT check_pr_number_positive 
    CHECK (pr_number IS NULL OR pr_number > 0);

ALTER TABLE pull_requests ADD CONSTRAINT check_branch_name_format 
    CHECK (branch_name ~ '^[a-zA-Z0-9][a-zA-Z0-9/_.-]*[a-zA-Z0-9]$');

ALTER TABLE pull_requests ADD CONSTRAINT check_base_branch_format 
    CHECK (base_branch ~ '^[a-zA-Z0-9][a-zA-Z0-9/_.-]*[a-zA-Z0-9]$');

ALTER TABLE pull_requests ADD CONSTRAINT check_pr_title_length 
    CHECK (length(trim(title)) >= 3 AND length(title) <= 500);

ALTER TABLE pull_requests ADD CONSTRAINT check_pr_timing_logic 
    CHECK (
        (merged_at IS NULL OR merged_at >= created_at) AND
        (closed_at IS NULL OR closed_at >= created_at) AND
        (merged_at IS NULL OR closed_at IS NULL OR merged_at <= closed_at)
    );

ALTER TABLE pull_requests ADD CONSTRAINT check_pr_status_timing 
    CHECK (
        (status != 'merged' OR merged_at IS NOT NULL) AND
        (status != 'closed' OR closed_at IS NOT NULL)
    );

-- Validations constraints
ALTER TABLE validations ADD CONSTRAINT check_validation_type_format 
    CHECK (validation_type ~ '^[a-z][a-z0-9_]*[a-z0-9]$');

ALTER TABLE validations ADD CONSTRAINT check_validator_name_format 
    CHECK (validator_name ~ '^[a-zA-Z][a-zA-Z0-9_.-]*[a-zA-Z0-9]$');

ALTER TABLE validations ADD CONSTRAINT check_validation_score_range 
    CHECK (score IS NULL OR (score >= 0 AND score <= 100));

ALTER TABLE validations ADD CONSTRAINT check_validation_timing 
    CHECK (completed_at IS NULL OR completed_at >= started_at);

ALTER TABLE validations ADD CONSTRAINT check_execution_time_positive 
    CHECK (execution_time_ms IS NULL OR execution_time_ms >= 0);

-- Workflow events constraints
ALTER TABLE workflow_events ADD CONSTRAINT check_event_type_format 
    CHECK (event_type ~ '^[a-z][a-z0-9_]*[a-z0-9]$');

ALTER TABLE workflow_events ADD CONSTRAINT check_action_format 
    CHECK (action ~ '^[a-z][a-z0-9_]*[a-z0-9]$');

ALTER TABLE workflow_events ADD CONSTRAINT check_actor_format 
    CHECK (actor IS NULL OR length(trim(actor)) >= 1);

-- Agent configurations constraints
ALTER TABLE agent_configurations ADD CONSTRAINT check_agent_name_format 
    CHECK (agent_name ~ '^[a-zA-Z][a-zA-Z0-9_.-]*[a-zA-Z0-9]$');

ALTER TABLE agent_configurations ADD CONSTRAINT check_version_format 
    CHECK (version IS NULL OR version ~ '^[0-9]+\.[0-9]+(\.[0-9]+)?(-[a-zA-Z0-9]+)?$');

ALTER TABLE agent_configurations ADD CONSTRAINT check_health_status_values 
    CHECK (health_status IN ('healthy', 'degraded', 'unhealthy', 'unknown', 'maintenance'));

-- Dependencies constraints
ALTER TABLE dependencies ADD CONSTRAINT check_dependency_type_values 
    CHECK (dependency_type IN ('blocks', 'requires', 'suggests', 'conflicts'));

-- ============================================================================
-- JSONB SCHEMA VALIDATION CONSTRAINTS
-- ============================================================================

-- Tasks JSONB validation
ALTER TABLE tasks ADD CONSTRAINT check_requirements_schema 
    CHECK (
        requirements IS NULL OR (
            jsonb_typeof(requirements) = 'object' AND
            (NOT requirements ? 'priority' OR jsonb_typeof(requirements->'priority') = 'number') AND
            (NOT requirements ? 'type' OR jsonb_typeof(requirements->'type') = 'string') AND
            (NOT requirements ? 'complexity' OR jsonb_typeof(requirements->'complexity') = 'string')
        )
    );

ALTER TABLE tasks ADD CONSTRAINT check_dependencies_schema 
    CHECK (
        dependencies IS NULL OR (
            jsonb_typeof(dependencies) = 'array' AND
            jsonb_array_length(dependencies) <= 50
        )
    );

ALTER TABLE tasks ADD CONSTRAINT check_context_schema 
    CHECK (
        context IS NULL OR (
            jsonb_typeof(context) = 'object' AND
            (NOT context ? 'files' OR jsonb_typeof(context->'files') = 'array') AND
            (NOT context ? 'repository' OR jsonb_typeof(context->'repository') = 'object')
        )
    );

ALTER TABLE tasks ADD CONSTRAINT check_tags_schema 
    CHECK (
        tags IS NULL OR (
            jsonb_typeof(tags) = 'array' AND
            jsonb_array_length(tags) <= 20
        )
    );

-- Task executions JSONB validation
ALTER TABLE task_executions ADD CONSTRAINT check_input_context_schema 
    CHECK (
        input_context IS NULL OR jsonb_typeof(input_context) = 'object'
    );

ALTER TABLE task_executions ADD CONSTRAINT check_output_results_schema 
    CHECK (
        output_results IS NULL OR (
            jsonb_typeof(output_results) = 'object' AND
            (NOT output_results ? 'artifacts' OR jsonb_typeof(output_results->'artifacts') = 'array')
        )
    );

ALTER TABLE task_executions ADD CONSTRAINT check_error_details_schema 
    CHECK (
        error_details IS NULL OR (
            jsonb_typeof(error_details) = 'object' AND
            (NOT error_details ? 'error_type' OR jsonb_typeof(error_details->'error_type') = 'string')
        )
    );

-- Pull requests JSONB validation
ALTER TABLE pull_requests ADD CONSTRAINT check_validation_results_schema 
    CHECK (
        validation_results IS NULL OR (
            jsonb_typeof(validation_results) = 'object' AND
            (NOT validation_results ? 'status' OR jsonb_typeof(validation_results->'status') = 'string') AND
            (NOT validation_results ? 'scores' OR jsonb_typeof(validation_results->'scores') = 'object')
        )
    );

ALTER TABLE pull_requests ADD CONSTRAINT check_review_comments_schema 
    CHECK (
        review_comments IS NULL OR jsonb_typeof(review_comments) = 'array'
    );

-- Validations JSONB validation
ALTER TABLE validations ADD CONSTRAINT check_validation_details_schema 
    CHECK (
        details IS NULL OR jsonb_typeof(details) = 'object'
    );

ALTER TABLE validations ADD CONSTRAINT check_suggestions_schema 
    CHECK (
        suggestions IS NULL OR jsonb_typeof(suggestions) = 'array'
    );

-- Workflow events JSONB validation
ALTER TABLE workflow_events ADD CONSTRAINT check_event_data_schema 
    CHECK (
        event_data IS NULL OR jsonb_typeof(event_data) = 'object'
    );

ALTER TABLE workflow_events ADD CONSTRAINT check_metadata_schema 
    CHECK (
        metadata IS NULL OR jsonb_typeof(metadata) = 'object'
    );

-- Agent configurations JSONB validation
ALTER TABLE agent_configurations ADD CONSTRAINT check_configuration_schema 
    CHECK (
        configuration IS NOT NULL AND jsonb_typeof(configuration) = 'object'
    );

ALTER TABLE agent_configurations ADD CONSTRAINT check_capabilities_schema 
    CHECK (
        capabilities IS NULL OR jsonb_typeof(capabilities) = 'array'
    );

ALTER TABLE agent_configurations ADD CONSTRAINT check_constraints_schema 
    CHECK (
        constraints IS NULL OR jsonb_typeof(constraints) = 'object'
    );

-- ============================================================================
-- BUSINESS LOGIC CONSTRAINTS
-- ============================================================================

-- Prevent circular task dependencies
CREATE OR REPLACE FUNCTION check_circular_dependency()
RETURNS TRIGGER AS $$
BEGIN
    -- Check if adding this dependency would create a cycle
    IF EXISTS (
        WITH RECURSIVE dependency_chain AS (
            -- Start from the new dependency
            SELECT NEW.dependency_task_id as task_id, 1 as depth
            UNION ALL
            SELECT d.dependent_task_id, dc.depth + 1
            FROM dependencies d
            JOIN dependency_chain dc ON d.dependency_task_id = dc.task_id
            WHERE dc.depth < 10 -- Prevent infinite recursion
        )
        SELECT 1 FROM dependency_chain WHERE task_id = NEW.dependent_task_id
    ) THEN
        RAISE EXCEPTION 'Circular dependency detected: task % cannot depend on task %', 
            NEW.dependent_task_id, NEW.dependency_task_id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_check_circular_dependency
    BEFORE INSERT OR UPDATE ON dependencies
    FOR EACH ROW EXECUTE FUNCTION check_circular_dependency();

-- Ensure task status transitions are valid
CREATE OR REPLACE FUNCTION validate_task_status_transition()
RETURNS TRIGGER AS $$
BEGIN
    -- Allow any transition for new records
    IF TG_OP = 'INSERT' THEN
        RETURN NEW;
    END IF;
    
    -- Define valid status transitions
    IF OLD.status = 'pending' AND NEW.status NOT IN ('pending', 'in_progress', 'cancelled') THEN
        RAISE EXCEPTION 'Invalid status transition from % to %', OLD.status, NEW.status;
    END IF;
    
    IF OLD.status = 'in_progress' AND NEW.status NOT IN ('in_progress', 'validation', 'completed', 'failed', 'cancelled') THEN
        RAISE EXCEPTION 'Invalid status transition from % to %', OLD.status, NEW.status;
    END IF;
    
    IF OLD.status = 'validation' AND NEW.status NOT IN ('validation', 'completed', 'failed', 'in_progress') THEN
        RAISE EXCEPTION 'Invalid status transition from % to %', OLD.status, NEW.status;
    END IF;
    
    IF OLD.status IN ('completed', 'cancelled') AND NEW.status != OLD.status THEN
        RAISE EXCEPTION 'Cannot change status from final state %', OLD.status;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_task_status_transition
    BEFORE UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION validate_task_status_transition();

-- Ensure PR status transitions are valid
CREATE OR REPLACE FUNCTION validate_pr_status_transition()
RETURNS TRIGGER AS $$
BEGIN
    -- Allow any transition for new records
    IF TG_OP = 'INSERT' THEN
        RETURN NEW;
    END IF;
    
    -- Define valid PR status transitions
    IF OLD.status = 'draft' AND NEW.status NOT IN ('draft', 'open', 'closed') THEN
        RAISE EXCEPTION 'Invalid PR status transition from % to %', OLD.status, NEW.status;
    END IF;
    
    IF OLD.status = 'open' AND NEW.status NOT IN ('open', 'review_requested', 'approved', 'closed', 'failed_validation') THEN
        RAISE EXCEPTION 'Invalid PR status transition from % to %', OLD.status, NEW.status;
    END IF;
    
    IF OLD.status = 'review_requested' AND NEW.status NOT IN ('review_requested', 'approved', 'open', 'closed', 'failed_validation') THEN
        RAISE EXCEPTION 'Invalid PR status transition from % to %', OLD.status, NEW.status;
    END IF;
    
    IF OLD.status = 'approved' AND NEW.status NOT IN ('approved', 'merged', 'closed') THEN
        RAISE EXCEPTION 'Invalid PR status transition from % to %', OLD.status, NEW.status;
    END IF;
    
    IF OLD.status IN ('merged', 'closed') AND NEW.status != OLD.status THEN
        RAISE EXCEPTION 'Cannot change PR status from final state %', OLD.status;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_validate_pr_status_transition
    BEFORE UPDATE ON pull_requests
    FOR EACH ROW EXECUTE FUNCTION validate_pr_status_transition();

-- Automatically update task status based on executions
CREATE OR REPLACE FUNCTION update_task_status_from_execution()
RETURNS TRIGGER AS $$
BEGIN
    -- Update task status when execution completes
    IF NEW.execution_status = 'completed' AND OLD.execution_status != 'completed' THEN
        UPDATE tasks 
        SET status = 'validation', 
            actual_duration = COALESCE(actual_duration, NEW.duration)
        WHERE id = NEW.task_id AND status = 'in_progress';
    END IF;
    
    -- Update task status when execution fails
    IF NEW.execution_status = 'failed' AND OLD.execution_status != 'failed' THEN
        UPDATE tasks 
        SET status = 'failed'
        WHERE id = NEW.task_id AND status = 'in_progress';
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_task_status_from_execution
    AFTER UPDATE ON task_executions
    FOR EACH ROW EXECUTE FUNCTION update_task_status_from_execution();

-- Automatically satisfy dependencies when tasks complete
CREATE OR REPLACE FUNCTION update_dependency_satisfaction()
RETURNS TRIGGER AS $$
BEGIN
    -- Mark dependencies as satisfied when dependency task completes
    IF NEW.status = 'completed' AND OLD.status != 'completed' THEN
        UPDATE dependencies 
        SET is_satisfied = true, 
            satisfied_at = NOW()
        WHERE dependency_task_id = NEW.id AND is_satisfied = false;
    END IF;
    
    -- Unmark dependencies if task status changes from completed
    IF OLD.status = 'completed' AND NEW.status != 'completed' THEN
        UPDATE dependencies 
        SET is_satisfied = false, 
            satisfied_at = NULL
        WHERE dependency_task_id = NEW.id;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_update_dependency_satisfaction
    AFTER UPDATE ON tasks
    FOR EACH ROW EXECUTE FUNCTION update_dependency_satisfaction();

-- ============================================================================
-- AUDIT TRAIL TRIGGERS
-- ============================================================================

-- Comprehensive audit logging for all major operations
CREATE OR REPLACE FUNCTION log_workflow_event()
RETURNS TRIGGER AS $$
DECLARE
    event_type_name VARCHAR(100);
    event_category_name VARCHAR(50);
    event_description TEXT;
    event_data_json JSONB;
BEGIN
    -- Determine event type and category based on table and operation
    CASE TG_TABLE_NAME
        WHEN 'tasks' THEN
            event_category_name := 'task';
            CASE TG_OP
                WHEN 'INSERT' THEN 
                    event_type_name := 'task_created';
                    event_description := 'Task "' || NEW.title || '" created';
                    event_data_json := jsonb_build_object(
                        'task_id', NEW.id,
                        'title', NEW.title,
                        'status', NEW.status,
                        'priority', NEW.priority
                    );
                WHEN 'UPDATE' THEN
                    event_type_name := 'task_updated';
                    event_description := 'Task "' || NEW.title || '" updated';
                    event_data_json := jsonb_build_object(
                        'task_id', NEW.id,
                        'title', NEW.title,
                        'old_status', OLD.status,
                        'new_status', NEW.status,
                        'changes', jsonb_build_object(
                            'status_changed', (OLD.status != NEW.status),
                            'priority_changed', (OLD.priority != NEW.priority),
                            'assignment_changed', (OLD.assigned_agent != NEW.assigned_agent)
                        )
                    );
                WHEN 'DELETE' THEN
                    event_type_name := 'task_deleted';
                    event_description := 'Task "' || OLD.title || '" deleted';
                    event_data_json := jsonb_build_object(
                        'task_id', OLD.id,
                        'title', OLD.title,
                        'final_status', OLD.status
                    );
            END CASE;
            
        WHEN 'task_executions' THEN
            event_category_name := 'execution';
            CASE TG_OP
                WHEN 'INSERT' THEN
                    event_type_name := 'execution_started';
                    event_description := 'Execution started for task by ' || NEW.agent_type;
                    event_data_json := jsonb_build_object(
                        'execution_id', NEW.id,
                        'task_id', NEW.task_id,
                        'agent_type', NEW.agent_type,
                        'agent_instance_id', NEW.agent_instance_id
                    );
                WHEN 'UPDATE' THEN
                    event_type_name := 'execution_updated';
                    event_description := 'Execution status changed to ' || NEW.execution_status;
                    event_data_json := jsonb_build_object(
                        'execution_id', NEW.id,
                        'task_id', NEW.task_id,
                        'old_status', OLD.execution_status,
                        'new_status', NEW.execution_status,
                        'duration', EXTRACT(EPOCH FROM NEW.duration)
                    );
            END CASE;
            
        WHEN 'pull_requests' THEN
            event_category_name := 'pr';
            CASE TG_OP
                WHEN 'INSERT' THEN
                    event_type_name := 'pr_created';
                    event_description := 'Pull request "' || NEW.title || '" created';
                    event_data_json := jsonb_build_object(
                        'pr_id', NEW.id,
                        'title', NEW.title,
                        'branch_name', NEW.branch_name,
                        'pr_number', NEW.pr_number
                    );
                WHEN 'UPDATE' THEN
                    event_type_name := 'pr_updated';
                    event_description := 'Pull request "' || NEW.title || '" updated';
                    event_data_json := jsonb_build_object(
                        'pr_id', NEW.id,
                        'title', NEW.title,
                        'old_status', OLD.status,
                        'new_status', NEW.status
                    );
            END CASE;
            
        WHEN 'validations' THEN
            event_category_name := 'validation';
            CASE TG_OP
                WHEN 'INSERT' THEN
                    event_type_name := 'validation_started';
                    event_description := 'Validation "' || NEW.validation_type || '" started';
                    event_data_json := jsonb_build_object(
                        'validation_id', NEW.id,
                        'validation_type', NEW.validation_type,
                        'validator_name', NEW.validator_name,
                        'pr_id', NEW.pr_id
                    );
                WHEN 'UPDATE' THEN
                    event_type_name := 'validation_completed';
                    event_description := 'Validation "' || NEW.validation_type || '" completed with result: ' || NEW.result;
                    event_data_json := jsonb_build_object(
                        'validation_id', NEW.id,
                        'validation_type', NEW.validation_type,
                        'result', NEW.result,
                        'score', NEW.score
                    );
            END CASE;
    END CASE;
    
    -- Insert the audit event
    INSERT INTO workflow_events (
        event_type,
        event_category,
        project_id,
        task_id,
        execution_id,
        pr_id,
        actor,
        action,
        description,
        event_data,
        occurred_at
    ) VALUES (
        event_type_name,
        event_category_name,
        CASE TG_TABLE_NAME
            WHEN 'tasks' THEN COALESCE(NEW.project_id, OLD.project_id)
            WHEN 'pull_requests' THEN COALESCE(NEW.project_id, OLD.project_id)
            ELSE NULL
        END,
        CASE TG_TABLE_NAME
            WHEN 'tasks' THEN COALESCE(NEW.id, OLD.id)
            WHEN 'task_executions' THEN COALESCE(NEW.task_id, OLD.task_id)
            ELSE NULL
        END,
        CASE TG_TABLE_NAME
            WHEN 'task_executions' THEN COALESCE(NEW.id, OLD.id)
            ELSE NULL
        END,
        CASE TG_TABLE_NAME
            WHEN 'pull_requests' THEN COALESCE(NEW.id, OLD.id)
            WHEN 'validations' THEN COALESCE(NEW.pr_id, OLD.pr_id)
            ELSE NULL
        END,
        CASE TG_TABLE_NAME
            WHEN 'tasks' THEN COALESCE(NEW.created_by, OLD.created_by)
            WHEN 'task_executions' THEN NEW.agent_type::text
            ELSE 'system'
        END,
        TG_OP,
        event_description,
        event_data_json,
        NOW()
    );
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Apply audit triggers to all major tables
CREATE TRIGGER trigger_audit_tasks
    AFTER INSERT OR UPDATE OR DELETE ON tasks
    FOR EACH ROW EXECUTE FUNCTION log_workflow_event();

CREATE TRIGGER trigger_audit_task_executions
    AFTER INSERT OR UPDATE ON task_executions
    FOR EACH ROW EXECUTE FUNCTION log_workflow_event();

CREATE TRIGGER trigger_audit_pull_requests
    AFTER INSERT OR UPDATE ON pull_requests
    FOR EACH ROW EXECUTE FUNCTION log_workflow_event();

CREATE TRIGGER trigger_audit_validations
    AFTER INSERT OR UPDATE ON validations
    FOR EACH ROW EXECUTE FUNCTION log_workflow_event();

-- ============================================================================
-- PERFORMANCE AND MAINTENANCE CONSTRAINTS
-- ============================================================================

-- Prevent excessive JSONB nesting depth
CREATE OR REPLACE FUNCTION check_jsonb_depth(data JSONB, max_depth INTEGER DEFAULT 5)
RETURNS BOOLEAN AS $$
BEGIN
    -- Simplified depth check - in production, you might want a more sophisticated implementation
    RETURN jsonb_typeof(data) != 'object' OR 
           length(data::text) < 10000; -- Rough approximation
END;
$$ LANGUAGE plpgsql IMMUTABLE;

-- Apply JSONB depth constraints
ALTER TABLE tasks ADD CONSTRAINT check_requirements_depth 
    CHECK (check_jsonb_depth(requirements));

ALTER TABLE tasks ADD CONSTRAINT check_context_depth 
    CHECK (check_jsonb_depth(context));

ALTER TABLE task_executions ADD CONSTRAINT check_input_context_depth 
    CHECK (check_jsonb_depth(input_context));

ALTER TABLE task_executions ADD CONSTRAINT check_output_results_depth 
    CHECK (check_jsonb_depth(output_results));

-- Prevent excessive array sizes in JSONB
ALTER TABLE tasks ADD CONSTRAINT check_dependencies_size 
    CHECK (dependencies IS NULL OR jsonb_array_length(dependencies) <= 100);

ALTER TABLE tasks ADD CONSTRAINT check_tags_size 
    CHECK (tags IS NULL OR jsonb_array_length(tags) <= 50);

-- Comments for constraint documentation
COMMENT ON CONSTRAINT check_circular_dependency ON dependencies IS 'Prevents circular task dependencies using recursive CTE';
COMMENT ON CONSTRAINT check_requirements_schema ON tasks IS 'Validates JSONB schema for task requirements field';
COMMENT ON CONSTRAINT check_validation_results_schema ON pull_requests IS 'Validates JSONB schema for PR validation results';
COMMENT ON TRIGGER trigger_validate_task_status_transition ON tasks IS 'Enforces valid task status transitions';
COMMENT ON TRIGGER trigger_audit_tasks ON tasks IS 'Comprehensive audit logging for task operations';

