"""
Application Settings
===================

Main application settings and environment configuration using Pydantic Settings.
Supports development, testing, and production environments.
"""

from typing import Optional, List, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json
from pathlib import Path


class Settings(BaseSettings):
    """Main application settings with environment variable support."""

    # Application Configuration
    app_name: str = Field(default="DSL to PNG MCP Server", description="Application name")
    app_version: str = Field(default="1.0.0", description="Application version")
    environment: str = Field(
        default="development", description="Environment: development, testing, production"
    )
    debug: bool = Field(default=True, description="Debug mode")

    # Server Configuration
    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    workers: int = Field(default=1, description="Number of worker processes")

    # MCP Server Configuration
    mcp_host: str = Field(default="localhost", description="MCP server host")
    mcp_port: int = Field(default=3001, description="MCP server port")

    # Redis Configuration
    redis_url: str = Field(
        default="redis://:devpassword@redis:6379/0", description="Redis connection URL"
    )
    redis_max_connections: int = Field(default=100, description="Redis connection pool size")

    # Database Configuration (for future use)
    database_url: Optional[str] = Field(default=None, description="Database connection URL")

    # Storage Configuration
    storage_path: Path = Field(default=Path("./storage"), description="Storage directory path")
    temp_path: Path = Field(default=Path("./tmp"), description="Temporary files directory")
    cache_ttl: int = Field(default=3600, description="Cache TTL in seconds")

    # Rendering Configuration
    default_width: int = Field(default=800, description="Default render width")
    default_height: int = Field(default=600, description="Default render height")
    max_width: int = Field(default=2000, description="Maximum render width")
    max_height: int = Field(default=2000, description="Maximum render height")
    render_timeout: int = Field(default=30, description="Render timeout in seconds")

    # Browser Configuration
    playwright_headless: bool = Field(default=True, description="Run browser in headless mode")
    playwright_timeout: int = Field(default=30000, description="Playwright timeout in milliseconds")
    browser_pool_size: int = Field(default=5, description="Browser instance pool size")

    # Celery Configuration
    celery_broker_url: str = Field(
        default="redis://:devpassword@redis:6379/1", description="Celery broker URL"
    )
    celery_result_backend: str = Field(
        default="redis://:devpassword@redis:6379/1", description="Celery result backend URL"
    )
    celery_task_timeout: int = Field(default=300, description="Celery task timeout in seconds")
    celery_log_level: str = Field(default="INFO", description="Celery log level")
    celery_concurrency: int = Field(default=2, description="Celery worker concurrency")

    # API Documentation Configuration
    enable_docs: bool = Field(default=True, description="Enable FastAPI docs endpoint")
    enable_redoc: bool = Field(default=True, description="Enable FastAPI redoc endpoint")

    # Security Configuration
    allowed_hosts: List[str] = Field(default=["*"], description="Allowed hosts for CORS")
    api_key: Optional[str] = Field(default=None, description="API key for authentication")
    api_keys: List[str] = Field(
        default=["test-api-key-123", "development-key"], description="Valid API keys"
    )
    api_key_hashes: List[str] = Field(default=[], description="Valid API key hashes")
    skip_api_key_validation: bool = Field(
        default=True, description="Skip API key validation in development"
    )
    secret_key: str = Field(
        default="dev-secret-key-change-in-production", description="Secret key for sessions"
    )

    # SSE Configuration
    sse_enabled: bool = Field(default=True, description="Enable Server-Sent Events")
    sse_max_connections: int = Field(default=50, description="Maximum SSE connections")
    sse_heartbeat_interval: int = Field(default=30, description="SSE heartbeat interval in seconds")
    sse_heartbeat_interval_seconds: int = Field(
        default=30, description="SSE heartbeat interval in seconds"
    )
    sse_connection_timeout: int = Field(
        default=300, description="SSE connection timeout in seconds"
    )
    sse_connection_timeout_seconds: int = Field(
        default=300, description="SSE connection timeout in seconds"
    )
    sse_redis_channel: str = Field(default="sse_events", description="Redis channel for SSE events")
    sse_event_buffer_size: int = Field(
        default=100, description="SSE event buffer size per connection"
    )

    # Monitoring Configuration
    enable_metrics: bool = Field(default=True, description="Enable Prometheus metrics")
    metrics_port: int = Field(default=9090, description="Metrics server port")
    log_level: str = Field(default="INFO", description="Logging level")

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Validate environment value."""
        allowed = {"development", "testing", "production"}
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level."""
        allowed = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in allowed:
            raise ValueError(f"Log level must be one of: {allowed}")
        return v.upper()

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def parse_allowed_hosts(cls, v: Union[str, List[str]]) -> List[str]:
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            # Handle JSON-like string: ["*"] or ["host1", "host2"]
            v = v.strip()
            if v.startswith("[") and v.endswith("]"):
                try:
                    return json.loads(v)
                except json.JSONDecodeError:
                    pass
            # Handle comma-separated string: "*" or "host1,host2"
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    @field_validator("storage_path", "temp_path")
    @classmethod
    def create_directories(cls, v: Path) -> Path:
        """Ensure directories exist."""
        v.mkdir(parents=True, exist_ok=True)
        return v

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False, env_prefix="DSL_PNG_"
    )


# Global settings instance - will be initialized when needed
settings = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global settings
    if settings is None:
        settings = Settings()
    return settings


def reload_settings() -> Settings:
    """Reload settings from environment."""
    global settings
    settings = Settings()
    return settings
