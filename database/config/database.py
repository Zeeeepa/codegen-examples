"""
Database Configuration and Connection Management
Provides centralized database configuration, connection pooling, and health monitoring
"""

import os
import logging
import asyncio
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, field
from contextlib import asynccontextmanager, contextmanager
import psycopg2
import psycopg2.pool
import asyncpg
from psycopg2.extras import RealDictCursor
import yaml
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class DatabaseConfig:
    """Database configuration settings"""
    host: str = "localhost"
    port: int = 5432
    database: str = "workflow_db"
    username: str = "postgres"
    password: str = ""
    ssl_mode: str = "prefer"
    
    # Connection pool settings
    min_connections: int = 5
    max_connections: int = 20
    max_idle_time: int = 300  # seconds
    max_lifetime: int = 3600  # seconds
    
    # Performance settings
    statement_timeout: int = 30000  # milliseconds
    idle_in_transaction_timeout: int = 10000  # milliseconds
    lock_timeout: int = 5000  # milliseconds
    
    # Monitoring settings
    log_slow_queries: bool = True
    slow_query_threshold: float = 1.0  # seconds
    enable_query_logging: bool = False
    
    # High availability settings
    read_replicas: List[str] = field(default_factory=list)
    connection_retry_attempts: int = 3
    connection_retry_delay: float = 1.0
    
    @classmethod
    def from_env(cls) -> 'DatabaseConfig':
        """Create configuration from environment variables"""
        return cls(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 5432)),
            database=os.getenv('DB_NAME', 'workflow_db'),
            username=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', ''),
            ssl_mode=os.getenv('DB_SSL_MODE', 'prefer'),
            min_connections=int(os.getenv('DB_MIN_CONNECTIONS', 5)),
            max_connections=int(os.getenv('DB_MAX_CONNECTIONS', 20)),
            max_idle_time=int(os.getenv('DB_MAX_IDLE_TIME', 300)),
            max_lifetime=int(os.getenv('DB_MAX_LIFETIME', 3600)),
            statement_timeout=int(os.getenv('DB_STATEMENT_TIMEOUT', 30000)),
            log_slow_queries=os.getenv('DB_LOG_SLOW_QUERIES', 'true').lower() == 'true',
            slow_query_threshold=float(os.getenv('DB_SLOW_QUERY_THRESHOLD', 1.0)),
            connection_retry_attempts=int(os.getenv('DB_RETRY_ATTEMPTS', 3)),
            connection_retry_delay=float(os.getenv('DB_RETRY_DELAY', 1.0))
        )
    
    @classmethod
    def from_yaml(cls, config_path: str) -> 'DatabaseConfig':
        """Load configuration from YAML file"""
        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Config file {config_path} not found, using environment variables")
            return cls.from_env()
        
        try:
            with open(path, 'r') as f:
                config_data = yaml.safe_load(f)
            
            # Merge with environment variables (env vars take precedence)
            env_config = cls.from_env()
            
            # Update with YAML values where env vars are not set
            for key, value in config_data.items():
                if hasattr(env_config, key) and not os.getenv(f'DB_{key.upper()}'):
                    setattr(env_config, key, value)
            
            return env_config
            
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            return cls.from_env()
    
    def get_connection_string(self, include_password: bool = True) -> str:
        """Get PostgreSQL connection string"""
        password_part = f"password={self.password} " if include_password and self.password else ""
        return (
            f"host={self.host} "
            f"port={self.port} "
            f"dbname={self.database} "
            f"user={self.username} "
            f"{password_part}"
            f"sslmode={self.ssl_mode} "
            f"connect_timeout=10 "
            f"application_name=workflow_system"
        )
    
    def get_asyncpg_dsn(self) -> str:
        """Get asyncpg DSN string"""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.ssl_mode}"
        )

