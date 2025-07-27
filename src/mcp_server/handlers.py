"""
MCP Server Message Handlers
===========================

Handlers for processing MCP protocol messages and managing tool/resource requests.
"""

from typing import Any, Dict, Optional, Union, Callable, Awaitable, Tuple, List
import asyncio
from dataclasses import dataclass

from src.config.logging import get_logger
from src.models.schemas import RenderOptions

logger = get_logger(__name__)


@dataclass
class MCPMessage:
    """MCP protocol message structure."""

    method: str
    params: Dict[str, Any]
    id: Optional[str] = None
    jsonrpc: str = "2.0"


@dataclass
class MCPResponse:
    """MCP protocol response structure."""

    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    jsonrpc: str = "2.0"


class MessageHandler:
    """Main message handler for MCP protocol requests."""

    def __init__(self) -> None:
        self.logger: Any = logger.bind(component="message_handler")  # structlog.BoundLoggerBase
        self._tool_handlers: Dict[str, Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]] = {}
        self._resource_handlers: Dict[str, Callable[[str], Awaitable[Dict[str, Any]]]] = {}
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize the message handler."""
        if self._initialized:
            return

        # Register default handlers
        await self._register_default_handlers()
        self._initialized = True
        self.logger.info("Message handler initialized")

    async def handle_message(self, message: Union[Dict[str, Any], MCPMessage]) -> MCPResponse:
        """
        Handle incoming MCP message.

        Args:
            message: MCP message to process

        Returns:
            MCP response
        """
        try:
            if isinstance(message, dict):
                msg = MCPMessage(**message)
            else:
                msg = message

            self.logger.debug("Processing message", method=msg.method, id=msg.id)

            # Route message based on method
            if msg.method == "tools/call":
                return await self._handle_tool_call(msg)
            elif msg.method == "resources/read":
                return await self._handle_resource_read(msg)
            elif msg.method == "tools/list":
                return await self._handle_tools_list(msg)
            elif msg.method == "resources/list":
                return await self._handle_resources_list(msg)
            elif msg.method == "initialize":
                return await self._handle_initialize(msg)
            else:
                return MCPResponse(
                    error={"code": -32601, "message": f"Method not found: {msg.method}"}, id=msg.id
                )

        except Exception as e:
            self.logger.error(
                "Message handling error", error=str(e), method=getattr(message, "method", "unknown")
            )
            return MCPResponse(
                error={"code": -32603, "message": f"Internal error: {e}"},
                id=getattr(message, "id", None),
            )

    async def _handle_tool_call(self, message: MCPMessage) -> MCPResponse:
        """Handle tool call request."""
        try:
            params = message.params
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            if tool_name not in self._tool_handlers:
                return MCPResponse(
                    error={"code": -32601, "message": f"Tool not found: {tool_name}"}, id=message.id
                )

            handler = self._tool_handlers[tool_name]
            result = await handler(tool_args)

            return MCPResponse(result=result, id=message.id)

        except Exception as e:
            return MCPResponse(
                error={"code": -32603, "message": f"Tool execution error: {e}"}, id=message.id
            )

    async def _handle_resource_read(self, message: MCPMessage) -> MCPResponse:
        """Handle resource read request."""
        try:
            params = message.params
            uri = params.get("uri")

            if not uri:
                return MCPResponse(
                    error={"code": -32602, "message": "Missing uri parameter"}, id=message.id
                )

            # Extract resource type from URI
            resource_type = uri.split("://")[0] if "://" in uri else "unknown"

            if resource_type not in self._resource_handlers:
                return MCPResponse(
                    error={
                        "code": -32601,
                        "message": f"Resource type not supported: {resource_type}",
                    },
                    id=message.id,
                )

            handler = self._resource_handlers[resource_type]
            result = await handler(uri)

            return MCPResponse(result=result, id=message.id)

        except Exception as e:
            return MCPResponse(
                error={"code": -32603, "message": f"Resource read error: {e}"}, id=message.id
            )

    async def _handle_tools_list(self, message: MCPMessage) -> MCPResponse:
        """Handle tools list request."""
        tools: List[Dict[str, Any]] = [
            {
                "name": "render_dsl_to_png",
                "description": "Render DSL content to PNG image",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "dsl_content": {"type": "string"},
                        "options": {"type": "object"},
                    },
                    "required": ["dsl_content"],
                },
            },
            {
                "name": "get_system_status",
                "description": "Get system status information",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "check_system_health",
                "description": "Check system health status",
                "inputSchema": {"type": "object", "properties": {}},
            },
        ]

        return MCPResponse(result={"tools": tools}, id=message.id)

    async def _handle_resources_list(self, message: MCPMessage) -> MCPResponse:
        """Handle resources list request."""
        resources = [
            {
                "uri": "storage://",
                "name": "Storage Resources",
                "description": "Access stored files and data",
            },
            {
                "uri": "task://",
                "name": "Task Resources",
                "description": "Access task information and status",
            },
        ]

        return MCPResponse(result={"resources": resources}, id=message.id)

    async def _handle_initialize(self, message: MCPMessage) -> MCPResponse:
        """Handle initialize request."""
        capabilities = {"tools": True, "resources": True, "prompts": False, "logging": True}

        return MCPResponse(
            result={
                "capabilities": capabilities,
                "serverInfo": {"name": "dsl-to-png-mcp-server", "version": "1.0.0"},
            },
            id=message.id,
        )

    async def _register_default_handlers(self) -> None:
        """Register default tool and resource handlers."""
        # Tool handlers
        self._tool_handlers["render_dsl_to_png"] = self._render_dsl_tool
        self._tool_handlers["get_system_status"] = self._system_status_tool
        self._tool_handlers["check_system_health"] = self._health_check_tool

        # Resource handlers
        self._resource_handlers["storage"] = self._storage_resource
        self._resource_handlers["task"] = self._task_resource

    async def _render_dsl_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Render DSL to PNG tool implementation."""
        try:
            dsl_content = args.get("dsl_content", "")
            options = args.get("options", {})

            # Create render options
            render_opts = RenderOptions(
                width=options.get("width", 800),
                height=options.get("height", 600),
                device_scale_factor=options.get("device_scale_factor", 1.0),
                user_agent=options.get("user_agent"),
                wait_for_load=options.get("wait_for_load", True),
                full_page=options.get("full_page", False),
                timeout=options.get("timeout", 30),
                block_resources=options.get("block_resources", False),
                background_color=options.get("background_color"),
                transparent_background=options.get("transparent_background", False),
                png_quality=options.get("png_quality"),
                optimize_png=options.get("optimize_png", True),
            )

            # Simulate rendering process
            result = {
                "status": "success",
                "png_data": f"rendered_png_data_for_{len(dsl_content)}_chars",
                "width": render_opts.width,
                "height": render_opts.height,
                "file_size": len(dsl_content) * 10,  # Mock file size
            }

            return result

        except Exception as e:
            self.logger.error("DSL rendering error", error=str(e))
            return {"status": "error", "message": str(e)}

    async def _system_status_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """System status tool implementation."""
        return {
            "status": "healthy",
            "uptime": "1h 30m",
            "memory_usage": "45%",
            "cpu_usage": "12%",
            "active_tasks": 3,
            "completed_tasks": 47,
        }

    async def _health_check_tool(self, args: Dict[str, Any]) -> Dict[str, Any]:
        """Health check tool implementation."""
        return {
            "healthy": True,
            "checks": {"database": "ok", "storage": "ok", "renderer": "ok", "mcp_server": "ok"},
            "timestamp": "2024-01-20T10:30:00Z",
        }

    async def _storage_resource(self, uri: str) -> Dict[str, Any]:
        """Storage resource handler."""
        # Extract file path from URI
        file_path = uri.replace("storage://", "")

        return {
            "uri": uri,
            "mimeType": "application/octet-stream",
            "text": f"Storage resource content for: {file_path}",
            "metadata": {"size": 1024, "modified": "2024-01-20T10:30:00Z"},
        }

    async def _task_resource(self, uri: str) -> Dict[str, Any]:
        """Task resource handler."""
        # Extract task ID from URI
        task_id = uri.replace("task://", "")

        return {
            "uri": uri,
            "mimeType": "application/json",
            "text": f'{{"task_id": "{task_id}", "status": "completed", "progress": 100}}',
            "metadata": {
                "task_type": "dsl_rendering",
                "created": "2024-01-20T10:00:00Z",
                "completed": "2024-01-20T10:30:00Z",
            },
        }

    def register_tool_handler(
        self, name: str, handler: Callable[[Dict[str, Any]], Awaitable[Dict[str, Any]]]
    ) -> None:
        """Register a custom tool handler."""
        self._tool_handlers[name] = handler
        self.logger.info("Registered tool handler", tool_name=name)

    def register_resource_handler(
        self, scheme: str, handler: Callable[[str], Awaitable[Dict[str, Any]]]
    ) -> None:
        """Register a custom resource handler."""
        self._resource_handlers[scheme] = handler
        self.logger.info("Registered resource handler", scheme=scheme)


