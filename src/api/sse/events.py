"""
SSE Events
==========

Server-Sent Events type definitions and formatting functions.
Defines event types and handles SSE protocol formatting.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from enum import Enum
import json
import uuid

from .models import SSEEventPayload, SSEProgressUpdate, SSEHeartbeat, SSEError


class SSEEventType(str, Enum):
    """Server-Sent Events event types."""

    # Connection events
    CONNECTION_OPENED = "connection.opened"
    CONNECTION_HEARTBEAT = "connection.heartbeat"
    CONNECTION_ERROR = "connection.error"
    CONNECTION_CLOSED = "connection.closed"

    # MCP tool events
    MCP_TOOL_CALL = "mcp.tool.call"
    MCP_TOOL_RESPONSE = "mcp.tool.response"
    MCP_TOOL_ERROR = "mcp.tool.error"
    MCP_TOOL_PROGRESS = "mcp.tool.progress"

    # Rendering events
    RENDER_STARTED = "render.started"
    RENDER_PROGRESS = "render.progress"
    RENDER_COMPLETED = "render.completed"
    RENDER_FAILED = "render.failed"

    # Validation events
    VALIDATION_STARTED = "validation.started"
    VALIDATION_COMPLETED = "validation.completed"
    VALIDATION_FAILED = "validation.failed"

    # Status events
    STATUS_UPDATE = "status.update"

    # System events
    SERVER_ERROR = "server.error"
    RATE_LIMIT_WARNING = "rate_limit.warning"
    RATE_LIMIT_EXCEEDED = "rate_limit.exceeded"


class SSEEvent:
    """SSE event with proper formatting."""

    def __init__(
        self,
        event_type: SSEEventType,
        data: Dict[str, Any],
        connection_id: str,
        event_id: Optional[str] = None,
        retry_after: Optional[int] = None,
    ):
        self.event_type = event_type
        self.data = data
        self.connection_id = connection_id
        self.event_id = event_id or str(uuid.uuid4())
        self.retry_after = retry_after
        self.timestamp = datetime.now(timezone.utc)

    def to_payload(self) -> SSEEventPayload:
        """Convert to SSEEventPayload model."""
        return SSEEventPayload(
            event_type=self.event_type.value,
            connection_id=self.connection_id,
            data=self.data,
            timestamp=self.timestamp,
            retry_after=self.retry_after,
        )

    def format_sse(self) -> str:
        """Format event for SSE protocol."""
        # Ensure data is JSON serializable by handling datetime objects
        serializable_data = self._make_data_serializable(self.data)

        return format_sse_event(
            event_type=self.event_type.value,
            data=serializable_data,
            event_id=self.event_id,
            retry_after=self.retry_after,
        )

    def _make_data_serializable(self, data: Any) -> Any:
        """Convert data to JSON-serializable format."""
        if hasattr(data, "model_dump"):
            return data.model_dump()
        elif isinstance(data, datetime):
            return data.isoformat()
        elif isinstance(data, dict):
            return {str(k): self._make_data_serializable(v) for k, v in data.items()}  # type: ignore[misc]
        elif isinstance(data, (list, tuple)):
            return [self._make_data_serializable(item) for item in data]  # type: ignore[misc]
        else:
            return data


def format_sse_event(
    event_type: str,
    data: Dict[str, Any],
    event_id: Optional[str] = None,
    retry_after: Optional[int] = None,
) -> str:
    """
    Format data for Server-Sent Events protocol.

    Args:
        event_type: Event type identifier
        data: Event data dictionary
        event_id: Optional event ID for client-side event tracking
        retry_after: Optional retry interval in milliseconds

    Returns:
        Formatted SSE message string
    """
    lines: List[str] = []

    # Add event ID if provided
    if event_id:
        lines.append(f"id: {event_id}")

    # Add event type
    lines.append(f"event: {event_type}")

    # Add retry interval if provided
    if retry_after:
        lines.append(f"retry: {retry_after}")

    # Add data (JSON formatted)
    data_json = json.dumps(data, default=str, separators=(",", ":"))
    lines.append(f"data: {data_json}")

    # SSE protocol requires double newline at end
    lines.append("")
    lines.append("")

    return "\n".join(lines)


def create_connection_opened_event(connection_id: str, metadata: Dict[str, Any]) -> SSEEvent:
    """Create connection opened event."""
    return SSEEvent(
        event_type=SSEEventType.CONNECTION_OPENED,
        data={
            "message": "SSE connection established",
            "connection_id": connection_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata,
        },
        connection_id=connection_id,
    )


def create_connection_closed_event(connection_id: str, reason: str = "closed") -> SSEEvent:
    """Create connection closed event."""
    return SSEEvent(
        event_type=SSEEventType.CONNECTION_CLOSED,
        data={
            "message": "SSE connection closed",
            "connection_id": connection_id,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        connection_id=connection_id,
    )


def create_heartbeat_event(connection_id: str, connection_age: Optional[float] = None) -> SSEEvent:
    """Create heartbeat event to keep connection alive."""
    heartbeat = SSEHeartbeat(connection_age=connection_age)

    # Quick fix: Manually serialize datetime fields to ISO format
    heartbeat_dict = heartbeat.model_dump()
    if "timestamp" in heartbeat_dict and isinstance(heartbeat_dict["timestamp"], datetime):
        heartbeat_dict["timestamp"] = heartbeat_dict["timestamp"].isoformat()

    return SSEEvent(
        event_type=SSEEventType.CONNECTION_HEARTBEAT,
        data=heartbeat_dict,
        connection_id=connection_id,
        retry_after=30000,  # 30 seconds
    )


def create_progress_event(
    connection_id: str,
    operation: str,
    progress: int,
    message: str,
    stage: Optional[str] = None,
    estimated_remaining: Optional[float] = None,
    details: Optional[Dict[str, Any]] = None,
) -> SSEEvent:
    """Create progress update event."""
    progress_update = SSEProgressUpdate(
        operation=operation,
        progress=progress,
        message=message,
        stage=stage,
        estimated_remaining=estimated_remaining,
        details=details or {},
    )
    return SSEEvent(
        event_type=SSEEventType.RENDER_PROGRESS,
        data=progress_update.model_dump(),
        connection_id=connection_id,
    )


def create_tool_call_event(
    connection_id: str, tool_name: str, arguments: Dict[str, Any], request_id: Optional[str] = None
) -> SSEEvent:
    """Create MCP tool call event."""
    return SSEEvent(
        event_type=SSEEventType.MCP_TOOL_CALL,
        data={
            "tool_name": tool_name,
            "arguments": arguments,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "started",
        },
        connection_id=connection_id,
    )


def create_tool_response_event(
    connection_id: str,
    tool_name: str,
    success: bool,
    result: Optional[Dict[str, Any]] = None,
    error: Optional[str] = None,
    execution_time: Optional[float] = None,
    request_id: Optional[str] = None,
) -> SSEEvent:
    """Create MCP tool response event."""
    return SSEEvent(
        event_type=SSEEventType.MCP_TOOL_RESPONSE,
        data={
            "tool_name": tool_name,
            "success": success,
            "result": result,
            "error": error,
            "execution_time": execution_time,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        connection_id=connection_id,
    )


def create_render_started_event(
    connection_id: str,
    request_id: Optional[str] = None,
    render_options: Optional[Dict[str, Any]] = None,
) -> SSEEvent:
    """Create render started event."""
    return SSEEvent(
        event_type=SSEEventType.RENDER_STARTED,
        data={
            "message": "DSL rendering started",
            "request_id": request_id,
            "render_options": render_options,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        connection_id=connection_id,
    )


def create_render_completed_event(
    connection_id: str,
    result: Dict[str, Any],
    processing_time: float,
    request_id: Optional[str] = None,
) -> SSEEvent:
    """Create render completed event."""
    return SSEEvent(
        event_type=SSEEventType.RENDER_COMPLETED,
        data={
            "message": "DSL rendering completed successfully",
            "result": result,
            "processing_time": processing_time,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        connection_id=connection_id,
    )


def create_render_failed_event(
    connection_id: str,
    error: str,
    error_code: Optional[str] = None,
    processing_time: Optional[float] = None,
    request_id: Optional[str] = None,
) -> SSEEvent:
    """Create render failed event."""
    return SSEEvent(
        event_type=SSEEventType.RENDER_FAILED,
        data={
            "message": "DSL rendering failed",
            "error": error,
            "error_code": error_code,
            "processing_time": processing_time,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        connection_id=connection_id,
    )


def create_validation_completed_event(
    connection_id: str,
    valid: bool,
    errors: List[str],
    warnings: List[str],
    suggestions: List[str],
    request_id: Optional[str] = None,
) -> SSEEvent:
    """Create validation completed event."""
    return SSEEvent(
        event_type=SSEEventType.VALIDATION_COMPLETED,
        data={
            "message": "DSL validation completed",
            "valid": valid,
            "errors": errors,
            "warnings": warnings,
            "suggestions": suggestions,
            "request_id": request_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        connection_id=connection_id,
    )


def create_error_event(
    connection_id: str,
    error_code: str,
    error_message: str,
    details: Optional[Dict[str, Any]] = None,
    recoverable: bool = True,
    suggested_action: Optional[str] = None,
) -> SSEEvent:
    """Create error event."""
    error = SSEError(
        error_code=error_code,
        error_message=error_message,
        details=details,
        recoverable=recoverable,
        suggested_action=suggested_action,
    )
    return SSEEvent(
        event_type=SSEEventType.CONNECTION_ERROR,
        data=error.model_dump(),
        connection_id=connection_id,
    )


def create_rate_limit_warning_event(
    connection_id: str, current_rate: int, limit: int, reset_time: datetime
) -> SSEEvent:
    """Create rate limit warning event."""
    return SSEEvent(
        event_type=SSEEventType.RATE_LIMIT_WARNING,
        data={
            "message": "Approaching rate limit",
            "current_rate": current_rate,
            "limit": limit,
            "reset_time": reset_time.isoformat(),
            "suggestion": "Please slow down your request rate",
        },
        connection_id=connection_id,
    )


def create_rate_limit_exceeded_event(
    connection_id: str, limit: int, reset_time: datetime
) -> SSEEvent:
    """Create rate limit exceeded event."""
    return SSEEvent(
        event_type=SSEEventType.RATE_LIMIT_EXCEEDED,
        data={
            "message": "Rate limit exceeded",
            "limit": limit,
            "reset_time": reset_time.isoformat(),
            "action": "blocking_requests_until_reset",
        },
        connection_id=connection_id,
        retry_after=int((reset_time - datetime.now(timezone.utc)).total_seconds() * 1000),
    )


# Task-specific SSE events
def create_task_progress_event(
    task_id: str,
    progress: int,
    status: str,
    message: str,
    details: Optional[Dict[str, Any]] = None,
    connection_id: Optional[str] = None,
) -> str:
    """
    Create task progress event.

    Args:
        task_id: Task identifier
        progress: Progress percentage (0-100)
        status: Task status string
        message: Status message
        details: Additional details
        connection_id: Optional connection ID

    Returns:
        Formatted SSE event string
    """
    conn_id = connection_id or f"task_{task_id}"

    event = SSEEvent(
        event_type=SSEEventType.RENDER_PROGRESS,
        data={
            "task_id": task_id,
            "progress": progress,
            "status": status,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        connection_id=conn_id,
    )

    return event.format_sse()


def create_task_completed_event(
    task_id: str,
    result: Dict[str, Any],
    processing_time: float,
    connection_id: Optional[str] = None,
) -> str:
    """
    Create task completed event.

    Args:
        task_id: Task identifier
        result: Task result data
        processing_time: Processing time in seconds
        connection_id: Optional connection ID

    Returns:
        Formatted SSE event string
    """
    conn_id = connection_id or f"task_{task_id}"

    event = SSEEvent(
        event_type=SSEEventType.RENDER_COMPLETED,
        data={
            "task_id": task_id,
            "result": result,
            "processing_time": processing_time,
            "message": "Task completed successfully",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        connection_id=conn_id,
    )

    return event.format_sse()


def create_task_failed_event(
    task_id: str,
    error: str,
    details: Dict[str, Any],
    connection_id: Optional[str] = None,
) -> str:
    """
    Create task failed event.

    Args:
        task_id: Task identifier
        error: Error message
        details: Error details
        connection_id: Optional connection ID

    Returns:
        Formatted SSE event string
    """
    conn_id = connection_id or f"task_{task_id}"

    event = SSEEvent(
        event_type=SSEEventType.RENDER_FAILED,
        data={
            "task_id": task_id,
            "error": error,
            "details": details,
            "message": f"Task failed: {error}",
            "timestamp": datetime.now(timezone.utc).isoformat(),
        },
        connection_id=conn_id,
    )

    return event.format_sse()
