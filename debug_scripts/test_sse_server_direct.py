#!/usr/bin/env python3
"""
Direct SSE Server Test - Isolation Testing Script

This script tests the SSE server components directly, bypassing FastAPI routing
and HTTP infrastructure to isolate the core SSE rendering logic.

Purpose: Determine if the 'NoneType' error is in SSE server core logic
"""

import sys
import os
import asyncio
import json
import logging
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# Configure logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test data - exact simple_button.json content
SIMPLE_BUTTON_DSL = {
    "title": "Simple Button Example",
    "description": "A basic button demonstration",
    "width": 400,
    "height": 200,
    "elements": [
        {
            "type": "button",
            "id": "primary-btn",
            "layout": {"x": 150, "y": 80, "width": 100, "height": 40},
            "style": {
                "background": "#007bff",
                "color": "white",
                "fontSize": 16,
                "fontWeight": "bold",
                "borderRadius": "8px",
            },
            "label": "Click Me!",
            "onClick": "handleClick()",
        }
    ],
    "css": ".dsl-button:hover { transform: scale(1.05); transition: transform 0.2s; }",
}


async def test_sse_mcp_bridge_direct():
    """Test the MCP bridge functionality directly without HTTP layer"""
    print("\n" + "=" * 60)
    print("TESTING: SSE MCP Bridge Direct Call")
    print("=" * 60)

    try:
        from src.api.sse.mcp_bridge import MCPBridge

        logger.info("Initializing MCP Bridge...")
        bridge = MCPBridge()

        logger.info("✓ MCP Bridge initialized successfully")
        logger.info(f"Bridge type: {type(bridge)}")
        logger.info(f"MCP Server type: {type(bridge.mcp_server)}")

        # Test the render_ui_mockup call directly
        logger.info("Testing render_ui_mockup with simple_button.json...")

        # Prepare arguments as they would come from SSE
        arguments = {
            "dsl_content": json.dumps(SIMPLE_BUTTON_DSL),
            "options": {
                "width": 400,
                "height": 200,
                "device_scale_factor": 1.0,
                "wait_for_load": True,
                "optimize_png": True,
                "transparent_background": False,
            },
            "async_mode": False,
        }

        logger.info(f"Calling MCP server directly with arguments: {list(arguments.keys())}")

        # Call the MCP server's call_tool method directly
        result = await bridge.mcp_server.call_tool("render_ui_mockup", arguments)

        logger.info(f"✓ MCP tool call result type: {type(result)}")
        logger.info(f"Result is None: {result is None}")

        if result is None:
            logger.error("❌ Result is None - FOUND NONETYPE SOURCE!")
            return None

        logger.info(f"Result length: {len(result) if hasattr(result, '__len__') else 'No len'}")

        if hasattr(result, "__len__") and len(result) > 0:
            first_item = result[0]
            logger.info(f"First item type: {type(first_item)}")
            logger.info(f"First item has text: {hasattr(first_item, 'text')}")

            if hasattr(first_item, "text"):
                text_content = first_item.text
                logger.info(f"Text content length: {len(text_content)}")
                logger.info(f"Text content preview: {text_content[:200]}...")

                # Try to parse the JSON
                try:
                    parsed_result = json.loads(text_content)
                    logger.info("✓ JSON parsing successful")
                    logger.info(f"Parsed result keys: {list(parsed_result.keys())}")
                    logger.info(f"Success field: {parsed_result.get('success')}")
                    return parsed_result
                except json.JSONDecodeError as e:
                    logger.error(f"❌ JSON parsing failed: {e}")
                    logger.error(f"Raw text content: {text_content}")
                    return None
            else:
                logger.info(f"First item string representation: {str(first_item)[:200]}...")
        else:
            logger.error("❌ Result list is empty")

        return result

    except Exception as e:
        logger.error(f"❌ Error in MCP Bridge direct test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_sse_connection_manager_direct():
    """Test the connection manager without actual WebSocket connections"""
    print("\n" + "=" * 60)
    print("TESTING: SSE Connection Manager Direct")
    print("=" * 60)

    try:
        from unittest.mock import Mock, patch
        from src.api.sse.connection_manager import SSEConnectionManager

        # Mock Redis to avoid "Redis not initialized" error
        logger.info("Mocking Redis for true isolation testing...")
        mock_redis = Mock()

        # Redis methods need to return async coroutines
        async def mock_ping():
            return True

        async def mock_hset(*args):
            return True

        async def mock_hget(*args):
            # Return valid JSON connection data for testing
            return json.dumps(
                {
                    "metadata": {
                        "connection_id": "test_conn",
                        "client_ip": "127.0.0.1",
                        "user_agent": "test",
                        "status": "connected",
                        "connected_at": "2023-01-01T00:00:00",
                        "last_heartbeat": "2023-01-01T00:00:00",
                        "metadata": {},
                    },
                    "last_activity": 1640995200.0,
                    "worker_pid": 1,
                }
            )

        async def mock_hdel(*args):
            return True

        async def mock_hlen(*args):
            return 0

        async def mock_hkeys(*args):
            return []

        async def mock_hexists(*args):
            return True

        async def mock_delete(*args):
            return True

        async def mock_aclose():
            return None

        mock_redis.ping = mock_ping
        mock_redis.hset = mock_hset
        mock_redis.hget = mock_hget
        mock_redis.hdel = mock_hdel
        mock_redis.hlen = mock_hlen
        mock_redis.hkeys = mock_hkeys
        mock_redis.hexists = mock_hexists
        mock_redis.delete = mock_delete
        mock_redis.aclose = mock_aclose

        with (
            patch("src.api.sse.connection_manager.get_redis_client", return_value=mock_redis),
            patch.object(SSEConnectionManager, "_start_background_tasks"),
        ):
            logger.info(
                "Creating SSE Connection Manager with mocked Redis and disabled background tasks..."
            )
            manager = SSEConnectionManager()

            logger.info("✓ Connection Manager created successfully")
            logger.info(f"Manager type: {type(manager)}")

            # Test if manager has expected methods
            expected_methods = [
                "create_connection",
                "close_connection",
                "send_to_connection",
                "get_connection_stream",
            ]
            for method in expected_methods:
                if hasattr(manager, method):
                    logger.info(f"✓ Method {method} exists")
                else:
                    logger.warning(f"⚠ Method {method} missing")

            # Test Redis connection (mocked)
            logger.info("Testing mocked Redis connection...")
            try:
                redis_info = await manager.redis.ping()
                logger.info(f"✓ Mocked Redis connection successful: {redis_info}")
            except Exception as redis_error:
                logger.error(f"❌ Mocked Redis connection failed: {redis_error}")

            return manager

    except Exception as e:
        logger.error(f"❌ Error in Connection Manager direct test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_sse_event_processing():
    """Test SSE event processing logic directly"""
    print("\n" + "=" * 60)
    print("TESTING: SSE Event Processing Direct")
    print("=" * 60)

    try:
        # Import SSE events and models
        from src.api.sse.events import SSEEventType
        from src.api.sse.models import SSEToolRequest, SSEToolResponse

        logger.info("Testing SSE event and model creation...")

        # Create a tool request
        tool_request = SSEToolRequest(
            tool_name="render_ui_mockup",
            arguments={
                "dsl_content": json.dumps(SIMPLE_BUTTON_DSL),
                "options": {"width": 400, "height": 200},
            },
            connection_id="test_conn",
            request_id="test_req_123",
        )

        logger.info(f"✓ Created SSEToolRequest: {type(tool_request)}")
        logger.info(f"Tool name: {tool_request.tool_name}")
        logger.info(f"Connection ID: {tool_request.connection_id}")

        # Create SSE response (success)
        sse_response = SSEToolResponse(
            success=True,
            tool_name="render_ui_mockup",
            request_id="test_req_123",
            result={"status": "test"},
            execution_time=1.5,
            error=None,
        )

        logger.info(f"✓ Created SSEToolResponse: {type(sse_response)}")

        # Test serialization
        request_dict = tool_request.dict() if hasattr(tool_request, "dict") else vars(tool_request)
        response_dict = sse_response.dict() if hasattr(sse_response, "dict") else vars(sse_response)

        logger.info(f"✓ Request serialized: {len(str(request_dict))} chars")
        logger.info(f"✓ Response serialized: {len(str(response_dict))} chars")

        return True

    except Exception as e:
        logger.error(f"❌ Error in SSE Event processing test: {e}")
        logger.exception("Full traceback:")
        return False


async def test_mcp_bridge_execute_tool():
    """Test the MCPBridge execute_tool_with_sse method directly"""
    print("\n" + "=" * 60)
    print("TESTING: MCP Bridge Execute Tool Direct")
    print("=" * 60)

    try:
        from unittest.mock import Mock, patch
        from src.api.sse.mcp_bridge import MCPBridge
        from src.api.sse.models import SSEToolRequest

        # Mock Redis for MCP Bridge that might use SSE Connection Manager
        logger.info("Mocking Redis for MCP Bridge test...")
        mock_redis = Mock()

        # Redis methods need to return async coroutines
        async def mock_ping():
            return True

        async def mock_hset(*args):
            return True

        async def mock_hget(*args):
            # Return valid JSON connection data for testing
            return json.dumps(
                {
                    "metadata": {
                        "connection_id": "test_conn_direct",
                        "client_ip": "127.0.0.1",
                        "user_agent": "test",
                        "status": "connected",
                        "connected_at": "2023-01-01T00:00:00",
                        "last_heartbeat": "2023-01-01T00:00:00",
                        "metadata": {},
                    },
                    "last_activity": 1640995200.0,
                    "worker_pid": 1,
                }
            )

        async def mock_hdel(*args):
            return True

        async def mock_hlen(*args):
            return 0

        async def mock_hkeys(*args):
            return []

        async def mock_hexists(*args):
            return True

        async def mock_delete(*args):
            return True

        async def mock_aclose():
            return None

        mock_redis.ping = mock_ping
        mock_redis.hset = mock_hset
        mock_redis.hget = mock_hget
        mock_redis.hdel = mock_hdel
        mock_redis.hlen = mock_hlen
        mock_redis.hkeys = mock_hkeys
        mock_redis.hexists = mock_hexists
        mock_redis.delete = mock_delete
        mock_redis.aclose = mock_aclose

        # Also need to mock get_sse_connection_manager which MCP Bridge calls
        mock_connection_manager = Mock()

        # Mock connection manager methods that MCP Bridge uses
        async def mock_send_to_connection(*args):
            return True

        mock_connection_manager.send_to_connection = mock_send_to_connection

        async def mock_get_connection_manager():
            return mock_connection_manager

        with (
            patch("src.api.sse.connection_manager.get_redis_client", return_value=mock_redis),
            patch(
                "src.api.sse.mcp_bridge.get_sse_connection_manager",
                side_effect=mock_get_connection_manager,
            ),
        ):
            logger.info("Creating MCP Bridge and tool request...")
            bridge = MCPBridge()

            # Create a proper SSE tool request
            tool_request = SSEToolRequest(
                tool_name="render_ui_mockup",
                arguments={
                    "dsl_content": json.dumps(SIMPLE_BUTTON_DSL),
                    "options": {
                        "width": 400,
                        "height": 200,
                        "device_scale_factor": 1.0,
                        "wait_for_load": True,
                        "optimize_png": True,
                        "transparent_background": False,
                    },
                    "async_mode": False,
                },
                connection_id="test_conn_direct",
                request_id="test_req_direct_123",
            )

            logger.info(
                "Executing tool via MCP Bridge (this will test SSE connection manager too)..."
            )

            # This will test the full SSE flow but without HTTP
            result = await bridge.execute_tool_with_sse(tool_request)

            logger.info(f"✓ Execute tool result type: {type(result)}")

            if result is None:
                logger.error("❌ Execute tool returned None - FOUND NONETYPE SOURCE!")
                return None

            logger.info(f"Success: {getattr(result, 'success', 'No success field')}")
            logger.info(f"Tool name: {getattr(result, 'tool_name', 'No tool_name field')}")
            logger.info(f"Request ID: {getattr(result, 'request_id', 'No request_id field')}")

            if hasattr(result, "result") and result.result:
                logger.info(
                    f"Result data keys: {list(result.result.keys()) if isinstance(result.result, dict) else 'Not a dict'}"
                )

            return result

    except Exception as e:
        logger.error(f"❌ Error in MCP Bridge execute tool test: {e}")
        logger.exception("Full traceback:")
        return None


async def main():
    """Run all direct SSE server tests"""
    print("🔍 DIRECT SSE SERVER ISOLATION TESTS")
    print("Purpose: Test SSE server components without FastAPI/HTTP layer")
    print("Goal: Isolate the source of 'NoneType' errors")

    results = {}

    # Test 1: Connection Manager Direct
    results["connection_manager"] = await test_sse_connection_manager_direct()

    # Test 2: Event Processing
    results["event_processing"] = await test_sse_event_processing()

    # Test 3: MCP Bridge Direct (simpler test)
    results["mcp_bridge"] = await test_sse_mcp_bridge_direct()

    # Test 4: MCP Bridge Execute Tool (full SSE flow)
    results["mcp_bridge_execute"] = await test_mcp_bridge_execute_tool()

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✓ PASS" if result is not None and result is not False else "❌ FAIL"
        print(f"{test_name:20} {status}")

        if result is None:
            print(f"  → {test_name} returned None (potential NoneType source)")
        elif result is False:
            print(f"  → {test_name} failed to execute")

    # Analysis
    print("\n" + "=" * 60)
    print("ANALYSIS")
    print("=" * 60)

    if results["mcp_bridge"] is None:
        print("🎯 POTENTIAL ISSUE FOUND: MCP Bridge returns None")
        print("   This suggests the NoneType error originates in the MCP server layer")
    elif results["mcp_bridge_execute"] is None:
        print("🎯 POTENTIAL ISSUE FOUND: MCP Bridge execute_tool_with_sse returns None")
        print("   This suggests issues in the SSE execution flow")
    elif results["connection_manager"] is None:
        print("🎯 POTENTIAL ISSUE FOUND: Connection Manager failed")
        print("   This suggests infrastructure dependency issues")
    elif results["event_processing"] is False:
        print("🎯 POTENTIAL ISSUE FOUND: Event Processing failed")
        print("   This suggests issues with SSE event handling models")
    else:
        print("✓ All SSE server components passed direct testing")
        print("  The NoneType error may be in HTTP/infrastructure layer")


if __name__ == "__main__":
    asyncio.run(main())
