"""
Celery Tasks
============

Async task definitions for background processing of DSL to PNG conversion.
Handles job queuing, status tracking, and result persistence.
"""

from typing import Optional, Dict, Any
import asyncio
from datetime import datetime, timedelta
import uuid

from celery import Celery
from celery.result import AsyncResult
from celery.signals import task_prerun, task_postrun, task_failure

from src.config.settings import get_settings
from src.config.logging import get_logger
from src.config.database import get_redis_client
from src.core.dsl.parser import parse_dsl
from src.core.rendering.html_generator import generate_html
from src.core.rendering.png_generator import generate_png_from_html
from src.models.schemas import (
    DSLRenderRequest, RenderOptions, TaskStatus, 
    TaskResult, PNGResult
)

logger = get_logger(__name__)

# Initialize Celery app
settings = get_settings()
celery_app = Celery(
    'dsl_png_tasks',
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=['src.core.queue.tasks']
)

# Configure Celery
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=settings.celery_task_timeout,
    task_soft_time_limit=settings.celery_task_timeout - 30,
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)


class TaskTracker:
    """Utility class for tracking task status and results."""
    
    @staticmethod
    async def update_task_status(task_id: str, status: TaskStatus, 
                               progress: Optional[int] = None,
                               message: Optional[str] = None,
                               result: Optional[Dict[str, Any]] = None) -> None:
        """
        Update task status in Redis.
        
        Args:
            task_id: Task identifier
            status: Task status
            progress: Progress percentage (0-100)
            message: Status message
            result: Task result data
        """
        async with get_redis_client() as redis:
            task_data = {
                "task_id": task_id,
                "status": status.value,
                "updated_at": datetime.utcnow().isoformat(),
                "progress": progress,
                "message": message,
                "result": result
            }
            
            await redis.hset(f"task:{task_id}", mapping=task_data)
            await redis.expire(f"task:{task_id}", 3600)  # Expire after 1 hour
    
    @staticmethod
    async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status from Redis.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task status data or None if not found
        """
        async with get_redis_client() as redis:
            task_data = await redis.hgetall(f"task:{task_id}")
            return task_data if task_data else None


@celery_app.task(bind=True, name='render_dsl_to_png')
def render_dsl_to_png_task(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Celery task for rendering DSL to PNG.
    
    Args:
        request_data: DSL render request data
        
    Returns:
        Task result data
    """
    task_id = self.request.id
    logger.info("Starting DSL to PNG rendering task", task_id=task_id)
    
    try:
        # Parse request
        request = DSLRenderRequest(**request_data)
        
        # Run async processing in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                _process_dsl_render_request(task_id, request)
            )
            return result.dict()
        finally:
            loop.close()
    
    except Exception as e:
        error_msg = f"Task failed: {str(e)}"
        logger.error("DSL to PNG task failed", task_id=task_id, error=error_msg)
        
        # Update task status
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(
                TaskTracker.update_task_status(
                    task_id, TaskStatus.FAILED, message=error_msg
                )
            )
        finally:
            loop.close()
        
        raise


async def _process_dsl_render_request(task_id: str, request: DSLRenderRequest) -> TaskResult:
    """
    Process DSL render request asynchronously.
    
    Args:
        task_id: Task identifier
        request: DSL render request
        
    Returns:
        Task result
    """
    start_time = datetime.utcnow()
    
    try:
        # Update status: Started
        await TaskTracker.update_task_status(
            task_id, TaskStatus.PROCESSING, progress=0,
            message="Starting DSL parsing"
        )
        
        # Step 1: Parse DSL
        logger.info("Parsing DSL content", task_id=task_id, content_length=len(request.dsl_content))
        parse_result = await parse_dsl(request.dsl_content)
        
        if not parse_result.success:
            error_msg = f"DSL parsing failed: {'; '.join(parse_result.errors)}"
            await TaskTracker.update_task_status(
                task_id, TaskStatus.FAILED, message=error_msg
            )
            raise ValueError(error_msg)
        
        await TaskTracker.update_task_status(
            task_id, TaskStatus.PROCESSING, progress=25,
            message="DSL parsed successfully, generating HTML"
        )
        
        # Step 2: Generate HTML
        logger.info("Generating HTML", task_id=task_id, element_count=len(parse_result.document.elements))
        html_content = await generate_html(parse_result.document, request.options)
        
        await TaskTracker.update_task_status(
            task_id, TaskStatus.PROCESSING, progress=50,
            message="HTML generated, creating PNG"
        )
        
        # Step 3: Generate PNG
        logger.info("Generating PNG", task_id=task_id,
                   width=request.options.width, height=request.options.height)
        png_result = await generate_png_from_html(html_content, request.options)
        
        await TaskTracker.update_task_status(
            task_id, TaskStatus.PROCESSING, progress=75,
            message="PNG generated, storing file"
        )
        
        # Step 4: Store PNG file
        from src.core.storage.manager import get_storage_manager
        storage_manager = await get_storage_manager()
        content_hash = await storage_manager.store_png(png_result, task_id)
        
        await TaskTracker.update_task_status(
            task_id, TaskStatus.PROCESSING, progress=90,
            message="File stored, finalizing result"
        )
        
        # Step 5: Prepare final result
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        
        # Add storage information to PNG result metadata
        png_result.metadata.update({
            'content_hash': content_hash,
            'storage_tier': 'hot',
            'task_id': task_id,
            'processing_time': processing_time
        })
        
        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            png_result=png_result,
            processing_time=processing_time,
            created_at=start_time,
            completed_at=datetime.utcnow()
        )
        
        # Update final status
        await TaskTracker.update_task_status(
            task_id, TaskStatus.COMPLETED, progress=100,
            message="Task completed successfully",
            result=task_result.dict()
        )
        
        logger.info("DSL to PNG task completed successfully",
                   task_id=task_id,
                   file_size=png_result.file_size,
                   content_hash=content_hash,
                   processing_time=processing_time)
        
        return task_result
        
    except Exception as e:
        processing_time = (datetime.utcnow() - start_time).total_seconds()
        error_msg = f"Task failed after {processing_time:.2f}s: {str(e)}"
        
        await TaskTracker.update_task_status(
            task_id, TaskStatus.FAILED,
            message=error_msg
        )
        
        logger.error("DSL to PNG task failed",
                    task_id=task_id,
                    error=str(e),
                    processing_time=processing_time)
        raise


