"""
Advanced Connection Pool Implementation with High Availability Features
Provides enterprise-grade connection pooling with load balancing, failover, and monitoring
"""

import asyncio
import logging
import time
import random
from typing import Dict, List, Optional, Any, Callable, Union
from dataclasses import dataclass, field
from enum import Enum
from contextlib import asynccontextmanager, contextmanager
import threading
from concurrent.futures import ThreadPoolExecutor
import psycopg2
import psycopg2.pool
import asyncpg
from psycopg2.extras import RealDictCursor
import json

logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """Connection state enumeration"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    MAINTENANCE = "maintenance"

class LoadBalancingStrategy(Enum):
    """Load balancing strategy enumeration"""
    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    RANDOM = "random"
    WEIGHTED = "weighted"

@dataclass
class ConnectionMetrics:
    """Connection metrics tracking"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_response_time: float = 0.0
    last_used: float = 0.0
    created_at: float = field(default_factory=time.time)
    
    def update_success(self, response_time: float):
        """Update metrics for successful request"""
        self.total_requests += 1
        self.successful_requests += 1
        self.last_used = time.time()
        
        # Update rolling average
        if self.avg_response_time == 0:
            self.avg_response_time = response_time
        else:
            self.avg_response_time = (self.avg_response_time * 0.9) + (response_time * 0.1)
    
    def update_failure(self):
        """Update metrics for failed request"""
        self.total_requests += 1
        self.failed_requests += 1
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_requests == 0:
            return 1.0
        return self.successful_requests / self.total_requests
    
    @property
    def age_seconds(self) -> float:
        """Get connection age in seconds"""
        return time.time() - self.created_at

@dataclass
class DatabaseEndpoint:
    """Database endpoint configuration"""
    host: str
    port: int
    database: str
    username: str
    password: str
    ssl_mode: str = "prefer"
    weight: int = 1
    max_connections: int = 10
    is_read_only: bool = False
    priority: int = 1  # Lower number = higher priority
    
    def get_connection_string(self) -> str:
        """Get connection string for this endpoint"""
        return (
            f"host={self.host} "
            f"port={self.port} "
            f"dbname={self.database} "
            f"user={self.username} "
            f"password={self.password} "
            f"sslmode={self.ssl_mode} "
            f"connect_timeout=10 "
            f"application_name=workflow_system"
        )
    
    def get_asyncpg_dsn(self) -> str:
        """Get asyncpg DSN for this endpoint"""
        return (
            f"postgresql://{self.username}:{self.password}@"
            f"{self.host}:{self.port}/{self.database}"
            f"?sslmode={self.ssl_mode}"
        )

