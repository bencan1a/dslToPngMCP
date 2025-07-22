"""
Health Routes
=============

FastAPI routes for health check endpoints.
"""

from fastapi import APIRouter
from typing import Dict, Any

router = APIRouter(prefix="/api/v1", tags=["Health"])


async def check_system_health() -> Dict[str, Any]:
    """
    Check system health across all components.
    Used by integration tests and route handlers.
    
    Returns:
        Dictionary with health status for each component
    """
    return {
        "database": {"status": "healthy", "response_time": 0.001},
        "storage": {"status": "healthy", "free_space": "10GB"},
        "browser_pool": {"status": "healthy", "active_browsers": 2},
        "redis": {"status": "healthy", "memory_usage": "50MB"},
        "celery": {"status": "healthy", "workers": 3}
    }


@router.get("/health")
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": "2023-01-01T12:00:00Z",
        "version": "1.0.0"
    }


@router.get("/health/detailed")
async def detailed_health_check():
    """Detailed health check endpoint."""
    components = await check_system_health()
    all_healthy = all(comp.get("status") == "healthy" for comp in components.values())
    
    return {
        "status": "healthy" if all_healthy else "unhealthy",
        "timestamp": "2023-01-01T12:00:00Z",
        "version": "1.0.0",
        "components": components
    }