"""
SSE Test Fixtures
=================

Specialized fixtures for Server-Sent Events testing.
Provides SSE clients, connection managers, and test utilities.
"""

import asyncio
import pytest
import pytest_asyncio
import uuid
import json
import time
from typing import Dict, Any, List, Optional, AsyncGenerator, Callable
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from src.api.sse.models import (
    SSEConnectionMetadata,
    SSEEventPayload,
    SSEToolRequest,
    SSEToolResponse,
    SSEProgressUpdate,
    SSEHeartbeat,
    SSEError,
    SSEConnectionStatus,
)
from src.api.sse.events import (
    SSEEventType,
    SSEEvent,
    create_connection_opened_event,
    create_heartbeat_event,
    create_progress_event,
    create_tool_call_event,
    create_tool_response_event,
    create_render_completed_event,
    create_render_failed_event,
)
from src.api.sse.mcp_bridge import MCPBridge, get_mcp_bridge
from src.config.settings import get_settings


class MockSSEClient:
    """Mock SSE client for testing SSE functionality without browser dependencies."""

    def __init__(self, connection_id: str = None, api_key: str = None):
        self.connection_id = connection_id or f"test-conn-{uuid.uuid4().hex[:8]}"
        self.api_key = api_key or "test-api-key"
        self.events: List[Dict[str, Any]] = []
        self.is_connected = False
        self.last_heartbeat = None
        self.request_callbacks: Dict[str, Callable] = {}

    async def connect(self) -> None:
        """Simulate SSE connection."""
        self.is_connected = True
        self.last_heartbeat = datetime.utcnow()

    async def disconnect(self) -> None:
        """Simulate SSE disconnection."""
        self.is_connected = False
        self.events.clear()

    async def add_event(self, event: SSEEvent) -> None:
        """Add an event to the client's event list."""
        self.events.append(
            {
                "type": event.event_type,
                "data": event.data,
                "timestamp": event.timestamp,
                "connection_id": event.connection_id,
            }
        )

        # Trigger callback if waiting for this event
        if event.data.get("request_id") in self.request_callbacks:
            callback = self.request_callbacks.pop(event.data["request_id"])
            await callback(event)

    async def wait_for_event(
        self, event_type: SSEEventType, timeout: float = 5.0, request_id: str = None
    ) -> Dict[str, Any]:
        """Wait for a specific event type."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            for event in self.events:
                if event["type"] == event_type:
                    if request_id is None or event["data"].get("request_id") == request_id:
                        return event
            await asyncio.sleep(0.1)

        raise TimeoutError(f"Event {event_type} not received within {timeout}s")

    async def get_events_by_type(self, event_type: SSEEventType) -> List[Dict[str, Any]]:
        """Get all events of a specific type."""
        return [event for event in self.events if event["type"] == event_type]

    async def clear_events(self) -> None:
        """Clear all collected events."""
        self.events.clear()


class MockSSEConnectionManager:
    """Mock SSE connection manager for testing."""

    def __init__(self):
        self.connections: Dict[str, MockSSEClient] = {}
        self.events_sent: List[SSEEvent] = []

    async def add_connection(self, connection_id: str, metadata: SSEConnectionMetadata) -> None:
        """Add a connection to the manager."""
        client = MockSSEClient(connection_id)
        await client.connect()
        self.connections[connection_id] = client

    async def remove_connection(self, connection_id: str) -> None:
        """Remove a connection from the manager."""
        if connection_id in self.connections:
            await self.connections[connection_id].disconnect()
            del self.connections[connection_id]

    async def send_to_connection(self, connection_id: str, event: SSEEvent) -> None:
        """Send event to specific connection."""
        self.events_sent.append(event)
        if connection_id in self.connections:
            await self.connections[connection_id].add_event(event)

    async def broadcast_event(self, event: SSEEvent) -> None:
        """Broadcast event to all connections."""
        self.events_sent.append(event)
        for client in self.connections.values():
            await client.add_event(event)

    async def get_connection_count(self) -> int:
        """Get number of active connections."""
        return len(self.connections)

    async def get_connection_ids(self) -> List[str]:
        """Get list of connection IDs."""
        return list(self.connections.keys())


@pytest_asyncio.fixture
async def mock_sse_client():
    """Create a mock SSE client for testing."""
    client = MockSSEClient()
    await client.connect()
    yield client
    await client.disconnect()


@pytest_asyncio.fixture
async def mock_sse_connection_manager():
    """Create a mock SSE connection manager."""
    manager = MockSSEConnectionManager()

    # Patch the global connection manager
    with patch("src.api.sse.mcp_bridge.get_sse_connection_manager", return_value=manager):
        yield manager


@pytest.fixture
def sse_connection_metadata():
    """Create sample SSE connection metadata."""
    return SSEConnectionMetadata(
        connection_id=f"test-conn-{uuid.uuid4().hex[:8]}",
        client_ip="127.0.0.1",
        user_agent="Mozilla/5.0 (Test Browser)",
        api_key_hash="test-api-key-hash",
        status=SSEConnectionStatus.CONNECTED,
        connected_at=datetime.utcnow(),
        metadata={"test": True},
    )


@pytest.fixture
def sample_sse_events():
    """Generate sample SSE events for testing."""
    connection_id = "test-conn-123"

    return {
        "connection_opened": create_connection_opened_event(connection_id, {"source": "test"}),
        "heartbeat": create_heartbeat_event(connection_id, 30.0),
        "progress": create_progress_event(connection_id, "render", 50, "Processing DSL", "parsing"),
        "tool_call": create_tool_call_event(
            connection_id, "render_ui_mockup", {"dsl_content": "{}"}, "req-123"
        ),
        "tool_response": create_tool_response_event(
            connection_id, "render_ui_mockup", True, {"success": True}, None, 2.5, "req-123"
        ),
        "render_completed": create_render_completed_event(
            connection_id, {"base64Data": "test"}, 3.0, "req-123"
        ),
        "render_failed": create_render_failed_event(
            connection_id, "Test error", "TEST_ERROR", 1.5, "req-123"
        ),
    }


@pytest.fixture
def sse_tool_requests():
    """Generate sample SSE tool requests."""
    connection_id = "test-conn-456"

    return {
        "render_request": SSEToolRequest(
            tool_name="render_ui_mockup",
            arguments={
                "dsl_content": json.dumps(
                    {
                        "title": "Test UI",
                        "width": 800,
                        "height": 600,
                        "elements": [{"type": "text", "content": "Test"}],
                    }
                ),
                "options": {"width": 800, "height": 600},
            },
            connection_id=connection_id,
            request_id="test-req-001",
        ),
        "validation_request": SSEToolRequest(
            tool_name="validate_dsl",
            arguments={"dsl_content": json.dumps({"title": "Test", "elements": []})},
            connection_id=connection_id,
            request_id="test-req-002",
        ),
        "status_request": SSEToolRequest(
            tool_name="get_render_status",
            arguments={"task_id": "test-task-123"},
            connection_id=connection_id,
            request_id="test-req-003",
        ),
    }


@pytest_asyncio.fixture
async def sse_event_validator():
    """Create SSE event validator for testing event structure."""

    class SSEEventValidator:
        """Validates SSE events for proper structure and content."""

        @staticmethod
        def validate_event_structure(event: SSEEvent) -> bool:
            """Validate basic event structure."""
            assert hasattr(event, "event_type")
            assert hasattr(event, "data")
            assert hasattr(event, "connection_id")
            assert hasattr(event, "timestamp")
            assert isinstance(event.data, dict)
            return True

        @staticmethod
        def validate_connection_event(event: SSEEvent) -> bool:
            """Validate connection-related events."""
            SSEEventValidator.validate_event_structure(event)
            if event.event_type in [SSEEventType.CONNECTION_OPENED, SSEEventType.CONNECTION_CLOSED]:
                assert "connection_id" in event.data
                assert "timestamp" in event.data
            return True

        @staticmethod
        def validate_progress_event(event: SSEEvent) -> bool:
            """Validate progress events."""
            SSEEventValidator.validate_event_structure(event)
            assert event.event_type == SSEEventType.RENDER_PROGRESS
            assert "operation" in event.data
            assert "progress" in event.data
            assert "message" in event.data
            assert 0 <= event.data["progress"] <= 100
            return True

        @staticmethod
        def validate_tool_response_event(event: SSEEvent) -> bool:
            """Validate tool response events."""
            SSEEventValidator.validate_event_structure(event)
            assert event.event_type == SSEEventType.MCP_TOOL_RESPONSE
            assert "tool_name" in event.data
            assert "success" in event.data
            assert isinstance(event.data["success"], bool)
            if event.data["success"]:
                assert "result" in event.data
            else:
                assert "error" in event.data
            return True

        @staticmethod
        def validate_render_result_event(event: SSEEvent) -> bool:
            """Validate render result events."""
            SSEEventValidator.validate_event_structure(event)
            assert event.event_type in [SSEEventType.RENDER_COMPLETED, SSEEventType.RENDER_FAILED]

            if event.event_type == SSEEventType.RENDER_COMPLETED:
                assert "result" in event.data
                assert "processing_time" in event.data
            else:
                assert "error" in event.data
            return True

    return SSEEventValidator()


@pytest_asyncio.fixture
async def sse_test_environment(mock_sse_connection_manager, redis_client):
    """Create complete SSE test environment."""

    class SSETestEnvironment:
        """Complete test environment for SSE testing."""

        def __init__(self, connection_manager, redis_client):
            self.connection_manager = connection_manager
            self.redis = redis_client
            self.active_connections: List[str] = []

        async def create_connection(self, api_key: str = "test-key") -> str:
            """Create a new SSE connection."""
            connection_id = f"test-conn-{uuid.uuid4().hex[:8]}"
            metadata = SSEConnectionMetadata(
                connection_id=connection_id,
                client_ip="127.0.0.1",
                user_agent="Test Client",
                api_key_hash=f"hash-{api_key}",
                status=SSEConnectionStatus.CONNECTED,
            )

            await self.connection_manager.add_connection(connection_id, metadata)
            self.active_connections.append(connection_id)
            return connection_id

        async def cleanup_connections(self):
            """Clean up all test connections."""
            for connection_id in self.active_connections:
                await self.connection_manager.remove_connection(connection_id)
            self.active_connections.clear()

        async def simulate_tool_execution(
            self, connection_id: str, tool_name: str, arguments: Dict[str, Any]
        ) -> str:
            """Simulate tool execution with progress events."""
            request_id = f"req-{uuid.uuid4().hex[:8]}"

            # Send tool call event
            call_event = create_tool_call_event(connection_id, tool_name, arguments, request_id)
            await self.connection_manager.send_to_connection(connection_id, call_event)

            # Send progress events
            for progress in [25, 50, 75]:
                progress_event = create_progress_event(
                    connection_id, "render", progress, f"Progress {progress}%", "processing"
                )
                await self.connection_manager.send_to_connection(connection_id, progress_event)
                await asyncio.sleep(0.1)  # Small delay for realism

            # Send completion event
            result = {"success": True, "data": "test-result"}
            response_event = create_tool_response_event(
                connection_id, tool_name, True, result, None, 2.0, request_id
            )
            await self.connection_manager.send_to_connection(connection_id, response_event)

            return request_id

        async def get_connection_events(self, connection_id: str) -> List[Dict[str, Any]]:
            """Get all events for a connection."""
            if connection_id in self.connection_manager.connections:
                return self.connection_manager.connections[connection_id].events
            return []

    env = SSETestEnvironment(mock_sse_connection_manager, redis_client)
    yield env
    await env.cleanup_connections()


@pytest.fixture
def sse_rate_limiter():
    """Create rate limiter for SSE testing."""

    class MockRateLimiter:
        """Mock rate limiter for testing."""

        def __init__(self, limit: int = 10, window: int = 60):
            self.limit = limit
            self.window = window
            self.requests: Dict[str, List[float]] = {}

        async def check_rate_limit(self, client_id: str) -> bool:
            """Check if client is within rate limits."""
            now = time.time()

            if client_id not in self.requests:
                self.requests[client_id] = []

            # Remove old requests outside the window
            self.requests[client_id] = [
                req_time for req_time in self.requests[client_id] if now - req_time < self.window
            ]

            # Check if under limit
            if len(self.requests[client_id]) < self.limit:
                self.requests[client_id].append(now)
                return True

            return False

        async def reset_client(self, client_id: str):
            """Reset rate limit for client."""
            self.requests.pop(client_id, None)

    return MockRateLimiter()


@pytest.fixture
def dsl_samples_for_sse():
    """DSL samples specifically for SSE testing."""
    return {
        "simple_button": {
            "title": "Simple Button Test",
            "width": 400,
            "height": 300,
            "elements": [
                {
                    "type": "button",
                    "id": "test-button",
                    "layout": {"x": 100, "y": 100, "width": 200, "height": 50},
                    "style": {"background": "#007bff", "color": "white"},
                    "label": "Test Button",
                }
            ],
        },
        "complex_dashboard": {
            "title": "SSE Dashboard Test",
            "width": 1200,
            "height": 800,
            "elements": [
                {
                    "type": "container",
                    "id": "header",
                    "layout": {"x": 0, "y": 0, "width": 1200, "height": 80},
                    "style": {"background": "#2563eb", "color": "white"},
                    "children": [
                        {
                            "type": "text",
                            "content": "SSE Test Dashboard",
                            "style": {"fontSize": "24px", "textAlign": "center"},
                        }
                    ],
                },
                {
                    "type": "container",
                    "id": "content",
                    "layout": {"x": 0, "y": 80, "width": 1200, "height": 720},
                    "children": [
                        {
                            "type": "card",
                            "title": "Metrics",
                            "content": "Test metrics content",
                            "layout": {"x": 50, "y": 50, "width": 300, "height": 200},
                        }
                    ],
                },
            ],
        },
        "invalid_dsl": {
            "title": "Invalid Test",
            # Missing required fields to trigger validation errors
        },
    }


@pytest.fixture
def performance_config():
    """Configuration for performance testing."""
    return {
        "concurrent_connections": [5, 10, 25, 50],
        "request_rates": [1, 5, 10],  # requests per second
        "test_duration": 30,  # seconds
        "timeout_threshold": 5.0,  # seconds
        "memory_threshold": 500,  # MB
        "event_latency_threshold": 0.1,  # seconds
    }


class MockRedisFailure:
    """Mock Redis failure for testing error handling."""

    def __init__(self):
        self.is_failed = False
        self.original_methods = {}

    async def trigger_failure(self):
        """Trigger Redis failure."""
        self.is_failed = True

    async def recover(self):
        """Recover from Redis failure."""
        self.is_failed = False


@pytest.fixture
def mock_redis_failure():
    """Fixture for mocking Redis failures."""
    return MockRedisFailure()


@pytest.fixture
def mock_network_interruption():
    """Fixture for mocking network interruptions."""

    class MockNetworkInterruption:
        def __init__(self):
            self.is_interrupted = False

        async def trigger_interruption(self):
            """Trigger network interruption."""
            self.is_interrupted = True

        async def restore_connection(self):
            """Restore network connection."""
            self.is_interrupted = False

    return MockNetworkInterruption()