class HealthChecker:
    """Database endpoint health checker"""
    
    def __init__(self, check_interval: int = 30, timeout: int = 5):
        self.check_interval = check_interval
        self.timeout = timeout
        self.health_status: Dict[str, ConnectionState] = {}
        self.last_check: Dict[str, float] = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None
    
    def start(self, endpoints: List[DatabaseEndpoint]):
        """Start health checking"""
        self._running = True
        self._thread = threading.Thread(
            target=self._health_check_loop,
            args=(endpoints,),
            daemon=True
        )
        self._thread.start()
        logger.info("Health checker started")
    
    def stop(self):
        """Stop health checking"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Health checker stopped")
    
    def _health_check_loop(self, endpoints: List[DatabaseEndpoint]):
        """Main health check loop"""
        while self._running:
            for endpoint in endpoints:
                endpoint_id = f"{endpoint.host}:{endpoint.port}"
                
                try:
                    # Perform health check
                    start_time = time.time()
                    is_healthy = self._check_endpoint_health(endpoint)
                    check_duration = time.time() - start_time
                    
                    # Update status
                    if is_healthy:
                        if check_duration > 2.0:  # Slow response
                            self.health_status[endpoint_id] = ConnectionState.DEGRADED
                        else:
                            self.health_status[endpoint_id] = ConnectionState.HEALTHY
                    else:
                        self.health_status[endpoint_id] = ConnectionState.FAILED
                    
                    self.last_check[endpoint_id] = time.time()
                    
                except Exception as e:
                    logger.error(f"Health check failed for {endpoint_id}: {e}")
                    self.health_status[endpoint_id] = ConnectionState.FAILED
            
            time.sleep(self.check_interval)
    
    def _check_endpoint_health(self, endpoint: DatabaseEndpoint) -> bool:
        """Check health of a specific endpoint"""
        try:
            conn = psycopg2.connect(
                endpoint.get_connection_string(),
                connect_timeout=self.timeout
            )
            
            with conn.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            
            conn.close()
            return result is not None
            
        except Exception:
            return False
    
    def get_healthy_endpoints(self, endpoints: List[DatabaseEndpoint]) -> List[DatabaseEndpoint]:
        """Get list of healthy endpoints"""
        healthy = []
        for endpoint in endpoints:
            endpoint_id = f"{endpoint.host}:{endpoint.port}"
            status = self.health_status.get(endpoint_id, ConnectionState.HEALTHY)
            
            if status in [ConnectionState.HEALTHY, ConnectionState.DEGRADED]:
                healthy.append(endpoint)
        
        return healthy

class LoadBalancer:
    """Connection load balancer"""
    
    def __init__(self, strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS):
        self.strategy = strategy
        self.round_robin_index = 0
        self.connection_counts: Dict[str, int] = {}
    
    def select_endpoint(self, endpoints: List[DatabaseEndpoint], read_only: bool = False) -> Optional[DatabaseEndpoint]:
        """Select best endpoint based on strategy"""
        # Filter by read/write preference
        available_endpoints = [
            ep for ep in endpoints
            if not read_only or ep.is_read_only or not any(e.is_read_only for e in endpoints)
        ]
        
        if not available_endpoints:
            return None
        
        if self.strategy == LoadBalancingStrategy.ROUND_ROBIN:
            return self._round_robin_select(available_endpoints)
        elif self.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS:
            return self._least_connections_select(available_endpoints)
        elif self.strategy == LoadBalancingStrategy.RANDOM:
            return random.choice(available_endpoints)
        elif self.strategy == LoadBalancingStrategy.WEIGHTED:
            return self._weighted_select(available_endpoints)
        else:
            return available_endpoints[0]
    
    def _round_robin_select(self, endpoints: List[DatabaseEndpoint]) -> DatabaseEndpoint:
        """Round-robin selection"""
        endpoint = endpoints[self.round_robin_index % len(endpoints)]
        self.round_robin_index += 1
        return endpoint
    
    def _least_connections_select(self, endpoints: List[DatabaseEndpoint]) -> DatabaseEndpoint:
        """Select endpoint with least connections"""
        min_connections = float('inf')
        selected_endpoint = endpoints[0]
        
        for endpoint in endpoints:
            endpoint_id = f"{endpoint.host}:{endpoint.port}"
            connections = self.connection_counts.get(endpoint_id, 0)
            
            if connections < min_connections:
                min_connections = connections
                selected_endpoint = endpoint
        
        return selected_endpoint
    
    def _weighted_select(self, endpoints: List[DatabaseEndpoint]) -> DatabaseEndpoint:
        """Weighted random selection"""
        total_weight = sum(ep.weight for ep in endpoints)
        random_weight = random.uniform(0, total_weight)
        
        current_weight = 0
        for endpoint in endpoints:
            current_weight += endpoint.weight
            if random_weight <= current_weight:
                return endpoint
        
        return endpoints[-1]  # Fallback
    
    def update_connection_count(self, endpoint: DatabaseEndpoint, delta: int):
        """Update connection count for endpoint"""
        endpoint_id = f"{endpoint.host}:{endpoint.port}"
        self.connection_counts[endpoint_id] = max(0, self.connection_counts.get(endpoint_id, 0) + delta)

class EnterpriseConnectionPool:
    """Enterprise-grade connection pool with HA features"""
    
    def __init__(
        self,
        endpoints: List[DatabaseEndpoint],
        min_connections_per_endpoint: int = 2,
        max_connections_per_endpoint: int = 10,
        load_balancing_strategy: LoadBalancingStrategy = LoadBalancingStrategy.LEAST_CONNECTIONS,
        health_check_interval: int = 30,
        connection_timeout: int = 10,
        query_timeout: int = 30,
        retry_attempts: int = 3,
        retry_delay: float = 1.0,
        enable_query_logging: bool = False,
        slow_query_threshold: float = 1.0
    ):
        self.endpoints = endpoints
        self.min_connections_per_endpoint = min_connections_per_endpoint
        self.max_connections_per_endpoint = max_connections_per_endpoint
        self.connection_timeout = connection_timeout
        self.query_timeout = query_timeout
        self.retry_attempts = retry_attempts
        self.retry_delay = retry_delay
        self.enable_query_logging = enable_query_logging
        self.slow_query_threshold = slow_query_threshold
        
        # Connection pools per endpoint
        self.pools: Dict[str, psycopg2.pool.ThreadedConnectionPool] = {}
        self.metrics: Dict[str, ConnectionMetrics] = {}
        
        # High availability components
        self.health_checker = HealthChecker(health_check_interval)
        self.load_balancer = LoadBalancer(load_balancing_strategy)
        
        # Statistics
        self.global_stats = {
            'total_queries': 0,
            'successful_queries': 0,
            'failed_queries': 0,
            'slow_queries': 0,
            'failovers': 0,
            'avg_query_time': 0.0
        }
        
        self._initialized = False
        self._lock = threading.RLock()
    
    def initialize(self):
        """Initialize all connection pools"""
        with self._lock:
            if self._initialized:
                return
            
            for endpoint in self.endpoints:
                endpoint_id = f"{endpoint.host}:{endpoint.port}"
                
                try:
                    pool = psycopg2.pool.ThreadedConnectionPool(
                        minconn=self.min_connections_per_endpoint,
                        maxconn=min(endpoint.max_connections, self.max_connections_per_endpoint),
                        dsn=endpoint.get_connection_string(),
                        cursor_factory=RealDictCursor
                    )
                    
                    self.pools[endpoint_id] = pool
                    self.metrics[endpoint_id] = ConnectionMetrics()
                    
                    logger.info(f"Initialized connection pool for {endpoint_id}")
                    
                except Exception as e:
                    logger.error(f"Failed to initialize pool for {endpoint_id}: {e}")
            
            # Start health checking
            self.health_checker.start(self.endpoints)
            self._initialized = True
            
            logger.info(f"Enterprise connection pool initialized with {len(self.pools)} endpoints")
    
    @contextmanager
    def get_connection(self, read_only: bool = False, preferred_endpoint: str = None):
        """Get connection with high availability features"""
        if not self._initialized:
            self.initialize()
        
        connection = None
        selected_endpoint = None
        attempts = 0
        
        while attempts < self.retry_attempts:
            try:
                # Select endpoint
                if preferred_endpoint:
                    selected_endpoint = next(
                        (ep for ep in self.endpoints if f"{ep.host}:{ep.port}" == preferred_endpoint),
                        None
                    )
                
                if not selected_endpoint:
                    healthy_endpoints = self.health_checker.get_healthy_endpoints(self.endpoints)
                    if not healthy_endpoints:
                        raise Exception("No healthy database endpoints available")
                    
                    selected_endpoint = self.load_balancer.select_endpoint(healthy_endpoints, read_only)
                
                if not selected_endpoint:
                    raise Exception("No suitable endpoint found")
                
                endpoint_id = f"{selected_endpoint.host}:{selected_endpoint.port}"
                pool = self.pools.get(endpoint_id)
                
                if not pool:
                    raise Exception(f"No pool available for endpoint {endpoint_id}")
                
                # Get connection from pool
                connection = pool.getconn()
                self.load_balancer.update_connection_count(selected_endpoint, 1)
                
                yield connection
                
                # Success - break retry loop
                break
                
            except Exception as e:
                attempts += 1
                self.global_stats['failovers'] += 1
                
                if connection:
                    try:
                        connection.rollback()
                    except:
                        pass
                
                if attempts >= self.retry_attempts:
                    logger.error(f"All retry attempts failed: {e}")
                    raise
                
                logger.warning(f"Connection attempt {attempts} failed, retrying: {e}")
                time.sleep(self.retry_delay * attempts)  # Exponential backoff
                
                # Try different endpoint on retry
                selected_endpoint = None
                
        # Cleanup
        if connection and selected_endpoint:
            endpoint_id = f"{selected_endpoint.host}:{selected_endpoint.port}"
            pool = self.pools.get(endpoint_id)
            if pool:
                pool.putconn(connection)
                self.load_balancer.update_connection_count(selected_endpoint, -1)
    
    def execute_query(
        self,
        query: str,
        params: tuple = None,
        fetch: str = 'all',
        read_only: bool = False,
        timeout: Optional[int] = None
    ) -> Any:
        """Execute query with retry logic and monitoring"""
        start_time = time.time()
        query_timeout = timeout or self.query_timeout
        
        try:
            with self.get_connection(read_only=read_only) as conn:
                # Set query timeout
                with conn.cursor() as cursor:
                    cursor.execute(f"SET statement_timeout = {query_timeout * 1000}")
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
                    
                    # Update statistics
                    self._update_query_stats(execution_time, True)
                    
                    if execution_time > self.slow_query_threshold:
                        self.global_stats['slow_queries'] += 1
                        logger.warning(f"Slow query ({execution_time:.2f}s): {query[:100]}...")
                    
                    if self.enable_query_logging:
                        logger.debug(f"Query executed ({execution_time:.3f}s): {query[:100]}...")
                    
                    return result
                    
        except Exception as e:
            execution_time = time.time() - start_time
            self._update_query_stats(execution_time, False)
            logger.error(f"Query execution failed after {execution_time:.2f}s: {e}")
            raise
    
    def execute_transaction(self, queries: List[tuple], read_only: bool = False) -> bool:
        """Execute transaction with retry logic"""
        try:
            with self.get_connection(read_only=read_only) as conn:
                with conn.cursor() as cursor:
                    for query, params in queries:
                        cursor.execute(query, params)
                    conn.commit()
                    return True
                    
        except Exception as e:
            logger.error(f"Transaction failed: {e}")
            return False
    
    def _update_query_stats(self, execution_time: float, success: bool):
        """Update global query statistics"""
        self.global_stats['total_queries'] += 1
        
        if success:
            self.global_stats['successful_queries'] += 1
        else:
            self.global_stats['failed_queries'] += 1
        
        # Update rolling average
        if self.global_stats['avg_query_time'] == 0:
            self.global_stats['avg_query_time'] = execution_time
        else:
            self.global_stats['avg_query_time'] = (
                self.global_stats['avg_query_time'] * 0.95 + execution_time * 0.05
            )
    
    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive pool statistics"""
        endpoint_stats = {}
        
        for endpoint in self.endpoints:
            endpoint_id = f"{endpoint.host}:{endpoint.port}"
            pool = self.pools.get(endpoint_id)
            metrics = self.metrics.get(endpoint_id, ConnectionMetrics())
            health_status = self.health_checker.health_status.get(endpoint_id, ConnectionState.HEALTHY)
            
            endpoint_stats[endpoint_id] = {
                'health_status': health_status.value,
                'is_read_only': endpoint.is_read_only,
                'weight': endpoint.weight,
                'priority': endpoint.priority,
                'metrics': {
                    'total_requests': metrics.total_requests,
                    'success_rate': metrics.success_rate,
                    'avg_response_time': metrics.avg_response_time,
                    'age_seconds': metrics.age_seconds
                },
                'pool_info': {
                    'min_connections': self.min_connections_per_endpoint,
                    'max_connections': min(endpoint.max_connections, self.max_connections_per_endpoint),
                    'active_connections': self.load_balancer.connection_counts.get(endpoint_id, 0)
                }
            }
        
        return {
            'global_stats': self.global_stats,
            'endpoints': endpoint_stats,
            'pool_config': {
                'total_endpoints': len(self.endpoints),
                'healthy_endpoints': len(self.health_checker.get_healthy_endpoints(self.endpoints)),
                'load_balancing_strategy': self.load_balancer.strategy.value,
                'health_check_interval': self.health_checker.check_interval
            }
        }
    
    def health_check(self) -> Dict[str, bool]:
        """Perform comprehensive health check"""
        healthy_endpoints = self.health_checker.get_healthy_endpoints(self.endpoints)
        
        return {
            'overall_healthy': len(healthy_endpoints) > 0,
            'all_endpoints_healthy': len(healthy_endpoints) == len(self.endpoints),
            'read_replicas_available': any(ep.is_read_only for ep in healthy_endpoints),
            'write_master_available': any(not ep.is_read_only for ep in healthy_endpoints)
        }
    
    def close(self):
        """Close all connection pools"""
        with self._lock:
            self.health_checker.stop()
            
            for endpoint_id, pool in self.pools.items():
                try:
                    pool.closeall()
                    logger.info(f"Closed connection pool for {endpoint_id}")
                except Exception as e:
                    logger.error(f"Error closing pool for {endpoint_id}: {e}")
            
            self.pools.clear()
            self.metrics.clear()
            self._initialized = False
            
            logger.info("Enterprise connection pool closed")

# Factory functions for easy setup
def create_single_endpoint_pool(
    host: str,
    port: int,
    database: str,
    username: str,
    password: str,
    **kwargs
) -> EnterpriseConnectionPool:
    """Create connection pool for single endpoint"""
    endpoint = DatabaseEndpoint(
        host=host,
        port=port,
        database=database,
        username=username,
        password=password
    )
    
    return EnterpriseConnectionPool([endpoint], **kwargs)

def create_master_replica_pool(
    master_config: Dict[str, Any],
    replica_configs: List[Dict[str, Any]],
    **kwargs
) -> EnterpriseConnectionPool:
    """Create connection pool with master-replica setup"""
    endpoints = []
    
    # Master endpoint
    master_endpoint = DatabaseEndpoint(**master_config, is_read_only=False, priority=1)
    endpoints.append(master_endpoint)
    
    # Replica endpoints
    for i, replica_config in enumerate(replica_configs):
        replica_endpoint = DatabaseEndpoint(**replica_config, is_read_only=True, priority=2)
        endpoints.append(replica_endpoint)
    
    return EnterpriseConnectionPool(endpoints, **kwargs)

