"""
Server-Sent Events (SSE) Infrastructure
======================================

SSE implementation for real-time communication with web clients.
Provides streaming events for MCP tool execution progress and results.

Components:
- Connection Manager: Handles SSE client connections and lifecycle
- Event System: Defines event types and formatting for SSE protocol
- MCP Bridge: Bridges HTTP requests to MCP protocol over SSE
- Models: Pydantic models for SSE-specific data structures
"""

from .connection_manager import SSEConnectionManager
from .events import SSEEventType, SSEEvent, format_sse_event
from .models import SSEConnectionMetadata, SSEEventPayload, SSEToolRequest
from .mcp_bridge import MCPBridge

__all__ = [
    "SSEConnectionManager",
    "SSEEventType", 
    "SSEEvent",
    "format_sse_event",
    "SSEConnectionMetadata",
    "SSEEventPayload", 
    "SSEToolRequest",
    "MCPBridge"
]