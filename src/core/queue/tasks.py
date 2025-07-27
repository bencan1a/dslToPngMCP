"""
Celery Tasks
============

Async task definitions for background processing of DSL to PNG conversion.
Handles job queuing, status tracking, and result persistence.
"""

from typing import Optional, Dict, Any
import asyncio
from datetime import datetime, timezone
import uuid
import os
import threading
from enum import Enum

from celery import Celery  # type: ignore
from celery.result import AsyncResult  # type: ignore
from celery.signals import task_prerun, task_postrun, task_failure, worker_ready, worker_process_init  # type: ignore

from src.config.settings import get_settings
from src.config.logging import get_logger
from src.config.database import get_redis_client  # type: ignore[attr-defined]
from src.core.dsl.parser import parse_dsl
from src.core.rendering.html_generator import generate_html
from src.core.rendering.png_generator import generate_png_from_html
from src.models.schemas import DSLRenderRequest, TaskStatus, TaskResult

logger = get_logger(__name__)


def _inspect_dict_structure(
    data: Dict[str, Any], max_depth: int = 3, current_depth: int = 0
) -> Dict[str, Any]:
    """
    Recursively inspect dictionary structure to identify None values and data types.

    Args:
        data: Dictionary to inspect
        max_depth: Maximum recursion depth
        current_depth: Current recursion depth

    Returns:
        Inspection result with types and None value locations
    """
    if current_depth >= max_depth:
        return {"_truncated": True, "_type": type(data).__name__}

    result = {}

    for key, value in data.items():
        if value is None:
            result[key] = {"_type": "NoneType", "_value": None}
        elif isinstance(value, dict):
            result[key] = {
                "_type": "dict",
                "_structure": _inspect_dict_structure(value, max_depth, current_depth + 1),  # type: ignore
            }
        elif isinstance(value, list):
            result[key] = {
                "_type": "list",
                "_length": len(value),  # type: ignore
                "_sample": [type(item).__name__ for item in value[:3]] if value else [],  # type: ignore
            }
        else:
            result[key] = {
                "_type": type(value).__name__,
                "_serializable": _is_json_serializable(value),
            }

    return result  # type: ignore


def _is_json_serializable(obj: Any) -> bool:
    """Check if an object is JSON serializable."""
    import json

    try:
        json.dumps(obj)
        return True
    except (TypeError, ValueError):
        return False


def _filter_none_values(obj: Any) -> Any:
    """
    Recursively filter None values from nested dictionaries and lists.

    This prevents Redis DataError when Celery tries to serialize task arguments
    containing None values to Redis.

    Args:
        obj: Object to filter (dict, list, or primitive)

    Returns:
        Filtered object with None values removed
    """
    if isinstance(obj, dict):
        # Filter None values from dictionary, recursively process remaining values
        return {str(k): _filter_none_values(v) for k, v in obj.items() if v is not None}
    elif isinstance(obj, list):
        # Filter None values from list, recursively process remaining items
        return [_filter_none_values(item) for item in obj if item is not None]
    else:
        # Return primitive values as-is (they're already not None due to filtering above)
        return obj


# Initialize Celery app
settings = get_settings()
celery_app = Celery(  # type: ignore[misc]
    "dsl_png_tasks",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["src.core.queue.tasks"],
)