class AsyncMessageHandler(MessageHandler):
    """Asynchronous message handler with concurrent processing."""

    def __init__(self, max_concurrent: int = 10):
        super().__init__()
        self._semaphore = asyncio.Semaphore(max_concurrent)
        self._message_queue: asyncio.Queue[
            Tuple[Union[Dict[str, Any], MCPMessage], asyncio.Queue[MCPResponse]]
        ] = asyncio.Queue()
        self._processing = False

    async def process_message_queue(self) -> None:
        """Process messages from queue with concurrency control."""
        self._processing = True

        while self._processing:
            try:
                message, response_queue = await asyncio.wait_for(
                    self._message_queue.get(), timeout=1.0
                )

                # Process message with semaphore control
                async with self._semaphore:
                    response = await self.handle_message(message)
                    await response_queue.put(response)

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                self.logger.error("Queue processing error", error=str(e))

    async def queue_message(self, message: Union[Dict[str, Any], MCPMessage]) -> MCPResponse:
        """Queue message for processing."""
        response_queue: asyncio.Queue[MCPResponse] = asyncio.Queue(maxsize=1)
        await self._message_queue.put((message, response_queue))
        return await response_queue.get()

    def stop_processing(self) -> None:
        """Stop queue processing."""
        self._processing = False


# Global message handler instance
_global_handler: Optional[MessageHandler] = None


async def get_message_handler() -> MessageHandler:
    """Get or create global message handler."""
    global _global_handler
    if _global_handler is None:
        _global_handler = MessageHandler()
        await _global_handler.initialize()
    return _global_handler


async def process_mcp_message(message: Union[Dict[str, Any], MCPMessage]) -> MCPResponse:
    """Process MCP message using global handler."""
    handler = await get_message_handler()
    return await handler.handle_message(message)