@celery_app.task(name='cleanup_expired_tasks')
def cleanup_expired_tasks() -> Dict[str, Any]:
    """
    Periodic task to cleanup expired task data.
    
    Returns:
        Cleanup result summary
    """
    logger.info("Running expired tasks cleanup")
    
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(_cleanup_expired_tasks())
            return result
        finally:
            loop.close()
    
    except Exception as e:
        logger.error("Cleanup task failed", error=str(e))
        raise


async def _cleanup_expired_tasks() -> Dict[str, Any]:
    """Cleanup expired task data from Redis."""
    async with get_redis_client() as redis:
        # TODO: Implement cleanup logic
        # This is a stub for the actual cleanup implementation
        return {"cleaned_tasks": 0, "status": "completed"}


# Task signal handlers
@task_prerun.connect
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):
    """Handle task prerun signal."""
    logger.info("Task starting", task_id=task_id, task_name=task.name)


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, 
                        retval=None, state=None, **kwds):
    """Handle task postrun signal."""
    logger.info("Task completed", task_id=task_id, task_name=task.name, state=state)


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """Handle task failure signal."""
    logger.error("Task failed", task_id=task_id, exception=str(exception))


# Task management functions
async def submit_render_task(request: DSLRenderRequest) -> str:
    """
    Submit a DSL to PNG rendering task.
    
    Args:
        request: DSL render request
        
    Returns:
        Task ID
    """
    task_id = str(uuid.uuid4())
    
    # Submit to Celery
    result = render_dsl_to_png_task.apply_async(
        args=[request.dict()],
        task_id=task_id
    )
    
    # Initialize task status
    await TaskTracker.update_task_status(
        task_id, TaskStatus.PENDING,
        message="Task queued for processing"
    )
    
    logger.info("DSL render task submitted", task_id=task_id)
    return task_id


async def get_task_result(task_id: str) -> Optional[TaskResult]:
    """
    Get task result by ID.
    
    Args:
        task_id: Task identifier
        
    Returns:
        Task result or None if not found
    """
    # Get from Redis first (faster)
    task_data = await TaskTracker.get_task_status(task_id)
    
    if task_data and task_data.get("result"):
        return TaskResult(**task_data["result"])
    
    # Fallback to Celery result backend
    celery_result = AsyncResult(task_id, app=celery_app)
    if celery_result.ready():
        try:
            result_data = celery_result.get()
            return TaskResult(**result_data)
        except Exception as e:
            logger.error("Failed to get Celery result", task_id=task_id, error=str(e))
    
    return None


async def cancel_task(task_id: str) -> bool:
    """
    Cancel a running task.
    
    Args:
        task_id: Task identifier
        
    Returns:
        True if cancelled successfully
    """
    try:
        celery_app.control.revoke(task_id, terminate=True)
        
        await TaskTracker.update_task_status(
            task_id, TaskStatus.CANCELLED,
            message="Task cancelled by user"
        )
        
        logger.info("Task cancelled", task_id=task_id)
        return True
    
    except Exception as e:
        logger.error("Failed to cancel task", task_id=task_id, error=str(e))
        return False