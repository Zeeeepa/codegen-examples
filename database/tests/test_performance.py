"""
Database Performance Tests
Tests query performance, index effectiveness, and scalability
"""

import pytest
import psycopg2
import psycopg2.extras
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import uuid
import time
import random
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

class TestDatabasePerformance:
    """Test database performance and scalability"""
    
    @pytest.fixture(scope="class")
    def db_connection(self):
        """Create test database connection"""
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
    def performance_data(self, db_connection):
        """Create performance test data"""
        with db_connection.cursor() as cursor:
            # Clean existing data
            cursor.execute("TRUNCATE TABLE workflow_events CASCADE")
            cursor.execute("TRUNCATE TABLE validations CASCADE")
            cursor.execute("TRUNCATE TABLE dependencies CASCADE")
            cursor.execute("TRUNCATE TABLE task_executions CASCADE")
            cursor.execute("TRUNCATE TABLE pull_requests CASCADE")
            cursor.execute("TRUNCATE TABLE tasks CASCADE")
            cursor.execute("TRUNCATE TABLE agent_configurations CASCADE")
            cursor.execute("TRUNCATE TABLE projects CASCADE")
            
            # Create test projects
            project_ids = []
            for i in range(10):
                project_id = str(uuid.uuid4())
                project_ids.append(project_id)
                cursor.execute("""
                    INSERT INTO projects (id, name, description, repository_url, repository_name)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    project_id,
                    f"performance-project-{i}",
                    f"Performance test project {i}",
                    f"https://github.com/test/repo-{i}",
                    f"repo-{i}"
                ))
            
            # Create test tasks (1000 tasks across projects)
            task_ids = []
            statuses = ["pending", "in_progress", "validation", "completed", "failed"]
            agent_types = ["codegen", "claude_code", "webhook_orchestrator"]
            
            for i in range(1000):
                task_id = str(uuid.uuid4())
                task_ids.append(task_id)
                project_id = random.choice(project_ids)
                status = random.choice(statuses)
                
                requirements = {
                    "type": random.choice(["feature", "bugfix", "enhancement", "refactor"]),
                    "priority": random.randint(1, 10),
                    "complexity": random.choice(["low", "medium", "high"]),
                    "estimated_hours": random.randint(1, 40)
                }
                
                context = {
                    "files": [f"src/file_{random.randint(1, 100)}.py" for _ in range(random.randint(1, 5))],
                    "repository": {
                        "branch": random.choice(["main", "develop", "feature/test"]),
                        "commit": f"abc{random.randint(1000, 9999)}"
                    },
                    "environment": random.choice(["development", "staging", "production"])
                }
                
                tags = [f"tag_{random.randint(1, 20)}" for _ in range(random.randint(1, 5))]
                
                cursor.execute("""
                    INSERT INTO tasks (
                        id, project_id, title, description, status, priority,
                        requirements, context, tags, assigned_agent,
                        created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    task_id,
                    project_id,
                    f"Performance Task {i}",
                    f"Performance test task description {i}",
                    status,
                    random.randint(1, 10),
                    json.dumps(requirements),
                    json.dumps(context),
                    json.dumps(tags),
                    random.choice(agent_types) if status != "pending" else None,
                    datetime.now() - timedelta(days=random.randint(0, 30)),
                    datetime.now() - timedelta(hours=random.randint(0, 24))
                ))
            
            # Create task executions (2000 executions)
            execution_statuses = ["queued", "running", "completed", "failed", "timeout"]
            for i in range(2000):
                execution_id = str(uuid.uuid4())
                task_id = random.choice(task_ids)
                agent_type = random.choice(agent_types)
                status = random.choice(execution_statuses)
                
                started_at = datetime.now() - timedelta(hours=random.randint(1, 72))
                completed_at = started_at + timedelta(minutes=random.randint(1, 120)) if status in ["completed", "failed", "timeout"] else None
                
                input_context = {
                    "agent_config": {"model": random.choice(["gpt-4", "gpt-3.5-turbo", "claude-3"])},
                    "parameters": {"temperature": random.uniform(0.1, 1.0)},
                    "context_size": random.randint(1000, 10000)
                }
                
                output_results = {
                    "artifacts": [f"output_{random.randint(1, 100)}.py" for _ in range(random.randint(0, 3))],
                    "status": "success" if status == "completed" else "error",
                    "metrics": {"lines_generated": random.randint(10, 500)}
                } if status in ["completed", "failed"] else {}
                
                cursor.execute("""
                    INSERT INTO task_executions (
                        id, task_id, agent_type, execution_status,
                        input_context, output_results, started_at, completed_at,
                        memory_usage_mb, cpu_time_ms
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    execution_id,
                    task_id,
                    agent_type,
                    status,
                    json.dumps(input_context),
                    json.dumps(output_results),
                    started_at,
                    completed_at,
                    random.randint(64, 2048),
                    random.randint(1000, 60000)
                ))
            
            # Create pull requests (500 PRs)
            pr_statuses = ["draft", "open", "review_requested", "approved", "merged", "closed"]
            for i in range(500):
                pr_id = str(uuid.uuid4())
                project_id = random.choice(project_ids)
                task_id = random.choice(task_ids) if random.random() > 0.3 else None
                
                cursor.execute("""
                    INSERT INTO pull_requests (
                        id, task_id, project_id, pr_number, repository_url,
                        branch_name, title, description, status, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    pr_id,
                    task_id,
                    project_id,
                    i + 1,
                    f"https://github.com/test/repo-{random.randint(0, 9)}",
                    f"feature/branch-{i}",
                    f"Performance PR {i}",
                    f"Performance test PR description {i}",
                    random.choice(pr_statuses),
                    datetime.now() - timedelta(days=random.randint(0, 14)),
                    datetime.now() - timedelta(hours=random.randint(0, 12))
                ))
        
        yield {
            "project_ids": project_ids,
            "task_ids": task_ids
        }
    
    def measure_query_time(self, cursor, query: str, params: tuple = None) -> float:
        """Measure query execution time"""
        start_time = time.time()
        cursor.execute(query, params)
        cursor.fetchall()  # Ensure all results are fetched
        end_time = time.time()
        return end_time - start_time
    
    def test_basic_query_performance(self, db_connection, performance_data):
        """Test basic query performance"""
        with db_connection.cursor() as cursor:
            # Test simple SELECT queries
            queries = [
                ("SELECT COUNT(*) FROM tasks", None),
                ("SELECT COUNT(*) FROM task_executions", None),
                ("SELECT COUNT(*) FROM pull_requests", None),
                ("SELECT * FROM tasks LIMIT 100", None),
                ("SELECT * FROM task_executions LIMIT 100", None)
            ]
            
            execution_times = []
            for query, params in queries:
                exec_time = self.measure_query_time(cursor, query, params)
                execution_times.append(exec_time)
                print(f"Query: {query[:50]}... - Time: {exec_time:.4f}s")
            
            # All basic queries should complete within 1 second
            assert all(t < 1.0 for t in execution_times), f"Slow queries detected: {execution_times}"
    
    def test_index_effectiveness(self, db_connection, performance_data):
        """Test index effectiveness for common queries"""
        with db_connection.cursor() as cursor:
            # Test indexed queries vs non-indexed
            indexed_queries = [
                # These should use indexes
                ("SELECT * FROM tasks WHERE project_id = %s", (performance_data["project_ids"][0],)),
                ("SELECT * FROM tasks WHERE status = 'pending'", None),
                ("SELECT * FROM tasks WHERE assigned_agent = 'codegen'", None),
                ("SELECT * FROM task_executions WHERE task_id = %s", (performance_data["task_ids"][0],)),
                ("SELECT * FROM task_executions WHERE agent_type = 'codegen'", None),
                ("SELECT * FROM pull_requests WHERE project_id = %s", (performance_data["project_ids"][0],)),
            ]
            
            for query, params in indexed_queries:
                exec_time = self.measure_query_time(cursor, query, params)
                print(f"Indexed query time: {exec_time:.4f}s - {query[:50]}...")
                
                # Indexed queries should be fast
                assert exec_time < 0.5, f"Slow indexed query: {query} took {exec_time:.4f}s"
    
    def test_jsonb_query_performance(self, db_connection, performance_data):
        """Test JSONB query performance"""
        with db_connection.cursor() as cursor:
            jsonb_queries = [
                # JSONB containment queries (should use GIN indexes)
                ("SELECT * FROM tasks WHERE requirements @> '{\"type\": \"feature\"}'", None),
                ("SELECT * FROM tasks WHERE context @> '{\"repository\": {\"branch\": \"main\"}}'", None),
                ("SELECT * FROM tasks WHERE tags ? 'tag_1'", None),
                
                # JSONB path queries
                ("SELECT * FROM tasks WHERE requirements->>'type' = 'feature'", None),
                ("SELECT * FROM tasks WHERE (requirements->'priority')::int > 5", None),
                ("SELECT * FROM task_executions WHERE input_context->>'agent_config' IS NOT NULL", None),
            ]
            
            for query, params in jsonb_queries:
                exec_time = self.measure_query_time(cursor, query, params)
                print(f"JSONB query time: {exec_time:.4f}s - {query[:50]}...")
                
                # JSONB queries should complete within reasonable time
                assert exec_time < 2.0, f"Slow JSONB query: {query} took {exec_time:.4f}s"
    
    def test_complex_aggregation_performance(self, db_connection, performance_data):
        """Test complex aggregation query performance"""
        with db_connection.cursor() as cursor:
            complex_queries = [
                # Task statistics by project
                ("""
                    SELECT 
                        p.name,
                        COUNT(t.id) as total_tasks,
                        COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks,
                        AVG(t.priority) as avg_priority
                    FROM projects p
                    LEFT JOIN tasks t ON p.id = t.project_id
                    GROUP BY p.id, p.name
                    ORDER BY total_tasks DESC
                """, None),
                
                # Execution performance by agent
                ("""
                    SELECT 
                        agent_type,
                        COUNT(*) as total_executions,
                        COUNT(CASE WHEN execution_status = 'completed' THEN 1 END) as successful,
                        AVG(EXTRACT(EPOCH FROM duration)) as avg_duration_seconds,
                        AVG(memory_usage_mb) as avg_memory_mb
                    FROM task_executions
                    WHERE completed_at IS NOT NULL
                    GROUP BY agent_type
                """, None),
                
                # Daily task creation trend
                ("""
                    SELECT 
                        DATE(created_at) as date,
                        COUNT(*) as tasks_created,
                        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_same_day
                    FROM tasks
                    WHERE created_at >= NOW() - INTERVAL '30 days'
                    GROUP BY DATE(created_at)
                    ORDER BY date DESC
                """, None),
            ]
            
            for query, params in complex_queries:
                exec_time = self.measure_query_time(cursor, query, params)
                print(f"Complex query time: {exec_time:.4f}s")
                
                # Complex aggregations should complete within reasonable time
                assert exec_time < 3.0, f"Slow complex query took {exec_time:.4f}s"
    
    def test_view_performance(self, db_connection, performance_data):
        """Test database view performance"""
        with db_connection.cursor() as cursor:
            view_queries = [
                ("SELECT * FROM active_tasks LIMIT 100", None),
                ("SELECT * FROM task_execution_summary LIMIT 100", None),
                ("SELECT * FROM pr_validation_status LIMIT 100", None),
            ]
            
            for query, params in view_queries:
                exec_time = self.measure_query_time(cursor, query, params)
                print(f"View query time: {exec_time:.4f}s - {query}")
                
                # Views should perform well
                assert exec_time < 1.0, f"Slow view query: {query} took {exec_time:.4f}s"
    
    def test_concurrent_access_performance(self, db_connection, performance_data):
        """Test performance under concurrent access"""
        def execute_concurrent_queries(connection_params: dict, queries: List[tuple], thread_id: int) -> List[float]:
            """Execute queries in a separate thread"""
            conn = psycopg2.connect(**connection_params, cursor_factory=psycopg2.extras.RealDictCursor)
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            
            execution_times = []
            try:
                with conn.cursor() as cursor:
                    for query, params in queries:
                        start_time = time.time()
                        cursor.execute(query, params)
                        cursor.fetchall()
                        exec_time = time.time() - start_time
                        execution_times.append(exec_time)
            finally:
                conn.close()
            
            return execution_times
        
        # Connection parameters
        conn_params = {
            'host': 'localhost',
            'port': 5432,
            'database': 'workflow_test_db',
            'user': 'postgres',
            'password': ''
        }
        
        # Queries to execute concurrently
        concurrent_queries = [
            ("SELECT COUNT(*) FROM tasks WHERE status = 'pending'", None),
            ("SELECT * FROM tasks WHERE project_id = %s LIMIT 10", (performance_data["project_ids"][0],)),
            ("SELECT * FROM task_executions WHERE agent_type = 'codegen' LIMIT 10", None),
            ("SELECT * FROM active_tasks LIMIT 20", None),
        ]
        
        # Execute with multiple threads
        num_threads = 5
        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = []
            for i in range(num_threads):
                future = executor.submit(
                    execute_concurrent_queries,
                    conn_params,
                    concurrent_queries,
                    i
                )
                futures.append(future)
            
            all_execution_times = []
            for future in as_completed(futures):
                thread_times = future.result()
                all_execution_times.extend(thread_times)
        
        # Analyze results
        avg_time = statistics.mean(all_execution_times)
        max_time = max(all_execution_times)
        
        print(f"Concurrent access - Avg time: {avg_time:.4f}s, Max time: {max_time:.4f}s")
        print(f"Total queries executed: {len(all_execution_times)}")
        
        # Performance should not degrade significantly under concurrent load
        assert avg_time < 1.0, f"Average query time too high under concurrent load: {avg_time:.4f}s"
        assert max_time < 3.0, f"Maximum query time too high under concurrent load: {max_time:.4f}s"
    
    def test_large_result_set_performance(self, db_connection, performance_data):
        """Test performance with large result sets"""
        with db_connection.cursor() as cursor:
            # Test queries that return large result sets
            large_queries = [
                ("SELECT * FROM tasks", None),
                ("SELECT * FROM task_executions", None),
                ("SELECT t.*, te.* FROM tasks t JOIN task_executions te ON t.id = te.task_id", None),
            ]
            
            for query, params in large_queries:
                start_time = time.time()
                cursor.execute(query, params)
                
                # Fetch results in batches to test streaming performance
                batch_count = 0
                while True:
                    batch = cursor.fetchmany(100)
                    if not batch:
                        break
                    batch_count += 1
                
                exec_time = time.time() - start_time
                print(f"Large result set query time: {exec_time:.4f}s, Batches: {batch_count}")
                
                # Large queries should complete within reasonable time
                assert exec_time < 5.0, f"Large result set query too slow: {exec_time:.4f}s"
    
    def test_index_usage_analysis(self, db_connection, performance_data):
        """Analyze index usage patterns"""
        with db_connection.cursor() as cursor:
            # Get index usage statistics
            cursor.execute("""
                SELECT 
                    schemaname,
                    tablename,
                    indexname,
                    idx_scan,
                    idx_tup_read,
                    idx_tup_fetch
                FROM pg_stat_user_indexes 
                WHERE schemaname = 'public'
                ORDER BY idx_scan DESC
            """)
            
            index_stats = cursor.fetchall()
            
            # Print index usage for analysis
            print("\nIndex Usage Statistics:")
            print("=" * 80)
            for stat in index_stats[:20]:  # Top 20 most used indexes
                print(f"{stat['tablename']}.{stat['indexname']}: "
                      f"scans={stat['idx_scan']}, "
                      f"tuples_read={stat['idx_tup_read']}")
            
            # Verify that key indexes are being used
            key_indexes = [
                'idx_tasks_project_status',
                'idx_tasks_status_priority',
                'idx_task_executions_task_status',
                'idx_pull_requests_project_status'
            ]
            
            used_indexes = {stat['indexname'] for stat in index_stats if stat['idx_scan'] > 0}
            
            for key_index in key_indexes:
                if key_index in used_indexes:
                    print(f"✓ Key index {key_index} is being used")
                else:
                    print(f"⚠ Key index {key_index} may not be used effectively")
    
    def test_query_plan_analysis(self, db_connection, performance_data):
        """Analyze query execution plans"""
        with db_connection.cursor() as cursor:
            # Test queries with EXPLAIN ANALYZE
            test_queries = [
                ("SELECT * FROM tasks WHERE project_id = %s", (performance_data["project_ids"][0],)),
                ("SELECT * FROM tasks WHERE requirements @> '{\"type\": \"feature\"}'", None),
                ("SELECT COUNT(*) FROM task_executions WHERE agent_type = 'codegen'", None),
            ]
            
            for query, params in test_queries:
                explain_query = f"EXPLAIN (ANALYZE, BUFFERS) {query}"
                cursor.execute(explain_query, params)
                plan = cursor.fetchall()
                
                print(f"\nQuery Plan for: {query[:50]}...")
                print("-" * 60)
                for row in plan:
                    print(row[0])
                
                # Check for index usage in plan
                plan_text = ' '.join([row[0] for row in plan])
                if 'Index Scan' in plan_text or 'Bitmap Index Scan' in plan_text:
                    print("✓ Query uses index")
                elif 'Seq Scan' in plan_text:
                    print("⚠ Query uses sequential scan")

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

