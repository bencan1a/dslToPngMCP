#!/usr/bin/env python3
"""
SSE Mock Infrastructure Test - Isolation Testing Script

This script tests SSE functionality with mocked Redis/database connections
to simulate the SSE workflow with minimal dependencies and validate if
infrastructure is causing the issue.

Purpose: Determine if infrastructure dependencies are causing the 'NoneType' error
"""

import sys
import os
import asyncio
import json
import logging
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

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


class MockRedis:
    """Mock Redis client that simulates basic Redis operations"""

    def __init__(self):
        self.data = {}
        self.hashes = {}

    async def ping(self):
        """Mock ping method"""
        return True

    async def hset(self, key, field, value):
        """Mock hset method"""
        if key not in self.hashes:
            self.hashes[key] = {}
        self.hashes[key][field] = value
        return 1

    async def hget(self, key, field):
        """Mock hget method"""
        return self.hashes.get(key, {}).get(field)

    async def hkeys(self, key):
        """Mock hkeys method"""
        return list(self.hashes.get(key, {}).keys())

    async def hlen(self, key):
        """Mock hlen method"""
        return len(self.hashes.get(key, {}))

    async def hexists(self, key, field):
        """Mock hexists method"""
        return field in self.hashes.get(key, {})

    async def hdel(self, key, field):
        """Mock hdel method"""
        if key in self.hashes and field in self.hashes[key]:
            del self.hashes[key][field]
            return 1
        return 0

    async def lpush(self, key, value):
        """Mock lpush method"""
        if key not in self.data:
            self.data[key] = []
        self.data[key].insert(0, value)
        return len(self.data[key])

    async def ltrim(self, key, start, stop):
        """Mock ltrim method"""
        if key in self.data:
            self.data[key] = self.data[key][start : stop + 1]
        return True

    async def delete(self, key):
        """Mock delete method"""
        deleted = 0
        if key in self.data:
            del self.data[key]
            deleted += 1
        if key in self.hashes:
            del self.hashes[key]
            deleted += 1
        return deleted

    async def scan(self, cursor=0, match=None, count=100):
        """Mock scan method"""
        # Simple implementation for testing
        keys = list(self.data.keys()) + list(self.hashes.keys())
        if match:
            # Simple pattern matching
            pattern = match.replace("*", "")
            keys = [k for k in keys if pattern in k]
        return (0, keys)  # cursor=0 means scan complete


class MockSSEConnectionManager:
    """Mock SSE Connection Manager that simulates connection operations"""

    def __init__(self):
        self.connections = {}
        self.redis = MockRedis()
        self.logger = logger.bind(component="mock_sse_manager")

    async def create_connection(self, request=None, client_id=None, last_event_id=None):
        """Mock create connection"""
        import uuid

        connection_id = str(uuid.uuid4())
        self.connections[connection_id] = {
            "client_id": client_id,
            "created_at": "2023-01-01T12:00:00Z",
            "status": "connected",
        }
        self.logger.info(f"Mock connection created: {connection_id}")
        return connection_id

    async def send_to_connection(self, connection_id, event):
        """Mock send to connection"""
        if connection_id in self.connections:
            self.logger.info(
                f"Mock event sent to {connection_id}: {event.event_type if hasattr(event, 'event_type') else 'unknown'}"
            )
            return True
        return False

    async def close_connection(self, connection_id, reason="test"):
        """Mock close connection"""
        if connection_id in self.connections:
            del self.connections[connection_id]
            self.logger.info(f"Mock connection closed: {connection_id}")

    async def get_connection_count(self):
        """Mock get connection count"""
        return len(self.connections)


class MockMCPServer:
    """Mock MCP Server that simulates successful tool calls"""

    def __init__(self):
        self.logger = logger.bind(component="mock_mcp_server")

    async def call_tool(self, tool_name, arguments):
        """Mock tool call that returns successful results"""
        self.logger.info(f"Mock MCP tool called: {tool_name}")

        if tool_name == "render_ui_mockup":
            # Simulate successful rendering
            result = {
                "success": True,
                "png_result": {
                    "base64_data": "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
                    "width": 400,
                    "height": 200,
                    "file_size": 1024,
                    "metadata": {"generator": "mock", "test": True},
                },
                "message": "Mock rendering completed successfully",
            }

            # Return in the format expected by MCP
            from mcp.types import TextContent

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        elif tool_name == "validate_dsl":
            result = {"valid": True, "errors": [], "warnings": [], "suggestions": []}
            from mcp.types import TextContent

            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        else:
            raise ValueError(f"Unknown tool: {tool_name}")


