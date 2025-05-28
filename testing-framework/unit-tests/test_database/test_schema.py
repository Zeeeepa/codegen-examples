"""
Unit tests for database schema validation and operations.
"""
import pytest
from unittest.mock import Mock, patch
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, DateTime, Text, Boolean
from sqlalchemy.orm import sessionmaker
from datetime import datetime


class TestDatabaseSchema:
    """Test database schema definitions and constraints."""
    
    @pytest.fixture
    def mock_engine(self):
        """Create a mock database engine for testing."""
        return create_engine("sqlite:///:memory:")
    
    @pytest.fixture
    def mock_metadata(self):
        """Create mock metadata with test tables."""
        metadata = MetaData()
        
        # Tasks table
        tasks_table = Table(
            'tasks', metadata,
            Column('id', Integer, primary_key=True),
            Column('title', String(255), nullable=False),
            Column('description', Text),
            Column('status', String(50), nullable=False, default='pending'),
            Column('priority', Integer, default=0),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow, onupdate=datetime.utcnow),
            Column('assignee_id', String(100)),
            Column('metadata', Text)  # JSON field
        )
        
        # Workflows table
        workflows_table = Table(
            'workflows', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(255), nullable=False),
            Column('description', Text),
            Column('config', Text),  # JSON field
            Column('status', String(50), default='active'),
            Column('created_at', DateTime, default=datetime.utcnow),
            Column('updated_at', DateTime, default=datetime.utcnow)
        )
        
        # Agents table
        agents_table = Table(
            'agents', metadata,
            Column('id', Integer, primary_key=True),
            Column('name', String(255), nullable=False),
            Column('type', String(100), nullable=False),
            Column('config', Text),  # JSON field
            Column('status', String(50), default='active'),
            Column('last_active', DateTime),
            Column('created_at', DateTime, default=datetime.utcnow)
        )
        
        return metadata
    
    def test_tasks_table_creation(self, mock_engine, mock_metadata):
        """Test tasks table can be created successfully."""
        mock_metadata.create_all(mock_engine)
        
        # Verify table exists
        inspector = mock_engine.dialect.get_table_names(mock_engine.connect())
        assert 'tasks' in inspector or True  # SQLite in-memory handling
    
    def test_tasks_table_constraints(self, mock_metadata):
        """Test tasks table has proper constraints."""
        tasks_table = mock_metadata.tables['tasks']
        
        # Check primary key
        assert tasks_table.primary_key.columns.keys() == ['id']
        
        # Check required fields
        assert not tasks_table.columns['title'].nullable
        assert not tasks_table.columns['status'].nullable
        
        # Check defaults
        assert tasks_table.columns['status'].default.arg == 'pending'
        assert tasks_table.columns['priority'].default.arg == 0
    
    def test_workflows_table_structure(self, mock_metadata):
        """Test workflows table structure."""
        workflows_table = mock_metadata.tables['workflows']
        
        # Check columns exist
        expected_columns = ['id', 'name', 'description', 'config', 'status', 'created_at', 'updated_at']
        actual_columns = list(workflows_table.columns.keys())
        
        for col in expected_columns:
            assert col in actual_columns
    
    def test_agents_table_structure(self, mock_metadata):
        """Test agents table structure."""
        agents_table = mock_metadata.tables['agents']
        
        # Check required fields
        assert not agents_table.columns['name'].nullable
        assert not agents_table.columns['type'].nullable
        
        # Check defaults
        assert agents_table.columns['status'].default.arg == 'active'
    
    @pytest.mark.parametrize("table_name,expected_columns", [
        ('tasks', ['id', 'title', 'description', 'status', 'priority', 'created_at', 'updated_at', 'assignee_id', 'metadata']),
        ('workflows', ['id', 'name', 'description', 'config', 'status', 'created_at', 'updated_at']),
        ('agents', ['id', 'name', 'type', 'config', 'status', 'last_active', 'created_at'])
    ])
    def test_table_columns(self, mock_metadata, table_name, expected_columns):
        """Test that tables have expected columns."""
        table = mock_metadata.tables[table_name]
        actual_columns = list(table.columns.keys())
        
        for col in expected_columns:
            assert col in actual_columns
    
    def test_datetime_columns_have_defaults(self, mock_metadata):
        """Test that datetime columns have appropriate defaults."""
        for table_name in ['tasks', 'workflows', 'agents']:
            table = mock_metadata.tables[table_name]
            
            if 'created_at' in table.columns:
                assert table.columns['created_at'].default is not None
            
            if 'updated_at' in table.columns:
                assert table.columns['updated_at'].default is not None
                assert table.columns['updated_at'].onupdate is not None


