"""
SSE Integration Tests
====================

Integration tests for Server-Sent Events functionality including:
- Connection lifecycle management
- Authentication and authorization
- Event streaming and delivery
- Connection management and cleanup
- Rate limiting enforcement
"""

import pytest
import pytest_asyncio
import asyncio
import time
import uuid
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from unittest.mock import patch, AsyncMock

from src.api.sse.models import (
    SSEConnectionMetadata, SSEConnectionStatus, SSEToolRequest, 
    SSEEventPayload, SSEProgressUpdate
)
from src.api.sse.events import (
    SSEEventType, create_connection_opened_event, create_heartbeat_event,
    create_progress_event, create_error_event, create_rate_limit_exceeded_event
)
from src.config.settings import get_settings

from tests.fixtures.sse_fixtures import (
    MockSSEClient, MockSSEConnectionManager, sse_test_environment,
    sse_event_validator, sse_rate_limiter
)
from tests.utils.helpers import wait_for_condition, measure_async_performance
from tests.utils.assertions import assert_performance_within_threshold


@pytest.mark.integration
@pytest.mark.sse
class TestSSEConnectionLifecycle:
    """Test SSE connection lifecycle management."""
    
    @pytest_asyncio.fixture
    async def connection_manager(self):
        """Mock connection manager for lifecycle tests."""
        manager = MockSSEConnectionManager()
        yield manager
    
    @pytest.mark.asyncio
    async def test_connection_establishment(self, connection_manager, sse_event_validator):
        """Test successful SSE connection establishment."""
        connection_id = f"test-conn-{uuid.uuid4().hex[:8]}"
        metadata = SSEConnectionMetadata(
            connection_id=connection_id,
            client_ip="127.0.0.1",
            user_agent="Test Browser",
            api_key_hash="test-key-hash",
            status=SSEConnectionStatus.CONNECTING
        )
        
        # Establish connection
        await connection_manager.add_connection(connection_id, metadata)
        
        # Verify connection is tracked
        assert await connection_manager.get_connection_count() == 1
        assert connection_id in await connection_manager.get_connection_ids()
        
        # Send connection opened event
        opened_event = create_connection_opened_event(connection_id, {"test": True})
        await connection_manager.send_to_connection(connection_id, opened_event)
        
        # Validate event structure
        assert sse_event_validator.validate_connection_event(opened_event)
        
        # Verify client received event
        client = connection_manager.connections[connection_id]
        assert len(client.events) == 1
        assert client.events[0]['type'] == SSEEventType.CONNECTION_OPENED
    
    @pytest.mark.asyncio
    async def test_connection_heartbeat_mechanism(self, connection_manager):
        """Test connection heartbeat and keepalive functionality."""
        connection_id = f"test-conn-{uuid.uuid4().hex[:8]}"
        metadata = SSEConnectionMetadata(
            connection_id=connection_id,
            client_ip="127.0.0.1",
            user_agent="Test Browser"
        )
        
        await connection_manager.add_connection(connection_id, metadata)
        
        # Send multiple heartbeat events
        heartbeat_count = 5
        for i in range(heartbeat_count):
            heartbeat_event = create_heartbeat_event(connection_id, i * 30.0)
            await connection_manager.send_to_connection(connection_id, heartbeat_event)
            await asyncio.sleep(0.1)  # Small delay between heartbeats
        
        # Verify all heartbeats received
        client = connection_manager.connections[connection_id]
        heartbeat_events = [e for e in client.events if e['type'] == SSEEventType.CONNECTION_HEARTBEAT]
        assert len(heartbeat_events) == heartbeat_count
        
        # Verify heartbeat data structure
        for event in heartbeat_events:
            assert 'timestamp' in event['data']
            assert 'server_time' in event['data']
            assert 'connection_age' in event['data']
    
    @pytest.mark.asyncio
    async def test_connection_cleanup(self, connection_manager):
        """Test proper connection cleanup and resource management."""
        # Create multiple connections
        connection_ids = []
        for i in range(5):
            connection_id = f"test-conn-{i}-{uuid.uuid4().hex[:8]}"
            metadata = SSEConnectionMetadata(
                connection_id=connection_id,
                client_ip="127.0.0.1",
                user_agent=f"Test Browser {i}"
            )
            await connection_manager.add_connection(connection_id, metadata)
            connection_ids.append(connection_id)
        
        # Verify all connections established
        assert await connection_manager.get_connection_count() == 5
        
        # Remove connections one by one
        for connection_id in connection_ids:
            await connection_manager.remove_connection(connection_id)
            
        # Verify all connections cleaned up
        assert await connection_manager.get_connection_count() == 0
        assert len(await connection_manager.get_connection_ids()) == 0
    
    @pytest.mark.asyncio
    async def test_concurrent_connections(self, connection_manager):
        """Test handling of multiple concurrent connections."""
        connection_count = 20
        connection_tasks = []
        
        async def create_connection(index: int):
            connection_id = f"concurrent-conn-{index}-{uuid.uuid4().hex[:8]}"
            metadata = SSEConnectionMetadata(
                connection_id=connection_id,
                client_ip=f"127.0.0.{index % 255}",
                user_agent=f"Concurrent Browser {index}"
            )
            await connection_manager.add_connection(connection_id, metadata)
            
            # Send a test event to each connection
            test_event = create_progress_event(
                connection_id, "test", 50, f"Test message {index}", "testing"
            )
            await connection_manager.send_to_connection(connection_id, test_event)
            
            return connection_id
        
        # Create connections concurrently
        with measure_async_performance() as timer:
            connection_tasks = [create_connection(i) for i in range(connection_count)]
            created_connections = await asyncio.gather(*connection_tasks)
        
        # Verify all connections were created
        assert len(created_connections) == connection_count
        assert await connection_manager.get_connection_count() == connection_count
        
        # Verify performance is acceptable
        assert_performance_within_threshold(timer.elapsed_time, 5.0)
        
        # Verify each connection received its event
        for connection_id in created_connections:
            client = connection_manager.connections[connection_id]
            assert len(client.events) == 1
            assert client.events[0]['type'] == SSEEventType.RENDER_PROGRESS


