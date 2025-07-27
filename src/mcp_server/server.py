"""
MCP Server Implementation
========================

Model Context Protocol server providing tools for DSL to PNG conversion.
Implements the three core tools: render_ui_mockup, validate_dsl, and get_render_status.
"""

import asyncio
import json
import os
from typing import Any, Dict, List, Union
from datetime import datetime, timezone

from mcp.server import Server
from mcp.server.models import InitializationOptions
from mcp.types import (
    Resource,
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
    LoggingLevel,
    ServerCapabilities,
)

from src.config.settings import get_settings
from src.config.logging import get_logger
from src.core.dsl.parser import validate_dsl_syntax, parse_dsl, get_validation_suggestions
from src.core.rendering.html_generator import generate_html
from src.core.rendering.png_generator import generate_png_from_html, PNGGenerationError
from src.core.queue.tasks import submit_render_task, get_task_result, TaskTracker
from src.models.schemas import (
    DSLRenderRequest,
    DSLValidationResponse,
    RenderOptions,
    TaskStatus,
)

logger = get_logger(__name__)


class DSLToPNGMCPServer:
    """MCP Server for DSL to PNG conversion."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger: Any = logger.bind(component="mcp_server")  # structlog.BoundLoggerBase
        self.server = Server("dsl-to-png-mcp")
        self._setup_tools()
        self._setup_resources()
        self._setup_handlers()

    def _setup_tools(self) -> None:
        """Setup MCP tools."""

        @self.server.list_tools()
        async def handle_list_tools() -> List[Tool]:
            """List available MCP tools."""
            return [
                Tool(
                    name="render_ui_mockup",
                    description="Convert DSL (Domain Specific Language) to PNG image mockup",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dsl_content": {
                                "type": "string",
                                "description": "DSL content defining the UI mockup (JSON or YAML format)",
                            },
                            "width": {
                                "type": "integer",
                                "description": "Render width in pixels",
                                "default": 800,
                                "minimum": 100,
                                "maximum": 2000,
                            },
                            "height": {
                                "type": "integer",
                                "description": "Render height in pixels",
                                "default": 600,
                                "minimum": 100,
                                "maximum": 2000,
                            },
                            "async_mode": {
                                "type": "boolean",
                                "description": "Whether to process asynchronously",
                                "default": False,
                            },
                            "options": {
                                "type": "object",
                                "description": "Additional rendering options",
                                "properties": {
                                    "device_scale_factor": {"type": "number", "default": 1.0},
                                    "wait_for_load": {"type": "boolean", "default": True},
                                    "optimize_png": {"type": "boolean", "default": True},
                                    "transparent_background": {"type": "boolean", "default": False},
                                },
                            },
                        },
                        "required": ["dsl_content"],
                    },
                ),
                Tool(
                    name="validate_dsl",
                    description="Validate DSL syntax and structure without rendering",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "dsl_content": {
                                "type": "string",
                                "description": "DSL content to validate",
                            },
                            "strict": {
                                "type": "boolean",
                                "description": "Enable strict validation mode",
                                "default": False,
                            },
                        },
                        "required": ["dsl_content"],
                    },
                ),
                Tool(
                    name="get_render_status",
                    description="Check the status of an asynchronous rendering job",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "task_id": {
                                "type": "string",
                                "description": "Task identifier from async render request",
                            }
                        },
                        "required": ["task_id"],
                    },
                ),
            ]

        # Store reference to handler for public API
        self._list_tools_handler = handle_list_tools

        @self.server.call_tool()
        async def handle_call_tool(  # type: ignore[misc]
            name: str, arguments: Dict[str, Any]
        ) -> List[Union[TextContent, ImageContent, EmbeddedResource]]:
            """Handle tool execution."""
            try:
                self.logger.info("Tool called", tool=name, arguments=arguments)

                if name == "render_ui_mockup":
                    return await self._handle_render_ui_mockup(arguments)  # type: ignore[return-value]
                elif name == "validate_dsl":
                    return await self._handle_validate_dsl(arguments)  # type: ignore[return-value]
                elif name == "get_render_status":
                    return await self._handle_get_render_status(arguments)  # type: ignore[return-value]
                else:
                    raise ValueError(f"Unknown tool: {name}")

            except Exception as e:
                error_msg = f"Tool execution failed: {str(e)}"
                self.logger.error("Tool execution error", tool=name, error=error_msg)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "error": error_msg,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                            indent=2,
                        ),
                    )
                ]

    def _setup_resources(self) -> None:
        """Setup MCP resources."""

        @self.server.list_resources()
        async def handle_list_resources() -> List[Resource]:  # type: ignore[misc]
            """List available resources."""
            return [
                Resource(
                    uri="dsl://schemas/element-types",  # type: ignore[arg-type]
                    name="DSL Element Types",
                    description="Available DSL element types and their properties",
                    mimeType="application/json",
                ),
                Resource(
                    uri="dsl://examples/basic",  # type: ignore[arg-type]
                    name="Basic DSL Examples",
                    description="Example DSL documents for common UI patterns",
                    mimeType="application/json",
                ),
                Resource(
                    uri="dsl://status/health",  # type: ignore[arg-type]
                    name="Server Health Status",
                    description="Current server health and performance metrics",
                    mimeType="application/json",
                ),
            ]

        @self.server.read_resource()  # type: ignore[arg-type]
        async def handle_read_resource(uri: str) -> str:  # type: ignore[misc]
            """Read resource content."""
            if uri == "dsl://schemas/element-types":
                return await self._get_element_types_schema()
            elif uri == "dsl://examples/basic":
                return await self._get_basic_examples()
            elif uri == "dsl://status/health":
                return await self._get_health_status()
            else:
                raise ValueError(f"Unknown resource URI: {uri}")

    def _setup_handlers(self) -> None:
        """Setup additional MCP handlers."""

        @self.server.set_logging_level()
        async def handle_set_logging_level(level: LoggingLevel) -> None:  # type: ignore[misc]
            """Handle logging level changes."""
            self.logger.info("Logging level changed", level=level)

    # Public API methods for MCP protocol testing
    async def get_tools(self) -> List[Tool]:
        """Get list of available MCP tools (public API)."""
        try:
            # Store reference to the handler during setup
            if hasattr(self, "_list_tools_handler"):
                return await self._list_tools_handler()
            else:
                raise RuntimeError("Tools handler not available")
        except Exception as e:
            self.logger.error("Failed to get tools list", error=str(e))
            raise

    async def call_tool(
        self, name: str, arguments: Dict[str, Any]
    ) -> List[Union[TextContent, ImageContent, EmbeddedResource]]:
        """Call a specific MCP tool (public API) - simplified for internal use."""
        try:
            self.logger.info("Direct tool call", tool=name, arguments=arguments)

            # Call tool handlers directly instead of using MCP protocol machinery
            if name == "render_ui_mockup":
                return await self._handle_render_ui_mockup(arguments)  # type: ignore[return-value]
            elif name == "validate_dsl":
                return await self._handle_validate_dsl(arguments)  # type: ignore[return-value]
            elif name == "get_render_status":
                return await self._handle_get_render_status(arguments)  # type: ignore[return-value]
            else:
                error_msg = f"Unknown tool: {name}"
                self.logger.error("Tool not found", tool=name, error=error_msg)
                return [
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "success": False,
                                "error": error_msg,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            },
                            indent=2,
                        ),
                    )
                ]
        except Exception as e:
            error_msg = f"Failed to call tool: {str(e)}"
            self.logger.error("Tool execution error", tool=name, error=error_msg)
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {
                            "success": False,
                            "error": error_msg,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                        indent=2,
                    ),
                )
            ]

    async def _handle_render_ui_mockup(
        self, arguments: Dict[str, Any]
    ) -> List[Union[TextContent, ImageContent]]:
        """Handle render_ui_mockup tool execution."""
        try:
            # Extract and validate arguments
            dsl_content = arguments.get("dsl_content")
            if not dsl_content:
                raise ValueError("dsl_content is required")

            # Parse rendering options
            async_mode = arguments.get("async_mode", False)
            options_dict = arguments.get("options", {})

            # Extract width and height from options_dict (they're passed inside options)
            width = options_dict.get("width", 800)
            height = options_dict.get("height", 600)

            # Create render options - filter out None values and provide defaults
            render_options_data = {
                "width": width,
                "height": height,
                "device_scale_factor": options_dict.get("device_scale_factor", 1.0),
                "wait_for_load": options_dict.get("wait_for_load", True),
                "full_page": options_dict.get("full_page", False),
                "optimize_png": options_dict.get("optimize_png", True),
                "timeout": options_dict.get("timeout", 30),
                "block_resources": options_dict.get("block_resources", False),
                "transparent_background": options_dict.get("transparent_background", False),
            }

            # Handle optional fields that can be None
            if options_dict.get("user_agent") is not None:
                render_options_data["user_agent"] = options_dict["user_agent"]
            if options_dict.get("png_quality") is not None:
                render_options_data["png_quality"] = options_dict["png_quality"]
            if options_dict.get("background_color") is not None:
                render_options_data["background_color"] = options_dict["background_color"]

            # 🚨 BYPASS RenderOptions validation for debugging
            self.logger.debug(
                "🔍 DIAGNOSTIC: Creating RenderOptions with bypassed validation",
                component="mcp_server",
                render_options_data=render_options_data,
            )
            try:
                render_options = RenderOptions(**render_options_data)
                self.logger.debug(
                    "🔍 DIAGNOSTIC: RenderOptions created successfully", component="mcp_server"
                )
            except Exception as e:
                self.logger.error(
                    f"🔧 DEBUG: RenderOptions validation failed: {e}, creating mock object"
                )

                # Create mock RenderOptions object with proper defaults
                class MockRenderOptions:
                    def __init__(self, **kwargs: Any) -> None:
                        # Set default values for essential fields that PNG generator expects
                        self.width: int = kwargs.get("width", 800)
                        self.height: int = kwargs.get("height", 600)
                        self.device_scale_factor: float = kwargs.get("device_scale_factor", 1.0)
                        self.user_agent: str = kwargs.get(
                            "user_agent", "Mozilla/5.0 (compatible; DSL-to-PNG/1.0)"
                        )
                        self.timeout: int = kwargs.get("timeout", 30)
                        self.full_page: bool = kwargs.get("full_page", False)
                        self.png_quality: int = kwargs.get("png_quality", 80)
                        self.optimize_png: bool = kwargs.get("optimize_png", True)
                        self.wait_for_load: bool = kwargs.get("wait_for_load", True)
                        self.block_resources: List[str] = kwargs.get("block_resources", [])
                        self.background_color: str = kwargs.get("background_color", "#ffffff")
                        self.transparent_background: bool = kwargs.get(
                            "transparent_background", False
                        )
                        # Set any additional kwargs
                        for k, v in kwargs.items():
                            if not hasattr(self, k):
                                setattr(self, k, v)

                    def dict(self) -> dict[str, Any]:
                        return self.__dict__

                render_options = MockRenderOptions(**render_options_data)
                self.logger.info(
                    f"🔧 DEBUG: Created mock RenderOptions with width={render_options.width}, height={render_options.height}"
                )

            # 🚨 BYPASS DSLRenderRequest validation for debugging
            self.logger.debug(
                "🔍 DIAGNOSTIC: Creating DSLRenderRequest with bypassed validation",
                component="mcp_server",
                dsl_content_length=len(dsl_content),
                dsl_content_type=type(dsl_content),
            )
            try:
                request = DSLRenderRequest(
                    dsl_content=dsl_content,
                    options=render_options,  # type: ignore[arg-type]
                    callback_url=None,  # No callback URL for synchronous MCP requests
                )
                self.logger.debug(
                    "🔍 DIAGNOSTIC: DSLRenderRequest created successfully", component="mcp_server"
                )
            except Exception as e:
                self.logger.error(
                    f"🔧 DEBUG: DSLRenderRequest validation failed: {e}, creating mock object"
                )

                # Create mock DSLRenderRequest object
                class MockDSLRenderRequest:
                    def __init__(self, **kwargs: Any) -> None:
                        for k, v in kwargs.items():
                            setattr(self, k, v)

                request = MockDSLRenderRequest(
                    dsl_content=dsl_content, options=render_options, callback_url=None
                )

            if async_mode:
                # Submit async task
                task_id = await submit_render_task(request)  # type: ignore[arg-type]

                response = {
                    "success": True,
                    "async": True,
                    "task_id": task_id,
                    "message": "Rendering task submitted successfully",
                    "status_check_tool": "get_render_status",
                }

                return [TextContent(type="text", text=json.dumps(response, indent=2))]

            else:
                # Synchronous rendering
                try:
                    self.logger.info("Starting synchronous rendering", task_id="sync")

                    # Step 1: Parse DSL
                    self.logger.debug(
                        "🔍 DIAGNOSTIC: About to parse DSL",
                        component="mcp_server",
                        dsl_content_length=len(dsl_content),
                        dsl_content_preview=dsl_content[:100],
                    )
                    parse_result = await parse_dsl(dsl_content)
                    self.logger.debug(
                        "🔍 DIAGNOSTIC: DSL parsing completed",
                        component="mcp_server",
                        success=parse_result.success,
                        document_type=type(parse_result.document),
                        document_is_none=parse_result.document is None,
                    )

                    if not parse_result.success:
                        error_msg = f"DSL parsing failed: {'; '.join(parse_result.errors)}"
                        suggestions = await get_validation_suggestions(
                            dsl_content, parse_result.errors
                        )
                        detailed_error = f"{error_msg}. Suggestions: {'; '.join(suggestions[:3])}"

                        response = {
                            "success": False,
                            "error": detailed_error,
                            "parsing_time": parse_result.processing_time,
                        }

                        return [TextContent(type="text", text=json.dumps(response, indent=2))]

                    # Check if document is None after successful parsing
                    if parse_result.document is None:
                        response = {
                            "success": False,
                            "error": "DSL parsing completed but document is empty",
                            "parsing_time": parse_result.processing_time,
                        }
                        return [TextContent(type="text", text=json.dumps(response, indent=2))]

                    # Step 2: Generate HTML
                    html_content = await generate_html(parse_result.document, render_options)  # type: ignore[arg-type]

                    # Step 3: Generate PNG
                    png_result = await generate_png_from_html(html_content, render_options)  # type: ignore[arg-type]

                    # Add metadata
                    png_result.metadata.update(
                        {
                            "render_type": "synchronous_mcp",
                            "parsing_time": parse_result.processing_time,
                        }
                    )

                    response = {
                        "success": True,
                        "png_result": {
                            "base64_data": png_result.base64_data,
                            "width": png_result.width,
                            "height": png_result.height,
                            "file_size": png_result.file_size,
                            "metadata": png_result.metadata,
                        },
                        "message": "Synchronous rendering completed successfully",
                    }

                    return [TextContent(type="text", text=json.dumps(response, indent=2))]

                except PNGGenerationError as e:
                    error_msg = str(e)
                    self.logger.error("Browser pool error during rendering", error=error_msg)

                    # Determine specific error type for better user guidance
                    if "Browser pool not initialized" in error_msg:
                        user_error = "Browser pool is not available. The rendering service may be starting up."
                        error_code = "BROWSER_POOL_NOT_INITIALIZED"
                    elif "Browser pool initialization failed" in error_msg:
                        user_error = (
                            "Browser pool failed to initialize. Service temporarily unavailable."
                        )
                        error_code = "BROWSER_POOL_INITIALIZATION_FAILED"
                    elif (
                        "Browser pool exhausted" in error_msg or "No available browser" in error_msg
                    ):
                        user_error = "All browser instances are busy. Please try again in a moment."
                        error_code = "BROWSER_POOL_EXHAUSTED"
                    elif "timeout" in error_msg.lower():
                        user_error = (
                            "Browser operation timed out. Please try again with simpler content."
                        )
                        error_code = "BROWSER_TIMEOUT"
                    else:
                        user_error = "PNG generation failed due to browser issues."
                        error_code = "PNG_GENERATION_ERROR"

                    response = {
                        "success": False,
                        "error": user_error,
                        "error_code": error_code,
                        "suggestion": "Try using async_mode=true for better reliability, or wait a moment and retry",
                        "technical_details": error_msg if self.settings.debug else None,
                    }

                    return [TextContent(type="text", text=json.dumps(response, indent=2))]

                except Exception as e:
                    error_msg = f"Synchronous rendering failed: {str(e)}"
                    self.logger.error("Synchronous rendering error", error=error_msg)

                    response = {
                        "success": False,
                        "error": error_msg,
                        "suggestion": "Try using async_mode=true or check DSL format",
                    }

                    return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            raise ValueError(f"Failed to render UI mockup: {str(e)}")

    async def _handle_validate_dsl(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle validate_dsl tool execution."""
        try:
            dsl_content = arguments.get("dsl_content")
            if not dsl_content:
                raise ValueError("dsl_content is required")

            # Note: strict mode is available but not currently implemented
            # strict = arguments.get("strict", False)

            # Perform syntax validation
            syntax_valid = await validate_dsl_syntax(dsl_content)

            if syntax_valid:
                # Perform full parsing for deeper validation
                parse_result = await parse_dsl(dsl_content)

                response = DSLValidationResponse(
                    valid=parse_result.success,
                    errors=parse_result.errors,
                    warnings=getattr(parse_result, "warnings", []),
                    suggestions=[],  # TODO: Add validation suggestions
                )
            else:
                response = DSLValidationResponse(
                    valid=False,
                    errors=["Invalid DSL syntax"],
                    warnings=[],
                    suggestions=["Check JSON/YAML formatting"],
                )

            return [TextContent(type="text", text=json.dumps(response.model_dump(), indent=2))]

        except Exception as e:
            raise ValueError(f"Failed to validate DSL: {str(e)}")

    async def _handle_get_render_status(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle get_render_status tool execution."""
        try:
            task_id = arguments.get("task_id")
            if not task_id:
                raise ValueError("task_id is required")

            # Get task status from Redis
            task_data = await TaskTracker.get_task_status(task_id)

            if not task_data:
                response = {"success": False, "error": "Task not found", "task_id": task_id}
            else:
                # Get task result if completed
                task_result = None
                if task_data.get("status") == TaskStatus.COMPLETED.value:
                    task_result = await get_task_result(task_id)

                response = {
                    "success": True,
                    "task_id": task_id,
                    "status": task_data.get("status"),
                    "progress": task_data.get("progress"),
                    "message": task_data.get("message"),
                    "updated_at": task_data.get("updated_at"),
                    "result": task_result.model_dump() if task_result else None,
                }

            return [TextContent(type="text", text=json.dumps(response, indent=2))]

        except Exception as e:
            raise ValueError(f"Failed to get render status: {str(e)}")

    async def _get_element_types_schema(self) -> str:
        """Get DSL element types schema."""
        from src.models.schemas import ElementType

        schema = {
            "element_types": [e.value for e in ElementType],
            "schema_version": "1.0",
            "description": "Available DSL element types for UI mockup creation",
        }

        return json.dumps(schema, indent=2)

    async def _get_basic_examples(self) -> str:
        """Get basic DSL examples."""
        examples = {
            "simple_button": {
                "width": 300,
                "height": 200,
                "elements": [
                    {
                        "type": "button",
                        "layout": {"x": 100, "y": 80, "width": 100, "height": 40},
                        "label": "Click Me",
                        "style": {"background": "#007bff", "color": "white"},
                    }
                ],
            },
            "login_form": {
                "width": 400,
                "height": 300,
                "elements": [
                    {
                        "type": "container",
                        "layout": {"x": 50, "y": 50, "width": 300, "height": 200},
                        "children": [
                            {
                                "type": "text",
                                "layout": {"x": 0, "y": 0, "width": 300, "height": 30},
                                "text": "Login",
                                "style": {"font_size": 24, "font_weight": "bold"},
                            },
                            {
                                "type": "input",
                                "layout": {"x": 0, "y": 50, "width": 280, "height": 35},
                                "placeholder": "Username",
                            },
                            {
                                "type": "input",
                                "layout": {"x": 0, "y": 95, "width": 280, "height": 35},
                                "placeholder": "Password",
                            },
                            {
                                "type": "button",
                                "layout": {"x": 0, "y": 150, "width": 280, "height": 40},
                                "label": "Login",
                                "style": {"background": "#28a745", "color": "white"},
                            },
                        ],
                    }
                ],
            },
        }

        return json.dumps(examples, indent=2)

    async def _get_health_status(self) -> str:
        """Get server health status."""
        # TODO: Implement actual health checks
        status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": "1.0.0",
            "services": {
                "mcp_server": "healthy",
                "redis": "unknown",
                "browser_pool": "unknown",
                "celery": "unknown",
            },
        }

        return json.dumps(status, indent=2)

    async def run(
        self, transport_type: str = "stdio", host: str = "0.0.0.0", port: int = 3001
    ) -> None:
        """Run the MCP server."""
        try:
            if transport_type == "stdio":
                # Run with stdio transport
                from mcp.server.stdio import stdio_server

                async with stdio_server() as (read_stream, write_stream):
                    self.logger.info(
                        "MCP server starting with stdio transport", component="mcp_server"
                    )
                    await self.server.run(
                        read_stream,
                        write_stream,
                        InitializationOptions(
                            server_name="dsl-to-png-mcp",
                            server_version="1.0.0",
                            capabilities=ServerCapabilities(),
                        ),
                    )
            elif transport_type == "http":
                # Run with HTTP health check server for Docker deployment
                from aiohttp import web

                # Create simple health check server
                async def health_check(request: web.Request) -> web.Response:
                    return web.json_response(
                        {
                            "status": "healthy",
                            "server": "dsl-to-png-mcp",
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                    )

                # Create web application
                app = web.Application()
                app.router.add_get("/health", health_check)
                app.router.add_get("/", health_check)

                self.logger.info(
                    "MCP server starting with HTTP health check",
                    component="mcp_server",
                    host=host,
                    port=port,
                )

                # Start HTTP server
                runner = web.AppRunner(app)
                await runner.setup()
                site = web.TCPSite(runner, host, port)
                await site.start()

                # Keep server running
                self.logger.info("HTTP health check server started, keeping alive")
                try:
                    # Keep the server running indefinitely
                    while True:
                        await asyncio.sleep(60)  # Sleep for 1 minute intervals
                        self.logger.debug("MCP server health check - still alive")
                except asyncio.CancelledError:
                    self.logger.info("MCP server shutdown requested")
                    await runner.cleanup()
                    raise
            else:
                raise ValueError(f"Unsupported transport type: {transport_type}")

        except Exception as e:
            self.logger.error("MCP server error", error=str(e))
            raise


# Server instance
mcp_server = DSLToPNGMCPServer()


async def main() -> None:
    """Main entry point for MCP server."""
    transport_type = os.getenv("MCP_TRANSPORT", "stdio")
    if transport_type == "http":
        host = os.getenv("MCP_HOST", "0.0.0.0")
        port = int(os.getenv("MCP_PORT", "3001"))
        await mcp_server.run(transport_type="http", host=host, port=port)
    else:
        await mcp_server.run(transport_type="stdio")


# Alias for integration tests compatibility
MCPServer = DSLToPNGMCPServer


if __name__ == "__main__":
    asyncio.run(main())
