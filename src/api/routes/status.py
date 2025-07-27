"""
Status Routes
=============

FastAPI routes for system status and metrics endpoints.
"""

from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/v1", tags=["Status"])


async def get_system_status() -> Dict[str, Any]:
    """
    Get system status information.
    Used by integration tests and route handlers.

    Returns:
        Dictionary with system status metrics
    """
    return {
        "queue_length": 0,
        "active_tasks": 0,
        "completed_tasks": 0,
        "failed_tasks": 0,
        "storage_usage": {"hot": "0MB", "warm": "0MB"},
        "uptime": 0,
    }


async def get_metrics() -> Dict[str, Any]:
    """
    Get system metrics.
    Used by integration tests and route handlers.

    Returns:
        Dictionary with system metrics
    """
    return {
        "requests_per_minute": 0.0,
        "average_processing_time": 0.0,
        "success_rate": 1.0,
        "error_rate": 0.0,
        "cache_hit_rate": 0.0,
    }


@router.get("/status")
async def system_status() -> dict[str, Any]:
    """Get system status endpoint."""
    return await get_system_status()


@router.get("/metrics")
async def metrics() -> dict[str, Any]:
    """Get system metrics endpoint."""
    return await get_metrics()
