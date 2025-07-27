# =============================================================================
# Multi-Stage Dockerfile for DSL to PNG MCP Server
# =============================================================================
# This Dockerfile supports multiple services:
# - mcp-server: MCP protocol handling service
# - fastapi-server: REST API service  
# - celery-workers: Background task processing workers
# - playwright-browsers: Browser pool service
# =============================================================================

# -----------------------------------------------------------------------------
# Stage 1: Base Python Environment
# -----------------------------------------------------------------------------
FROM python:3.11-slim as base

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # Essential build tools
    build-essential \
    curl \
    git \
    # Required for Playwright
    libnss3 \
    libatk-bridge2.0-0 \
    libdrm2 \
    libxkbcommon0 \
    libgtk-3-0 \
    libgbm1 \
    libasound2 \
    # Required for image processing
    libmagickwand-dev \
    # Cleanup
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd --gid 1000 appuser \
    && useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

# Set working directory
WORKDIR /app

# -----------------------------------------------------------------------------
# Stage 2: Dependencies Installation
# -----------------------------------------------------------------------------
FROM base as dependencies

# Copy requirements files
COPY requirements/ requirements/

# Install Python dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements/base.txt

# -----------------------------------------------------------------------------
# Stage 3: Development Dependencies (for dev builds)
# -----------------------------------------------------------------------------
FROM dependencies as dev-dependencies

# Install development dependencies
RUN pip install -r requirements/dev.txt

# -----------------------------------------------------------------------------
# Stage 4: Production Dependencies 
# -----------------------------------------------------------------------------
FROM dependencies as prod-dependencies

# Install production dependencies
RUN pip install -r requirements/prod.txt

# -----------------------------------------------------------------------------
# Stage 5: Application Code (before browser install)
# -----------------------------------------------------------------------------
FROM prod-dependencies as app-prep

# Copy application code
COPY src/ src/
COPY pyproject.toml setup.cfg ./

# Install the application
RUN pip install -e .

# Create necessary directories and set permissions
RUN mkdir -p /app/storage /app/tmp /app/logs /ms-playwright && \
    chown -R appuser:appuser /app /ms-playwright

# -----------------------------------------------------------------------------
# Stage 6: Playwright Browser Installation
# -----------------------------------------------------------------------------
FROM app-prep as app-base

# Set Playwright environment for proper installation
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# Install Playwright browsers and dependencies as root but with proper permissions
RUN playwright install chromium firefox webkit && \
    playwright install-deps && \
    chown -R appuser:appuser /ms-playwright

# Switch to non-root user
USER appuser

# -----------------------------------------------------------------------------
# Stage 7: MCP Server Service
# -----------------------------------------------------------------------------
FROM app-base as mcp-server

# Expose MCP server port
EXPOSE 3001

# Set environment variables for HTTP transport
ENV MCP_TRANSPORT=http \
    MCP_HOST=0.0.0.0 \
    MCP_PORT=3001

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:3001/health || exit 1

# Run MCP server
CMD ["python", "-m", "src.mcp_server.server"]

# -----------------------------------------------------------------------------
# Stage 8: FastAPI Server Service
# -----------------------------------------------------------------------------
FROM app-base as fastapi-server

# Expose FastAPI port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI server with Gunicorn in production
CMD ["gunicorn", "src.api.main:app", \
    "--workers", "2", \
    "--worker-class", "uvicorn.workers.UvicornWorker", \
    "--bind", "0.0.0.0:8000", \
    "--timeout", "300", \
    "--keep-alive", "5", \
    "--max-requests", "1000", \
    "--max-requests-jitter", "100"]

# -----------------------------------------------------------------------------
# Stage 9: Celery Worker Service
# -----------------------------------------------------------------------------
FROM app-base as celery-worker

# Health check for Celery workers
HEALTHCHECK --interval=60s --timeout=10s --start-period=10s --retries=3 \
    CMD celery -A src.core.queue.tasks inspect ping || exit 1

# Run Celery worker
CMD ["celery", "-A", "src.core.queue.tasks", "worker", \
    "--loglevel=info", \
    "--concurrency=2", \
    "--max-tasks-per-child=100", \
    "--time-limit=300", \
    "--soft-time-limit=270"]

# -----------------------------------------------------------------------------
# Stage 10: Playwright Browser Pool Service
# -----------------------------------------------------------------------------
FROM app-base as playwright-browsers

# Expose browser pool port (if needed)
EXPOSE 9222

# Set browser-specific environment variables
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD=0

# Health check for browser pool
HEALTHCHECK --interval=30s --timeout=15s --start-period=10s --retries=3 \
    CMD python -c "from playwright.async_api import async_playwright; import asyncio; asyncio.run(async_playwright().start())" || exit 1

# Run browser service HTTP API server
CMD ["uvicorn", "src.core.rendering.browser_service_api:app", \
    "--host", "0.0.0.0", \
    "--port", "8080", \
    "--workers", "1"]

# -----------------------------------------------------------------------------
# Stage 11: Development Build
# -----------------------------------------------------------------------------
FROM dev-dependencies as development

# Copy application code
COPY src/ src/
COPY pyproject.toml setup.cfg ./

# Install the application in development mode
RUN pip install -e .

# Install Playwright browsers for development
RUN playwright install chromium

# Create directories
RUN mkdir -p /app/storage /app/tmp /app/logs && \
    chown -R appuser:appuser /app

USER appuser

# Default development command
CMD ["python", "-m", "src.api.main"]

# -----------------------------------------------------------------------------
# Build Arguments and Labels
# -----------------------------------------------------------------------------
ARG BUILD_DATE
ARG VCS_REF
ARG VERSION=1.0.0

LABEL org.label-schema.build-date=$BUILD_DATE \
    org.label-schema.name="dsl-to-png-mcp" \
    org.label-schema.description="DSL to PNG conversion service with MCP protocol" \
    org.label-schema.version=$VERSION \
    org.label-schema.vcs-ref=$VCS_REF \
    org.label-schema.schema-version="1.0" \
    maintainer="DSL PNG Team"
