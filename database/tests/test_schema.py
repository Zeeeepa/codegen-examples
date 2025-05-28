"""
Comprehensive Database Schema Tests
Tests schema integrity, constraints, triggers, and business logic
"""

import pytest
import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List
import json

class TestDatabaseSchema:
    """Test database schema functionality"""
    
    @pytest.fixture(scope="class")
    def db_connection(self):
        """Create test database connection"""
        # Use test database configuration
        conn = psycopg2.connect(
            host="localhost",
            port=5432,
            database="workflow_test_db",
            user="postgres",
            password="",
            cursor_factory=psycopg2.extras.RealDictCursor
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        yield conn
        conn.close()
    
    @pytest.fixture(scope="function")
    def clean_database(self, db_connection):
        """Clean database before each test"""
        with db_connection.cursor() as cursor:
            # Clean up in reverse dependency order
            cursor.execute("TRUNCATE TABLE workflow_events CASCADE")
            cursor.execute("TRUNCATE TABLE validations CASCADE")
            cursor.execute("TRUNCATE TABLE dependencies CASCADE")
            cursor.execute("TRUNCATE TABLE task_executions CASCADE")
            cursor.execute("TRUNCATE TABLE pull_requests CASCADE")
            cursor.execute("TRUNCATE TABLE tasks CASCADE")
            cursor.execute("TRUNCATE TABLE agent_configurations CASCADE")
            cursor.execute("TRUNCATE TABLE projects CASCADE")
        yield
    
    def test_project_creation(self, db_connection, clean_database):
        """Test project creation and constraints"""
        with db_connection.cursor() as cursor:
            project_id = str(uuid.uuid4())
            
            # Test successful project creation
            cursor.execute("""
                INSERT INTO projects (id, name, description, repository_url, repository_name)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                project_id,
                "test-project",
                "Test project description",
                "https://github.com/test/repo",
                "test-repo"
            ))
            
            # Verify project was created
            cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
            project = cursor.fetchone()
            assert project is not None
            assert project['name'] == "test-project"
            assert project['default_branch'] == "main"
            
            # Test unique constraint
            with pytest.raises(psycopg2.IntegrityError):
                cursor.execute("""
                    INSERT INTO projects (name, repository_url)
                    VALUES (%s, %s)
                """, ("test-project", "https://github.com/test/repo2"))
    
    def test_task_creation_and_constraints(self, db_connection, clean_database):
        """Test task creation with various constraints"""
        with db_connection.cursor() as cursor:
            # Create project first
            project_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO projects (id, name, repository_url)
                VALUES (%s, %s, %s)
            """, (project_id, "test-project", "https://github.com/test/repo"))
            
            # Test successful task creation
            task_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO tasks (id, project_id, title, description, priority, requirements, context)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                task_id,
                project_id,
                "Test Task",
                "Test task description",
                5,
                json.dumps({"type": "feature", "complexity": "medium"}),
                json.dumps({"files": ["src/main.py"], "repository": {"branch": "main"}})
            ))
            
            # Verify task was created
            cursor.execute("SELECT * FROM tasks WHERE id = %s", (task_id,))
            task = cursor.fetchone()
            assert task is not None
            assert task['title'] == "Test Task"
            assert task['priority'] == 5
            assert task['status'] == 'pending'
            
            # Test priority constraint
            with pytest.raises(psycopg2.IntegrityError):
                cursor.execute("""
                    INSERT INTO tasks (project_id, title, priority)
                    VALUES (%s, %s, %s)
                """, (project_id, "Invalid Priority Task", 15))
            
            # Test title length constraint
            with pytest.raises(psycopg2.IntegrityError):
                cursor.execute("""
                    INSERT INTO tasks (project_id, title)
                    VALUES (%s, %s)
                """, (project_id, "AB"))  # Too short
    
    def test_task_status_transitions(self, db_connection, clean_database):
        """Test task status transition validation"""
        with db_connection.cursor() as cursor:
            # Setup
            project_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO projects (id, name, repository_url)
                VALUES (%s, %s, %s)
            """, (project_id, "test-project", "https://github.com/test/repo"))
            
            task_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO tasks (id, project_id, title, status)
                VALUES (%s, %s, %s, %s)
            """, (task_id, project_id, "Test Task", "pending"))
            
            # Test valid transition: pending -> in_progress
            cursor.execute("""
                UPDATE tasks SET status = 'in_progress', assigned_agent = 'codegen'
                WHERE id = %s
            """, (task_id,))
            
            # Test valid transition: in_progress -> validation
            cursor.execute("""
                UPDATE tasks SET status = 'validation'
                WHERE id = %s
            """, (task_id,))
            
            # Test valid transition: validation -> completed
            cursor.execute("""
                UPDATE tasks SET status = 'completed', completed_at = NOW()
                WHERE id = %s
            """, (task_id,))
            
            # Test invalid transition from completed
            with pytest.raises(psycopg2.IntegrityError):
                cursor.execute("""
                    UPDATE tasks SET status = 'pending'
                    WHERE id = %s
                """, (task_id,))
    
    def test_task_execution_tracking(self, db_connection, clean_database):
        """Test task execution creation and tracking"""
        with db_connection.cursor() as cursor:
            # Setup
            project_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO projects (id, name, repository_url)
                VALUES (%s, %s, %s)
            """, (project_id, "test-project", "https://github.com/test/repo"))
            
            task_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO tasks (id, project_id, title)
                VALUES (%s, %s, %s)
            """, (task_id, project_id, "Test Task"))
            
            # Create task execution
            execution_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO task_executions (
                    id, task_id, agent_type, execution_status, 
                    input_context, started_at
                )
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                execution_id,
                task_id,
                "codegen",
                "running",
                json.dumps({"agent_config": {"model": "gpt-4"}}),
                datetime.now()
            ))
            
            # Update execution to completed
            cursor.execute("""
                UPDATE task_executions 
                SET execution_status = 'completed', 
                    completed_at = NOW(),
                    output_results = %s,
                    memory_usage_mb = 256,
                    cpu_time_ms = 5000
                WHERE id = %s
            """, (
                json.dumps({"artifacts": ["generated_code.py"], "status": "success"}),
                execution_id
            ))
            
            # Verify execution was updated
            cursor.execute("SELECT * FROM task_executions WHERE id = %s", (execution_id,))
            execution = cursor.fetchone()
            assert execution['execution_status'] == 'completed'
            assert execution['duration'] is not None
            assert execution['memory_usage_mb'] == 256
    
    def test_pull_request_management(self, db_connection, clean_database):
        """Test pull request lifecycle management"""
        with db_connection.cursor() as cursor:
            # Setup
            project_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO projects (id, name, repository_url)
                VALUES (%s, %s, %s)
            """, (project_id, "test-project", "https://github.com/test/repo"))
            
            task_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO tasks (id, project_id, title)
                VALUES (%s, %s, %s)
            """, (task_id, project_id, "Test Task"))
            
            # Create pull request
            pr_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO pull_requests (
                    id, task_id, project_id, pr_number, repository_url,
                    branch_name, title, description, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                pr_id,
                task_id,
                project_id,
                123,
                "https://github.com/test/repo",
                "feature/test-branch",
                "Test PR",
                "Test pull request description",
                "draft"
            ))
            
            # Test PR status transitions
            cursor.execute("""
                UPDATE pull_requests SET status = 'open'
                WHERE id = %s
            """, (pr_id,))
            
            cursor.execute("""
                UPDATE pull_requests SET status = 'review_requested'
                WHERE id = %s
            """, (pr_id,))
            
            cursor.execute("""
                UPDATE pull_requests SET status = 'approved'
                WHERE id = %s
            """, (pr_id,))
            
            cursor.execute("""
                UPDATE pull_requests SET status = 'merged', merged_at = NOW()
                WHERE id = %s
            """, (pr_id,))
            
            # Verify final state
            cursor.execute("SELECT * FROM pull_requests WHERE id = %s", (pr_id,))
            pr = cursor.fetchone()
            assert pr['status'] == 'merged'
            assert pr['merged_at'] is not None
    
    def test_validation_system(self, db_connection, clean_database):
        """Test validation tracking system"""
        with db_connection.cursor() as cursor:
            # Setup
            project_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO projects (id, name, repository_url)
                VALUES (%s, %s, %s)
            """, (project_id, "test-project", "https://github.com/test/repo"))
            
            pr_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO pull_requests (
                    id, project_id, pr_number, repository_url,
                    branch_name, title, status
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                pr_id,
                project_id,
                123,
                "https://github.com/test/repo",
                "feature/test-branch",
                "Test PR",
                "open"
            ))
            
            # Create validations
            validations = [
                ("tests", "pytest", "passed", 95.5),
                ("linting", "eslint", "failed", 60.0),
                ("security", "sonarqube", "warning", 85.0),
                ("performance", "lighthouse", "passed", 92.0)
            ]
            
            for validation_type, validator_name, result, score in validations:
                validation_id = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO validations (
                        id, pr_id, validation_type, validator_name,
                        result, score, details, started_at, completed_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    validation_id,
                    pr_id,
                    validation_type,
                    validator_name,
                    result,
                    score,
                    json.dumps({"details": f"{validation_type} validation details"}),
                    datetime.now() - timedelta(minutes=5),
                    datetime.now()
                ))
            
            # Test validation summary view
            cursor.execute("""
                SELECT * FROM pr_validation_status WHERE pr_id = %s
            """, (pr_id,))
            
            validation_summary = cursor.fetchone()
            assert validation_summary['total_validations'] == 4
            assert validation_summary['passed_validations'] == 2
            assert validation_summary['failed_validations'] == 1
            assert validation_summary['warning_validations'] == 1
    
    def test_dependency_management(self, db_connection, clean_database):
        """Test task dependency management"""
        with db_connection.cursor() as cursor:
            # Setup
            project_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO projects (id, name, repository_url)
                VALUES (%s, %s, %s)
            """, (project_id, "test-project", "https://github.com/test/repo"))
            
            # Create tasks
            task1_id = str(uuid.uuid4())
            task2_id = str(uuid.uuid4())
            task3_id = str(uuid.uuid4())
            
            for task_id, title in [(task1_id, "Task 1"), (task2_id, "Task 2"), (task3_id, "Task 3")]:
                cursor.execute("""
                    INSERT INTO tasks (id, project_id, title)
                    VALUES (%s, %s, %s)
                """, (task_id, project_id, title))
            
            # Create dependencies: Task 2 depends on Task 1, Task 3 depends on Task 2
            cursor.execute("""
                INSERT INTO dependencies (dependent_task_id, dependency_task_id, dependency_type)
                VALUES (%s, %s, %s)
            """, (task2_id, task1_id, "blocks"))
            
            cursor.execute("""
                INSERT INTO dependencies (dependent_task_id, dependency_task_id, dependency_type)
                VALUES (%s, %s, %s)
            """, (task3_id, task2_id, "blocks"))
            
            # Test circular dependency prevention
            with pytest.raises(psycopg2.IntegrityError):
                cursor.execute("""
                    INSERT INTO dependencies (dependent_task_id, dependency_task_id, dependency_type)
                    VALUES (%s, %s, %s)
                """, (task1_id, task3_id, "blocks"))  # This would create a cycle
            
            # Test dependency satisfaction
            cursor.execute("""
                UPDATE tasks SET status = 'completed', completed_at = NOW()
                WHERE id = %s
            """, (task1_id,))
            
            # Check that dependency was automatically satisfied
            cursor.execute("""
                SELECT is_satisfied FROM dependencies 
                WHERE dependent_task_id = %s AND dependency_task_id = %s
            """, (task2_id, task1_id))
            
            dependency = cursor.fetchone()
            assert dependency['is_satisfied'] is True
    
    def test_workflow_events_audit_trail(self, db_connection, clean_database):
        """Test workflow events audit trail"""
        with db_connection.cursor() as cursor:
            # Setup
            project_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO projects (id, name, repository_url)
                VALUES (%s, %s, %s)
            """, (project_id, "test-project", "https://github.com/test/repo"))
            
            # Create task (should trigger audit event)
            task_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO tasks (id, project_id, title, created_by)
                VALUES (%s, %s, %s, %s)
            """, (task_id, project_id, "Test Task", "test_user"))
            
            # Check that audit event was created
            cursor.execute("""
                SELECT * FROM workflow_events 
                WHERE event_type = 'task_created' AND task_id = %s
            """, (task_id,))
            
            events = cursor.fetchall()
            assert len(events) >= 1
            
            event = events[0]
            assert event['event_category'] == 'task'
            assert event['action'] == 'INSERT'
            assert event['project_id'] == project_id
            
            # Update task (should trigger another audit event)
            cursor.execute("""
                UPDATE tasks SET status = 'in_progress', assigned_agent = 'codegen'
                WHERE id = %s
            """, (task_id,))
            
            # Check for update event
            cursor.execute("""
                SELECT * FROM workflow_events 
                WHERE event_type = 'task_updated' AND task_id = %s
            """, (task_id,))
            
            update_events = cursor.fetchall()
            assert len(update_events) >= 1
    
    def test_jsonb_queries_and_indexes(self, db_connection, clean_database):
        """Test JSONB functionality and query performance"""
        with db_connection.cursor() as cursor:
            # Setup
            project_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO projects (id, name, repository_url)
                VALUES (%s, %s, %s)
            """, (project_id, "test-project", "https://github.com/test/repo"))
            
            # Create tasks with complex JSONB data
            tasks_data = [
                {
                    "title": "Frontend Task",
                    "requirements": {"type": "frontend", "framework": "react", "priority": 1},
                    "context": {"files": ["src/components/App.js"], "repository": {"branch": "main"}},
                    "tags": ["frontend", "react", "ui"]
                },
                {
                    "title": "Backend Task", 
                    "requirements": {"type": "backend", "language": "python", "priority": 2},
                    "context": {"files": ["src/api/main.py"], "repository": {"branch": "develop"}},
                    "tags": ["backend", "python", "api"]
                },
                {
                    "title": "Database Task",
                    "requirements": {"type": "database", "engine": "postgresql", "priority": 1},
                    "context": {"files": ["migrations/001_initial.sql"], "repository": {"branch": "main"}},
                    "tags": ["database", "postgresql", "migration"]
                }
            ]
            
            task_ids = []
            for task_data in tasks_data:
                task_id = str(uuid.uuid4())
                task_ids.append(task_id)
                cursor.execute("""
                    INSERT INTO tasks (id, project_id, title, requirements, context, tags)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (
                    task_id,
                    project_id,
                    task_data["title"],
                    json.dumps(task_data["requirements"]),
                    json.dumps(task_data["context"]),
                    json.dumps(task_data["tags"])
                ))
            
            # Test JSONB queries
            
            # Query by requirement type
            cursor.execute("""
                SELECT id, title FROM tasks 
                WHERE requirements->>'type' = 'frontend'
            """)
            frontend_tasks = cursor.fetchall()
            assert len(frontend_tasks) == 1
            assert frontend_tasks[0]['title'] == "Frontend Task"
            
            # Query by priority in requirements
            cursor.execute("""
                SELECT id, title FROM tasks 
                WHERE (requirements->'priority')::int = 1
            """)
            priority_1_tasks = cursor.fetchall()
            assert len(priority_1_tasks) == 2
            
            # Query by tag containment
            cursor.execute("""
                SELECT id, title FROM tasks 
                WHERE tags ? 'python'
            """)
            python_tasks = cursor.fetchall()
            assert len(python_tasks) == 1
            assert python_tasks[0]['title'] == "Backend Task"
            
            # Query by file path in context
            cursor.execute("""
                SELECT id, title FROM tasks 
                WHERE context->'files' ? 'src/components/App.js'
            """)
            component_tasks = cursor.fetchall()
            assert len(component_tasks) == 1
            
            # Test GIN index usage (this would need EXPLAIN ANALYZE in real testing)
            cursor.execute("""
                SELECT id, title FROM tasks 
                WHERE requirements @> '{"type": "backend"}'
            """)
            backend_tasks = cursor.fetchall()
            assert len(backend_tasks) == 1
    
    def test_views_and_aggregations(self, db_connection, clean_database):
        """Test database views and aggregation queries"""
        with db_connection.cursor() as cursor:
            # Setup test data
            project_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO projects (id, name, repository_url)
                VALUES (%s, %s, %s)
            """, (project_id, "test-project", "https://github.com/test/repo"))
            
            # Create tasks with different statuses
            task_statuses = ["pending", "in_progress", "validation", "completed", "failed"]
            task_ids = []
            
            for i, status in enumerate(task_statuses):
                task_id = str(uuid.uuid4())
                task_ids.append(task_id)
                
                completed_at = datetime.now() if status == "completed" else None
                cursor.execute("""
                    INSERT INTO tasks (id, project_id, title, status, completed_at)
                    VALUES (%s, %s, %s, %s, %s)
                """, (task_id, project_id, f"Task {i+1}", status, completed_at))
                
                # Create executions for some tasks
                if status in ["completed", "failed"]:
                    execution_id = str(uuid.uuid4())
                    cursor.execute("""
                        INSERT INTO task_executions (
                            id, task_id, agent_type, execution_status,
                            started_at, completed_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        execution_id,
                        task_id,
                        "codegen",
                        "completed" if status == "completed" else "failed",
                        datetime.now() - timedelta(minutes=10),
                        datetime.now() - timedelta(minutes=5)
                    ))
            
            # Test active_tasks view
            cursor.execute("SELECT * FROM active_tasks")
            active_tasks = cursor.fetchall()
            # Should include pending, in_progress, validation (3 tasks)
            assert len(active_tasks) == 3
            
            # Test task_execution_summary view
            cursor.execute("SELECT * FROM task_execution_summary")
            execution_summaries = cursor.fetchall()
            assert len(execution_summaries) == len(task_statuses)
            
            # Find completed task summary
            completed_summary = next(
                (s for s in execution_summaries if s['task_status'] == 'completed'),
                None
            )
            assert completed_summary is not None
            assert completed_summary['total_executions'] == 1
            assert completed_summary['successful_executions'] == 1
    
    def test_performance_and_constraints(self, db_connection, clean_database):
        """Test performance constraints and data validation"""
        with db_connection.cursor() as cursor:
            # Setup
            project_id = str(uuid.uuid4())
            cursor.execute("""
                INSERT INTO projects (id, name, repository_url)
                VALUES (%s, %s, %s)
            """, (project_id, "test-project", "https://github.com/test/repo"))
            
            # Test JSONB depth constraint (should pass)
            task_id = str(uuid.uuid4())
            valid_requirements = {
                "type": "feature",
                "details": {
                    "complexity": "medium",
                    "estimated_hours": 8
                }
            }
            
            cursor.execute("""
                INSERT INTO tasks (id, project_id, title, requirements)
                VALUES (%s, %s, %s, %s)
            """, (task_id, project_id, "Valid Task", json.dumps(valid_requirements)))
            
            # Test array size constraint
            large_tags = [f"tag_{i}" for i in range(25)]  # Should be within limit
            cursor.execute("""
                UPDATE tasks SET tags = %s WHERE id = %s
            """, (json.dumps(large_tags), task_id))
            
            # Test constraint violation - too many tags
            too_many_tags = [f"tag_{i}" for i in range(60)]  # Should exceed limit
            with pytest.raises(psycopg2.IntegrityError):
                cursor.execute("""
                    UPDATE tasks SET tags = %s WHERE id = %s
                """, (json.dumps(too_many_tags), task_id))

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

