"""
SSE Error Handling Tests
=======================

Tests for error handling in SSE implementation including:
- Network failure recovery
- Server error handling
- Client disconnection handling
- Redis connection failures
- Malformed event handling
- Reconnection behavior
"""

import pytest
import pytest_asyncio
import asyncio
import json
import time
import uuid
from typing import List, Dict, Any, Optional
from unittest.mock import patch, AsyncMock, MagicMock

from src.api.sse.models import (
    SSEConnectionMetadata,
    SSEConnectionStatus,
    SSEToolRequest,
    SSEEventPayload,
    SSEError,
)
from src.api.sse.events import (
    SSEEventType,
    create_error_event,
    create_connection_closed_event,
    create_connection_opened_event,
)
from src.api.sse.connection_manager import SSEConnectionManager
from src.api.sse.mcp_bridge import MCPBridge

from tests.fixtures.sse_fixtures import (
    sse_test_environment,
    mock_sse_client,
    mock_redis_failure,
    mock_network_interruption,
)


@pytest.mark.integration
@pytest.mark.sse
class TestSSENetworkFailures:
    """Test SSE behavior during network failures."""

    @pytest.mark.asyncio
    async def test_client_reconnection_after_network_failure(
        self, sse_test_environment, mock_network_interruption
    ):
        """Test client reconnection behavior after network interruption."""
        # Create initial connection
        connection_id = await sse_test_environment.create_connection("network-test")
        client_id = "test-client-reconnect"

        # Associate client ID with connection
        await sse_test_environment.connection_manager.associate_client_id(connection_id, client_id)

        # Send initial events
        for i in range(3):
            await sse_test_environment.send_test_event(connection_id, f"Pre-interruption event {i}")

        # Simulate network failure
        await mock_network_interruption.trigger_failure(connection_id)

        # Verify connection was marked as disconnected
        connection_status = await sse_test_environment.connection_manager.get_connection_status(
            connection_id
        )
        assert connection_status == SSEConnectionStatus.DISCONNECTED

        # Simulate client reconnection with same client ID
        new_connection_id = await sse_test_environment.create_connection("network-test-reconnect")
        await sse_test_environment.connection_manager.associate_client_id(
            new_connection_id, client_id
        )

        # Verify connection recovery
        assert (
            new_connection_id in await sse_test_environment.connection_manager.get_connection_ids()
        )

        # Send post-reconnection events
        for i in range(2):
            await sse_test_environment.send_test_event(
                new_connection_id, f"Post-reconnection event {i}"
            )

        # Verify events after reconnection
        events = await sse_test_environment.get_connection_events(new_connection_id)
        event_data = [e["data"] for e in events if "data" in e]

        # Should have reconnection event
        assert any("reconnected" in str(data).lower() for data in event_data)

        # Should have post-reconnection events
        assert "Post-reconnection event 0" in str(event_data)
        assert "Post-reconnection event 1" in str(event_data)

    @pytest.mark.asyncio
    async def test_event_delivery_during_intermittent_connectivity(
        self, sse_test_environment, mock_network_interruption
    ):
        """Test event delivery during intermittent network connectivity."""
        connection_id = await sse_test_environment.create_connection("intermittent-test")

        # Send initial batch of events
        for i in range(5):
            await sse_test_environment.send_test_event(connection_id, f"Initial event {i}")

        # Simulate brief network interruption
        await mock_network_interruption.trigger_failure(connection_id, duration_seconds=1)

        # Send events during interruption (should be queued)
        for i in range(3):
            await sse_test_environment.send_test_event(
                connection_id, f"During interruption event {i}"
            )

        # Allow reconnection
        await asyncio.sleep(1.5)

        # Simulate client reconnection
        await sse_test_environment.reconnect(connection_id)

        # Send final events after reconnection
        for i in range(2):
            await sse_test_environment.send_test_event(
                connection_id, f"After reconnection event {i}"
            )

        # Verify all events were delivered
        events = await sse_test_environment.get_connection_events(connection_id)
        event_data = [e["data"] for e in events if "data" in e]

        # Check for events from all phases
        assert "Initial event 0" in str(event_data)
        assert "During interruption event 0" in str(event_data)
        assert "After reconnection event 0" in str(event_data)

        # Verify event count (should have all events plus reconnection event)
        assert len(events) >= 10  # 5 initial + 3 during + 2 after + reconnection event

    @pytest.mark.asyncio
    async def test_connection_timeout_handling(self, sse_test_environment):
        """Test handling of connection timeouts."""
        # Create connection with short timeout
        with patch("src.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.SSE_CONNECTION_TIMEOUT_SECONDS = 2
            mock_settings.return_value.SSE_HEARTBEAT_INTERVAL_SECONDS = 1

            connection_id = await sse_test_environment.create_connection("timeout-test")

            # Send initial event
            await sse_test_environment.send_test_event(connection_id, "Initial event")

            # Wait for heartbeat
            await asyncio.sleep(1.5)

            # Verify heartbeat was sent
            events = await sse_test_environment.get_connection_events(connection_id)
            assert any(e["type"] == SSEEventType.CONNECTION_HEARTBEAT for e in events)

            # Wait for timeout
            await asyncio.sleep(2.5)

            # Verify connection was closed due to timeout
            assert (
                connection_id
                not in await sse_test_environment.connection_manager.get_connection_ids()
            )

            # Verify close event was sent
            events = await sse_test_environment.get_connection_events(connection_id)
            assert any(e["type"] == SSEEventType.CONNECTION_CLOSED for e in events)


@pytest.mark.integration
@pytest.mark.sse
class TestSSEServerErrors:
    """Test SSE behavior during server errors."""

    @pytest.mark.asyncio
    async def test_server_error_handling(self, sse_test_environment):
        """Test handling of server-side errors."""
        connection_id = await sse_test_environment.create_connection("server-error-test")

        # Simulate server error during event processing
        error_message = "Internal server error during event processing"
        error_code = "SERVER_ERROR"

        error_event = create_error_event(
            connection_id=connection_id,
            error_code=error_code,
            error_message=error_message,
            details={"source": "event_processor"},
            recoverable=True,
        )

        # Send error event
        await sse_test_environment.connection_manager.send_to_connection(connection_id, error_event)

        # Verify error event was delivered
        events = await sse_test_environment.get_connection_events(connection_id)
        error_events = [e for e in events if e["type"] == SSEEventType.CONNECTION_ERROR]

        assert len(error_events) == 1
        assert error_events[0]["data"]["error_code"] == error_code
        assert error_events[0]["data"]["error_message"] == error_message
        assert error_events[0]["data"]["recoverable"] is True

    @pytest.mark.asyncio
    async def test_server_restart_recovery(self, sse_test_environment):
        """Test recovery after server restart."""
        # Create connection
        connection_id = await sse_test_environment.create_connection("restart-test")
        client_id = "restart-recovery-client"

        # Associate client ID with connection
        await sse_test_environment.connection_manager.associate_client_id(connection_id, client_id)

        # Send initial events
        for i in range(3):
            await sse_test_environment.send_test_event(connection_id, f"Pre-restart event {i}")

        # Simulate server restart
        with patch.object(sse_test_environment.connection_manager, "connections", {}):
            # All connections are lost in memory
            assert (
                connection_id
                not in await sse_test_environment.connection_manager.get_connection_ids()
            )

            # Simulate client reconnection after server restart
            new_connection_id = await sse_test_environment.create_connection("restart-reconnect")
            await sse_test_environment.connection_manager.associate_client_id(
                new_connection_id, client_id
            )

            # Send post-restart events
            for i in range(2):
                await sse_test_environment.send_test_event(
                    new_connection_id, f"Post-restart event {i}"
                )

            # Verify new connection is active
            assert (
                new_connection_id
                in await sse_test_environment.connection_manager.get_connection_ids()
            )

            # Verify events after restart
            events = await sse_test_environment.get_connection_events(new_connection_id)
            event_data = [e["data"] for e in events if "data" in e]

            # Should have post-restart events
            assert "Post-restart event 0" in str(event_data)
            assert "Post-restart event 1" in str(event_data)

    @pytest.mark.asyncio
    async def test_mcp_bridge_error_handling(self, sse_test_environment):
        """Test handling of errors from MCP bridge."""
        connection_id = await sse_test_environment.create_connection("mcp-error-test")

        # Create mock MCP bridge with error
        with patch("src.api.sse.mcp_bridge.MCPBridge.execute_tool") as mock_execute:
            # Simulate MCP bridge error
            mock_execute.side_effect = Exception("MCP bridge execution failed")

            # Attempt to execute tool via MCP bridge
            tool_request = SSEToolRequest(
                connection_id=connection_id,
                request_id=str(uuid.uuid4()),
                tool_name="test_tool",
                arguments={"param": "value"},
            )

            # Execute tool (should handle error)
            with pytest.raises(Exception):
                await sse_test_environment.execute_tool(tool_request)

            # Verify error event was sent
            events = await sse_test_environment.get_connection_events(connection_id)
            error_events = [e for e in events if e["type"] == SSEEventType.CONNECTION_ERROR]

            assert len(error_events) >= 1
            assert "MCP bridge" in str(error_events[0]["data"])


@pytest.mark.integration
@pytest.mark.sse
class TestSSERedisFailures:
    """Test SSE behavior during Redis failures."""

    @pytest.mark.asyncio
    async def test_redis_connection_failure(self, sse_test_environment, mock_redis_failure):
        """Test handling of Redis connection failures."""
        connection_id = await sse_test_environment.create_connection("redis-failure-test")

        # Send event before Redis failure
        await sse_test_environment.send_test_event(connection_id, "Pre-failure event")

        # Simulate Redis connection failure
        await mock_redis_failure.trigger_failure()

        # Attempt to send event during Redis failure
        with pytest.raises(Exception) as excinfo:
            await sse_test_environment.send_test_event(connection_id, "During failure event")

        # Verify Redis error
        assert "redis" in str(excinfo.value).lower()

        # Simulate Redis recovery
        await mock_redis_failure.recover()

        # Send event after Redis recovery
        await sse_test_environment.send_test_event(connection_id, "Post-recovery event")

        # Verify events before and after failure
        events = await sse_test_environment.get_connection_events(connection_id)
        event_data = [e["data"] for e in events if "data" in e]

        assert "Pre-failure event" in str(event_data)
        assert "Post-recovery event" in str(event_data)
        assert "During failure event" not in str(event_data)

    @pytest.mark.asyncio
    async def test_redis_pubsub_failure(self, sse_test_environment, mock_redis_failure):
        """Test handling of Redis PubSub failures."""
        connection_id = await sse_test_environment.create_connection("redis-pubsub-test")

        # Simulate Redis PubSub failure
        with patch("src.api.sse.connection_manager.redis_subscribe") as mock_subscribe:
            mock_subscribe.side_effect = Exception("Redis PubSub subscription failed")

            # Attempt to create new connection during PubSub failure
            with pytest.raises(Exception) as excinfo:
                await sse_test_environment.create_connection("pubsub-failure")

            # Verify PubSub error
            assert (
                "pubsub" in str(excinfo.value).lower()
                or "subscription" in str(excinfo.value).lower()
            )

        # Verify existing connection still works
        await sse_test_environment.send_test_event(connection_id, "After PubSub failure")

        events = await sse_test_environment.get_connection_events(connection_id)
        event_data = [e["data"] for e in events if "data" in e]

        assert "After PubSub failure" in str(event_data)


@pytest.mark.integration
@pytest.mark.sse
class TestSSEMalformedEvents:
    """Test SSE handling of malformed events."""

    @pytest.mark.asyncio
    async def test_malformed_event_handling(self, sse_test_environment):
        """Test handling of malformed events."""
        connection_id = await sse_test_environment.create_connection("malformed-event-test")

        # Test with various malformed events
        malformed_events = [
            # Missing required fields
            {"type": SSEEventType.RENDER_PROGRESS},
            {"connection_id": connection_id},
            # Invalid event type
            {"type": "INVALID_TYPE", "connection_id": connection_id, "data": {}},
            # Invalid JSON in data
            {
                "type": SSEEventType.RENDER_PROGRESS,
                "connection_id": connection_id,
                "data": "Not a valid JSON object",
            },
            # Mismatched connection ID
            {
                "type": SSEEventType.RENDER_PROGRESS,
                "connection_id": "wrong-id",
                "data": {"progress": 50},
            },
        ]

        # Process each malformed event
        for event in malformed_events:
            # Simulate receiving malformed event from Redis
            with pytest.raises(Exception):
                await sse_test_environment.connection_manager.process_redis_message(
                    json.dumps(event)
                )

        # Verify connection still works after malformed events
        await sse_test_environment.send_test_event(connection_id, "After malformed events")

        events = await sse_test_environment.get_connection_events(connection_id)
        event_data = [e["data"] for e in events if "data" in e]

        assert "After malformed events" in str(event_data)

    @pytest.mark.asyncio
    async def test_oversized_event_handling(self, sse_test_environment):
        """Test handling of oversized events."""
        connection_id = await sse_test_environment.create_connection("oversized-event-test")

        # Create oversized event payload
        oversized_data = "X" * (1024 * 1024)  # 1MB of data

        # Attempt to send oversized event
        with pytest.raises(Exception) as excinfo:
            await sse_test_environment.send_test_event(connection_id, oversized_data)

        # Verify size limit error
        assert "size" in str(excinfo.value).lower() or "too large" in str(excinfo.value).lower()

        # Verify connection still works after oversized event
        await sse_test_environment.send_test_event(connection_id, "After oversized event")

        events = await sse_test_environment.get_connection_events(connection_id)
        event_data = [e["data"] for e in events if "data" in e]

        assert "After oversized event" in str(event_data)


@pytest.mark.integration
@pytest.mark.sse
class TestSSEReconnectionBehavior:
    """Test SSE reconnection behavior."""

    @pytest.mark.asyncio
    async def test_client_reconnection_with_last_event_id(self, sse_test_environment):
        """Test client reconnection with Last-Event-ID header."""
        # Create initial connection
        connection_id = await sse_test_environment.create_connection("last-event-id-test")

        # Send initial events
        event_ids = []
        for i in range(5):
            event_id = f"event-{i}"
            await sse_test_environment.send_test_event(
                connection_id, f"Event {i}", event_id=event_id
            )
            event_ids.append(event_id)

        # Simulate client disconnection
        await sse_test_environment.disconnect(connection_id)

        # Simulate client reconnection with Last-Event-ID
        last_event_id = event_ids[2]  # Reconnect from the 3rd event
        new_connection_id = await sse_test_environment.create_connection(
            "last-event-id-reconnect", last_event_id=last_event_id
        )

        # Verify missed events are resent
        events = await sse_test_environment.get_connection_events(new_connection_id)
        resent_event_ids = [e.get("id") for e in events if "id" in e]

        # Should have events 3, 4 (events after the Last-Event-ID)
        assert event_ids[3] in resent_event_ids
        assert event_ids[4] in resent_event_ids

        # Should not have events 0, 1, 2 (events before or equal to Last-Event-ID)
        assert event_ids[0] not in resent_event_ids
        assert event_ids[1] not in resent_event_ids
        assert event_ids[2] not in resent_event_ids

    @pytest.mark.asyncio
    async def test_reconnection_with_event_buffer(self, sse_test_environment):
        """Test reconnection with event buffer."""
        # Configure event buffer size
        with patch("src.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.SSE_EVENT_BUFFER_SIZE = 10

            # Create connection
            connection_id = await sse_test_environment.create_connection("buffer-test")

            # Send events to fill buffer
            for i in range(15):
                await sse_test_environment.send_test_event(
                    connection_id, f"Event {i}", event_id=f"event-{i}"
                )

            # Simulate client disconnection
            await sse_test_environment.disconnect(connection_id)

            # Simulate client reconnection with old Last-Event-ID (should be outside buffer)
            old_event_id = "event-2"  # This should be outside the buffer
            new_connection_id = await sse_test_environment.create_connection(
                "buffer-reconnect", last_event_id=old_event_id
            )

            # Verify only buffered events are resent
            events = await sse_test_environment.get_connection_events(new_connection_id)
            resent_event_ids = [e.get("id") for e in events if "id" in e]

            # Should have the most recent events (buffer size = 10)
            assert "event-14" in resent_event_ids
            assert "event-10" in resent_event_ids

            # Should not have events outside buffer
            assert "event-2" not in resent_event_ids
            assert "event-4" not in resent_event_ids

            # Should have received a warning about missed events
            warning_events = [e for e in events if e["type"] == SSEEventType.CONNECTION_WARNING]
            assert len(warning_events) >= 1
            assert "missed events" in str(warning_events[0]["data"]).lower()
