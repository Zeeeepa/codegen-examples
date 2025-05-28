"""
Core configuration settings for the webhook orchestrator.
"""
import os
from typing import Optional, List
from pydantic import Field, validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application
    app_name: str = "Webhook Orchestrator"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    environment: str = Field(default="development", env="ENVIRONMENT")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    
    # Database
    database_url: str = Field(env="DATABASE_URL")
    database_pool_size: int = Field(default=20, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=30, env="DATABASE_MAX_OVERFLOW")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_max_connections: int = Field(default=20, env="REDIS_MAX_CONNECTIONS")
    
    # Celery
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    celery_task_serializer: str = Field(default="json", env="CELERY_TASK_SERIALIZER")
    celery_result_serializer: str = Field(default="json", env="CELERY_RESULT_SERIALIZER")
    
    # GitHub
    github_webhook_secret: str = Field(env="GITHUB_WEBHOOK_SECRET")
    github_app_id: Optional[str] = Field(default=None, env="GITHUB_APP_ID")
    github_private_key: Optional[str] = Field(default=None, env="GITHUB_PRIVATE_KEY")
    github_token: Optional[str] = Field(default=None, env="GITHUB_TOKEN")
    
    # Codegen
    codegen_token: str = Field(env="CODEGEN_TOKEN")
    codegen_org_id: int = Field(env="CODEGEN_ORG_ID")
    codegen_base_url: str = Field(default="https://api.codegen.sh", env="CODEGEN_BASE_URL")
    
    # Security
    secret_key: str = Field(env="SECRET_KEY")
    access_token_expire_minutes: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    allowed_hosts: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    # Rate Limiting
    rate_limit_requests: int = Field(default=100, env="RATE_LIMIT_REQUESTS")
    rate_limit_window: int = Field(default=60, env="RATE_LIMIT_WINDOW")  # seconds
    
    # Circuit Breaker
    circuit_breaker_failure_threshold: int = Field(default=5, env="CIRCUIT_BREAKER_FAILURE_THRESHOLD")
    circuit_breaker_recovery_timeout: int = Field(default=30, env="CIRCUIT_BREAKER_RECOVERY_TIMEOUT")
    circuit_breaker_expected_exception: tuple = (Exception,)
    
    # Retry Logic
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    retry_backoff_factor: float = Field(default=2.0, env="RETRY_BACKOFF_FACTOR")
    retry_max_delay: int = Field(default=300, env="RETRY_MAX_DELAY")  # seconds
    
    # Monitoring
    enable_metrics: bool = Field(default=True, env="ENABLE_METRICS")
    metrics_port: int = Field(default=9090, env="METRICS_PORT")
    enable_tracing: bool = Field(default=True, env="ENABLE_TRACING")
    jaeger_endpoint: Optional[str] = Field(default=None, env="JAEGER_ENDPOINT")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_format: str = Field(default="json", env="LOG_FORMAT")  # json or text
    
    # Health Check
    health_check_timeout: int = Field(default=30, env="HEALTH_CHECK_TIMEOUT")
    
    # Webhook Processing
    webhook_timeout: int = Field(default=30, env="WEBHOOK_TIMEOUT")
    webhook_max_payload_size: int = Field(default=1024 * 1024, env="WEBHOOK_MAX_PAYLOAD_SIZE")  # 1MB
    
    # Task Processing
    task_timeout: int = Field(default=300, env="TASK_TIMEOUT")  # 5 minutes
    task_max_retries: int = Field(default=3, env="TASK_MAX_RETRIES")
    
    @validator("allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        if isinstance(v, str):
            return [host.strip() for host in v.split(",")]
        return v
    
    @validator("log_level")
    def validate_log_level(cls, v):
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()
    
    @validator("log_format")
    def validate_log_format(cls, v):
        valid_formats = ["json", "text"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Log format must be one of {valid_formats}")
        return v.lower()
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# Global settings instance
settings = Settings()

