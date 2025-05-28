#!/usr/bin/env python3
"""
Codegen AI Workflow Platform - System Health Check Tool

This script performs comprehensive health checks on all platform components
and provides detailed diagnostics and recommendations.
"""

import asyncio
import json
import logging
import sys
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
import aiohttp
import asyncpg
import redis.asyncio as redis
import psutil
import docker
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class HealthCheckResult:
    """Health check result for a component"""
    component: str
    status: str  # 'healthy', 'warning', 'critical', 'unknown'
    message: str
    details: Dict
    timestamp: datetime
    response_time_ms: Optional[float] = None

@dataclass
class SystemHealthReport:
    """Complete system health report"""
    overall_status: str
    timestamp: datetime
    components: List[HealthCheckResult]
    recommendations: List[str]
    summary: Dict

class HealthChecker:
    """Main health checker class"""
    
    def __init__(self, config_file: str = "health_check_config.json"):
        self.config = self._load_config(config_file)
        self.docker_client = None
        self.results: List[HealthCheckResult] = []
        
    def _load_config(self, config_file: str) -> Dict:
        """Load configuration from file"""
        default_config = {
            "services": {
                "task_manager": {
                    "url": "http://localhost:8001",
                    "health_endpoint": "/health",
                    "timeout": 10
                },
                "webhook_orchestrator": {
                    "url": "http://localhost:8002",
                    "health_endpoint": "/health",
                    "timeout": 10
                },
                "codegen_agent": {
                    "url": "http://localhost:8003",
                    "health_endpoint": "/health",
                    "timeout": 10
                },
                "docs_website": {
                    "url": "http://localhost:8080",
                    "health_endpoint": "/",
                    "timeout": 10
                }
            },
            "databases": {
                "postgres": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "codegen_platform",
                    "user": "codegen",
                    "timeout": 5
                },
                "redis": {
                    "host": "localhost",
                    "port": 6379,
                    "timeout": 5
                }
            },
            "docker": {
                "enabled": True,
                "containers": [
                    "codegen-postgres",
                    "codegen-redis",
                    "codegen-minio",
                    "codegen-task-manager",
                    "codegen-webhook-orchestrator",
                    "codegen-codegen-agent",
                    "codegen-docs",
                    "codegen-prometheus",
                    "codegen-grafana"
                ]
            },
            "system": {
                "check_disk_space": True,
                "check_memory": True,
                "check_cpu": True,
                "disk_warning_threshold": 80,
                "memory_warning_threshold": 85,
                "cpu_warning_threshold": 90
            }
        }
        
        try:
            config_path = Path(config_file)
            if config_path.exists():
                with open(config_path, 'r') as f:
                    user_config = json.load(f)
                # Merge with defaults
                default_config.update(user_config)
            else:
                logger.warning(f"Config file {config_file} not found, using defaults")
        except Exception as e:
            logger.error(f"Error loading config: {e}, using defaults")
            
        return default_config

    async def check_http_service(self, name: str, config: Dict) -> HealthCheckResult:
        """Check HTTP service health"""
        start_time = time.time()
        
        try:
            url = f"{config['url']}{config['health_endpoint']}"
            timeout = aiohttp.ClientTimeout(total=config['timeout'])
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url) as response:
                    response_time = (time.time() - start_time) * 1000
                    
                    if response.status == 200:
                        try:
                            data = await response.json()
                            return HealthCheckResult(
                                component=name,
                                status='healthy',
                                message=f"Service is healthy (HTTP {response.status})",
                                details=data if isinstance(data, dict) else {"response": str(data)},
                                timestamp=datetime.now(),
                                response_time_ms=response_time
                            )
                        except:
                            return HealthCheckResult(
                                component=name,
                                status='healthy',
                                message=f"Service is responding (HTTP {response.status})",
                                details={"status_code": response.status},
                                timestamp=datetime.now(),
                                response_time_ms=response_time
                            )
                    else:
                        return HealthCheckResult(
                            component=name,
                            status='warning',
                            message=f"Service returned HTTP {response.status}",
                            details={"status_code": response.status, "url": url},
                            timestamp=datetime.now(),
                            response_time_ms=response_time
                        )
                        
        except asyncio.TimeoutError:
            return HealthCheckResult(
                component=name,
                status='critical',
                message=f"Service timeout after {config['timeout']}s",
                details={"url": url, "timeout": config['timeout']},
                timestamp=datetime.now()
            )
        except Exception as e:
            return HealthCheckResult(
                component=name,
                status='critical',
                message=f"Service unreachable: {str(e)}",
                details={"url": url, "error": str(e)},
                timestamp=datetime.now()
            )

    async def check_postgres(self, config: Dict) -> HealthCheckResult:
        """Check PostgreSQL database health"""
        start_time = time.time()
        
        try:
            # Try to connect without password first (for testing)
            try:
                conn = await asyncpg.connect(
                    host=config['host'],
                    port=config['port'],
                    database=config['database'],
                    user=config['user'],
                    timeout=config['timeout']
                )
            except:
                # If that fails, try with environment variable
                import os
                password = os.getenv('POSTGRES_PASSWORD', '')
                conn = await asyncpg.connect(
                    host=config['host'],
                    port=config['port'],
                    database=config['database'],
                    user=config['user'],
                    password=password,
                    timeout=config['timeout']
                )
            
            response_time = (time.time() - start_time) * 1000
            
            # Run basic health queries
            version = await conn.fetchval('SELECT version()')
            db_size = await conn.fetchval(
                'SELECT pg_size_pretty(pg_database_size($1))', 
                config['database']
            )
            active_connections = await conn.fetchval(
                'SELECT count(*) FROM pg_stat_activity WHERE state = $1', 
                'active'
            )
            
            await conn.close()
            
            return HealthCheckResult(
                component='postgres',
                status='healthy',
                message="PostgreSQL is healthy",
                details={
                    "version": version,
                    "database_size": db_size,
                    "active_connections": active_connections,
                    "host": config['host'],
                    "port": config['port']
                },
                timestamp=datetime.now(),
                response_time_ms=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component='postgres',
                status='critical',
                message=f"PostgreSQL connection failed: {str(e)}",
                details={
                    "host": config['host'],
                    "port": config['port'],
                    "database": config['database'],
                    "error": str(e)
                },
                timestamp=datetime.now()
            )

    async def check_redis(self, config: Dict) -> HealthCheckResult:
        """Check Redis health"""
        start_time = time.time()
        
        try:
            # Try to connect
            import os
            password = os.getenv('REDIS_PASSWORD', None)
            
            redis_client = redis.Redis(
                host=config['host'],
                port=config['port'],
                password=password,
                socket_timeout=config['timeout']
            )
            
            # Test basic operations
            await redis_client.ping()
            info = await redis_client.info()
            
            response_time = (time.time() - start_time) * 1000
            
            await redis_client.close()
            
            return HealthCheckResult(
                component='redis',
                status='healthy',
                message="Redis is healthy",
                details={
                    "version": info.get('redis_version'),
                    "connected_clients": info.get('connected_clients'),
                    "used_memory_human": info.get('used_memory_human'),
                    "uptime_in_seconds": info.get('uptime_in_seconds'),
                    "host": config['host'],
                    "port": config['port']
                },
                timestamp=datetime.now(),
                response_time_ms=response_time
            )
            
        except Exception as e:
            return HealthCheckResult(
                component='redis',
                status='critical',
                message=f"Redis connection failed: {str(e)}",
                details={
                    "host": config['host'],
                    "port": config['port'],
                    "error": str(e)
                },
                timestamp=datetime.now()
            )

    def check_docker_containers(self) -> List[HealthCheckResult]:
        """Check Docker container health"""
        results = []
        
        try:
            if not self.docker_client:
                self.docker_client = docker.from_env()
            
            containers = self.config['docker']['containers']
            
            for container_name in containers:
                try:
                    container = self.docker_client.containers.get(container_name)
                    
                    status = container.status
                    health = getattr(container.attrs['State'], 'Health', {})
                    
                    if status == 'running':
                        if health and health.get('Status') == 'healthy':
                            status_level = 'healthy'
                            message = "Container is running and healthy"
                        elif health and health.get('Status') == 'unhealthy':
                            status_level = 'critical'
                            message = "Container is running but unhealthy"
                        else:
                            status_level = 'warning'
                            message = "Container is running (health status unknown)"
                    else:
                        status_level = 'critical'
                        message = f"Container is {status}"
                    
                    results.append(HealthCheckResult(
                        component=f'docker_{container_name}',
                        status=status_level,
                        message=message,
                        details={
                            "container_name": container_name,
                            "status": status,
                            "health": health,
                            "image": container.image.tags[0] if container.image.tags else "unknown"
                        },
                        timestamp=datetime.now()
                    ))
                    
                except docker.errors.NotFound:
                    results.append(HealthCheckResult(
                        component=f'docker_{container_name}',
                        status='critical',
                        message="Container not found",
                        details={"container_name": container_name},
                        timestamp=datetime.now()
                    ))
                except Exception as e:
                    results.append(HealthCheckResult(
                        component=f'docker_{container_name}',
                        status='unknown',
                        message=f"Error checking container: {str(e)}",
                        details={"container_name": container_name, "error": str(e)},
                        timestamp=datetime.now()
                    ))
                    
        except Exception as e:
            results.append(HealthCheckResult(
                component='docker',
                status='critical',
                message=f"Docker daemon unreachable: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now()
            ))
            
        return results

    def check_system_resources(self) -> List[HealthCheckResult]:
        """Check system resource usage"""
        results = []
        config = self.config['system']
        
        try:
            # Check disk space
            if config['check_disk_space']:
                disk_usage = psutil.disk_usage('/')
                disk_percent = (disk_usage.used / disk_usage.total) * 100
                
                if disk_percent > config['disk_warning_threshold']:
                    status = 'warning' if disk_percent < 95 else 'critical'
                    message = f"Disk usage is {disk_percent:.1f}%"
                else:
                    status = 'healthy'
                    message = f"Disk usage is {disk_percent:.1f}%"
                
                results.append(HealthCheckResult(
                    component='system_disk',
                    status=status,
                    message=message,
                    details={
                        "usage_percent": round(disk_percent, 1),
                        "total_gb": round(disk_usage.total / (1024**3), 1),
                        "used_gb": round(disk_usage.used / (1024**3), 1),
                        "free_gb": round(disk_usage.free / (1024**3), 1)
                    },
                    timestamp=datetime.now()
                ))
            
            # Check memory
            if config['check_memory']:
                memory = psutil.virtual_memory()
                memory_percent = memory.percent
                
                if memory_percent > config['memory_warning_threshold']:
                    status = 'warning' if memory_percent < 95 else 'critical'
                    message = f"Memory usage is {memory_percent:.1f}%"
                else:
                    status = 'healthy'
                    message = f"Memory usage is {memory_percent:.1f}%"
                
                results.append(HealthCheckResult(
                    component='system_memory',
                    status=status,
                    message=message,
                    details={
                        "usage_percent": round(memory_percent, 1),
                        "total_gb": round(memory.total / (1024**3), 1),
                        "used_gb": round(memory.used / (1024**3), 1),
                        "available_gb": round(memory.available / (1024**3), 1)
                    },
                    timestamp=datetime.now()
                ))
            
            # Check CPU
            if config['check_cpu']:
                cpu_percent = psutil.cpu_percent(interval=1)
                
                if cpu_percent > config['cpu_warning_threshold']:
                    status = 'warning' if cpu_percent < 98 else 'critical'
                    message = f"CPU usage is {cpu_percent:.1f}%"
                else:
                    status = 'healthy'
                    message = f"CPU usage is {cpu_percent:.1f}%"
                
                results.append(HealthCheckResult(
                    component='system_cpu',
                    status=status,
                    message=message,
                    details={
                        "usage_percent": round(cpu_percent, 1),
                        "cpu_count": psutil.cpu_count(),
                        "load_average": list(psutil.getloadavg()) if hasattr(psutil, 'getloadavg') else None
                    },
                    timestamp=datetime.now()
                ))
                
        except Exception as e:
            results.append(HealthCheckResult(
                component='system_resources',
                status='unknown',
                message=f"Error checking system resources: {str(e)}",
                details={"error": str(e)},
                timestamp=datetime.now()
            ))
            
        return results

    async def run_all_checks(self) -> SystemHealthReport:
        """Run all health checks and generate report"""
        logger.info("Starting comprehensive health check...")
        
        # HTTP Services
        for service_name, service_config in self.config['services'].items():
            result = await self.check_http_service(service_name, service_config)
            self.results.append(result)
        
        # Databases
        if 'postgres' in self.config['databases']:
            result = await self.check_postgres(self.config['databases']['postgres'])
            self.results.append(result)
            
        if 'redis' in self.config['databases']:
            result = await self.check_redis(self.config['databases']['redis'])
            self.results.append(result)
        
        # Docker containers
        if self.config['docker']['enabled']:
            docker_results = self.check_docker_containers()
            self.results.extend(docker_results)
        
        # System resources
        system_results = self.check_system_resources()
        self.results.extend(system_results)
        
        # Generate report
        return self._generate_report()

    def _generate_report(self) -> SystemHealthReport:
        """Generate comprehensive health report"""
        # Calculate overall status
        statuses = [result.status for result in self.results]
        if 'critical' in statuses:
            overall_status = 'critical'
        elif 'warning' in statuses:
            overall_status = 'warning'
        elif 'unknown' in statuses:
            overall_status = 'unknown'
        else:
            overall_status = 'healthy'
        
        # Generate recommendations
        recommendations = []
        
        for result in self.results:
            if result.status == 'critical':
                recommendations.append(f"CRITICAL: Fix {result.component} - {result.message}")
            elif result.status == 'warning':
                recommendations.append(f"WARNING: Monitor {result.component} - {result.message}")
        
        # Generate summary
        summary = {
            "total_components": len(self.results),
            "healthy": len([r for r in self.results if r.status == 'healthy']),
            "warning": len([r for r in self.results if r.status == 'warning']),
            "critical": len([r for r in self.results if r.status == 'critical']),
            "unknown": len([r for r in self.results if r.status == 'unknown']),
            "average_response_time_ms": round(
                sum(r.response_time_ms for r in self.results if r.response_time_ms) / 
                len([r for r in self.results if r.response_time_ms]), 2
            ) if any(r.response_time_ms for r in self.results) else None
        }
        
        return SystemHealthReport(
            overall_status=overall_status,
            timestamp=datetime.now(),
            components=self.results,
            recommendations=recommendations,
            summary=summary
        )

    def print_report(self, report: SystemHealthReport):
        """Print formatted health report"""
        print("\n" + "="*80)
        print("CODEGEN AI WORKFLOW PLATFORM - HEALTH CHECK REPORT")
        print("="*80)
        print(f"Timestamp: {report.timestamp}")
        print(f"Overall Status: {report.overall_status.upper()}")
        print(f"Components Checked: {report.summary['total_components']}")
        print()
        
        # Status summary
        print("STATUS SUMMARY:")
        print(f"  ✅ Healthy:  {report.summary['healthy']}")
        print(f"  ⚠️  Warning:  {report.summary['warning']}")
        print(f"  ❌ Critical: {report.summary['critical']}")
        print(f"  ❓ Unknown:  {report.summary['unknown']}")
        
        if report.summary['average_response_time_ms']:
            print(f"  ⏱️  Avg Response Time: {report.summary['average_response_time_ms']}ms")
        print()
        
        # Component details
        print("COMPONENT DETAILS:")
        for result in report.components:
            status_icon = {
                'healthy': '✅',
                'warning': '⚠️',
                'critical': '❌',
                'unknown': '❓'
            }.get(result.status, '❓')
            
            response_time = f" ({result.response_time_ms:.1f}ms)" if result.response_time_ms else ""
            print(f"  {status_icon} {result.component}: {result.message}{response_time}")
        
        print()
        
        # Recommendations
        if report.recommendations:
            print("RECOMMENDATIONS:")
            for rec in report.recommendations:
                print(f"  • {rec}")
            print()
        
        print("="*80)

    def save_report(self, report: SystemHealthReport, filename: str = None):
        """Save report to JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"health_report_{timestamp}.json"
        
        # Convert to dict for JSON serialization
        report_dict = {
            "overall_status": report.overall_status,
            "timestamp": report.timestamp.isoformat(),
            "summary": report.summary,
            "recommendations": report.recommendations,
            "components": [
                {
                    "component": r.component,
                    "status": r.status,
                    "message": r.message,
                    "details": r.details,
                    "timestamp": r.timestamp.isoformat(),
                    "response_time_ms": r.response_time_ms
                }
                for r in report.components
            ]
        }
        
        with open(filename, 'w') as f:
            json.dump(report_dict, f, indent=2)
        
        logger.info(f"Health report saved to {filename}")

async def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Codegen Platform Health Check")
    parser.add_argument('--config', '-c', default='health_check_config.json',
                       help='Configuration file path')
    parser.add_argument('--output', '-o', help='Output file for JSON report')
    parser.add_argument('--quiet', '-q', action='store_true',
                       help='Suppress console output')
    
    args = parser.parse_args()
    
    # Create health checker
    checker = HealthChecker(args.config)
    
    try:
        # Run health checks
        report = await checker.run_all_checks()
        
        # Print report
        if not args.quiet:
            checker.print_report(report)
        
        # Save report
        if args.output:
            checker.save_report(report, args.output)
        
        # Exit with appropriate code
        if report.overall_status == 'critical':
            sys.exit(2)
        elif report.overall_status in ['warning', 'unknown']:
            sys.exit(1)
        else:
            sys.exit(0)
            
    except KeyboardInterrupt:
        logger.info("Health check interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())