@pytest.mark.integration
@pytest.mark.sse
class TestSSEAuthentication:
    """Test SSE authentication and authorization."""
    
    @pytest.mark.asyncio
    async def test_valid_api_key_authentication(self, sse_test_environment):
        """Test authentication with valid API key."""
        # Create connection with valid API key
        valid_api_key = "valid-test-key-123"
        connection_id = await sse_test_environment.create_connection(valid_api_key)
        
        # Verify connection was established
        assert connection_id in await sse_test_environment.connection_manager.get_connection_ids()
        
        # Verify connection metadata includes API key hash
        client = sse_test_environment.connection_manager.connections[connection_id]
        assert client.api_key == valid_api_key
    
    @pytest.mark.asyncio
    async def test_invalid_api_key_rejection(self, connection_manager):
        """Test rejection of invalid API keys."""
        # This test simulates the authentication logic that would be in the actual endpoint
        invalid_api_keys = ["", "invalid-key", "expired-key", None]
        
        for invalid_key in invalid_api_keys:
            connection_id = f"invalid-conn-{uuid.uuid4().hex[:8]}"
            
            # Simulate authentication failure by sending error event
            error_event = create_error_event(
                connection_id=connection_id,
                error_code="AUTHENTICATION_FAILED",
                error_message="Invalid API key",
                details={"api_key": invalid_key},
                recoverable=False
            )
            
            # In real implementation, connection would be rejected
            # Here we simulate by sending error event
            await connection_manager.broadcast_event(error_event)
            
            # Verify error event was created
            assert len(connection_manager.events_sent) > 0
            last_event = connection_manager.events_sent[-1]
            assert last_event.event_type == SSEEventType.CONNECTION_ERROR
            assert "AUTHENTICATION_FAILED" in last_event.data['error_code']
    
    @pytest.mark.asyncio
    async def test_api_key_rotation_handling(self, sse_test_environment):
        """Test handling of API key rotation scenarios."""
        # Create connection with initial API key
        initial_key = "initial-key-123"
        connection_id = await sse_test_environment.create_connection(initial_key)
        
        # Simulate API key rotation by creating new connection with new key
        new_key = "rotated-key-456"
        new_connection_id = await sse_test_environment.create_connection(new_key)
        
        # Both connections should be valid
        assert len(await sse_test_environment.connection_manager.get_connection_ids()) == 2
        
        # Verify different API keys are tracked
        client1 = sse_test_environment.connection_manager.connections[connection_id]
        client2 = sse_test_environment.connection_manager.connections[new_connection_id]
        assert client1.api_key != client2.api_key