class DatabaseConnectionPool:
    """Synchronous database connection pool using psycopg2"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: Optional[psycopg2.pool.ThreadedConnectionPool] = None
        self._stats = {
            'total_connections': 0,
            'active_connections': 0,
            'queries_executed': 0,
            'slow_queries': 0,
            'connection_errors': 0
        }
    
    def initialize(self) -> None:
        """Initialize the connection pool"""
        try:
            self._pool = psycopg2.pool.ThreadedConnectionPool(
                minconn=self.config.min_connections,
                maxconn=self.config.max_connections,
                dsn=self.config.get_connection_string(),
                cursor_factory=RealDictCursor
            )
            
            # Configure connection parameters
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(f"SET statement_timeout = {self.config.statement_timeout}")
                    cursor.execute(f"SET idle_in_transaction_session_timeout = {self.config.idle_in_transaction_timeout}")
                    cursor.execute(f"SET lock_timeout = {self.config.lock_timeout}")
                    
            logger.info(f"Database connection pool initialized with {self.config.min_connections}-{self.config.max_connections} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize connection pool: {e}")
            raise
    
    @contextmanager
    def get_connection(self):
        """Get a connection from the pool"""
        if not self._pool:
            raise RuntimeError("Connection pool not initialized")
        
        conn = None
        try:
            conn = self._pool.getconn()
            self._stats['active_connections'] += 1
            yield conn
            
        except Exception as e:
            self._stats['connection_errors'] += 1
            if conn:
                conn.rollback()
            raise
            
        finally:
            if conn:
                self._stats['active_connections'] -= 1
                self._pool.putconn(conn)
    
    @contextmanager
    def get_cursor(self, connection=None):
        """Get a cursor, optionally from a specific connection"""
        if connection:
            cursor = connection.cursor()
            try:
                yield cursor
            finally:
                cursor.close()
        else:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    yield cursor
    
    def execute_query(self, query: str, params: tuple = None, fetch: str = 'all') -> Any:
        """Execute a query and return results"""
        import time
        start_time = time.time()
        
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(query, params)
                    
                    if fetch == 'all':
                        result = cursor.fetchall()
                    elif fetch == 'one':
                        result = cursor.fetchone()
                    elif fetch == 'many':
                        result = cursor.fetchmany()
                    else:
                        result = cursor.rowcount
                    
                    execution_time = time.time() - start_time
                    self._stats['queries_executed'] += 1
                    
                    if execution_time > self.config.slow_query_threshold:
                        self._stats['slow_queries'] += 1
                        if self.config.log_slow_queries:
                            logger.warning(f"Slow query ({execution_time:.2f}s): {query[:100]}...")
                    
                    if self.config.enable_query_logging:
                        logger.debug(f"Query executed ({execution_time:.3f}s): {query[:100]}...")
                    
                    return result
                    
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            raise
    
    def execute_transaction(self, queries: List[tuple]) -> bool:
        """Execute multiple queries in a transaction"""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    for query, params in queries:
                        cursor.execute(query, params)
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        pool_stats = {}
        if self._pool:
            # Note: psycopg2 ThreadedConnectionPool doesn't expose detailed stats
            # These would need to be tracked manually or use a different pool implementation
            pool_stats = {
                'min_connections': self.config.min_connections,
                'max_connections': self.config.max_connections,
                'current_connections': 'unknown',  # Not available in psycopg2
                'available_connections': 'unknown'
            }
        
        return {
            **self._stats,
            **pool_stats
        }
    
    def health_check(self) -> bool:
        """Perform health check on the database connection"""
        try:
            result = self.execute_query("SELECT 1", fetch='one')
            return result is not None
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False
    
    def close(self) -> None:
        """Close the connection pool"""
        if self._pool:
            self._pool.closeall()
            logger.info("Database connection pool closed")

class AsyncDatabaseConnectionPool:
    """Asynchronous database connection pool using asyncpg"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self._pool: Optional[asyncpg.Pool] = None
        self._stats = {
            'total_connections': 0,
            'active_connections': 0,
            'queries_executed': 0,
            'slow_queries': 0,
            'connection_errors': 0
        }
    
    async def initialize(self) -> None:
        """Initialize the async connection pool"""
        try:
            self._pool = await asyncpg.create_pool(
                dsn=self.config.get_asyncpg_dsn(),
                min_size=self.config.min_connections,
                max_size=self.config.max_connections,
                max_inactive_connection_lifetime=self.config.max_idle_time,
                command_timeout=self.config.statement_timeout / 1000,  # Convert to seconds
                server_settings={
                    'application_name': 'workflow_system_async',
                    'statement_timeout': str(self.config.statement_timeout),
                    'idle_in_transaction_session_timeout': str(self.config.idle_in_transaction_timeout),
                    'lock_timeout': str(self.config.lock_timeout)
                }
            )
            
            logger.info(f"Async database connection pool initialized with {self.config.min_connections}-{self.config.max_connections} connections")
            
        except Exception as e:
            logger.error(f"Failed to initialize async connection pool: {e}")
            raise
    
    @asynccontextmanager
    async def get_connection(self):
        """Get an async connection from the pool"""
        if not self._pool:
            raise RuntimeError("Async connection pool not initialized")
        
        async with self._pool.acquire() as conn:
            self._stats['active_connections'] += 1
            try:
                yield conn
            finally:
                self._stats['active_connections'] -= 1
    
    async def execute_query(self, query: str, *params) -> Any:
        """Execute an async query"""
        import time
        start_time = time.time()
        
        try:
            async with self.get_connection() as conn:
                result = await conn.fetch(query, *params)
                
                execution_time = time.time() - start_time
                self._stats['queries_executed'] += 1
                
                if execution_time > self.config.slow_query_threshold:
                    self._stats['slow_queries'] += 1
                    if self.config.log_slow_queries:
                        logger.warning(f"Slow async query ({execution_time:.2f}s): {query[:100]}...")
                
                return result
                
        except Exception as e:
            self._stats['connection_errors'] += 1
            logger.error(f"Async query execution failed: {e}")
            raise
    
    async def execute_transaction(self, queries: List[tuple]) -> bool:
        """Execute multiple queries in an async transaction"""
        try:
            async with self.get_connection() as conn:
                async with conn.transaction():
                    for query, params in queries:
                        await conn.execute(query, *params)
                    return True
                    
        except Exception as e:
            logger.error(f"Async transaction failed: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Perform async health check"""
        try:
            result = await self.execute_query("SELECT 1")
            return len(result) > 0
        except Exception as e:
            logger.error(f"Async database health check failed: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get async connection pool statistics"""
        pool_stats = {}
        if self._pool:
            pool_stats = {
                'min_connections': self._pool.get_min_size(),
                'max_connections': self._pool.get_max_size(),
                'current_connections': self._pool.get_size(),
                'available_connections': self._pool.get_idle_size()
            }
        
        return {
            **self._stats,
            **pool_stats
        }
    
    async def close(self) -> None:
        """Close the async connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("Async database connection pool closed")

class DatabaseManager:
    """High-level database manager with both sync and async support"""
    
    def __init__(self, config: DatabaseConfig):
        self.config = config
        self.sync_pool = DatabaseConnectionPool(config)
        self.async_pool = AsyncDatabaseConnectionPool(config)
        self._initialized = False
    
    def initialize_sync(self) -> None:
        """Initialize synchronous connection pool"""
        self.sync_pool.initialize()
        self._initialized = True
    
    async def initialize_async(self) -> None:
        """Initialize asynchronous connection pool"""
        await self.async_pool.initialize()
    
    def get_sync_pool(self) -> DatabaseConnectionPool:
        """Get synchronous connection pool"""
        if not self._initialized:
            self.initialize_sync()
        return self.sync_pool
    
    def get_async_pool(self) -> AsyncDatabaseConnectionPool:
        """Get asynchronous connection pool"""
        return self.async_pool
    
    def health_check(self) -> Dict[str, bool]:
        """Comprehensive health check"""
        return {
            'sync_pool': self.sync_pool.health_check() if self._initialized else False,
            'database_accessible': True  # Basic check
        }
    
    async def async_health_check(self) -> Dict[str, bool]:
        """Async comprehensive health check"""
        sync_health = self.health_check()
        async_health = await self.async_pool.health_check()
        
        return {
            **sync_health,
            'async_pool': async_health
        }
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics from all pools"""
        stats = {
            'sync_pool': self.sync_pool.get_stats() if self._initialized else {},
            'async_pool': self.async_pool.get_stats(),
            'config': {
                'host': self.config.host,
                'database': self.config.database,
                'min_connections': self.config.min_connections,
                'max_connections': self.config.max_connections
            }
        }
        return stats
    
    def close_all(self) -> None:
        """Close all connection pools"""
        if self._initialized:
            self.sync_pool.close()
    
    async def async_close_all(self) -> None:
        """Close all connection pools (async)"""
        await self.async_pool.close()
        self.close_all()

# Global database manager instance
_db_manager: Optional[DatabaseManager] = None

def get_database_manager(config_path: str = "database/config/database.yaml") -> DatabaseManager:
    """Get or create global database manager instance"""
    global _db_manager
    
    if _db_manager is None:
        config = DatabaseConfig.from_yaml(config_path)
        _db_manager = DatabaseManager(config)
    
    return _db_manager

def get_sync_connection_pool(config_path: str = "database/config/database.yaml") -> DatabaseConnectionPool:
    """Get synchronous connection pool"""
    return get_database_manager(config_path).get_sync_pool()

def get_async_connection_pool(config_path: str = "database/config/database.yaml") -> AsyncDatabaseConnectionPool:
    """Get asynchronous connection pool"""
    return get_database_manager(config_path).get_async_pool()

# Convenience functions for common operations
def execute_query(query: str, params: tuple = None, fetch: str = 'all') -> Any:
    """Execute a synchronous query"""
    pool = get_sync_connection_pool()
    return pool.execute_query(query, params, fetch)

async def async_execute_query(query: str, *params) -> Any:
    """Execute an asynchronous query"""
    pool = get_async_connection_pool()
    return await pool.execute_query(query, *params)

def execute_transaction(queries: List[tuple]) -> bool:
    """Execute a synchronous transaction"""
    pool = get_sync_connection_pool()
    return pool.execute_transaction(queries)

async def async_execute_transaction(queries: List[tuple]) -> bool:
    """Execute an asynchronous transaction"""
    pool = get_async_connection_pool()
    return await pool.execute_transaction(queries)

