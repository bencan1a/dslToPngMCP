"""
Logging Configuration
====================

Structured logging configuration with environment-specific settings.
Uses structlog for structured logging with JSON output in production.
"""

import logging
import logging.config
import sys
from typing import Dict, Any, TYPE_CHECKING
import structlog
from structlog.types import Processor

from .settings import get_settings

if TYPE_CHECKING:
    from .settings import Settings


def setup_logging() -> None:
    """Setup application logging configuration."""
    settings = get_settings()

    # Configure structlog
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    if settings.environment == "production":
        # JSON output for production
        processors.append(structlog.processors.JSONRenderer())
    else:
        # Pretty output for development
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging_config = get_logging_config(settings)
    logging.config.dictConfig(logging_config)


def get_logging_config(settings: "Settings") -> Dict[str, Any]:
    """Get logging configuration dictionary."""
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "detailed": {
                "format": "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": "pythonjsonlogger.jsonlogger.JsonFormatter",
                "format": "%(asctime)s %(name)s %(levelname)s %(message)s",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "standard" if settings.environment != "production" else "json",
                "stream": sys.stdout,
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "detailed",
                "filename": f"{settings.storage_path}/logs/app.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
            "error_file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": "ERROR",
                "formatter": "detailed",
                "filename": f"{settings.storage_path}/logs/error.log",
                "maxBytes": 10485760,  # 10MB
                "backupCount": 5,
            },
        },
        "loggers": {
            "": {  # Root logger
                "level": settings.log_level,
                "handlers": (
                    ["console", "file", "error_file"]
                    if settings.environment != "testing"
                    else ["console"]
                ),
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "celery": {
                "level": "INFO",
                "handlers": ["console", "file"],
                "propagate": False,
            },
            "playwright": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a structured logger instance."""
    return structlog.get_logger(name)


# Ensure log directories exist
def ensure_log_directories() -> None:
    """Ensure log directories exist."""
    settings = get_settings()
    log_dir = settings.storage_path / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)


# Initialize logging on import
ensure_log_directories()
setup_logging()