async def test_sse_with_mock_redis():
    """Test SSE connection manager with mock Redis"""
    print("\n" + "=" * 60)
    print("TESTING: SSE Connection Manager with Mock Redis")
    print("=" * 60)

    try:
        # Mock Redis client
        mock_redis = MockRedis()

        # Test Redis operations
        logger.info("Testing mock Redis operations...")
        await mock_redis.hset("test_connections", "conn1", json.dumps({"status": "connected"}))
        result = await mock_redis.hget("test_connections", "conn1")
        logger.info(f"✓ Mock Redis hset/hget: {result is not None}")

        # Test with real SSE Connection Manager but mocked Redis
        with patch("src.config.database.get_redis_client", return_value=mock_redis):
            from src.api.sse.connection_manager import SSEConnectionManager

            logger.info("Creating SSE Connection Manager with mock Redis...")
            manager = SSEConnectionManager()

            # Test creating a connection
            mock_request = Mock()
            mock_request.client.host = "127.0.0.1"
            mock_request.headers = {"user-agent": "test"}

            connection_id = await manager.create_connection(mock_request)
            logger.info(f"✓ Mock connection created: {connection_id}")

            # Test sending events
            from src.api.sse.events import SSEEvent, SSEEventType

            test_event = SSEEvent(
                event_type=SSEEventType.RENDER_START,
                data={"message": "test"},
                connection_id=connection_id,
            )

            success = await manager.send_to_connection(connection_id, test_event)
            logger.info(f"✓ Mock event sent: {success}")

            return manager

    except Exception as e:
        logger.error(f"❌ Error in mock Redis test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_sse_with_mock_mcp():
    """Test SSE MCP Bridge with mock MCP server"""
    print("\n" + "=" * 60)
    print("TESTING: SSE MCP Bridge with Mock MCP Server")
    print("=" * 60)

    try:
        # Create mock MCP server
        mock_mcp_server = MockMCPServer()

        # Test mock MCP server directly
        logger.info("Testing mock MCP server...")
        arguments = {
            "dsl_content": json.dumps(SIMPLE_BUTTON_DSL),
            "options": {"width": 400, "height": 200, "device_scale_factor": 1.0},
            "async_mode": False,
        }

        result = await mock_mcp_server.call_tool("render_ui_mockup", arguments)
        logger.info(f"✓ Mock MCP tool result: {type(result)}")

        if result is None:
            logger.error("❌ Mock MCP server returned None - Issue not in MCP layer!")
            return None

        # Test with real MCP Bridge but mocked MCP server
        with patch("src.mcp_server.server.DSLToPNGMCPServer", return_value=mock_mcp_server):
            from src.api.sse.mcp_bridge import MCPBridge
            from src.api.sse.models import SSEToolRequest

            logger.info("Creating MCP Bridge with mock MCP server...")
            bridge = MCPBridge()
            bridge.mcp_server = mock_mcp_server  # Replace with mock

            # Create tool request
            tool_request = SSEToolRequest(
                tool_name="render_ui_mockup",
                arguments=arguments,
                connection_id="mock_conn_123",
                request_id="mock_req_123",
            )

            logger.info("Testing MCP Bridge execute_tool_with_sse with mock...")

            # Mock the connection manager too
            with patch(
                "src.api.sse.mcp_bridge.get_sse_connection_manager",
                return_value=MockSSEConnectionManager(),
            ):
                bridge_result = await bridge.execute_tool_with_sse(tool_request)

                logger.info(f"✓ MCP Bridge result: {type(bridge_result)}")

                if bridge_result is None:
                    logger.error("❌ MCP Bridge returned None with mocks - Issue in Bridge logic!")
                    return None

                logger.info(
                    f"Bridge success: {getattr(bridge_result, 'success', 'No success field')}"
                )
                return bridge_result

    except Exception as e:
        logger.error(f"❌ Error in mock MCP test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_sse_full_mock_pipeline():
    """Test complete SSE pipeline with all infrastructure mocked"""
    print("\n" + "=" * 60)
    print("TESTING: Complete SSE Pipeline with Mock Infrastructure")
    print("=" * 60)

    try:
        # Mock all infrastructure dependencies
        mock_redis = MockRedis()
        mock_mcp_server = MockMCPServer()
        mock_connection_manager = MockSSEConnectionManager()

        logger.info("Setting up full mock infrastructure...")

        # Test the complete workflow
        with (
            patch.multiple(
                "src.api.sse.mcp_bridge",
                get_sse_connection_manager=AsyncMock(return_value=mock_connection_manager),
            ),
            patch("src.mcp_server.server.DSLToPNGMCPServer", return_value=mock_mcp_server),
            patch("src.config.database.get_redis_client", return_value=mock_redis),
        ):

            from src.api.sse.mcp_bridge import MCPBridge
            from src.api.sse.models import SSEToolRequest

            logger.info("Creating fully mocked SSE pipeline...")

            # Create bridge with mocked dependencies
            bridge = MCPBridge()
            bridge.mcp_server = mock_mcp_server

            # Create tool request
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
                connection_id="full_mock_conn",
                request_id="full_mock_req",
            )

            logger.info("Executing full mock SSE pipeline...")
            result = await bridge.execute_tool_with_sse(tool_request)

            logger.info(f"✓ Full mock pipeline result: {type(result)}")

            if result is None:
                logger.error("❌ Full mock pipeline returned None - Issue in SSE Bridge logic!")
                return None

            logger.info(f"Full mock success: {getattr(result, 'success', 'No success field')}")
            logger.info(f"Full mock tool: {getattr(result, 'tool_name', 'No tool_name field')}")

            # Test the result structure
            if hasattr(result, "result") and result.result:
                logger.info(f"Result data type: {type(result.result)}")
                if isinstance(result.result, dict):
                    logger.info(f"Result keys: {list(result.result.keys())}")
                    if result.result.get("success"):
                        logger.info("✓ Full mock pipeline reports success")
                    else:
                        logger.warning(
                            f"⚠ Full mock pipeline reports failure: {result.result.get('error')}"
                        )

            return result

    except Exception as e:
        logger.error(f"❌ Error in full mock pipeline test: {e}")
        logger.exception("Full traceback:")
        return None


async def test_infrastructure_component_isolation():
    """Test individual infrastructure components in isolation"""
    print("\n" + "=" * 60)
    print("TESTING: Infrastructure Component Isolation")
    print("=" * 60)

    try:
        # Test 1: Database/Redis isolation
        logger.info("Testing database/Redis isolation...")

        mock_redis = MockRedis()

        # Test basic Redis operations
        await mock_redis.ping()
        await mock_redis.hset("test", "field", "value")
        value = await mock_redis.hget("test", "field")

        if value != "value":
            logger.error("❌ Mock Redis basic operations failed")
            return None

        logger.info("✓ Mock Redis operations successful")

        # Test 2: Settings/Config isolation
        logger.info("Testing settings/config isolation...")

        try:
            from src.config.settings import get_settings

            settings = get_settings()
            logger.info(f"✓ Settings loaded: {type(settings)}")
        except Exception as settings_error:
            logger.error(f"❌ Settings loading failed: {settings_error}")
            return None

        # Test 3: Logging isolation
        logger.info("Testing logging isolation...")

        try:
            from src.config.logging import get_logger

            test_logger = get_logger("infrastructure_test")
            test_logger.info("Test log message")
            logger.info("✓ Logging system functional")
        except Exception as logging_error:
            logger.error(f"❌ Logging system failed: {logging_error}")
            return None

        return {"redis": "functional", "settings": "functional", "logging": "functional"}

    except Exception as e:
        logger.error(f"❌ Error in infrastructure isolation test: {e}")
        logger.exception("Full traceback:")
        return None


async def main():
    """Run all mock infrastructure tests"""
    print("🔍 SSE MOCK INFRASTRUCTURE ISOLATION TESTS")
    print("Purpose: Test SSE functionality with mocked infrastructure dependencies")
    print("Goal: Determine if infrastructure is causing the 'NoneType' error")

    results = {}

    # Test 1: Infrastructure Component Isolation
    results["infrastructure_isolation"] = await test_infrastructure_component_isolation()

    # Test 2: SSE with Mock Redis
    results["sse_mock_redis"] = await test_sse_with_mock_redis()

    # Test 3: SSE with Mock MCP
    results["sse_mock_mcp"] = await test_sse_with_mock_mcp()

    # Test 4: Full Mock Pipeline
    results["full_mock_pipeline"] = await test_sse_full_mock_pipeline()

    # Summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    for test_name, result in results.items():
        status = "✓ PASS" if result is not None and result is not False else "❌ FAIL"
        print(f"{test_name:25} {status}")

        if result is None:
            print(f"  → {test_name} returned None (potential NoneType source)")
        elif result is False:
            print(f"  → {test_name} failed to execute")

    # Analysis
    print("\n" + "=" * 60)
    print("INFRASTRUCTURE ANALYSIS")
    print("=" * 60)

    if results["infrastructure_isolation"] is None:
        print("🎯 ISSUE FOUND: Basic infrastructure components failed")
        print("   The NoneType error is in fundamental infrastructure (Redis, settings, logging)")
    elif results["sse_mock_redis"] is None:
        print("🎯 ISSUE FOUND: SSE with mock Redis failed")
        print("   The NoneType error is related to Redis connectivity or SSE-Redis interaction")
    elif results["sse_mock_mcp"] is None:
        print("🎯 ISSUE FOUND: SSE with mock MCP failed")
        print("   The NoneType error is in MCP-SSE interaction logic")
    elif results["full_mock_pipeline"] is None:
        print("🎯 ISSUE FOUND: Full mock pipeline failed")
        print("   The NoneType error is in the SSE pipeline logic itself")
    else:
        print("✓ All infrastructure components work with mocks")
        print("  The NoneType error is likely in:")
        print("  1. Real infrastructure dependencies (actual Redis, PostgreSQL)")
        print("  2. Browser dependencies (Playwright, browser pool)")
        print("  3. Network/connectivity issues")
        print("  4. Environment configuration problems")

        # Additional analysis
        mock_pipeline_result = results["full_mock_pipeline"]
        if hasattr(mock_pipeline_result, "success") and mock_pipeline_result.success:
            print("  → Mock pipeline succeeded completely")
            print("  → Issue is definitely in real infrastructure dependencies")
        else:
            print("  → Mock pipeline had internal issues")
            print("  → Issue may be in SSE logic even with mocks")


if __name__ == "__main__":
    asyncio.run(main())