@pytest.mark.integration
@pytest.mark.sse
class TestSSEEventStreaming:
    """Test SSE event streaming and delivery."""
    
    @pytest.mark.asyncio
    async def test_single_event_delivery(self, sse_test_environment, sse_event_validator):
        """Test delivery of single events to connections."""
        connection_id = await sse_test_environment.create_connection()
        
        # Send various types of events
        events_to_send = [
            create_progress_event(connection_id, "render", 25, "Starting", "init"),
            create_progress_event(connection_id, "render", 50, "Processing", "render"),
            create_progress_event(connection_id, "render", 100, "Complete", "done")
        ]
        
        for event in events_to_send:
            await sse_test_environment.connection_manager.send_to_connection(connection_id, event)
            assert sse_event_validator.validate_progress_event(event)
        
        # Verify all events were received
        client_events = await sse_test_environment.get_connection_events(connection_id)
        assert len(client_events) == len(events_to_send)
        
        # Verify event order and content
        for i, event in enumerate(client_events):
            assert event['type'] == SSEEventType.RENDER_PROGRESS
            assert event['data']['progress'] == [25, 50, 100][i]
    
    @pytest.mark.asyncio
    async def test_broadcast_event_delivery(self, sse_test_environment):
        """Test broadcasting events to multiple connections."""
        # Create multiple connections
        connection_count = 5
        connection_ids = []
        for i in range(connection_count):
            connection_id = await sse_test_environment.create_connection(f"broadcast-key-{i}")
            connection_ids.append(connection_id)
        
        # Send broadcast event
        broadcast_event = create_progress_event(
            "broadcast", "system", 100, "System announcement", "broadcast"
        )
        await sse_test_environment.connection_manager.broadcast_event(broadcast_event)
        
        # Verify all connections received the event
        for connection_id in connection_ids:
            client_events = await sse_test_environment.get_connection_events(connection_id)
            assert len(client_events) == 1
            assert client_events[0]['type'] == SSEEventType.RENDER_PROGRESS
            assert client_events[0]['data']['message'] == "System announcement"
    
    @pytest.mark.asyncio
    async def test_event_ordering_preservation(self, sse_test_environment):
        """Test that event ordering is preserved during delivery."""
        connection_id = await sse_test_environment.create_connection()
        
        # Send events in specific order
        event_sequence = []
        for i in range(10):
            event = create_progress_event(
                connection_id, "sequence_test", i * 10, f"Step {i}", f"stage_{i}"
            )
            event_sequence.append(event)
            await sse_test_environment.connection_manager.send_to_connection(connection_id, event)
            # Small delay to ensure ordering
            await asyncio.sleep(0.01)
        
        # Verify events received in correct order
        client_events = await sse_test_environment.get_connection_events(connection_id)
        assert len(client_events) == 10
        
        for i, event in enumerate(client_events):
            assert event['data']['progress'] == i * 10
            assert event['data']['message'] == f"Step {i}"
    
    @pytest.mark.asyncio
    async def test_high_frequency_event_handling(self, sse_test_environment):
        """Test handling of high-frequency event streams."""
        connection_id = await sse_test_environment.create_connection()
        
        # Send many events rapidly
        event_count = 100
        with measure_async_performance() as timer:
            for i in range(event_count):
                event = create_progress_event(
                    connection_id, "high_freq", i, f"Event {i}", "rapid"
                )
                await sse_test_environment.connection_manager.send_to_connection(connection_id, event)
        
        # Verify all events were delivered
        client_events = await sse_test_environment.get_connection_events(connection_id)
        assert len(client_events) == event_count
        
        # Verify reasonable performance
        assert_performance_within_threshold(timer.elapsed_time, 2.0)
        
        # Verify no events were lost or corrupted
        for i, event in enumerate(client_events):
            assert event['data']['progress'] == i
            assert event['data']['message'] == f"Event {i}"


