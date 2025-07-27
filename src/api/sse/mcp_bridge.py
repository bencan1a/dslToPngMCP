"""
MCP Bridge
==========

Bridge between HTTP requests and MCP protocol over SSE.
Handles tool execution with progress streaming via SSE events.
"""

from typing import Optional, Dict, Any
import asyncio
import json
import uuid
import time
import logging
import sys
import traceback

from src.config.logging import get_logger
from src.mcp_server.server import DSLToPNGMCPServer
from src.models.schemas import DSLRenderRequest, RenderOptions, TaskStatus
from src.core.queue.tasks import TaskTracker

from .models import (
    SSEToolRequest,
    SSEToolResponse,
)
from .events import (
    create_tool_call_event,
    create_tool_response_event,
    create_render_started_event,
    create_render_completed_event,
    create_render_failed_event,
    create_validation_completed_event,
    create_progress_event,
    create_error_event,
)
from .connection_manager import get_sse_connection_manager

logger = get_logger(__name__)


class MCPBridge:
    """
    Bridge between HTTP requests and MCP protocol with SSE progress updates.

    Interfaces with existing DSLToPNGMCPServer to execute tools while streaming
    progress updates to SSE clients.
    """

    def __init__(self) -> None:
        self.logger: Any = logger.bind(component="mcp_bridge")  # structlog.BoundLoggerBase
        self.mcp_server = DSLToPNGMCPServer()
        self._active_requests: Dict[str, Dict[str, Any]] = {}

    async def execute_tool_with_sse(self, tool_request: SSEToolRequest) -> SSEToolResponse:
        """
        Execute MCP tool with SSE progress updates.

        Args:
            tool_request: SSE tool request

        Returns:
            Tool execution response
        """
        # 🚨 DIAGNOSTIC CODE - Log Level Investigation
        import logging
        import sys
        from src.config.settings import get_settings

        settings = get_settings()
        root_logger = logging.getLogger()
        this_logger = logging.getLogger(__name__)

        # Force console output to bypass all filtering
        print("=" * 80, file=sys.stderr)
        print("🔍 DIAGNOSTIC - MCP Bridge Log Level Investigation", file=sys.stderr)
        print(f"  Tool: {tool_request.tool_name}", file=sys.stderr)
        print(f"  Settings log_level: {settings.log_level}", file=sys.stderr)
        print(f"  Settings environment: {settings.environment}", file=sys.stderr)
        print(
            f"  Root logger level: {root_logger.level} ({logging.getLevelName(root_logger.level)})",
            file=sys.stderr,
        )
        print(
            f"  This logger level: {this_logger.level} ({logging.getLevelName(this_logger.level)})",
            file=sys.stderr,
        )
        print(
            f"  This logger effective level: {this_logger.getEffectiveLevel()} ({logging.getLevelName(this_logger.getEffectiveLevel())})",
            file=sys.stderr,
        )
        print(f"  INFO level value: {logging.INFO}", file=sys.stderr)
        print(
            f"  Handlers on root: {[h.__class__.__name__ for h in root_logger.handlers]}",
            file=sys.stderr,
        )
        print(
            f"  Handlers on this logger: {[h.__class__.__name__ for h in this_logger.handlers]}",
            file=sys.stderr,
        )
        print("=" * 80, file=sys.stderr)

        # Force multiple logging attempts at different levels
        self.logger.critical("🚨 CRITICAL - MCP Bridge execute_tool_with_sse called")
        self.logger.error("🚨 ERROR - MCP Bridge execute_tool_with_sse called")
        self.logger.warning("🚨 WARNING - MCP Bridge execute_tool_with_sse called")
        self.logger.info("🚨 INFO - MCP Bridge execute_tool_with_sse called")
        self.logger.debug("🚨 DEBUG - MCP Bridge execute_tool_with_sse called")

        # Also try standard logging module directly
        logging.critical("🚨 STDLIB CRITICAL - MCP Bridge called")
        logging.error("🚨 STDLIB ERROR - MCP Bridge called")
        logging.warning("🚨 STDLIB WARNING - MCP Bridge called")
        logging.info("🚨 STDLIB INFO - MCP Bridge called")
        logging.debug("🚨 STDLIB DEBUG - MCP Bridge called")

        start_time = time.time()
        request_id = tool_request.request_id or str(uuid.uuid4())

        # Track active request
        self._active_requests[request_id] = {
            "tool_name": tool_request.tool_name,
            "connection_id": tool_request.connection_id,
            "start_time": start_time,
            "status": "started",
        }

        try:
            # Get connection manager
            connection_manager = await get_sse_connection_manager()

            # Send tool call started event
            call_event = create_tool_call_event(
                connection_id=tool_request.connection_id,
                tool_name=tool_request.tool_name,
                arguments=tool_request.arguments,
                request_id=request_id,
            )
            await connection_manager.send_to_connection(tool_request.connection_id, call_event)

            # Execute the specific tool
            if tool_request.tool_name == "render_ui_mockup":
                result = await self._execute_render_tool(tool_request, request_id)
            elif tool_request.tool_name == "validate_dsl":
                result = await self._execute_validation_tool(tool_request, request_id)
            elif tool_request.tool_name == "get_render_status":
                result = await self._execute_status_tool(tool_request, request_id)
            else:
                raise ValueError(f"Unsupported tool: {tool_request.tool_name}")

            execution_time = time.time() - start_time

            # Send tool response event
            response_event = create_tool_response_event(
                connection_id=tool_request.connection_id,
                tool_name=tool_request.tool_name,
                success=True,
                result=result,
                execution_time=execution_time,
                request_id=request_id,
            )
            await connection_manager.send_to_connection(tool_request.connection_id, response_event)

            # Create response
            response = SSEToolResponse(
                success=True,
                tool_name=tool_request.tool_name,
                request_id=request_id,
                result=result,
                error=None,
                execution_time=execution_time,
                events_sent=self._active_requests.get(request_id, {}).get("events_sent", 0),
            )

            self.logger.info(
                "Tool executed successfully via SSE",
                tool=tool_request.tool_name,
                request_id=request_id,
                execution_time=execution_time,
            )

            return response

        except Exception as e:
            execution_time = time.time() - start_time

            # 🚨 ENHANCED EXCEPTION DEBUGGING - Comprehensive diagnostic logging
            print(f"🔍 EXCEPTION DIAGNOSTIC: {type(e).__name__}: {repr(e)[:200]}", file=sys.stderr)
            self.logger.error(
                "🔍 EXCEPTION DIAGNOSTIC: Detailed exception information before error logging",
                exception_type=type(e).__name__,
                exception_module=getattr(type(e), "__module__", "unknown"),
                exception_repr=repr(e)[:500],  # First 500 chars to avoid huge logs
                exception_str_attempt="attempting_str_conversion",
                tool_request_type=type(tool_request).__name__,
                tool_name_value=getattr(tool_request, "tool_name", "MISSING_TOOL_NAME"),
                tool_name_type=type(getattr(tool_request, "tool_name", None)).__name__,
                request_id_value=request_id,
                request_id_type=type(request_id).__name__,
                execution_time_value=execution_time,
                execution_time_type=type(execution_time).__name__,
            )

            # Safe error message conversion with detailed diagnostics
            try:
                error_message = str(e)
                error_message_type = type(error_message).__name__
                error_message_length = len(error_message)

                print(f"🔍 ERROR MESSAGE: {error_message[:100]}", file=sys.stderr)
                self.logger.error(
                    "🔍 ERROR MESSAGE DIAGNOSTIC: String conversion details",
                    error_message_type=error_message_type,
                    error_message_length=error_message_length,
                    error_message_preview=error_message[:100] if error_message else "None",
                )

                # Ensure we have a meaningful error message
                if not error_message:
                    error_message = f"Exception occurred with empty string: {repr(e)}"
                    self.logger.error(
                        "🚨 EMPTY ERROR MESSAGE: Forced replacement",
                        replacement_message=error_message,
                    )

            except Exception as str_error:
                error_message = (
                    f"Failed to get exception message: {type(str_error).__name__}: {str(str_error)}"
                )
                self.logger.error(
                    "🚨 STRING CONVERSION FAILED: Exception during str() conversion",
                    str_error_type=type(str_error).__name__,
                    str_error_message=str(str_error),
                    original_exception_repr=repr(e),
                    fallback_message=error_message,
                )

            # Validate all logging parameters before attempting to log
            safe_tool_name = getattr(tool_request, "tool_name", "UNKNOWN_TOOL")
            if safe_tool_name is None:
                safe_tool_name = "NULL_TOOL_NAME"

            safe_request_id = request_id
            safe_execution_time = execution_time
            safe_error_message = error_message

            print(
                f"🔍 SAFE LOGGING PARAMETERS: {safe_tool_name}, {safe_request_id}", file=sys.stderr
            )
            self.logger.error(
                "🔍 SAFE LOGGING PARAMETERS: Pre-logging validation",
                safe_tool_name=safe_tool_name,
                safe_tool_name_type=type(safe_tool_name).__name__,
                safe_request_id=safe_request_id,
                safe_request_id_type=type(safe_request_id).__name__,
                safe_execution_time=safe_execution_time,
                safe_execution_time_type=type(safe_execution_time).__name__,
                safe_error_message_length=len(safe_error_message),
                safe_error_message_type=type(safe_error_message).__name__,
            )

            # Attempt the actual error logging with enhanced error handling
            try:
                self.logger.error(
                    "Tool execution failed via SSE",
                    tool=safe_tool_name,
                    request_id=safe_request_id,
                    error=safe_error_message,
                    execution_time=safe_execution_time,
                )
                print(
                    "🔍 ERROR LOGGING SUCCESS: Error log completed without issues", file=sys.stderr
                )
                self.logger.error("🔍 ERROR LOGGING SUCCESS: Error log completed without issues")
            except Exception as log_error:
                # Fallback logging with minimal parameters
                self.logger.critical(
                    "🚨 ERROR LOGGING FAILED: Cannot log structured error",
                    log_error_type=type(log_error).__name__,
                    log_error_message=str(log_error),
                    fallback_tool=str(safe_tool_name)[:50],
                    fallback_request=str(safe_request_id)[:50],
                    fallback_error=str(safe_error_message)[:100],
                )
                # Try basic logging as last resort
                try:
                    self.logger.error(
                        f"BASIC LOG: Tool {safe_tool_name} failed: {safe_error_message}"
                    )
                except Exception:
                    print(f"CRITICAL: All logging failed for tool {safe_tool_name}")

            # Send error event
            try:
                connection_manager = await get_sse_connection_manager()
                error_event = create_error_event(
                    connection_id=tool_request.connection_id,
                    error_code="TOOL_EXECUTION_ERROR",
                    error_message=f"Tool execution failed: {error_message}",
                    details={"tool_name": tool_request.tool_name, "request_id": request_id},
                )
                await connection_manager.send_to_connection(tool_request.connection_id, error_event)
            except Exception as event_error:
                self.logger.error("Failed to send error event", error=str(event_error))

            # Return error response
            return SSEToolResponse(
                success=False,
                tool_name=tool_request.tool_name,
                request_id=request_id,
                result=None,
                error=error_message,
                execution_time=execution_time,
                events_sent=self._active_requests.get(request_id, {}).get("events_sent", 0),
            )

        finally:
            # Clean up active request tracking
            self._active_requests.pop(request_id, None)

    async def _execute_render_tool(
        self, tool_request: SSEToolRequest, request_id: str
    ) -> Dict[str, Any]:
        """Execute render_ui_mockup tool with progress updates."""
        connection_manager = await get_sse_connection_manager()

        # Parse arguments
        arguments = tool_request.arguments
        dsl_content = arguments.get("dsl_content")
        if not dsl_content:
            raise ValueError("dsl_content is required")

        # Create render options - extract options_dict first with robust null checks
        raw_options = arguments.get("options", {}) or {}  # type: ignore

        # Additional safety check to ensure options_dict is a dictionary
        if not isinstance(raw_options, dict):
            self.logger.warning(
                "Invalid options_dict type, using empty dict",
                options_dict_type=type(raw_options),
                options_dict_value=raw_options,
            )
            options_dict: Dict[str, Any] = {}
        else:
            options_dict: Dict[str, Any] = raw_options  # type: ignore

        width: int = options_dict.get("width", 800)
        height: int = options_dict.get("height", 600)

        # 🚨 ENHANCED DIAGNOSTIC: Log all RenderOptions fields
        self.logger.info(
            "🔍 DIAGNOSTIC: Creating RenderOptions with comprehensive null safety",
            arguments=arguments,
            width=width,
            width_type=type(width).__name__,
            height=height,
            height_type=type(height).__name__,
            options_dict=options_dict,
            device_scale_factor=options_dict.get("device_scale_factor", 1.0),
            device_scale_factor_type=type(options_dict.get("device_scale_factor", 1.0)).__name__,
            timeout=options_dict.get("timeout", 30),
            timeout_type=type(options_dict.get("timeout", 30)).__name__,
            user_agent=options_dict.get("user_agent"),
            png_quality=options_dict.get("png_quality"),
            background_color=options_dict.get("background_color"),
        )

        # 🚨 FIX: Filter None values before creating RenderOptions to prevent Redis DataError
        render_options_data: Dict[str, Any] = {
            "width": width,
            "height": height,
            "device_scale_factor": float(options_dict.get("device_scale_factor", 1.0)),
            "wait_for_load": bool(options_dict.get("wait_for_load", True)),
            "full_page": bool(options_dict.get("full_page", False)),
            "optimize_png": bool(options_dict.get("optimize_png", True)),
            "timeout": int(options_dict.get("timeout", 30)),
            "block_resources": bool(options_dict.get("block_resources", False)),
            "transparent_background": bool(options_dict.get("transparent_background", False)),
        }

        # Only add optional fields if they are not None to prevent Redis serialization errors
        user_agent = options_dict.get("user_agent")
        if user_agent is not None:
            render_options_data["user_agent"] = str(user_agent)
        else:
            render_options_data["user_agent"] = "Mozilla/5.0 (Linux; MCP Bridge)"

        png_quality = options_dict.get("png_quality")
        if png_quality is not None:
            render_options_data["png_quality"] = int(png_quality)
        else:
            render_options_data["png_quality"] = 90

        background_color = options_dict.get("background_color")
        if background_color is not None:
            render_options_data["background_color"] = str(background_color)
        else:
            render_options_data["background_color"] = "#ffffff"

        render_options = RenderOptions(**render_options_data)

        # Send render started event
        started_event = create_render_started_event(
            connection_id=tool_request.connection_id,
            request_id=request_id,
            render_options=render_options.model_dump(),
        )
        await connection_manager.send_to_connection(tool_request.connection_id, started_event)
        self._increment_events_sent(request_id)

        async_mode = arguments.get("async_mode", False)

        if async_mode:
            # Submit async task and track progress
            render_request = DSLRenderRequest(
                dsl_content=dsl_content,
                options=render_options,
                callback_url=None,  # No callback URL for SSE bridge requests
            )

            # Import here to avoid circular imports
            from src.core.queue.tasks import submit_render_task_with_sse

            task_id = await submit_render_task_with_sse(render_request, tool_request.connection_id)

            # Start monitoring task progress (just for final tool response)
            asyncio.create_task(
                self._monitor_async_task(task_id, tool_request.connection_id, request_id)
            )

            return {
                "async": True,
                "task_id": task_id,
                "message": "Rendering task submitted successfully",
                "status_check_tool": "get_render_status",
            }
        else:
            # Synchronous rendering with progress updates
            await self._send_progress_update(
                tool_request.connection_id,
                request_id,
                "render",
                10,
                "Starting DSL parsing",
                "parsing",
            )

            # Use MCP server's tool execution
            # Parse JSON string to object if needed, but keep as dsl_content parameter

            if isinstance(dsl_content, str):
                # Ensure it's valid JSON by parsing and re-serializing with robust error handling
                try:
                    dsl_object = json.loads(dsl_content)
                    dsl_content = json.dumps(dsl_object)
                    self.logger.info(
                        "JSON parsing successful",
                        dsl_content_length=len(dsl_content),
                        connection_id=tool_request.connection_id,
                    )
                except json.JSONDecodeError as e:
                    error_msg = f"Invalid JSON in dsl_content: {str(e)}"
                    self.logger.error(
                        "JSON parsing failed",
                        error=error_msg,
                        dsl_content_preview=(
                            dsl_content[:200] + "..." if len(dsl_content) > 200 else dsl_content
                        ),
                        connection_id=tool_request.connection_id,
                    )
                    raise ValueError(error_msg)
                except Exception as e:
                    error_msg = f"Unexpected error during JSON processing: {str(e)}"
                    self.logger.error(
                        "Unexpected JSON processing error",
                        error=error_msg,
                        connection_id=tool_request.connection_id,
                    )
                    raise ValueError(error_msg)

            mcp_arguments = {
                "dsl_content": dsl_content,
                "width": width,
                "height": height,
                "options": options_dict,
                "async_mode": async_mode,
            }

            # 🚨 CRITICAL DIAGNOSTIC: Log exact arguments structure being sent to MCP Server
            self.logger.info(
                "🔍 CRITICAL DIAGNOSTIC: About to send arguments to MCP Server",
                tool="render_ui_mockup",
                connection_id=tool_request.connection_id,
                request_id=getattr(tool_request, "request_id", "unknown"),
                async_mode=async_mode,
                dsl_length=len(dsl_content),
                mcp_arguments_keys=list(mcp_arguments.keys()),
                mcp_arguments_structure={
                    "dsl_content_type": type(mcp_arguments["dsl_content"]),
                    "width_value": mcp_arguments["width"],
                    "width_type": type(mcp_arguments["width"]),
                    "height_value": mcp_arguments["height"],
                    "height_type": type(mcp_arguments["height"]),
                    "options_keys": (
                        list(mcp_arguments["options"].keys())  # type: ignore
                        if isinstance(mcp_arguments["options"], dict)
                        else "not_dict"
                    ),
                    "options_width": (
                        mcp_arguments["options"].get("width")  # type: ignore
                        if isinstance(mcp_arguments["options"], dict)
                        else "no_access"
                    ),
                    "options_height": (
                        mcp_arguments["options"].get("height")  # type: ignore
                        if isinstance(mcp_arguments["options"], dict)
                        else "no_access"
                    ),
                    "async_mode": mcp_arguments["async_mode"],
                },
            )

            # 🚨 ENHANCED MCP CALL DEBUGGING - Pre-call diagnostic logging
            self.logger.info(
                "🔍 MCP CALL DIAGNOSTIC: Pre-call state validation",
                tool="render_ui_mockup",
                connection_id=tool_request.connection_id,
                request_id=getattr(tool_request, "request_id", "unknown"),
                async_mode=async_mode,
                dsl_length=len(dsl_content),
                mcp_server_type=type(self.mcp_server).__name__,
                mcp_arguments_keys=list(mcp_arguments.keys()),
                mcp_arguments_validation={
                    "dsl_content_type": type(mcp_arguments.get("dsl_content")).__name__,
                    "dsl_content_is_none": mcp_arguments.get("dsl_content") is None,
                    "width_type": type(mcp_arguments.get("width")).__name__,
                    "width_value": mcp_arguments.get("width"),
                    "height_type": type(mcp_arguments.get("height")).__name__,
                    "height_value": mcp_arguments.get("height"),
                    "options_type": type(mcp_arguments.get("options")).__name__,
                    "options_is_none": mcp_arguments.get("options") is None,
                    "async_mode_type": type(mcp_arguments.get("async_mode")).__name__,
                    "async_mode_value": mcp_arguments.get("async_mode"),
                },
            )

            # Add timeout to prevent hanging with enhanced error tracking
            import traceback

            mcp_call_start_time = time.time()

            try:
                self.logger.info(
                    "🔍 MCP CALL: Initiating call_tool with timeout",
                    tool="render_ui_mockup",
                    timeout_seconds=60.0,
                    call_start_time=mcp_call_start_time,
                )

                mcp_result = await asyncio.wait_for(
                    self.mcp_server.call_tool("render_ui_mockup", mcp_arguments),
                    timeout=60.0,  # 60 second timeout
                )

                mcp_call_duration = time.time() - mcp_call_start_time

                # 🚨 ENHANCED SUCCESS LOGGING
                self.logger.info(
                    "🔍 MCP CALL SUCCESS: Tool call completed successfully",
                    connection_id=tool_request.connection_id,
                    request_id=getattr(tool_request, "request_id", "unknown"),
                    call_duration=mcp_call_duration,
                    result_type=type(mcp_result).__name__,
                    result_length=len(mcp_result) if hasattr(mcp_result, "__len__") else "no_len",
                    result_first_item_type=(
                        type(mcp_result[0]).__name__ if len(mcp_result) > 0 else "no_first_item"
                    ),
                )

                # Additional result content inspection
                if len(mcp_result) > 0:
                    first_item = mcp_result[0]
                    self.logger.info(
                        "🔍 MCP RESULT ANALYSIS: First item detailed inspection",
                        first_item_type=type(first_item).__name__,
                        first_item_has_text=hasattr(first_item, "text"),
                        first_item_text_type=(
                            type(getattr(first_item, "text", None)).__name__
                            if hasattr(first_item, "text")
                            else "no_text_attr"
                        ),
                        first_item_text_is_none=(
                            getattr(first_item, "text", None) is None
                            if hasattr(first_item, "text")
                            else "no_text_attr"
                        ),
                        first_item_text_length=(
                            len(getattr(first_item, "text", ""))
                            if hasattr(first_item, "text")
                            and getattr(first_item, "text", None) is not None
                            else "no_text_or_none"
                        ),
                        first_item_repr=repr(first_item)[:200],
                    )

            except asyncio.TimeoutError:
                mcp_call_duration = time.time() - mcp_call_start_time
                error_msg = (
                    f"MCP tool call timed out after 60 seconds (actual: {mcp_call_duration:.2f}s)"
                )

                self.logger.error(
                    "🚨 MCP TIMEOUT: Tool call timed out",
                    connection_id=tool_request.connection_id,
                    request_id=getattr(tool_request, "request_id", "unknown"),
                    error=error_msg,
                    call_duration=mcp_call_duration,
                    traceback=traceback.format_exc(),
                )
                raise Exception(error_msg)

            except Exception as mcp_error:
                mcp_call_duration = time.time() - mcp_call_start_time

                # 🚨 ENHANCED ERROR LOGGING for MCP failures
                self.logger.error(
                    "🚨 MCP CALL FAILED: Tool call failed with detailed diagnostics",
                    connection_id=tool_request.connection_id,
                    request_id=getattr(tool_request, "request_id", "unknown"),
                    call_duration=mcp_call_duration,
                    error_type=type(mcp_error).__name__,
                    error_module=getattr(type(mcp_error), "__module__", "unknown"),
                    error_repr=repr(mcp_error)[:500],
                    error_str=str(mcp_error)[:500],
                    error_args=getattr(mcp_error, "args", "no_args"),
                    traceback=traceback.format_exc(),
                    mcp_server_state={
                        "server_type": type(self.mcp_server).__name__,
                        "server_repr": repr(self.mcp_server)[:200],
                    },
                )
                raise

            # Parse MCP result using robust helper
            try:
                result_data = self._parse_mcp_response(mcp_result, "render_ui_mockup")
            except ValueError as e:
                # Log the parsing error and re-raise with more context
                self.logger.error(
                    "Failed to parse render_ui_mockup response",
                    connection_id=tool_request.connection_id,
                    request_id=request_id,
                    error=str(e),
                    raw_result_type=type(mcp_result).__name__,
                    raw_result_length=len(mcp_result) if hasattr(mcp_result, "__len__") else "N/A",
                )
                raise ValueError(f"Failed to parse MCP response: {str(e)}")

            if result_data.get("success"):
                # Send completion event
                completed_event = create_render_completed_event(
                    connection_id=tool_request.connection_id,
                    result=result_data,
                    processing_time=result_data.get("processing_time", 0),
                    request_id=request_id,
                )
                await connection_manager.send_to_connection(
                    tool_request.connection_id, completed_event
                )
                self._increment_events_sent(request_id)

                return result_data
            else:
                # Send failure event
                failed_event = create_render_failed_event(
                    connection_id=tool_request.connection_id,
                    error=result_data.get("error", "Unknown error"),
                    processing_time=result_data.get("processing_time", 0),
                    request_id=request_id,
                )
                await connection_manager.send_to_connection(
                    tool_request.connection_id, failed_event
                )
                self._increment_events_sent(request_id)

                raise ValueError(result_data.get("error", "Rendering failed"))

    async def _execute_validation_tool(
        self, tool_request: SSEToolRequest, request_id: str
    ) -> Dict[str, Any]:
        """Execute validate_dsl tool."""
        connection_manager = await get_sse_connection_manager()

        # Send progress update
        await self._send_progress_update(
            tool_request.connection_id,
            request_id,
            "validation",
            50,
            "Validating DSL syntax",
            "validation",
        )

        # Use MCP server's tool execution
        mcp_result = await self.mcp_server.call_tool("validate_dsl", tool_request.arguments)

        # Parse MCP result using robust helper
        try:
            result_data = self._parse_mcp_response(mcp_result, "validate_dsl")
        except ValueError as e:
            # Log the parsing error and re-raise with more context
            self.logger.error(
                "Failed to parse validate_dsl response",
                connection_id=tool_request.connection_id,
                request_id=request_id,
                error=str(e),
                raw_result_type=type(mcp_result).__name__,
                raw_result_length=len(mcp_result) if hasattr(mcp_result, "__len__") else "N/A",
            )
            raise ValueError(f"Failed to parse MCP response: {str(e)}")

        # Send validation completed event
        validation_event = create_validation_completed_event(
            connection_id=tool_request.connection_id,
            valid=result_data.get("valid", False),
            errors=result_data.get("errors", []),
            warnings=result_data.get("warnings", []),
            suggestions=result_data.get("suggestions", []),
            request_id=request_id,
        )
        await connection_manager.send_to_connection(tool_request.connection_id, validation_event)
        self._increment_events_sent(request_id)

        return result_data

    async def _execute_status_tool(
        self, tool_request: SSEToolRequest, request_id: str
    ) -> Dict[str, Any]:
        """Execute get_render_status tool."""
        # Use MCP server's tool execution
        mcp_result = await self.mcp_server.call_tool("get_render_status", tool_request.arguments)

        # Parse MCP result using robust helper
        try:
            result_data = self._parse_mcp_response(mcp_result, "get_render_status")
        except ValueError as e:
            # Log the parsing error and re-raise with more context
            self.logger.error(
                "Failed to parse get_render_status response",
                request_id=request_id,
                error=str(e),
                raw_result_type=type(mcp_result).__name__,
                raw_result_length=len(mcp_result) if hasattr(mcp_result, "__len__") else "N/A",
            )
            raise ValueError(f"Failed to parse MCP response: {str(e)}")

        return result_data

    async def _monitor_async_task(self, task_id: str, connection_id: str, request_id: str) -> None:
        """Monitor async task progress and send updates via SSE."""
        try:
            connection_manager = await get_sse_connection_manager()

            while True:
                # Check task status
                task_data = await TaskTracker.get_task_status(task_id)

                if not task_data:
                    await asyncio.sleep(2)
                    continue

                status = task_data.get("status")
                progress = task_data.get("progress", 0)
                message = task_data.get("message", "Processing...")

                # Send progress update
                await self._send_progress_update(
                    connection_id, request_id, "render", progress, message, "rendering"
                )

                # Check if completed or failed
                if status in [TaskStatus.COMPLETED.value, TaskStatus.FAILED.value]:
                    if status == TaskStatus.COMPLETED.value:
                        result = task_data.get("result")
                        # Ensure result is a dict, default to empty dict if None
                        result_dict: Dict[str, Any] = result if isinstance(result, dict) else {}  # type: ignore
                        completed_event = create_render_completed_event(
                            connection_id=connection_id,
                            result=result_dict,
                            processing_time=int(result_dict.get("processing_time", 0)),  # type: ignore
                            request_id=request_id,
                        )
                        await connection_manager.send_to_connection(connection_id, completed_event)
                    else:
                        error_message = task_data.get("message", "Task failed")
                        failed_event = create_render_failed_event(
                            connection_id=connection_id, error=error_message, request_id=request_id
                        )
                        await connection_manager.send_to_connection(connection_id, failed_event)

                    break

                await asyncio.sleep(2)  # Poll every 2 seconds

        except Exception as e:
            self.logger.error(
                "Task monitoring failed", task_id=task_id, request_id=request_id, error=str(e)
            )

    async def _send_progress_update(
        self,
        connection_id: str,
        request_id: str,
        operation: str,
        progress: int,
        message: str,
        stage: Optional[str] = None,
    ) -> None:
        """Send progress update event."""
        try:
            connection_manager = await get_sse_connection_manager()
            progress_event = create_progress_event(
                connection_id=connection_id,
                operation=operation,
                progress=progress,
                message=message,
                stage=stage,
                details={"request_id": request_id},
            )
            await connection_manager.send_to_connection(connection_id, progress_event)
            self._increment_events_sent(request_id)
        except Exception as e:
            self.logger.error("Failed to send progress update", request_id=request_id, error=str(e))

    def _parse_mcp_response(
        self, mcp_result: Any, operation_name: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Parse MCP server response with robust error handling.

        Handles both TextContent format and legacy direct JSON format.

        Args:
            mcp_result: Raw response from MCP server
            operation_name: Name of operation for logging context

        Returns:
            Parsed JSON data as dictionary

        Raises:
            ValueError: If response cannot be parsed
        """
        import traceback

        try:
            # 🚨 ENHANCED MCP RESPONSE PARSING - Comprehensive diagnostic logging
            self.logger.info(
                "🔍 MCP RESPONSE DIAGNOSTIC: Starting response parsing with detailed inspection",
                operation=operation_name,
                result_type=type(mcp_result).__name__,
                result_is_none=mcp_result is None,
                result_is_truthy=bool(mcp_result) if mcp_result is not None else False,
                result_length=len(mcp_result) if hasattr(mcp_result, "__len__") else "N/A",
                result_dir=str(dir(mcp_result))[:300] if mcp_result is not None else "None",
                result_repr=repr(mcp_result)[:300] if mcp_result is not None else "None",
                result_str_preview=str(mcp_result)[:200] if mcp_result else "None",
            )

            # Check if response is empty or None with detailed logging
            if not mcp_result:
                self.logger.error(
                    "🚨 EMPTY MCP RESPONSE: Response is empty or falsy",
                    operation=operation_name,
                    result_is_none=mcp_result is None,
                    result_bool=bool(mcp_result) if mcp_result is not None else "None",
                    result_type=type(mcp_result).__name__,
                )
                raise ValueError(f"Empty MCP response for {operation_name}")

            # Check if it's a list (expected format) with enhanced diagnostics
            if not isinstance(mcp_result, list):
                self.logger.error(
                    "🚨 INVALID RESPONSE TYPE: Expected list, got different type",
                    operation=operation_name,
                    actual_type=type(mcp_result).__name__,
                    result_repr=repr(mcp_result)[:200],
                    result_str=str(mcp_result)[:200],
                )
                raise ValueError(
                    f"Expected list response, got {type(mcp_result).__name__} for {operation_name}"
                )

            if len(mcp_result) == 0:  # type: ignore
                self.logger.error(
                    "🚨 EMPTY RESPONSE LIST: List is empty",
                    operation=operation_name,
                    list_length=len(mcp_result),  # type: ignore
                )
                raise ValueError(f"Empty response list for {operation_name}")

            first_item = mcp_result[0]  # type: ignore

            # Enhanced first item inspection
            self.logger.info(
                "🔍 FIRST ITEM DIAGNOSTIC: Detailed first item analysis",
                operation=operation_name,
                first_item_type=type(first_item).__name__,  # type: ignore
                first_item_repr=repr(first_item)[:300],  # type: ignore
                first_item_str=str(first_item)[:300],  # type: ignore
                first_item_has_text=hasattr(first_item, "text"),  # type: ignore
                first_item_dir=str(dir(first_item))[:300],  # type: ignore
                first_item_is_dict=isinstance(first_item, dict),
            )

            # Handle TextContent format (standard MCP protocol) with enhanced diagnostics
            if hasattr(first_item, "text"):  # type: ignore
                result_text = getattr(
                    first_item, "text", None  # type: ignore
                )  # Safe attribute access

                self.logger.info(
                    "🔍 TEXT CONTENT DIAGNOSTIC: Extracting JSON from TextContent",
                    operation=operation_name,
                    text_type=type(result_text).__name__,
                    text_is_none=result_text is None,
                    text_is_str=isinstance(result_text, str),
                    text_length=(
                        len(result_text)
                        if result_text and hasattr(result_text, "__len__")
                        else "N/A"
                    ),
                    text_preview=str(result_text)[:200] if result_text else "None",
                    text_repr=repr(result_text)[:200] if result_text else "None",
                )

                # Validate that text field is not empty
                if not result_text:
                    self.logger.error(
                        "🚨 EMPTY TEXT FIELD: TextContent.text is empty or None",
                        operation=operation_name,
                        text_value=result_text,
                        text_type=type(result_text).__name__,
                    )
                    raise ValueError(f"Empty text field in TextContent for {operation_name}")

                if not isinstance(result_text, str):
                    self.logger.error(
                        "🚨 INVALID TEXT TYPE: TextContent.text is not a string",
                        operation=operation_name,
                        text_type=type(result_text).__name__,
                        text_value=result_text,
                    )
                    raise ValueError(
                        f"TextContent.text is not a string: {type(result_text).__name__} for {operation_name}"  # type: ignore
                    )

                # Try to parse as JSON with detailed error handling
                try:
                    self.logger.info(
                        "🔍 JSON PARSING: Attempting JSON parse",
                        operation=operation_name,
                        text_length=len(result_text),
                        text_first_100=result_text[:100],
                    )

                    result_data = json.loads(result_text)

                    self.logger.info(
                        "🔍 JSON PARSE SUCCESS: Successfully parsed JSON from TextContent",
                        operation=operation_name,
                        result_data_type=type(result_data).__name__,
                        result_data_is_dict=isinstance(result_data, dict),
                        result_keys=(
                            list(result_data.keys())[:10]  # First 10 keys  # type: ignore
                            if isinstance(result_data, dict)
                            else "not_dict"
                        ),
                        result_data_length=(
                            len(result_data) if hasattr(result_data, "__len__") else "N/A"  # type: ignore
                        ),
                    )
                    return result_data  # type: ignore

                except json.JSONDecodeError as json_error:
                    self.logger.error(
                        "🚨 JSON DECODE ERROR: Failed to parse JSON from TextContent",
                        operation=operation_name,
                        json_error_type=type(json_error).__name__,
                        json_error_msg=str(json_error),
                        json_error_pos=getattr(json_error, "pos", "unknown"),
                        json_error_lineno=getattr(json_error, "lineno", "unknown"),
                        json_error_colno=getattr(json_error, "colno", "unknown"),
                        text_content_sample=result_text[:500],  # More content for debugging
                        text_around_error=(
                            result_text[
                                max(0, getattr(json_error, "pos", 0) - 50) : getattr(
                                    json_error, "pos", 0
                                )
                                + 50
                            ]
                            if hasattr(json_error, "pos")
                            and isinstance(getattr(json_error, "pos"), int)
                            else "position_unknown"
                        ),
                    )
                    raise ValueError(
                        f"Invalid JSON in TextContent.text for {operation_name}: {str(json_error)}"
                    )
                except Exception as parse_error:
                    self.logger.error(
                        "🚨 UNEXPECTED PARSE ERROR: Unexpected error during JSON parsing",
                        operation=operation_name,
                        parse_error_type=type(parse_error).__name__,
                        parse_error_msg=str(parse_error),
                        text_content_sample=result_text[:500],
                        traceback=traceback.format_exc(),
                    )
                    raise ValueError(
                        f"Unexpected error parsing JSON for {operation_name}: {str(parse_error)}"
                    )

            # Handle legacy direct format (fallback) with enhanced diagnostics
            else:
                self.logger.info(
                    "🔍 LEGACY FORMAT DIAGNOSTIC: Handling legacy direct response format",
                    operation=operation_name,
                    item_type=type(first_item).__name__,  # type: ignore
                    item_is_dict=isinstance(first_item, dict),
                    item_content_preview=str(first_item)[:200],  # type: ignore
                    item_repr=repr(first_item)[:200],  # type: ignore
                )

                # If it's already a dict, return it
                if isinstance(first_item, dict):
                    self.logger.info(
                        "🔍 LEGACY DICT SUCCESS: Found dictionary, returning directly",
                        operation=operation_name,
                        dict_keys=list(first_item.keys())[:10],  # First 10 keys  # type: ignore
                        dict_length=len(first_item),  # type: ignore
                    )
                    return first_item  # type: ignore

                # Try to convert to string and parse as JSON
                try:
                    result_text = str(first_item)  # type: ignore

                    self.logger.info(
                        "🔍 LEGACY STR CONVERSION: Converting to string for JSON parse",
                        operation=operation_name,
                        str_result_type=type(result_text).__name__,
                        str_result_length=len(result_text),
                        str_result_preview=result_text[:200],
                    )

                    if not result_text or result_text == "None":
                        self.logger.error(
                            "🚨 INVALID STRING CONVERSION: Cannot convert to valid JSON string",
                            operation=operation_name,
                            result_text=result_text,
                            original_item_type=type(first_item).__name__,  # type: ignore
                            original_item_repr=repr(first_item)[:200],  # type: ignore
                        )
                        raise ValueError(
                            f"Cannot convert response to valid JSON string for {operation_name}"
                        )

                    result_data = json.loads(result_text)

                    self.logger.info(
                        "🔍 LEGACY JSON SUCCESS: Successfully parsed JSON from legacy format",
                        operation=operation_name,
                        result_data_type=type(result_data).__name__,
                        result_keys=(
                            list(result_data.keys())[:10]  # First 10 keys  # type: ignore
                            if isinstance(result_data, dict)
                            else "not_dict"
                        ),
                    )
                    return result_data  # type: ignore

                except json.JSONDecodeError as json_error:
                    # Use simple fallback for result_text
                    safe_result_text = "conversion_failed"
                    try:
                        safe_result_text = str(first_item)[:500]  # type: ignore
                    except Exception:
                        safe_result_text = "string_conversion_error"

                    self.logger.error(
                        "🚨 LEGACY JSON ERROR: Failed to parse JSON from legacy format",
                        operation=operation_name,
                        json_error_type=type(json_error).__name__,
                        json_error_msg=str(json_error),
                        text_content_sample=safe_result_text,
                        original_item_type="unknown",
                    )
                    raise ValueError(
                        f"Invalid JSON in legacy response format for {operation_name}: {str(json_error)}"
                    )

        except Exception as e:
            # 🚨 COMPREHENSIVE ERROR LOGGING for parsing failures
            self.logger.error(
                "🚨 MCP RESPONSE PARSING FAILED: Complete parsing failure with full diagnostics",
                operation=operation_name,
                error_type=type(e).__name__,
                error_module=getattr(type(e), "__module__", "unknown"),
                error_msg=str(e),
                error_repr=repr(e),
                error_args=getattr(e, "args", "no_args"),
                raw_response_type=type(mcp_result).__name__ if mcp_result is not None else "None",  # type: ignore
                raw_response_debug=str(mcp_result)[:1000] if mcp_result else "None",  # type: ignore
                raw_response_repr=repr(mcp_result)[:1000] if mcp_result else "None",  # type: ignore
                traceback=traceback.format_exc(),
            )
            raise

    def _increment_events_sent(self, request_id: str) -> None:
        """Increment events sent counter for request."""
        if request_id in self._active_requests:
            self._active_requests[request_id]["events_sent"] = (
                self._active_requests[request_id].get("events_sent", 0) + 1
            )

    async def cancel_tool_execution(self, request_id: str) -> bool:
        """
        Cancel active tool execution.

        Args:
            request_id: Request ID to cancel

        Returns:
            True if cancelled successfully
        """
        if request_id in self._active_requests:
            request_info = self._active_requests[request_id]

            # If it's an async task, try to cancel it
            if "task_id" in request_info:
                from src.core.queue.tasks import cancel_task

                success = await cancel_task(request_info["task_id"])

                if success:
                    # Send cancellation event
                    try:
                        connection_manager = await get_sse_connection_manager()
                        error_event = create_error_event(
                            connection_id=request_info["connection_id"],
                            error_code="TOOL_CANCELLED",
                            error_message="Tool execution was cancelled",
                            details={"request_id": request_id},
                        )
                        await connection_manager.send_to_connection(
                            request_info["connection_id"], error_event
                        )
                    except Exception as e:
                        self.logger.error("Failed to send cancellation event", error=str(e))

                return success

            # Mark as cancelled
            request_info["status"] = "cancelled"
            return True

        return False

    def get_active_requests(self) -> Dict[str, Dict[str, Any]]:
        """Get currently active requests."""
        return self._active_requests.copy()


# Global bridge instance
_mcp_bridge: Optional[MCPBridge] = None


def get_mcp_bridge() -> MCPBridge:
    """Get global MCP bridge instance."""
    global _mcp_bridge
    if _mcp_bridge is None:
        _mcp_bridge = MCPBridge()
    return _mcp_bridge
