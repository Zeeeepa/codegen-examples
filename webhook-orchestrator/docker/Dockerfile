# Multi-stage Dockerfile for webhook orchestrator
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r app && useradd -r -g app app

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ ./app/
COPY alembic.ini .
COPY alembic/ ./alembic/

# Create necessary directories
RUN mkdir -p /app/logs && chown -R app:app /app

# Switch to app user
USER app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]


# Development stage
FROM base as development

USER root

# Install development dependencies
RUN pip install --no-cache-dir \
    pytest \
    pytest-asyncio \
    pytest-cov \
    black \
    isort \
    flake8 \
    mypy

USER app

# Override command for development
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]


# Production stage
FROM base as production

# Copy only necessary files
COPY --from=base /app /app

# Set production environment
ENV ENVIRONMENT=production

# Use gunicorn for production
CMD ["gunicorn", "app.main:app", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000"]


# Celery worker stage
FROM base as celery-worker

# Copy application code
COPY --from=base /app /app

# Set environment for worker
ENV CELERY_WORKER=true

# Command for Celery worker
CMD ["celery", "-A", "app.tasks.celery_app", "worker", "--loglevel=info", "--concurrency=4"]


# Celery beat stage
FROM base as celery-beat

# Copy application code
COPY --from=base /app /app

# Set environment for beat
ENV CELERY_BEAT=true

# Command for Celery beat
CMD ["celery", "-A", "app.tasks.celery_app", "beat", "--loglevel=info"]


# Celery flower stage (monitoring)
FROM base as celery-flower

# Install flower
RUN pip install --no-cache-dir flower

# Copy application code
COPY --from=base /app /app

# Expose flower port
EXPOSE 5555

# Command for Celery flower
CMD ["celery", "-A", "app.tasks.celery_app", "flower", "--port=5555"]