@pytest.mark.integration
@pytest.mark.sse
class TestSSERateLimiting:
    """Test SSE rate limiting functionality."""
    
    @pytest.mark.asyncio
    async def test_rate_limit_enforcement(self, sse_test_environment, sse_rate_limiter):
        """Test rate limiting enforcement."""
        connection_id = await sse_test_environment.create_connection()
        client_id = "test-client-123"
        
        # Configure rate limiter: 5 requests per 10 seconds
        sse_rate_limiter.limit = 5
        sse_rate_limiter.window = 10
        
        # Make requests within limit
        successful_requests = 0
        for i in range(5):
            if await sse_rate_limiter.check_rate_limit(client_id):
                successful_requests += 1
        
        assert successful_requests == 5
        
        # Next request should be rate limited
        rate_limited = not await sse_rate_limiter.check_rate_limit(client_id)
        assert rate_limited is True
    
    @pytest.mark.asyncio
    async def test_rate_limit_warning_events(self, sse_test_environment):
        """Test rate limit warning event generation."""
        connection_id = await sse_test_environment.create_connection()
        
        # Simulate approaching rate limit
        warning_event = create_error_event(
            connection_id=connection_id,
            error_code="RATE_LIMIT_WARNING",
            error_message="Approaching rate limit",
            details={"current_rate": 8, "limit": 10},
            recoverable=True,
            suggested_action="Slow down request rate"
        )
        
        await sse_test_environment.connection_manager.send_to_connection(connection_id, warning_event)
        
        # Verify warning event received
        client_events = await sse_test_environment.get_connection_events(connection_id)
        assert len(client_events) == 1
        assert client_events[0]['type'] == SSEEventType.CONNECTION_ERROR
        assert "RATE_LIMIT_WARNING" in client_events[0]['data']['error_code']
    
    @pytest.mark.asyncio
    async def test_rate_limit_exceeded_events(self, sse_test_environment):
        """Test rate limit exceeded event generation."""
        connection_id = await sse_test_environment.create_connection()
        
        # Create rate limit exceeded event
        exceeded_event = create_rate_limit_exceeded_event(
            connection_id=connection_id,
            limit=10,
            reset_time=datetime.utcnow() + timedelta(seconds=60)
        )
        
        await sse_test_environment.connection_manager.send_to_connection(connection_id, exceeded_event)
        
        # Verify rate limit exceeded event
        client_events = await sse_test_environment.get_connection_events(connection_id)
        assert len(client_events) == 1
        assert client_events[0]['type'] == SSEEventType.RATE_LIMIT_EXCEEDED
        assert client_events[0]['data']['limit'] == 10
        assert 'reset_time' in client_events[0]['data']
    
    @pytest.mark.asyncio
    async def test_rate_limit_reset_after_window(self, sse_rate_limiter):
        """Test rate limit reset after time window."""
        client_id = "test-client-reset"
        
        # Configure very short window for testing
        sse_rate_limiter.limit = 2
        sse_rate_limiter.window = 1  # 1 second window
        
        # Exhaust rate limit
        assert await sse_rate_limiter.check_rate_limit(client_id) is True
        assert await sse_rate_limiter.check_rate_limit(client_id) is True
        assert await sse_rate_limiter.check_rate_limit(client_id) is False  # Rate limited
        
        # Wait for window to reset
        await asyncio.sleep(1.1)
        
        # Should be able to make requests again
        assert await sse_rate_limiter.check_rate_limit(client_id) is True


