"""
FastAPI Application
==================

Main FastAPI application with REST endpoints for DSL to PNG conversion.
Provides both synchronous and asynchronous rendering capabilities.
"""

from contextlib import asynccontextmanager
from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import JSONResponse
from fastapi.exception_handlers import http_exception_handler
import uvicorn

from src.config.settings import get_settings
from src.config.logging import get_logger
from src.config.database import initialize_databases, close_databases, check_database_health
from src.core.rendering.png_generator import initialize_browser_pool, close_browser_pool, PNGGenerationError
from src.core.rendering.html_generator import generate_html
from src.core.rendering.png_generator import generate_png_from_html
from src.core.storage.manager import get_storage_manager, close_storage_manager
from src.core.queue.tasks import submit_render_task, get_task_result, cancel_task
from src.core.dsl.parser import validate_dsl_syntax, parse_dsl, get_validation_suggestions
from src.models.schemas import (
    DSLRenderRequest, DSLValidationRequest, DSLValidationResponse,
    RenderResponse, AsyncRenderResponse, TaskStatusResponse,
    HealthStatus, ErrorResponse, TaskStatus, PNGResult
)

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting FastAPI application")
    
    # Initialize databases first
    try:
        await initialize_databases()
        logger.info("Databases initialized")
    except Exception as e:
        logger.error("Failed to initialize databases", error=str(e))
        raise RuntimeError(f"Database initialization failed: {e}")
    
    # Initialize storage manager
    try:
        storage_manager = await get_storage_manager()
        logger.info("Storage manager initialized")
    except Exception as e:
        logger.error("Failed to initialize storage manager", error=str(e))
        # Storage manager is optional, continue without it
        logger.warning("Continuing without storage manager")
    
    # Initialize browser pool with error handling
    try:
        await initialize_browser_pool()
        logger.info("Browser pool initialized")
    except PNGGenerationError as e:
        logger.error("Browser pool initialization failed", error=str(e))
        raise RuntimeError(f"Browser pool initialization failed: {e}")
    except Exception as e:
        logger.error("Unexpected error during browser pool initialization", error=str(e))
        raise RuntimeError(f"Browser pool initialization failed: {e}")
    
    try:
        yield
    finally:
        # Shutdown
        logger.info("Shutting down FastAPI application")
        
        # Close storage manager
        try:
            await close_storage_manager()
            logger.info("Storage manager closed")
        except Exception as e:
            logger.error("Error closing storage manager", error=str(e))
        
        # Close browser pool
        try:
            await close_browser_pool()
            logger.info("Browser pool closed")
        except Exception as e:
            logger.error("Error closing browser pool", error=str(e))
        
        # Close databases last
        try:
            await close_databases()
            logger.info("Databases closed")
        except Exception as e:
            logger.error("Error closing databases", error=str(e))


