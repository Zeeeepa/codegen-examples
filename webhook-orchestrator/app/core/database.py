"""
Database configuration and models for the webhook orchestrator.
"""
import asyncio
from datetime import datetime
from typing import Optional, AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Boolean, 
    JSON, ForeignKey, Index, create_engine
)
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.pool import NullPool

from .config import settings
from .logging import get_logger

logger = get_logger(__name__)

Base = declarative_base()


class WebhookEvent(Base):
    """Model for storing webhook events."""
    __tablename__ = "webhook_events"
    
    id = Column(Integer, primary_key=True, index=True)
    delivery_id = Column(String(255), unique=True, index=True, nullable=False)
    event_type = Column(String(100), index=True, nullable=False)
    source = Column(String(50), nullable=False, default="github")
    payload = Column(JSON, nullable=False)
    headers = Column(JSON)
    signature = Column(String(255))
    processed = Column(Boolean, default=False, index=True)
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    tasks = relationship("WorkflowTask", back_populates="webhook_event")
    
    __table_args__ = (
        Index("idx_webhook_events_type_created", "event_type", "created_at"),
        Index("idx_webhook_events_processed_created", "processed", "created_at"),
    )


class WorkflowTask(Base):
    """Model for storing workflow tasks."""
    __tablename__ = "workflow_tasks"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), unique=True, index=True, nullable=False)
    webhook_event_id = Column(Integer, ForeignKey("webhook_events.id"), index=True)
    task_type = Column(String(100), index=True, nullable=False)
    status = Column(String(50), default="pending", index=True)
    priority = Column(Integer, default=0, index=True)
    
    # Task context
    repository = Column(String(255), index=True)
    pr_number = Column(Integer, index=True)
    branch = Column(String(255))
    commit_sha = Column(String(40))
    
    # Task configuration
    config = Column(JSON)
    input_data = Column(JSON)
    output_data = Column(JSON)
    
    # Execution tracking
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    max_retries = Column(Integer, default=3)
    
    # External references
    codegen_task_id = Column(String(255), index=True)
    codegen_task_url = Column(String(500))
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    webhook_event = relationship("WebhookEvent", back_populates="tasks")
    
    __table_args__ = (
        Index("idx_workflow_tasks_status_priority", "status", "priority"),
        Index("idx_workflow_tasks_repo_pr", "repository", "pr_number"),
        Index("idx_workflow_tasks_type_status", "task_type", "status"),
    )


class TaskExecution(Base):
    """Model for storing task execution history."""
    __tablename__ = "task_executions"
    
    id = Column(Integer, primary_key=True, index=True)
    task_id = Column(String(255), ForeignKey("workflow_tasks.task_id"), index=True)
    execution_id = Column(String(255), unique=True, index=True, nullable=False)
    status = Column(String(50), nullable=False)
    
    # Execution details
    started_at = Column(DateTime, nullable=False)
    completed_at = Column(DateTime)
    duration_ms = Column(Integer)
    
    # Results
    result = Column(JSON)
    error_message = Column(Text)
    error_traceback = Column(Text)
    
    # Metadata
    worker_id = Column(String(255))
    queue_name = Column(String(100))
    
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_task_executions_task_started", "task_id", "started_at"),
        Index("idx_task_executions_status_created", "status", "created_at"),
    )


class SystemMetrics(Base):
    """Model for storing system metrics."""
    __tablename__ = "system_metrics"
    
    id = Column(Integer, primary_key=True, index=True)
    metric_name = Column(String(100), index=True, nullable=False)
    metric_value = Column(JSON, nullable=False)
    labels = Column(JSON)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        Index("idx_system_metrics_name_timestamp", "metric_name", "timestamp"),
    )


# Database engine and session management
class DatabaseManager:
    """Database connection and session manager."""
    
    def __init__(self):
        self.async_engine = None
        self.async_session_factory = None
        self.sync_engine = None
        self.sync_session_factory = None
    
    async def initialize(self):
        """Initialize database connections."""
        logger.info("Initializing database connections")
        
        # Async engine for FastAPI
        self.async_engine = create_async_engine(
            settings.database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.debug,
            poolclass=NullPool if "sqlite" in settings.database_url else None,
        )
        
        self.async_session_factory = async_sessionmaker(
            self.async_engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )
        
        # Sync engine for Celery tasks
        sync_database_url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        self.sync_engine = create_engine(
            sync_database_url,
            pool_size=settings.database_pool_size,
            max_overflow=settings.database_max_overflow,
            echo=settings.debug,
        )
        
        self.sync_session_factory = sessionmaker(
            self.sync_engine,
            expire_on_commit=False,
        )
        
        logger.info("Database connections initialized")
    
    async def close(self):
        """Close database connections."""
        if self.async_engine:
            await self.async_engine.dispose()
        if self.sync_engine:
            self.sync_engine.dispose()
        logger.info("Database connections closed")
    
    @asynccontextmanager
    async def get_async_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get async database session."""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    def get_sync_session(self):
        """Get sync database session for Celery tasks."""
        return self.sync_session_factory()


# Global database manager instance
db_manager = DatabaseManager()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Dependency for getting database session in FastAPI."""
    async with db_manager.get_async_session() as session:
        yield session


async def create_tables():
    """Create database tables."""
    logger.info("Creating database tables")
    async with db_manager.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables created")


async def drop_tables():
    """Drop database tables."""
    logger.info("Dropping database tables")
    async with db_manager.async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.info("Database tables dropped")

