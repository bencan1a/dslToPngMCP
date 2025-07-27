"""
SSE Models
==========

Pydantic models for Server-Sent Events infrastructure.
Defines data structures for SSE connections, events, and tool requests.
"""

from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
from pydantic import BaseModel, Field, field_validator, ConfigDict

from src.models.schemas import RenderOptions


class SSEConnectionStatus(str, Enum):
    """SSE connection status."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"


class SSEConnectionMetadata(BaseModel):
    """Metadata for SSE connection."""

    connection_id: str = Field(..., description="Unique connection identifier")
    client_ip: str = Field(..., description="Client IP address")
    user_agent: Optional[str] = Field(None, description="Client user agent")
    api_key_hash: Optional[str] = Field(None, description="Hash of API key for tracking")
    status: SSEConnectionStatus = Field(
        default=SSEConnectionStatus.CONNECTING, description="Connection status"
    )
    connected_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Connection timestamp"
    )
    last_heartbeat: Optional[datetime] = Field(None, description="Last heartbeat timestamp")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    model_config = ConfigDict(use_enum_values=True)


class SSEEventPayload(BaseModel):
    """Payload for SSE events."""

    event_type: str = Field(..., description="Event type identifier")
    connection_id: str = Field(..., description="Target connection ID")
    data: Dict[str, Any] = Field(default_factory=dict, description="Event data")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Event timestamp"
    )
    retry_after: Optional[int] = Field(None, description="Client retry interval in milliseconds")

    model_config = ConfigDict(use_enum_values=True)


class SSEToolRequest(BaseModel):
    """Request model for MCP tool execution via SSE."""

    tool_name: str = Field(..., description="MCP tool name to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Tool arguments")
    connection_id: str = Field(..., description="SSE connection ID for progress updates")
    request_id: Optional[str] = Field(None, description="Optional request ID for tracking")
    timeout: int = Field(default=300, description="Tool execution timeout in seconds")

    @field_validator("tool_name")
    @classmethod
    def validate_tool_name(cls, v: str) -> str:
        """Validate tool name."""
        allowed_tools = ["render_ui_mockup", "validate_dsl", "get_render_status"]
        if v not in allowed_tools:
            raise ValueError(f"Tool '{v}' not supported. Allowed tools: {allowed_tools}")
        return v

    @field_validator("timeout")
    @classmethod
    def validate_timeout(cls, v: int) -> int:
        """Validate timeout range."""
        if v < 10 or v > 600:
            raise ValueError("Timeout must be between 10 and 600 seconds")
        return v


class SSEToolResponse(BaseModel):
    """Response model for MCP tool execution via SSE."""

    success: bool = Field(..., description="Whether tool execution succeeded")
    tool_name: str = Field(..., description="MCP tool name that was executed")
    request_id: Optional[str] = Field(None, description="Request ID if provided")
    result: Optional[Dict[str, Any]] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")
    execution_time: float = Field(..., description="Tool execution time in seconds")
    events_sent: int = Field(default=0, description="Number of progress events sent")


class SSEProgressUpdate(BaseModel):
    """Progress update for long-running operations."""

    operation: str = Field(..., description="Operation being performed")
    progress: int = Field(..., ge=0, le=100, description="Progress percentage (0-100)")
    message: str = Field(..., description="Progress message")
    stage: Optional[str] = Field(None, description="Current processing stage")
    estimated_remaining: Optional[float] = Field(None, description="Estimated remaining seconds")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional details")


class SSEHeartbeat(BaseModel):
    """Heartbeat message to keep SSE connections alive."""

    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Heartbeat timestamp"
    )
    server_time: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(), description="Server time"
    )
    connection_age: Optional[float] = Field(None, description="Connection age in seconds")

    model_config = ConfigDict()


class SSEError(BaseModel):
    """Error event for SSE connections."""

    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    recoverable: bool = Field(True, description="Whether the error is recoverable")
    suggested_action: Optional[str] = Field(None, description="Suggested action for client")


class SSEConnectionStats(BaseModel):
    """Statistics for SSE connections."""

    total_connections: int = Field(default=0, description="Total active connections")
    connections_by_status: Dict[str, int] = Field(
        default_factory=dict, description="Connections by status"
    )
    average_connection_age: Optional[float] = Field(
        None, description="Average connection age in seconds"
    )
    total_events_sent: int = Field(
        default=0, description="Total events sent across all connections"
    )
    events_per_second: float = Field(default=0.0, description="Current events per second rate")
    memory_usage: Optional[float] = Field(None, description="Memory usage for SSE infrastructure")
    last_updated: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc), description="Last stats update"
    )

    model_config = ConfigDict()


class SSERenderRequest(BaseModel):
    """Specialized render request for SSE."""

    dsl_content: str = Field(..., description="DSL content to render")
    options: Optional[RenderOptions] = Field(None, description="Render options")
    connection_id: str = Field(..., description="SSE connection ID")
    request_id: Optional[str] = Field(None, description="Optional request ID")
    progress_updates: bool = Field(True, description="Send progress updates via SSE")

    model_config = ConfigDict(
        validate_assignment=False, arbitrary_types_allowed=True, use_enum_values=True
    )

    # @validator('dsl_content')  # DISABLED FOR DEBUGGING
    # def validate_dsl_content(cls, v):
    #     """Validate DSL content is not empty."""
    #     if not v.strip():
    #         raise ValueError("DSL content cannot be empty")
    #     return v


class SSEValidationRequest(BaseModel):
    """Specialized validation request for SSE."""

    dsl_content: str = Field(..., min_length=1, description="DSL content to validate")
    connection_id: str = Field(..., description="SSE connection ID")
    request_id: Optional[str] = Field(None, description="Optional request ID")
    strict: bool = Field(False, description="Enable strict validation")

    @field_validator("dsl_content")
    @classmethod
    def validate_dsl_content(cls, v: str) -> str:
        """Validate DSL content is not empty."""
        if not v.strip():
            raise ValueError("DSL content cannot be empty")
        return v


class SSEStatusRequest(BaseModel):
    """Specialized status check request for SSE."""

    task_id: str = Field(..., description="Task ID to check status")
    connection_id: str = Field(..., description="SSE connection ID")
    request_id: Optional[str] = Field(None, description="Optional request ID")
    include_result: bool = Field(True, description="Include result if task is completed")