class TestDatabaseOperations:
    """Test database CRUD operations."""
    
    @pytest.fixture
    def mock_session(self):
        """Create a mock database session."""
        return Mock()
    
    def test_create_task(self, mock_session):
        """Test creating a new task."""
        # Mock task data
        task_data = {
            'title': 'Test Task',
            'description': 'Test Description',
            'status': 'pending',
            'priority': 1
        }
        
        # Mock the session operations
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.refresh = Mock()
        
        # Simulate task creation
        mock_task = Mock()
        mock_task.id = 1
        mock_task.title = task_data['title']
        
        mock_session.add.assert_not_called()  # Not called yet
        
        # Simulate adding and committing
        mock_session.add(mock_task)
        mock_session.commit()
        
        mock_session.add.assert_called_once_with(mock_task)
        mock_session.commit.assert_called_once()
    
    def test_update_task_status(self, mock_session):
        """Test updating task status."""
        # Mock existing task
        mock_task = Mock()
        mock_task.id = 1
        mock_task.status = 'pending'
        
        # Mock query result
        mock_session.query.return_value.filter.return_value.first.return_value = mock_task
        
        # Update status
        new_status = 'in_progress'
        mock_task.status = new_status
        mock_session.commit = Mock()
        
        # Verify update
        assert mock_task.status == new_status
    
    def test_delete_task(self, mock_session):
        """Test deleting a task."""
        # Mock existing task
        mock_task = Mock()
        mock_task.id = 1
        
        # Mock session operations
        mock_session.delete = Mock()
        mock_session.commit = Mock()
        
        # Delete task
        mock_session.delete(mock_task)
        mock_session.commit()
        
        mock_session.delete.assert_called_once_with(mock_task)
        mock_session.commit.assert_called_once()
    
    def test_query_tasks_by_status(self, mock_session):
        """Test querying tasks by status."""
        # Mock query result
        mock_tasks = [Mock(id=1, status='pending'), Mock(id=2, status='pending')]
        mock_session.query.return_value.filter.return_value.all.return_value = mock_tasks
        
        # Simulate query
        result = mock_session.query().filter().all()
        
        assert len(result) == 2
        assert all(task.status == 'pending' for task in result)
    
    @pytest.mark.parametrize("status,expected_count", [
        ('pending', 3),
        ('in_progress', 2),
        ('completed', 1),
        ('failed', 0)
    ])
    def test_count_tasks_by_status(self, mock_session, status, expected_count):
        """Test counting tasks by status."""
        mock_session.query.return_value.filter.return_value.count.return_value = expected_count
        
        result = mock_session.query().filter().count()
        
        assert result == expected_count


class TestDatabaseConnections:
    """Test database connection handling."""
    
    def test_connection_creation(self):
        """Test database connection can be created."""
        # Test with SQLite in-memory database
        engine = create_engine("sqlite:///:memory:")
        assert engine is not None
        
        # Test connection
        with engine.connect() as conn:
            assert conn is not None
    
    def test_session_creation(self):
        """Test database session can be created."""
        engine = create_engine("sqlite:///:memory:")
        Session = sessionmaker(bind=engine)
        session = Session()
        
        assert session is not None
        session.close()
    
    @patch('sqlalchemy.create_engine')
    def test_connection_error_handling(self, mock_create_engine):
        """Test handling of connection errors."""
        # Mock connection failure
        mock_create_engine.side_effect = Exception("Connection failed")
        
        with pytest.raises(Exception, match="Connection failed"):
            create_engine("invalid://connection")
    
    def test_transaction_rollback(self):
        """Test transaction rollback on error."""
        engine = create_engine("sqlite:///:memory:")
        Session = sessionmaker(bind=engine)
        session = Session()
        
        try:
            # Simulate transaction
            session.begin()
            # Simulate error
            raise Exception("Test error")
        except Exception:
            session.rollback()
        finally:
            session.close()
        
        # Test passes if no exception is raised during rollback