# Configure Celery
celery_app.conf.update(  # type: ignore[attr-defined]
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
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
    async def update_task_status(
        task_id: str,
        status: TaskStatus,
        progress: Optional[int] = None,
        message: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None,
        connection_id: Optional[str] = None,
    ) -> None:
        """
        Update task status in Redis and emit SSE event.

        Args:
            task_id: Task identifier
            status: Task status
            progress: Progress percentage (0-100)
            message: Status message
            result: Task result data
            connection_id: SSE connection ID for targeted events
        """
        # 🔍 ENHANCED DIAGNOSTIC: Log event loop state at the start of update_task_status
        try:
            current_loop = asyncio.get_running_loop()
            loop_info = {
                "loop_id": id(current_loop),
                "loop_running": current_loop.is_running(),
                "loop_closed": current_loop.is_closed(),
                "thread_id": threading.current_thread().ident,
                "process_id": os.getpid(),
            }
            logger.info(
                "🔍 TASK STATUS UPDATE: Starting task status update with event loop info",
                task_id=task_id,
                status=status.value,
                **loop_info,
            )
        except RuntimeError as e:
            logger.error(
                "🚨 NO EVENT LOOP: No running event loop detected in update_task_status",
                task_id=task_id,
                status=status.value,
                error=str(e),
                thread_id=threading.current_thread().ident,
                process_id=os.getpid(),
            )
            # Create a new event loop if none exists
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            logger.info(
                "✅ NEW EVENT LOOP: Created new event loop in update_task_status",
                task_id=task_id,
                loop_id=id(new_loop),
                thread_id=threading.current_thread().ident,
                process_id=os.getpid(),
            )

        try:
            task_data = {
                "task_id": task_id,
                "status": status.value,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "progress": progress,
                "message": message,
                "result": result,
            }

            # 🔍 ENHANCED DIAGNOSTIC LOGGING: Deep inspection of datetime and enum serialization
            logger.info(
                "🔍 REDIS DIAGNOSTIC: About to store task data in Redis",
                task_id=task_id,
                redis_key=f"task:{task_id}",
                task_data_keys=list(task_data.keys()),
                task_data_types={k: type(v).__name__ for k, v in task_data.items()},
                none_values=[k for k, v in task_data.items() if v is None],
                progress_value=progress,
                progress_type=type(progress).__name__ if progress is not None else "None",
                message_value=message,
                message_type=type(message).__name__ if message is not None else "None",
                result_value=result,
                result_type=type(result).__name__ if result is not None else "None",
                status_value=status.value,
                connection_id=connection_id,
                task_data_structure=_inspect_dict_structure(task_data, max_depth=2),
            )

            # 🔍 ROOT CAUSE VALIDATION: Specific checks for datetime and enum serialization issues
            if result is not None:
                logger.info(
                    "🔍 RESULT DATA ANALYSIS: Validating TaskResult serialization hypothesis",
                    task_id=task_id,
                    result_is_dict=isinstance(result, dict),  # type: ignore
                    result_keys=list(result.keys()) if isinstance(result, dict) else "not_dict",  # type: ignore
                    datetime_fields_detected=[
                        k
                        for k, v in (result.items() if isinstance(result, dict) else [])  # type: ignore
                        if isinstance(v, datetime)
                    ],
                    enum_fields_detected=[
                        k
                        for k, v in (result.items() if isinstance(result, dict) else [])  # type: ignore
                        if hasattr(v, "__class__") and issubclass(v.__class__, Enum)
                    ],
                    nested_datetime_scan={
                        k: [
                            nested_k
                            for nested_k, nested_v in (v.items() if isinstance(v, dict) else [])  # type: ignore
                            if isinstance(nested_v, datetime)
                        ]
                        for k, v in (result.items() if isinstance(result, dict) else [])  # type: ignore
                        if isinstance(v, dict)  # type: ignore
                    },
                    serialization_safe=all(
                        _is_json_serializable(v)
                        for v in (result.values() if isinstance(result, dict) else [])  # type: ignore
                    ),
                )

            # 🚨 FIX: JSON serialize complex objects for Redis storage
            import json

            redis_data = {}
            for key, value in task_data.items():
                if value is None:
                    # Skip None values to prevent Redis DataError
                    continue
                elif isinstance(value, (dict, list)):
                    # JSON serialize complex objects
                    redis_data[key] = json.dumps(value)
                else:
                    # Store primitive types directly
                    redis_data[key] = value

            # Get Redis client using async context manager
            from src.config.database import get_redis_client_context

            # 🔍 DIAGNOSTIC: Log Redis client context usage
            logger.info(
                "🔍 REDIS CONTEXT MANAGER: About to get Redis client using context manager",
                task_id=task_id,
                redis_key=f"task:{task_id}",
            )

            # REDIS OPERATION: Use async context manager for proper connection handling
            async with get_redis_client_context() as redis_client:
                try:
                    await redis_client.hset(f"task:{task_id}", mapping=redis_data)  # type: ignore
                    logger.info(
                        "🔍 REDIS SUCCESS: Task data stored successfully",
                        task_id=task_id,
                        redis_key=f"task:{task_id}",
                        original_none_count=len([k for k, v in task_data.items() if v is None]),
                        stored_keys_count=len(redis_data),
                        json_serialized_fields=[
                            k
                            for k, v in redis_data.items()
                            if isinstance(v, str) and v.startswith('{"')
                        ],
                    )
                except Exception as redis_error:
                    logger.error(
                        "🚨 REDIS ERROR: Failed to store task data - EXACT ERROR LOCATION IDENTIFIED",
                        task_id=task_id,
                        redis_key=f"task:{task_id}",
                        error_type=type(redis_error).__name__,
                        error_module=getattr(type(redis_error), "__module__", "unknown"),
                        error_message=str(redis_error),
                        error_repr=repr(redis_error),
                        task_data_causing_error=task_data,
                        none_fields_in_data=[k for k, v in task_data.items() if v is None],
                        problematic_values={
                            k: {"value": v, "type": type(v).__name__, "is_none": v is None}
                            for k, v in task_data.items()
                        },
                    )
                    # Re-raise the error to maintain original behavior
                    raise

                await redis_client.expire(f"task:{task_id}", 3600)  # type: ignore  # Expire after 1 hour

                # Emit SSE event if SSE is enabled
                settings = get_settings()
                if settings.sse_enabled:
                    await TaskTracker._emit_sse_event(
                        redis_client, task_id, status, progress, message, result, connection_id
                    )
        except Exception as e:
            # Log the error but don't close the Redis client
            logger.error(
                "🚨 ERROR in update_task_status",
                task_id=task_id,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            raise

    @staticmethod
    async def _emit_sse_event(
        redis: Any,  # Redis client type annotation
        task_id: str,
        status: TaskStatus,
        progress: Optional[int],
        message: Optional[str],
        result: Optional[Dict[str, Any]],
        connection_id: Optional[str],
    ) -> None:
        """
        Emit SSE event for task status update.

        Args:
            redis: Redis client
            task_id: Task identifier
            status: Task status
            progress: Progress percentage
            message: Status message
            result: Task result data
            connection_id: SSE connection ID for targeted events
        """
        # 🔍 ENHANCED DIAGNOSTIC: Log event loop state at the start of _emit_sse_event
        try:
            current_loop = asyncio.get_running_loop()
            loop_info = {
                "loop_id": id(current_loop),
                "loop_running": current_loop.is_running(),
                "loop_closed": current_loop.is_closed(),
                "thread_id": threading.current_thread().ident,
                "process_id": os.getpid(),
            }
            logger.info(
                "🔍 SSE EVENT EMISSION: Starting SSE event emission with event loop info",
                task_id=task_id,
                status=status.value,
                **loop_info,
            )
        except RuntimeError as e:
            logger.error(
                "🚨 NO EVENT LOOP: No running event loop detected in _emit_sse_event",
                task_id=task_id,
                status=status.value,
                error=str(e),
                thread_id=threading.current_thread().ident,
                process_id=os.getpid(),
            )
            # Don't create a new event loop here, as this is a nested async function
            # and should be called from a context that already has an event loop

        try:
            # 🔍 DIAGNOSTIC: Log import attempt details
            logger.info(
                "🔍 SSE IMPORT DIAGNOSTIC: Attempting to import SSE event functions",
                task_id=task_id,
                module_path="src.api.sse.events",
                required_functions=[
                    "create_task_progress_event",
                    "create_task_completed_event",
                    "create_task_failed_event",
                ],
            )

            # Import here to avoid circular imports
            from src.api.sse.events import (  # type: ignore[attr-defined]
                create_task_progress_event,  # type: ignore[attr-defined]
                create_task_completed_event,  # type: ignore[attr-defined]
                create_task_failed_event,  # type: ignore[attr-defined]
            )

            logger.info(
                "✅ SSE IMPORT SUCCESS: All required SSE event functions imported successfully",
                task_id=task_id,
            )

            # 🚨 ARCHITECTURAL FIX: Publish structured JSON instead of SSE format
            # Create JSON event object that SSE Connection Manager can process
            import json

            if status == TaskStatus.COMPLETED:
                event_json = {
                    "event_type": "render.completed",
                    "task_id": task_id,
                    "connection_id": connection_id,
                    "data": {
                        "task_id": task_id,
                        "result": result or {},
                        "processing_time": result.get("processing_time", 0) if result else 0,
                        "message": message or "Task completed successfully",
                    },
                }
            elif status == TaskStatus.FAILED:
                event_json = {
                    "event_type": "render.failed",
                    "task_id": task_id,
                    "connection_id": connection_id,
                    "data": {
                        "task_id": task_id,
                        "error": message or "Task failed",
                        "details": {},
                        "message": message or "Task failed",
                    },
                }
            else:
                event_json = {
                    "event_type": "render.progress",
                    "task_id": task_id,
                    "connection_id": connection_id,
                    "data": {
                        "task_id": task_id,
                        "progress": progress or 0,
                        "status": status.value,
                        "message": message or "",
                    },
                }

            # Convert to JSON string for Redis publishing
            event_data = json.dumps(event_json)

            # 🔍 ENHANCED DIAGNOSTIC: Log the event data and channel before publishing
            logger.info(
                "🔍 SSE EVENT PUBLISHING: About to publish JSON event to Redis channel",
                task_id=task_id,
                event_type=status.value,
                channel="sse_events",
                event_json_keys=list(event_json.keys()),
                event_data_type=type(event_data).__name__,
                event_data_length=len(event_data),
                connection_id=connection_id,
            )

            # 🔍 DIAGNOSTIC: Log what's actually being published to Redis
            logger.info(
                "🔍 CELERY REDIS PUBLISH DIAGNOSTIC: About to publish JSON to Redis channel",
                task_id=task_id,
                channel="sse_events",
                event_data_type=type(event_data).__name__,
                event_data_length=len(event_data),
                event_data_preview=event_data[:200],
                is_json_format=event_data.strip().startswith("{"),
                is_sse_format=event_data.startswith("event:"),
                event_json_structure=event_json,
            )

            # Publish to the channel that the connection manager is subscribed to
            publish_result = await redis.publish("sse_events", event_data)  # type: ignore
            logger.info(
                "✅ SSE EVENT PUBLISHED: Published JSON event to sse_events channel",
                task_id=task_id,
                channel="sse_events",
                publish_result=publish_result,
                receivers=publish_result,
            )

            # 🔍 ENHANCED DIAGNOSTIC: Log detailed event data for debugging
            logger.info(
                "🔍 SSE EVENT DATA DIAGNOSTIC: Detailed event data being published",
                task_id=task_id,
                channel="sse_events",
                event_type=status.value,
                event_data_preview=(
                    event_data[:100] if isinstance(event_data, str) else "non-string-data"  # type: ignore
                ),
                event_data_length=len(event_data) if isinstance(event_data, str) else "unknown",  # type: ignore
                connection_id=connection_id,
                status=status.value,
                progress=progress,
                message=message,
            )

            # Also publish to the original channels for backward compatibility
            if connection_id:
                # Send to specific connection
                conn_result = await redis.publish(f"sse:connection:{connection_id}", event_data)  # type: ignore
                logger.info(
                    "✅ SSE EVENT PUBLISHED: Published to connection-specific channel",
                    task_id=task_id,
                    channel=f"sse:connection:{connection_id}",
                    publish_result=conn_result,
                    receivers=conn_result,
                )

                # 🔍 ENHANCED DIAGNOSTIC: Log detailed event data for connection-specific channel
                logger.info(
                    "🔍 CONNECTION CHANNEL DIAGNOSTIC: Detailed event data for connection channel",
                    task_id=task_id,
                    channel=f"sse:connection:{connection_id}",
                    event_type=status.value,
                    connection_id=connection_id,
                    receivers=conn_result,
                    event_data_preview=(
                        event_data[:100] if isinstance(event_data, str) else "non-string-data"  # type: ignore
                    ),
                )
            else:
                # Send to all connections monitoring this task
                task_result = await redis.publish(f"sse:task:{task_id}", event_data)  # type: ignore
                logger.info(
                    "✅ SSE EVENT PUBLISHED: Published to task-specific channel",
                    task_id=task_id,
                    channel=f"sse:task:{task_id}",
                    publish_result=task_result,
                    receivers=task_result,
                )

                # 🔍 ENHANCED DIAGNOSTIC: Log detailed event data for task-specific channel
                logger.info(
                    "🔍 TASK CHANNEL DIAGNOSTIC: Detailed event data for task channel",
                    task_id=task_id,
                    channel=f"sse:task:{task_id}",
                    event_type=status.value,
                    receivers=task_result,
                    event_data_preview=(
                        event_data[:100] if isinstance(event_data, str) else "non-string-data"  # type: ignore
                    ),
                )

                # Also send to general task updates channel
                updates_result = await redis.publish("sse:task_updates", event_data)  # type: ignore
                logger.info(
                    "✅ SSE EVENT PUBLISHED: Published to task updates channel",
                    task_id=task_id,
                    channel="sse:task_updates",
                    publish_result=updates_result,
                    receivers=updates_result,
                )

                # 🔍 ENHANCED DIAGNOSTIC: Log detailed event data for task updates channel
                logger.info(
                    "🔍 TASK UPDATES CHANNEL DIAGNOSTIC: Detailed event data for updates channel",
                    task_id=task_id,
                    channel="sse:task_updates",
                    event_type=status.value,
                    receivers=updates_result,
                    event_data_preview=(
                        event_data[:100] if isinstance(event_data, str) else "non-string-data"  # type: ignore
                    ),
                )

        except Exception as e:
            # Don't let SSE event emission failure break task processing
            logger.warning("Failed to emit SSE event", task_id=task_id, error=str(e))

    @staticmethod
    async def get_task_status(task_id: str) -> Optional[Dict[str, Any]]:
        """
        Get task status from Redis.

        Args:
            task_id: Task identifier

        Returns:
            Task status data or None if not found
        """
        # Use Redis client context manager for proper connection handling
        from src.config.database import get_redis_client_context

        try:
            # 🔍 DIAGNOSTIC: Log Redis client context usage
            logger.info(
                "🔍 REDIS CONTEXT MANAGER: About to get Redis client using context manager in get_task_status",
                task_id=task_id,
                redis_key=f"task:{task_id}",
            )

            async with get_redis_client_context() as redis:
                task_data = await redis.hgetall(f"task:{task_id}")  # type: ignore

                logger.info(
                    "🔍 REDIS SUCCESS: Task data retrieved successfully in get_task_status",
                    task_id=task_id,
                    redis_key=f"task:{task_id}",
                    has_data=bool(task_data),
                )

                return task_data if task_data else None  # type: ignore
        except Exception as e:
            logger.error(
                "🚨 ERROR in get_task_status",
                task_id=task_id,
                error_type=type(e).__name__,
                error_message=str(e),
            )
            return None


@celery_app.task(bind=True, name="render_dsl_to_png")  # type: ignore
def render_dsl_to_png_task(self: Any, request_data: Dict[str, Any]) -> Dict[str, Any]:  # type: ignore
    """
    Celery task for rendering DSL to PNG.

    Args:
        request_data: DSL render request data

    Returns:
        Task result data
    """
    # 🔍 TASK DECORATOR DIAGNOSTIC: Log immediately upon task function invocation
    try:
        task_id: str = self.request.id  # type: ignore

        # 🔍 EARLY DIAGNOSTIC: Log task function entry IMMEDIATELY with event loop check
        try:
            current_loop = asyncio.get_running_loop()
            logger.info(
                "🔍 TASK ENTRY: Celery task function started execution WITH event loop",
                task_id=task_id,
                thread_id=threading.current_thread().ident,
                process_id=os.getpid(),
                current_thread_name=threading.current_thread().name,
                main_thread=threading.current_thread() is threading.main_thread(),
                loop_id=id(current_loop),
                loop_running=current_loop.is_running(),
                loop_closed=current_loop.is_closed(),
            )
        except RuntimeError as loop_error:
            logger.error(
                "🚨 TASK ENTRY: Celery task function started WITHOUT event loop",
                task_id=task_id,
                thread_id=threading.current_thread().ident,
                process_id=os.getpid(),
                current_thread_name=threading.current_thread().name,
                main_thread=threading.current_thread() is threading.main_thread(),
                loop_error=str(loop_error),
            )

    except Exception as task_id_error:
        logger.error(
            "🚨 TASK ENTRY CRITICAL: Failed to get task_id from self.request",
            error=str(task_id_error),
            error_type=type(task_id_error).__name__,
            thread_id=threading.current_thread().ident,
            process_id=os.getpid(),
            self_type=type(self).__name__ if self else "None",
            has_request=hasattr(self, "request") if self else False,
        )
        # Set fallback task_id
        task_id = "UNKNOWN_TASK_ID"

    logger.info("Starting DSL to PNG rendering task", task_id=task_id)

    # 🔍 EARLY DIAGNOSTIC: Log request_data structure before parsing
    logger.info(
        "🔍 REQUEST DATA DIAGNOSTIC: About to parse request_data with DSLRenderRequest",
        task_id=task_id,
        request_data_type=type(request_data).__name__,
        request_data_keys=(
            list(request_data.keys()) if isinstance(request_data, dict) else "not_dict"  # type: ignore
        ),
        request_data_size=(
            len(request_data) if isinstance(request_data, (dict, list)) else "unknown"  # type: ignore
        ),
        has_dsl_content="dsl_content" in request_data if isinstance(request_data, dict) else False,  # type: ignore
        has_options="options" in request_data if isinstance(request_data, dict) else False,  # type: ignore
        options_type=(
            type(request_data.get("options")).__name__
            if isinstance(request_data, dict) and "options" in request_data  # type: ignore
            else "missing"
        ),
    )

    # Create a single event loop for the entire task lifecycle
    loop = None
    result_data = None

    try:
        # 🔍 EARLY DIAGNOSTIC: Log before DSLRenderRequest parsing (CRITICAL FAILURE POINT)
        logger.info(
            "🔍 PYDANTIC PARSING: About to parse request_data with DSLRenderRequest (CRITICAL FAILURE POINT)",
            task_id=task_id,
            request_data_preview=str(request_data)[:200] if request_data else "empty",
        )

        # Parse request
        request = DSLRenderRequest(**request_data)

        # 🔍 EARLY DIAGNOSTIC: Log successful DSLRenderRequest parsing
        logger.info(
            "🔍 PYDANTIC SUCCESS: DSLRenderRequest parsing completed successfully",
            task_id=task_id,
            request_type=type(request).__name__,
            has_dsl_content=bool(request.dsl_content),
            dsl_content_length=len(request.dsl_content) if request.dsl_content else 0,
            has_options=request.options is not None,
        )

        # 🔄 FORK-SAFE EVENT LOOP: Always create fresh event loop for Celery fork workers
        logger.info(
            "🔄 FORK-SAFE EVENT LOOP: Creating fresh event loop for fork worker task",
            task_id=task_id,
            thread_id=threading.current_thread().ident,
            process_id=os.getpid(),
            current_thread_name=threading.current_thread().name,
            main_thread=threading.current_thread() is threading.main_thread(),
        )

        # For fork workers, always create a new event loop to avoid isolation issues
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        logger.info(
            "✅ FRESH EVENT LOOP CREATED: New event loop ready for task execution",
            task_id=task_id,
            loop_id=id(loop),
            loop_running=loop.is_running(),
            loop_closed=loop.is_closed(),
        )

        # Run async processing in the fresh event loop
        logger.info(
            "🔄 ASYNC PROCESSING: Running task processing in fresh event loop",
            task_id=task_id,
            loop_id=id(loop),
        )

        # Execute the async task processing
        result = loop.run_until_complete(_process_dsl_render_request(task_id, request))
        result_data = result.model_dump(mode="json")

        logger.info(
            "✅ ASYNC PROCESSING SUCCESS: Task processing completed successfully",
            task_id=task_id,
            loop_id=id(loop),
            loop_running=loop.is_running(),
            loop_closed=loop.is_closed(),
        )

        return result_data

    except Exception as e:
        error_msg = f"Task failed: {str(e)}"

        # 🔍 ENHANCED DIAGNOSTIC: Log detailed error information for task failures
        import traceback

        logger.error(
            "🔍 TASK FAILURE DIAGNOSTIC: Detailed error information",
            task_id=task_id,
            error=error_msg,
            error_type=type(e).__name__,
            error_module=getattr(type(e), "__module__", "unknown"),
            error_repr=repr(e),
            error_args=getattr(e, "args", "no_args"),
            traceback=traceback.format_exc(),
            current_thread=threading.current_thread().name,
            is_main_thread=threading.current_thread() is threading.main_thread(),
        )

        logger.error(
            "DSL to PNG task failed",
            task_id=task_id,
            error=error_msg,
            error_type=type(e).__name__,
            error_module=getattr(type(e), "__module__", "unknown"),
        )

        # Use the same event loop for error handling (it should still be available)
        try:
            logger.info(
                "🔄 ERROR HANDLING: Using current event loop for error status update",
                task_id=task_id,
                loop_id=id(loop) if loop else "none",
                loop_closed=loop.is_closed() if loop else True,
            )

            if loop and not loop.is_closed():
                # Use the existing loop
                loop.run_until_complete(
                    TaskTracker.update_task_status(task_id, TaskStatus.FAILED, message=error_msg)
                )
            else:
                # Create a fresh loop for error handling
                error_loop = asyncio.new_event_loop()
                asyncio.set_event_loop(error_loop)
                try:
                    error_loop.run_until_complete(
                        TaskTracker.update_task_status(
                            task_id, TaskStatus.FAILED, message=error_msg
                        )
                    )
                finally:
                    error_loop.close()
        except Exception as status_error:
            logger.error(
                "Failed to update task status during error handling",
                task_id=task_id,
                error=str(status_error),
                error_type=type(status_error).__name__,
                original_error=error_msg,
            )

        raise
    finally:
        # IMPORTANT: Never close the event loop in a Celery task
        # This allows the event loop to be reused for future operations
        logger.info(
            "🔍 EVENT LOOP PRESERVED: Not closing event loop to prevent 'Event loop is closed' errors",
            task_id=task_id,
            loop_id=id(loop) if loop else "none",
            loop_closed=loop.is_closed() if loop else True,
            is_current_loop=loop is asyncio.get_event_loop() if loop else False,
        )


async def _process_dsl_render_request(task_id: str, request: DSLRenderRequest) -> TaskResult:
    """
    Process DSL render request asynchronously.

    Args:
        task_id: Task identifier
        request: DSL render request

    Returns:
        Task result
    """
    start_time = datetime.now(timezone.utc)

    # 🔍 ENHANCED DIAGNOSTIC: Log task processing start with event loop info
    current_loop = asyncio.get_running_loop()
    logger.info(
        "🔍 TASK PROCESSING: Starting DSL render request processing",
        task_id=task_id,
        request_type=type(request).__name__,
        has_options=request.options is not None,
        dsl_content_length=len(request.dsl_content) if request.dsl_content else 0,
        loop_id=id(current_loop),
        loop_running=current_loop.is_running(),
        loop_closed=current_loop.is_closed(),
        thread_id=threading.current_thread().ident,
        process_id=os.getpid(),
    )

    try:
        # Update status: Started
        await TaskTracker.update_task_status(
            task_id, TaskStatus.PROCESSING, progress=0, message="Starting DSL parsing"
        )

        # 🔍 DIAGNOSTIC: Log event loop status before DSL parsing
        try:
            current_loop = asyncio.get_running_loop()
            logger.info(
                "🔍 PIPELINE STEP 1 - BEFORE DSL PARSING: Event loop status",
                task_id=task_id,
                step="parse_dsl",
                phase="before",
                loop_id=id(current_loop),
                loop_running=current_loop.is_running(),
                loop_closed=current_loop.is_closed(),
                thread_id=threading.current_thread().ident,
                process_id=os.getpid(),
            )
        except RuntimeError as e:
            logger.error(
                "🚨 PIPELINE STEP 1 - NO EVENT LOOP BEFORE DSL PARSING",
                task_id=task_id,
                step="parse_dsl",
                phase="before",
                error=str(e),
            )

        # Step 1: Parse DSL
        logger.info("Parsing DSL content", task_id=task_id, content_length=len(request.dsl_content))
        parse_result = await parse_dsl(request.dsl_content)

        # 🔍 DIAGNOSTIC: Log event loop status after DSL parsing
        try:
            current_loop = asyncio.get_running_loop()
            logger.info(
                "🔍 PIPELINE STEP 1 - AFTER DSL PARSING: Event loop status",
                task_id=task_id,
                step="parse_dsl",
                phase="after",
                loop_id=id(current_loop),
                loop_running=current_loop.is_running(),
                loop_closed=current_loop.is_closed(),
                parse_success=parse_result.success,
            )
        except RuntimeError as e:
            logger.error(
                "🚨 PIPELINE STEP 1 - NO EVENT LOOP AFTER DSL PARSING",
                task_id=task_id,
                step="parse_dsl",
                phase="after",
                error=str(e),
                parse_success=parse_result.success,
            )

        if not parse_result.success:
            error_msg = f"DSL parsing failed: {'; '.join(parse_result.errors)}"
            await TaskTracker.update_task_status(task_id, TaskStatus.FAILED, message=error_msg)
            raise ValueError(error_msg)

        # Ensure we have parsed document and options
        if parse_result.document is None:
            error_msg = "DSL parsing succeeded but no document was produced"
            await TaskTracker.update_task_status(task_id, TaskStatus.FAILED, message=error_msg)
            raise ValueError(error_msg)

        if request.options is None:
            error_msg = "No render options provided"
            await TaskTracker.update_task_status(task_id, TaskStatus.FAILED, message=error_msg)
            raise ValueError(error_msg)

        await TaskTracker.update_task_status(
            task_id,
            TaskStatus.PROCESSING,
            progress=25,
            message="DSL parsed successfully, generating HTML",
        )

        # Step 2: Generate HTML
        logger.info(
            "Generating HTML", task_id=task_id, element_count=len(parse_result.document.elements)
        )
        html_content = await generate_html(parse_result.document, request.options)

        await TaskTracker.update_task_status(
            task_id, TaskStatus.PROCESSING, progress=50, message="HTML generated, creating PNG"
        )

        # 🔍 DIAGNOSTIC: Log event loop status before PNG generation (CRITICAL - Browser automation)
        try:
            current_loop = asyncio.get_running_loop()
            logger.info(
                "🔍 PIPELINE STEP 3 - BEFORE PNG GENERATION: Event loop status (CRITICAL - Browser automation)",
                task_id=task_id,
                step="generate_png",
                phase="before",
                loop_id=id(current_loop),
                loop_running=current_loop.is_running(),
                loop_closed=current_loop.is_closed(),
                thread_id=threading.current_thread().ident,
                process_id=os.getpid(),
                html_content_length=len(html_content),
                width=request.options.width,
                height=request.options.height,
            )
        except RuntimeError as e:
            logger.error(
                "🚨 PIPELINE STEP 3 - NO EVENT LOOP BEFORE PNG GENERATION",
                task_id=task_id,
                step="generate_png",
                phase="before",
                error=str(e),
                thread_id=threading.current_thread().ident,
                process_id=os.getpid(),
            )

        # Step 3: Generate PNG
        logger.info(
            "Generating PNG",
            task_id=task_id,
            width=request.options.width,
            height=request.options.height,
        )

        try:
            png_result = await generate_png_from_html(html_content, request.options)

            # 🔍 DIAGNOSTIC: Log event loop status after PNG generation (CRITICAL - Check if browser automation closed it)
            try:
                current_loop = asyncio.get_running_loop()
                logger.info(
                    "🔍 PIPELINE STEP 3 - AFTER PNG GENERATION: Event loop status (Browser automation completed)",
                    task_id=task_id,
                    step="generate_png",
                    phase="after",
                    loop_id=id(current_loop),
                    loop_running=current_loop.is_running(),
                    loop_closed=current_loop.is_closed(),
                    png_file_size=png_result.file_size if png_result else 0,
                    png_width=png_result.width if png_result else 0,
                    png_height=png_result.height if png_result else 0,
                )
            except RuntimeError as e:
                logger.error(
                    "🚨 PIPELINE STEP 3 - NO EVENT LOOP AFTER PNG GENERATION (LIKELY SOURCE)",
                    task_id=task_id,
                    step="generate_png",
                    phase="after",
                    error=str(e),
                    thread_id=threading.current_thread().ident,
                    process_id=os.getpid(),
                    png_generated=png_result is not None,  # type: ignore
                )

        except Exception as png_error:
            # 🔍 DIAGNOSTIC: Log PNG generation failures with event loop status
            try:
                current_loop = asyncio.get_running_loop()
                logger.error(
                    "🚨 PNG GENERATION FAILED - Event loop still available",
                    task_id=task_id,
                    step="generate_png",
                    phase="error",
                    error_type=type(png_error).__name__,
                    error_message=str(png_error),
                    loop_id=id(current_loop),
                    loop_running=current_loop.is_running(),
                    loop_closed=current_loop.is_closed(),
                )
            except RuntimeError as loop_error:
                logger.error(
                    "🚨 PNG GENERATION FAILED - NO EVENT LOOP (CONFIRMED SOURCE)",
                    task_id=task_id,
                    step="generate_png",
                    phase="error",
                    png_error_type=type(png_error).__name__,
                    png_error_message=str(png_error),
                    loop_error=str(loop_error),
                    thread_id=threading.current_thread().ident,
                    process_id=os.getpid(),
                )
            raise

        await TaskTracker.update_task_status(
            task_id, TaskStatus.PROCESSING, progress=75, message="PNG generated, storing file"
        )

        # 🔍 DIAGNOSTIC: Log event loop status before storage operations
        try:
            current_loop = asyncio.get_running_loop()
            logger.info(
                "🔍 PIPELINE STEP 4 - BEFORE STORAGE: Event loop status",
                task_id=task_id,
                step="store_png",
                phase="before",
                loop_id=id(current_loop),
                loop_running=current_loop.is_running(),
                loop_closed=current_loop.is_closed(),
                png_file_size=png_result.file_size,
            )
        except RuntimeError as e:
            logger.error(
                "🚨 PIPELINE STEP 4 - NO EVENT LOOP BEFORE STORAGE",
                task_id=task_id,
                step="store_png",
                phase="before",
                error=str(e),
            )

        # Step 4: Store PNG file
        from src.core.storage.manager import get_storage_manager

        storage_manager = await get_storage_manager()
        content_hash = await storage_manager.store_png(png_result, task_id)

        # 🔍 DIAGNOSTIC: Log event loop status after storage operations
        try:
            current_loop = asyncio.get_running_loop()
            logger.info(
                "🔍 PIPELINE STEP 4 - AFTER STORAGE: Event loop status",
                task_id=task_id,
                step="store_png",
                phase="after",
                loop_id=id(current_loop),
                loop_running=current_loop.is_running(),
                loop_closed=current_loop.is_closed(),
                content_hash=content_hash,
            )
        except RuntimeError as e:
            logger.error(
                "🚨 PIPELINE STEP 4 - NO EVENT LOOP AFTER STORAGE",
                task_id=task_id,
                step="store_png",
                phase="after",
                error=str(e),
                content_hash=content_hash,
            )

        await TaskTracker.update_task_status(
            task_id, TaskStatus.PROCESSING, progress=90, message="File stored, finalizing result"
        )

        # Step 5: Prepare final result
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()

        # Add storage information to PNG result metadata
        png_result.metadata.update(
            {
                "content_hash": content_hash,
                "storage_tier": "hot",
                "task_id": task_id,
                "processing_time": processing_time,
            }
        )

        task_result = TaskResult(
            task_id=task_id,
            status=TaskStatus.COMPLETED,
            png_result=png_result,
            error=None,
            processing_time=processing_time,
            created_at=start_time,
            completed_at=datetime.now(timezone.utc),
        )

        # 🔍 DIAGNOSTIC: Log task result before final status update
        logger.info(
            "🔍 TASK RESULT: Task completed successfully, about to update final status",
            task_id=task_id,
            result_type=type(task_result).__name__,
            processing_time=processing_time,
        )

        # Update final status
        try:
            # 🔍 DIAGNOSTIC: Test TaskResult serialization before status update
            logger.info(
                "🔍 FINAL COMPLETION: About to serialize TaskResult for final status update",
                task_id=task_id,
                task_result_type=type(task_result).__name__,
                png_result_type=(
                    type(task_result.png_result).__name__ if task_result.png_result else "None"
                ),
                has_metadata=bool(
                    task_result.png_result.metadata if task_result.png_result else False
                ),
            )

            # 🚨 FIX: Properly serialize complex objects to JSON-compatible format
            import json

            try:
                # First convert to JSON-compatible dict
                raw_result = task_result.model_dump(mode="json")
                # Then serialize to JSON string and parse back to ensure full serialization
                json_string = json.dumps(raw_result)
                serialized_result = json.loads(json_string)

                logger.info(
                    "✅ SERIALIZATION SUCCESS: TaskResult fully serialized to JSON-compatible format",
                    task_id=task_id,
                    serialized_keys=(
                        list(serialized_result.keys())
                        if isinstance(serialized_result, dict)
                        else "not_dict"
                    ),
                    serialized_size=len(str(serialized_result)),
                    json_string_length=len(json_string),
                )
            except Exception as serialization_error:
                logger.error(
                    "🚨 SERIALIZATION FAILURE: TaskResult JSON serialization failed",
                    task_id=task_id,
                    error_type=type(serialization_error).__name__,
                    error_message=str(serialization_error),
                    error_repr=repr(serialization_error),
                )
                # Create a fallback serializable result
                serialized_result = {
                    "task_id": task_id,
                    "status": "completed",
                    "processing_time": task_result.processing_time,
                    "png_file_size": (
                        task_result.png_result.file_size if task_result.png_result else 0
                    ),
                    "error": None,
                    "completed_at": (
                        task_result.completed_at.isoformat() if task_result.completed_at else None
                    ),
                    "created_at": (
                        task_result.created_at.isoformat() if task_result.created_at else None
                    ),
                }
                logger.info(
                    "🔧 FALLBACK SERIALIZATION: Using simplified result structure",
                    task_id=task_id,
                    fallback_keys=list(serialized_result.keys()),
                )

            await TaskTracker.update_task_status(
                task_id,
                TaskStatus.COMPLETED,
                progress=100,
                message="Task completed successfully",
                result=serialized_result,
            )
        except Exception as status_error:
            # Don't let status update failure prevent returning the result
            logger.error(
                "🚨 FINAL STATUS UPDATE FAILED: Critical error in final status update",
                task_id=task_id,
                error_type=type(status_error).__name__,
                error_message=str(status_error),
                error_repr=repr(status_error),
            )

        logger.info(
            "DSL to PNG task completed successfully",
            task_id=task_id,
            file_size=png_result.file_size,
            content_hash=content_hash,
            processing_time=processing_time,
        )

        return task_result

    except Exception as e:
        processing_time = (datetime.now(timezone.utc) - start_time).total_seconds()
        error_msg = f"Task failed after {processing_time:.2f}s: {str(e)}"

        # 🔍 DIAGNOSTIC: Log exception details
        logger.error(
            "🔍 TASK EXCEPTION: Exception during task processing",
            task_id=task_id,
            error_type=type(e).__name__,
            error_message=str(e),
            processing_time=processing_time,
        )

        try:
            await TaskTracker.update_task_status(task_id, TaskStatus.FAILED, message=error_msg)
        except Exception as status_error:
            # Don't let status update failure prevent raising the original error
            logger.error(
                "Failed to update error task status",
                task_id=task_id,
                original_error=str(e),
                status_error=str(status_error),
            )

        logger.error(
            "DSL to PNG task failed", task_id=task_id, error=str(e), processing_time=processing_time
        )
        raise


@celery_app.task(name="cleanup_expired_tasks")  # type: ignore[misc]
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
    # Use Redis client context manager for proper connection handling
    from src.config.database import get_redis_client_context

    async with get_redis_client_context() as redis:  # type: ignore
        # TODO: Implement cleanup logic
        # This is a stub for the actual cleanup implementation
        return {"cleaned_tasks": 0, "status": "completed"}


# Task signal handlers
@task_prerun.connect  # type: ignore[misc]
def task_prerun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, **kwds):  # type: ignore[misc]
    """Handle task prerun signal."""
    # 🔍 SIGNAL DIAGNOSTIC: Log event loop status in task_prerun
    try:
        current_loop = asyncio.get_running_loop()
        logger.info(
            "🔍 TASK_PRERUN SIGNAL: Event loop available in prerun handler",
            task_id=task_id,
            task_name=getattr(task, "name", "unknown") if task else "unknown",
            loop_id=id(current_loop),
            loop_running=current_loop.is_running(),
            loop_closed=current_loop.is_closed(),
            thread_id=threading.current_thread().ident,
            process_id=os.getpid(),
        )
    except RuntimeError as e:
        logger.error(
            "🚨 TASK_PRERUN SIGNAL: No event loop in prerun handler",
            task_id=task_id,
            task_name=getattr(task, "name", "unknown") if task else "unknown",
            error=str(e),
            thread_id=threading.current_thread().ident,
            process_id=os.getpid(),
        )
        # Create event loop if needed for this worker
        try:
            new_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(new_loop)
            logger.info(
                "✅ TASK_PRERUN SIGNAL: Created new event loop in prerun handler",
                task_id=task_id,
                loop_id=id(new_loop),
                thread_id=threading.current_thread().ident,
                process_id=os.getpid(),
            )
        except Exception as loop_error:
            logger.error(
                "🚨 TASK_PRERUN SIGNAL: Failed to create event loop in prerun handler",
                task_id=task_id,
                error=str(loop_error),
                error_type=type(loop_error).__name__,
            )

    logger.info("Task starting", task_id=task_id, task_name=getattr(task, "name", "unknown") if task else "unknown")  # type: ignore[misc]


@task_postrun.connect  # type: ignore[misc]
def task_postrun_handler(  # type: ignore[misc]
    sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds  # type: ignore[misc]
):  # type: ignore[misc]
    """Handle task postrun signal."""
    # 🔍 SIGNAL DIAGNOSTIC: Log event loop status in task_postrun
    try:
        current_loop = asyncio.get_running_loop()
        logger.info(
            "🔍 TASK_POSTRUN SIGNAL: Event loop available in postrun handler",
            task_id=task_id,
            task_name=getattr(task, "name", "unknown") if task else "unknown",
            state=state,
            loop_id=id(current_loop),
            loop_running=current_loop.is_running(),
            loop_closed=current_loop.is_closed(),
        )
    except RuntimeError as e:
        logger.error(
            "🚨 TASK_POSTRUN SIGNAL: No event loop in postrun handler",
            task_id=task_id,
            task_name=getattr(task, "name", "unknown") if task else "unknown",
            state=state,
            error=str(e),
        )

    logger.info("Task completed", task_id=task_id, task_name=getattr(task, "name", "unknown") if task else "unknown", state=state)  # type: ignore[misc]


@task_failure.connect  # type: ignore[misc]
def task_failure_handler(  # type: ignore[misc]
    sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds  # type: ignore[misc]
):  # type: ignore[misc]
    """Handle task failure signal."""
    # 🔍 SIGNAL DIAGNOSTIC: Log event loop status in task_failure
    try:
        current_loop = asyncio.get_running_loop()
        logger.error(
            "🔍 TASK_FAILURE SIGNAL: Event loop available in failure handler",
            task_id=task_id,
            exception=str(exception) if exception else "unknown",
            loop_id=id(current_loop),
            loop_running=current_loop.is_running(),
            loop_closed=current_loop.is_closed(),
        )
    except RuntimeError as e:
        logger.error(
            "🚨 TASK_FAILURE SIGNAL: No event loop in failure handler",
            task_id=task_id,
            exception=str(exception) if exception else "unknown",
            signal_error=str(e),
        )

    logger.error("Task failed", task_id=task_id, exception=str(exception) if exception else "unknown")  # type: ignore[misc]


@worker_ready.connect  # type: ignore[misc]
def worker_ready_handler(sender=None, **kwargs):  # type: ignore[misc]
    """Handle worker ready signal - fires once per worker node."""
    logger.info(
        "🟡 WORKER_READY signal triggered - This fires once per worker node",
        sender=str(sender) if sender else "None",
        kwargs=kwargs,
    )
    try:
        # Import here to avoid circular imports
        from src.config.database import initialize_databases

        # Initialize database connections synchronously in worker process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(initialize_databases())
            logger.info(
                "✅ WORKER_READY: Celery worker database connections initialized successfully"
            )
        finally:
            loop.close()
    except Exception as e:
        logger.error(
            "🚨 WORKER_READY CRITICAL: Failed to initialize database connections",
            error=str(e),
            error_type=type(e).__name__,
        )


@worker_process_init.connect  # type: ignore[misc]
def worker_process_init_handler(sender=None, **kwargs):  # type: ignore[misc]
    """Handle worker process init signal - fires once per worker process."""
    import os

    logger.info(
        "🟢 WORKER_PROCESS_INIT signal triggered - This fires once per worker process",
        sender=str(sender) if sender else "None",
        process_id=os.getpid(),
        kwargs=kwargs,
    )
    try:
        # Import here to avoid circular imports
        from src.config.database import initialize_databases

        # Initialize database connections synchronously in worker process
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(initialize_databases())
            logger.info(
                "✅ WORKER_PROCESS_INIT: Database connections initialized successfully",
                process_id=os.getpid(),
            )
        finally:
            loop.close()
    except Exception as e:
        logger.error(
            "🚨 WORKER_PROCESS_INIT CRITICAL: Failed to initialize database connections",
            error=str(e),
            error_type=type(e).__name__,
            process_id=os.getpid(),
        )
        # Don't raise - let worker start but log the critical error


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
    result = render_dsl_to_png_task.apply_async(args=[request.model_dump(mode="json")], task_id=task_id)  # type: ignore[attr-defined]

    # Initialize task status
    await TaskTracker.update_task_status(
        task_id, TaskStatus.PENDING, message="Task queued for processing"
    )

    logger.info("DSL render task submitted", task_id=task_id)
    return task_id


async def submit_render_task_with_sse(request: DSLRenderRequest, connection_id: str) -> str:
    """
    Submit a DSL to PNG rendering task with SSE connection tracking.

    Args:
        request: DSL render request
        connection_id: SSE connection ID for targeted events

    Returns:
        Task ID
    """
    task_id = str(uuid.uuid4())

    # DIAGNOSTIC: Log request data before serialization
    request_dict = request.model_dump(mode="json")
    logger.info(
        "🔍 DIAGNOSTIC: About to submit task with request data",
        task_id=task_id,
        request_keys=list(request_dict.keys()),
        options_keys=(
            list(request_dict.get("options", {}).keys()) if request_dict.get("options") else None
        ),
        options_none_values=[k for k, v in request_dict.get("options", {}).items() if v is None],
    )

    # 🚨 FIX: Filter None values before Celery submission to prevent Redis DataError
    filtered_request_dict = _filter_none_values(request_dict)

    # DIAGNOSTIC: Log filtering results
    logger.info(
        "🔍 DEFENSIVE FILTERING: Applied None value filtering before Celery submission",
        task_id=task_id,
        original_options_none_count=(
            len([k for k, v in request_dict.get("options", {}).items() if v is None])
            if request_dict.get("options")
            else 0
        ),
        filtered_options_none_count=(
            len([k for k, v in filtered_request_dict.get("options", {}).items() if v is None])
            if filtered_request_dict.get("options")
            else 0
        ),
        original_structure=_inspect_dict_structure(request_dict, max_depth=2),
        filtered_structure=_inspect_dict_structure(filtered_request_dict, max_depth=2),
    )

    # Submit to Celery with enhanced error handling using filtered data
    try:
        result = render_dsl_to_png_task.apply_async(args=[filtered_request_dict], task_id=task_id)  # type: ignore[attr-defined]
    except Exception as serialization_error:
        logger.error(
            "🔥 JSON SERIALIZATION ERROR: Failed to submit task to Celery",
            task_id=task_id,
            error_type=type(serialization_error).__name__,
            error_message=str(serialization_error),
            request_dict_structure=_inspect_dict_structure(request_dict),
            connection_id=connection_id,
        )
        raise

    # Initialize task status with connection tracking
    await TaskTracker.update_task_status(
        task_id,
        TaskStatus.PENDING,
        message="Task queued for processing",
        connection_id=connection_id,
    )

    logger.info("DSL render task with SSE submitted", task_id=task_id, connection_id=connection_id)
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
    celery_result = AsyncResult(task_id, app=celery_app)  # type: ignore[misc]
    if celery_result.ready():  # type: ignore[attr-defined]
        try:
            result_data = celery_result.get()  # type: ignore[attr-defined]
            return TaskResult(**result_data)  # type: ignore[misc]
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
        celery_app.control.revoke(task_id, terminate=True)  # type: ignore[attr-defined]

        await TaskTracker.update_task_status(
            task_id, TaskStatus.CANCELLED, message="Task cancelled by user"
        )

        logger.info("Task cancelled", task_id=task_id)
        return True

    except Exception as e:
        logger.error("Failed to cancel task", task_id=task_id, error=str(e))
        return False


# 🔍 DIAGNOSTIC: Log signal handler registration after all handlers are defined
logger.info(
    "📦 CELERY TASKS MODULE LOADED - Signal handlers registered",
    module_name=__name__,
    celery_app_name=celery_app.main,
    signal_handlers_registered=True,
)
