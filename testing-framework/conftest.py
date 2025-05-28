"""
Global pytest configuration and fixtures for the testing framework.
"""
import pytest
import asyncio
import json
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, AsyncMock
from datetime import datetime, timedelta
import os
import sys

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers and settings."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test"
    )
    config.addinivalue_line(
        "markers", "performance: mark test as a performance test"
    )
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
    config.addinivalue_line(
        "markers", "database: mark test as requiring database"
    )
    config.addinivalue_line(
        "markers", "network: mark test as requiring network access"
    )
    config.addinivalue_line(
        "markers", "docker: mark test as requiring Docker"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add markers based on test file location
        if "unit-tests" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration-tests" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "performance-tests" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "security-tests" in str(item.fspath):
            item.add_marker(pytest.mark.security)
        
        # Mark slow tests
        if "slow" in item.name.lower() or "load" in item.name.lower():
            item.add_marker(pytest.mark.slow)


# Async test support
@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# Database fixtures
@pytest.fixture(scope="session")
def database_url():
    """Provide database URL for testing."""
    return os.getenv("TEST_DATABASE_URL", "sqlite:///:memory:")


@pytest.fixture
def mock_database_session():
    """Provide a mock database session."""
    session = Mock()
    session.add = Mock()
    session.commit = Mock()
    session.rollback = Mock()
    session.close = Mock()
    session.query = Mock()
    return session


@pytest.fixture
def sample_task_data():
    """Provide sample task data for testing."""
    return {
        "id": "test_task_001",
        "title": "Test Task",
        "description": "A test task for unit testing",
        "status": "pending",
        "priority": 3,
        "assignee_id": "test_user_001",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
        "metadata": {
            "source": "test",
            "category": "testing",
            "estimated_hours": 2,
            "tags": ["test", "unit"]
        }
    }


@pytest.fixture
def sample_workflow_data():
    """Provide sample workflow data for testing."""
    return {
        "id": "test_workflow_001",
        "name": "Test Workflow",
        "description": "A test workflow for unit testing",
        "steps": [
            {
                "id": "step_1",
                "name": "Initialize",
                "type": "initialization",
                "config": {"timeout": 30}
            },
            {
                "id": "step_2",
                "name": "Process",
                "type": "processing",
                "config": {"batch_size": 10}
            }
        ],
        "status": "active",
        "created_at": datetime.utcnow()
    }


# MCP Server fixtures
@pytest.fixture
def mock_mcp_server():
    """Provide a mock MCP server."""
    server = AsyncMock()
    server.start = AsyncMock()
    server.stop = AsyncMock()
    server.handle_request = AsyncMock()
    return server


@pytest.fixture
def mcp_request_data():
    """Provide sample MCP request data."""
    return {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/call",
        "params": {
            "name": "create_task",
            "arguments": {
                "title": "Test Task",
                "description": "Test Description"
            }
        }
    }


# GitHub webhook fixtures
@pytest.fixture
def github_webhook_payload():
    """Provide sample GitHub webhook payload."""
    return {
        "action": "opened",
        "pull_request": {
            "id": 123456,
            "number": 42,
            "title": "Test PR",
            "body": "Test pull request",
            "head": {
                "ref": "feature/test",
                "sha": "abc123"
            },
            "base": {
                "ref": "main",
                "sha": "def456"
            }
        },
        "repository": {
            "name": "test-repo",
            "full_name": "org/test-repo"
        }
    }


# File system fixtures
@pytest.fixture
def temp_directory():
    """Provide a temporary directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir)


@pytest.fixture
def sample_test_files(temp_directory):
    """Create sample test files in temporary directory."""
    files = {}
    
    # Create Python test file
    python_file = temp_directory / "test_sample.py"
    python_content = '''
def test_example():
    assert True

def test_another():
    assert 1 + 1 == 2
'''
    python_file.write_text(python_content)
    files['python'] = python_file
    
    # Create JSON test data
    json_file = temp_directory / "test_data.json"
    json_data = {"test": True, "data": [1, 2, 3]}
    json_file.write_text(json.dumps(json_data, indent=2))
    files['json'] = json_file
    
    # Create configuration file
    config_file = temp_directory / "test_config.yaml"
    config_content = '''
test:
  enabled: true
  timeout: 30
  retries: 3
'''
    config_file.write_text(config_content)
    files['config'] = config_file
    
    return files


# Performance testing fixtures
@pytest.fixture
def performance_metrics():
    """Provide performance metrics for testing."""
    return {
        "response_time_ms": 150.5,
        "throughput_rps": 250.0,
        "memory_usage_mb": 128.0,
        "cpu_usage_percent": 45.2,
        "error_rate_percent": 0.1
    }


@pytest.fixture
def benchmark_data():
    """Provide benchmark data for performance testing."""
    return {
        "test_name": "api_endpoint_benchmark",
        "iterations": 1000,
        "min_time": 0.001,
        "max_time": 0.500,
        "mean_time": 0.150,
        "median_time": 0.145,
        "std_dev": 0.025,
        "percentiles": {
            "50": 0.145,
            "90": 0.200,
            "95": 0.250,
            "99": 0.400
        }
    }


# Security testing fixtures
@pytest.fixture
def security_scan_results():
    """Provide security scan results for testing."""
    return {
        "scan_id": "security_scan_001",
        "target": "http://localhost:8000",
        "scan_type": "comprehensive",
        "start_time": datetime.utcnow() - timedelta(minutes=30),
        "end_time": datetime.utcnow(),
        "alerts": [
            {
                "id": "alert_001",
                "risk": "Medium",
                "confidence": "High",
                "name": "SQL Injection",
                "description": "Possible SQL injection vulnerability",
                "url": "http://localhost:8000/api/users",
                "param": "id"
            },
            {
                "id": "alert_002",
                "risk": "Low",
                "confidence": "Medium",
                "name": "Missing Security Headers",
                "description": "Missing X-Frame-Options header",
                "url": "http://localhost:8000/",
                "param": ""
            }
        ],
        "summary": {
            "high_risk": 0,
            "medium_risk": 1,
            "low_risk": 1,
            "informational": 0
        }
    }


# Coverage testing fixtures
@pytest.fixture
def coverage_data():
    """Provide coverage data for testing."""
    return {
        "files": {
            "src/main.py": {
                "statements": 100,
                "missing": 10,
                "covered": 90,
                "coverage_percentage": 90.0,
                "missing_lines": [15, 16, 25, 26, 27, 35, 45, 46, 55, 65]
            },
            "src/utils.py": {
                "statements": 50,
                "missing": 5,
                "covered": 45,
                "coverage_percentage": 90.0,
                "missing_lines": [12, 23, 34, 45, 56]
            }
        },
        "summary": {
            "total_statements": 150,
            "covered_statements": 135,
            "missing_statements": 15,
            "coverage_percentage": 90.0
        }
    }


# Mock external services
@pytest.fixture
def mock_github_api():
    """Provide a mock GitHub API client."""
    api = Mock()
    api.get_repo = Mock()
    api.create_pull_request = Mock()
    api.get_pull_request = Mock()
    api.create_issue = Mock()
    api.get_issue = Mock()
    return api


@pytest.fixture
def mock_claude_api():
    """Provide a mock Claude API client."""
    api = AsyncMock()
    api.messages = AsyncMock()
    api.messages.create = AsyncMock(return_value=Mock(
        content=[Mock(text="Mock Claude response")]
    ))
    return api


@pytest.fixture
def mock_codegen_client():
    """Provide a mock Codegen client."""
    client = Mock()
    client.create_agent = Mock()
    client.execute_task = Mock()
    client.get_results = Mock()
    return client


# Environment fixtures
@pytest.fixture(autouse=True)
def test_environment():
    """Set up test environment variables."""
    original_env = os.environ.copy()
    
    # Set test environment variables
    test_env = {
        "ENVIRONMENT": "test",
        "DEBUG": "true",
        "LOG_LEVEL": "debug",
        "DATABASE_URL": "sqlite:///:memory:",
        "REDIS_URL": "redis://localhost:6379/1",
        "SECRET_KEY": "test-secret-key",
        "API_BASE_URL": "http://localhost:8000",
        "MCP_SERVER_URL": "http://localhost:9000"
    }
    
    os.environ.update(test_env)
    
    yield
    
    # Restore original environment
    os.environ.clear()
    os.environ.update(original_env)


# Cleanup fixtures
@pytest.fixture(autouse=True)
def cleanup_after_test():
    """Clean up after each test."""
    yield
    
    # Clean up any temporary files, connections, etc.
    # This runs after each test
    pass


# Parametrized fixtures for different test scenarios
@pytest.fixture(params=["pending", "in_progress", "completed", "failed"])
def task_status(request):
    """Parametrized fixture for different task statuses."""
    return request.param


@pytest.fixture(params=[1, 2, 3, 4, 5])
def task_priority(request):
    """Parametrized fixture for different task priorities."""
    return request.param


@pytest.fixture(params=["unit", "integration", "performance", "security"])
def test_category(request):
    """Parametrized fixture for different test categories."""
    return request.param


# Factory fixtures
@pytest.fixture
def task_factory():
    """Factory for creating test tasks."""
    def _create_task(**kwargs):
        default_data = {
            "id": f"task_{datetime.now().timestamp()}",
            "title": "Test Task",
            "description": "Test Description",
            "status": "pending",
            "priority": 3,
            "assignee_id": "test_user",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "metadata": {"source": "test"}
        }
        default_data.update(kwargs)
        return default_data
    
    return _create_task


@pytest.fixture
def workflow_factory():
    """Factory for creating test workflows."""
    def _create_workflow(**kwargs):
        default_data = {
            "id": f"workflow_{datetime.now().timestamp()}",
            "name": "Test Workflow",
            "description": "Test Description",
            "steps": [],
            "status": "active",
            "created_at": datetime.utcnow()
        }
        default_data.update(kwargs)
        return default_data
    
    return _create_workflow


# Utility fixtures
@pytest.fixture
def assert_timing():
    """Utility for asserting execution timing."""
    def _assert_timing(func, max_time_ms=1000):
        import time
        start_time = time.time()
        result = func()
        end_time = time.time()
        
        execution_time_ms = (end_time - start_time) * 1000
        assert execution_time_ms <= max_time_ms, f"Execution took {execution_time_ms:.2f}ms, expected <= {max_time_ms}ms"
        
        return result
    
    return _assert_timing


@pytest.fixture
def capture_logs():
    """Utility for capturing log messages during tests."""
    import logging
    from io import StringIO
    
    log_capture = StringIO()
    handler = logging.StreamHandler(log_capture)
    handler.setLevel(logging.DEBUG)
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.DEBUG)
    
    yield log_capture
    
    # Clean up
    root_logger.removeHandler(handler)


# Session-scoped fixtures for expensive setup
@pytest.fixture(scope="session")
def test_database():
    """Set up test database for the session."""
    # This would set up a real test database
    # For now, we'll just return a mock
    return Mock()


@pytest.fixture(scope="session")
def test_redis():
    """Set up test Redis for the session."""
    # This would set up a real test Redis instance
    # For now, we'll just return a mock
    return Mock()


# Skip conditions
def pytest_runtest_setup(item):
    """Set up conditions for skipping tests."""
    # Skip Docker tests if Docker is not available
    if "docker" in item.keywords:
        docker_available = shutil.which("docker") is not None
        if not docker_available:
            pytest.skip("Docker not available")
    
    # Skip network tests if no network access
    if "network" in item.keywords:
        # Simple network check
        import socket
        try:
            socket.create_connection(("8.8.8.8", 53), timeout=3)
        except OSError:
            pytest.skip("No network access")
    
    # Skip slow tests unless explicitly requested
    if "slow" in item.keywords and not item.config.getoption("--runslow", default=False):
        pytest.skip("Slow test skipped (use --runslow to run)")


def pytest_addoption(parser):
    """Add custom command line options."""
    parser.addoption(
        "--runslow", action="store_true", default=False,
        help="Run slow tests"
    )
    parser.addoption(
        "--runintegration", action="store_true", default=False,
        help="Run integration tests"
    )
    parser.addoption(
        "--runperformance", action="store_true", default=False,
        help="Run performance tests"
    )
    parser.addoption(
        "--runsecurity", action="store_true", default=False,
        help="Run security tests"
    )