@pytest.mark.integration
@pytest.mark.sse
class TestSSEErrorHandling:
    """Test SSE error handling and recovery."""
    
    @pytest.mark.asyncio
    async def test_connection_error_propagation(self, sse_test_environment):
        """Test proper error event propagation."""
        connection_id = await sse_test_environment.create_connection()
        
        # Send various error types
        error_scenarios = [
            ("PARSE_ERROR", "Invalid DSL syntax", True),
            ("TOOL_EXECUTION_FAILED", "Rendering failed", True),
            ("SERVER_ERROR", "Internal server error", False),
            ("TIMEOUT", "Request timeout", True)
        ]
        
        for error_code, error_message, recoverable in error_scenarios:
            error_event = create_error_event(
                connection_id=connection_id,
                error_code=error_code,
                error_message=error_message,
                recoverable=recoverable
            )
            await sse_test_environment.connection_manager.send_to_connection(connection_id, error_event)
        
        # Verify all errors were received
        client_events = await sse_test_environment.get_connection_events(connection_id)
        assert len(client_events) == len(error_scenarios)
        
        # Verify error event structure
        for i, event in enumerate(client_events):
            assert event['type'] == SSEEventType.CONNECTION_ERROR
            assert event['data']['error_code'] == error_scenarios[i][0]
            assert event['data']['error_message'] == error_scenarios[i][1]
            assert event['data']['recoverable'] == error_scenarios[i][2]
    
    @pytest.mark.asyncio
    async def test_malformed_event_handling(self, sse_test_environment):
        """Test handling of malformed events."""
        connection_id = await sse_test_environment.create_connection()
        
        # This test simulates how the system should handle malformed events
        # In practice, malformed events should be caught before reaching clients
        
        # Send a well-formed event first
        valid_event = create_progress_event(connection_id, "test", 50, "Valid event", "test")
        await sse_test_environment.connection_manager.send_to_connection(connection_id, valid_event)
        
        # Simulate error handling for malformed data
        error_event = create_error_event(
            connection_id=connection_id,
            error_code="MALFORMED_EVENT",
            error_message="Received malformed event data",
            details={"event_type": "unknown", "data": "corrupted"},
            recoverable=True
        )
        await sse_test_environment.connection_manager.send_to_connection(connection_id, error_event)
        
        # Verify both events were handled
        client_events = await sse_test_environment.get_connection_events(connection_id)
        assert len(client_events) == 2
        assert client_events[0]['type'] == SSEEventType.RENDER_PROGRESS
        assert client_events[1]['type'] == SSEEventType.CONNECTION_ERROR
    
    @pytest.mark.asyncio
    async def test_connection_recovery_scenarios(self, sse_test_environment):
        """Test connection recovery scenarios."""
        connection_id = await sse_test_environment.create_connection()
        
        # Send some events normally
        for i in range(3):
            event = create_progress_event(connection_id, "recovery_test", i * 33, f"Before disconnect {i}", "normal")
            await sse_test_environment.connection_manager.send_to_connection(connection_id, event)
        
        # Simulate connection interruption by removing connection
        await sse_test_environment.connection_manager.remove_connection(connection_id)
        
        # Simulate reconnection with same connection ID
        await sse_test_environment.create_connection()
        
        # Send events after reconnection
        for i in range(3, 6):
            event = create_progress_event(connection_id, "recovery_test", i * 33, f"After reconnect {i}", "recovered")
            # This will create a new connection since the old one was removed
            new_connections = await sse_test_environment.connection_manager.get_connection_ids()
            if new_connections:
                await sse_test_environment.connection_manager.send_to_connection(new_connections[0], event)
        
        # Verify recovery behavior
        current_connections = await sse_test_environment.connection_manager.get_connection_ids()
        assert len(current_connections) >= 1  # At least one connection should exist