# Create FastAPI app
settings = get_settings()
app = FastAPI(
    title="DSL to PNG MCP Server",
    description="Convert Domain Specific Language (DSL) definitions to PNG images",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_hosts,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

app.add_middleware(GZipMiddleware, minimum_size=1000)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add request ID to all requests."""
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    
    return response


# Exception handlers
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    """Custom HTTP exception handler with structured error response."""
    error_response = ErrorResponse(
        error=exc.detail,
        error_code=str(exc.status_code),
        request_id=getattr(request.state, "request_id", None)
    )
    
    logger.error("HTTP exception", 
                status_code=exc.status_code,
                detail=exc.detail,
                request_id=error_response.request_id)
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(PNGGenerationError)
async def png_generation_exception_handler(request: Request, exc: PNGGenerationError):
    """Handle PNG generation errors with specific error codes."""
    error_message = str(exc)
    
    # Determine specific error code based on error message
    if "Browser pool not initialized" in error_message:
        error_code = "BROWSER_POOL_NOT_INITIALIZED"
        status_code = 503
        user_message = "Browser pool is not available. Please try again later."
    elif "Browser pool initialization failed" in error_message:
        error_code = "BROWSER_POOL_INITIALIZATION_FAILED"
        status_code = 503
        user_message = "Failed to initialize browser pool. Service temporarily unavailable."
    elif "Browser pool exhausted" in error_message or "No available browser" in error_message:
        error_code = "BROWSER_POOL_EXHAUSTED"
        status_code = 503
        user_message = "All browser instances are busy. Please try again in a moment."
    elif "Browser launch failed" in error_message or "launch" in error_message.lower():
        error_code = "BROWSER_LAUNCH_FAILED"
        status_code = 503
        user_message = "Failed to launch browser instance. Service temporarily unavailable."
    elif "timeout" in error_message.lower() or "timed out" in error_message.lower():
        error_code = "BROWSER_TIMEOUT"
        status_code = 504
        user_message = "Browser operation timed out. Please try again."
    else:
        error_code = "PNG_GENERATION_ERROR"
        status_code = 500
        user_message = "PNG generation failed due to an internal error."
    
    error_response = ErrorResponse(
        error=user_message,
        error_code=error_code,
        details={"message": error_message} if settings.debug else None,
        request_id=getattr(request.state, "request_id", None)
    )
    
    logger.error("PNG generation error",
                error_code=error_code,
                error_message=error_message,
                request_id=error_response.request_id)
    
    return JSONResponse(
        status_code=status_code,
        content=error_response.model_dump(mode='json')
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """General exception handler for unexpected errors."""
    error_response = ErrorResponse(
        error="Internal server error",
        error_code="INTERNAL_ERROR",
        details={"exception": str(exc)} if settings.debug else None,
        request_id=getattr(request.state, "request_id", None)
    )
    
    logger.error("Unhandled exception",
                exception=str(exc),
                request_id=error_response.request_id,
                exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=error_response.model_dump(mode='json')
    )


# Dependency for getting current settings
def get_current_settings():
    """Dependency to get current settings."""
    return get_settings()


async def check_browser_pool_health():
    """Check browser pool health status."""
    from src.core.rendering.png_generator import _global_browser_pool
    
    try:
        if _global_browser_pool is None:
            return {
                "healthy": False,
                "status": "not_initialized",
                "available_browsers": 0,
                "total_browsers": 0,
                "error": "Browser pool not initialized"
            }
        
        # Check if browsers are available
        available_browsers = len(_global_browser_pool.browsers)
        total_browsers = _global_browser_pool.pool_size
        
        # Consider healthy if at least one browser is available
        healthy = available_browsers > 0
        
        return {
            "healthy": healthy,
            "status": "healthy" if healthy else "no_browsers_available",
            "available_browsers": available_browsers,
            "total_browsers": total_browsers,
            "pool_size": total_browsers
        }
        
    except Exception as e:
        return {
            "healthy": False,
            "status": "error",
            "available_browsers": 0,
            "total_browsers": 0,
            "error": str(e)
        }


# Health check endpoint
@app.get("/health", response_model=HealthStatus, tags=["Health"])
async def health_check():
    """
    Get application health status.
    
    Returns comprehensive health information including:
    - Overall application status
    - Database connectivity
    - Browser pool status
    - Queue status
    """
    try:
        logger.info("Health check requested")
        
        # Check database health
        db_health = await check_database_health()
        
        # Check browser pool health
        browser_pool_health = await check_browser_pool_health()
        browser_healthy = browser_pool_health["healthy"]
        
        # TODO: Add Celery health checks
        celery_healthy = True   # Placeholder
        
        # Determine overall status
        all_healthy = all([
            db_health.get("redis", False),
            db_health.get("postgres", True),  # Optional
            browser_healthy,
            celery_healthy
        ])
        
        overall_status = "healthy" if all_healthy else "unhealthy"
        
        health_status = HealthStatus(
            status=overall_status,
            version="1.0.0",
            database=db_health.get("redis", False),
            redis=db_health.get("redis", False),
            browser_pool=browser_healthy,
            celery=celery_healthy,
            active_tasks=0,  # TODO: Get actual task count
            queue_size=0     # TODO: Get actual queue size
        )
        
        # Add browser pool details to response if available
        if hasattr(health_status, 'details'):
            health_status.details = {
                "browser_pool": browser_pool_health,
                "database": db_health
            }
        
        logger.info("Health check completed",
                   status=overall_status,
                   browser_pool_status=browser_pool_health["status"],
                   available_browsers=browser_pool_health["available_browsers"])
        return health_status
        
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=503, detail="Health check failed")


# DSL validation endpoint
@app.post("/validate", response_model=DSLValidationResponse, tags=["DSL"])
async def validate_dsl(request: DSLValidationRequest):
    """
    Validate DSL syntax and structure without rendering.
    
    Args:
        request: DSL validation request
        
    Returns:
        Validation result with errors and suggestions
    """
    try:
        logger.info("DSL validation requested", content_length=len(request.dsl_content))
        
        # Perform syntax validation
        syntax_valid = await validate_dsl_syntax(request.dsl_content)
        
        if syntax_valid:
            # Perform full parsing for deeper validation
            parse_result = await parse_dsl(request.dsl_content)
            
            response = DSLValidationResponse(
                valid=parse_result.success,
                errors=parse_result.errors,
                warnings=getattr(parse_result, 'warnings', []),
                suggestions=[]  # TODO: Add validation suggestions
            )
        else:
            response = DSLValidationResponse(
                valid=False,
                errors=["Invalid DSL syntax"],
                warnings=[],
                suggestions=["Check JSON/YAML formatting", "Ensure proper nesting structure"]
            )
        
        logger.info("DSL validation completed", valid=response.valid, errors=len(response.errors))
        return response
        
    except Exception as e:
        logger.error("DSL validation failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Validation failed: {str(e)}")


# Synchronous rendering endpoint
@app.post("/render", response_model=RenderResponse, tags=["Rendering"])
async def render_dsl_sync(request: DSLRenderRequest):
    """
    Render DSL to PNG synchronously.
    
    Args:
        request: DSL render request
        
    Returns:
        Render result with PNG data
    """
    start_time = datetime.utcnow()
    
    try:
        logger.info("Synchronous render requested",
                   content_length=len(request.dsl_content),
                   width=request.options.width,
                   height=request.options.height)
        
        # Step 1: Parse DSL
        parse_result = await parse_dsl(request.dsl_content)
        
        if not parse_result.success:
            error_msg = f"DSL parsing failed: {'; '.join(parse_result.errors)}"
            suggestions = await get_validation_suggestions(request.dsl_content, parse_result.errors)
            detailed_error = f"{error_msg}. Suggestions: {'; '.join(suggestions[:3])}"
            
            processing_time = (datetime.utcnow() - start_time).total_seconds()
            return RenderResponse(
                success=False,
                png_result=None,
                error=detailed_error,
                processing_time=processing_time
            )
        
        # Step 2: Generate HTML
        html_content = await generate_html(parse_result.document, request.options)
        
        # Step 3: Generate PNG
        png_result = await generate_png_from_html(html_content, request.options)
        
        # Step 4: No storage system implemented yet
        # Add basic metadata
        png_result.metadata.update({
            'render_type': 'synchronous'
        })
        
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        response = RenderResponse(
            success=True,
            png_result=png_result,
            error=None,
            processing_time=processing_time
        )
        
        logger.info("Synchronous render completed successfully",
                   file_size=png_result.file_size,
                   processing_time=processing_time)
        
        return response
        
    except Exception as e:
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        error_msg = f"Rendering failed: {str(e)}"
        
        logger.error("Synchronous rendering failed",
                    error=error_msg,
                    processing_time=processing_time)
        
        return RenderResponse(
            success=False,
            png_result=None,
            error=error_msg,
            processing_time=processing_time
        )


# Asynchronous rendering endpoint
@app.post("/render/async", response_model=AsyncRenderResponse, tags=["Rendering"])
async def render_dsl_async(request: DSLRenderRequest):
    """
    Render DSL to PNG asynchronously.
    
    Args:
        request: DSL render request
        
    Returns:
        Task information for tracking render progress
    """
    try:
        logger.info("Asynchronous render requested",
                   content_length=len(request.dsl_content),
                   width=request.options.width,
                   height=request.options.height)
        
        # Submit rendering task
        task_id = await submit_render_task(request)
        
        response = AsyncRenderResponse(
            task_id=task_id,
            status=TaskStatus.PENDING,
            estimated_completion=None  # TODO: Calculate based on queue size
        )
        
        logger.info("Asynchronous render submitted", task_id=task_id)
        return response
        
    except Exception as e:
        logger.error("Asynchronous rendering submission failed", error=str(e))
        raise HTTPException(status_code=400, detail=f"Failed to submit render task: {str(e)}")


# Task status endpoint
@app.get("/status/{task_id}", response_model=TaskStatusResponse, tags=["Tasks"])
async def get_task_status(task_id: str):
    """
    Get the status of an asynchronous rendering task.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Current task status and result if completed
    """
    try:
        logger.info("Task status requested", task_id=task_id)
        
        # Get task status from Redis
        from src.core.queue.tasks import TaskTracker
        task_data = await TaskTracker.get_task_status(task_id)
        
        if not task_data:
            raise HTTPException(status_code=404, detail="Task not found")
        
        # Get task result if completed
        task_result = None
        if task_data.get("status") == TaskStatus.COMPLETED.value:
            task_result = await get_task_result(task_id)
        
        response = TaskStatusResponse(
            task_id=task_id,
            status=TaskStatus(task_data.get("status", "unknown")),
            progress=task_data.get("progress"),
            message=task_data.get("message"),
            result=task_result,
            created_at=datetime.fromisoformat(task_data.get("created_at", datetime.utcnow().isoformat())),
            updated_at=datetime.fromisoformat(task_data.get("updated_at", datetime.utcnow().isoformat()))
        )
        
        logger.info("Task status retrieved", task_id=task_id, status=response.status)
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get task status", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to get task status: {str(e)}")


# Task cancellation endpoint
@app.delete("/tasks/{task_id}", tags=["Tasks"])
async def cancel_render_task(task_id: str):
    """
    Cancel a running rendering task.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Cancellation result
    """
    try:
        logger.info("Task cancellation requested", task_id=task_id)
        
        success = await cancel_task(task_id)
        
        if success:
            logger.info("Task cancelled successfully", task_id=task_id)
            return {"success": True, "message": "Task cancelled successfully"}
        else:
            raise HTTPException(status_code=400, detail="Failed to cancel task")
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Task cancellation failed", task_id=task_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to cancel task: {str(e)}")


# Root endpoint
@app.get("/", tags=["General"])
async def root():
    """
    Root endpoint with basic API information.
    """
    return {
        "name": "DSL to PNG MCP Server",
        "version": "1.0.0",
        "description": "Convert Domain Specific Language definitions to PNG images",
        "docs_url": "/docs" if settings.debug else None,
        "health_check": "/health",
        "endpoints": {
            "validate_dsl": "POST /validate",
            "render_sync": "POST /render",
            "render_async": "POST /render/async",
            "task_status": "GET /status/{task_id}",
            "cancel_task": "DELETE /tasks/{task_id}"
        }
    }


# Development server runner
def run_development_server():
    """Run development server with auto-reload."""
    uvicorn.run(
        "src.api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level=settings.log_level.lower(),
        access_log=True
    )


def create_app() -> FastAPI:
    """
    Application factory function for creating FastAPI app instance.
    Used by integration tests and external deployment scripts.
    
    Returns:
        FastAPI application instance
    """
    return app


if __name__ == "__main__":
    run_development_server()