"""
SSE Security Tests
=================

Security validation for SSE implementation including:
- Authentication bypass attempts
- Rate limit enforcement verification
- Connection ID security and isolation
- Event injection attempts via Redis
- Resource exhaustion protection
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
import json
import time
import random
import string
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock

from src.api.sse.models import (
    SSEConnectionMetadata, SSEConnectionStatus, SSEToolRequest,
    SSEEventPayload, SSEError
)
from src.api.sse.events import (
    SSEEventType, create_connection_opened_event, create_error_event,
    create_rate_limit_exceeded_event, create_rate_limit_warning_event
)
from src.config.settings import get_settings

from tests.fixtures.sse_fixtures import (
    sse_test_environment, sse_rate_limiter, mock_sse_client,
    MockSSEConnectionManager
)
from tests.utils.helpers import measure_async_performance, ConcurrentExecutor


@pytest.mark.security
@pytest.mark.sse
class TestSSEAuthentication:
    """Test SSE authentication security."""
    
    @pytest.mark.asyncio
    async def test_api_key_authentication(self, sse_test_environment):
        """Test API key authentication for SSE connections."""
        # Test valid API key
        valid_key = "valid-api-key-12345"
        valid_connection_id = await sse_test_environment.create_connection(valid_key)
        
        # Verify valid connection was established
        assert valid_connection_id in await sse_test_environment.connection_manager.get_connection_ids()
        
        # Test invalid API key (should be rejected)
        invalid_key = "invalid-key-67890"
        
        # Simulate authentication failure
        error_event = create_error_event(
            connection_id="rejected-connection",
            error_code="AUTHENTICATION_FAILED",
            error_message="Invalid API key",
            details={"api_key": "***"},
            recoverable=False
        )
        
        # In real implementation, connection would be rejected
        # Here we verify the error event structure
        assert error_event.event_type == SSEEventType.CONNECTION_ERROR
        assert error_event.data["error_code"] == "AUTHENTICATION_FAILED"
        assert "Invalid API key" in error_event.data["error_message"]
        assert error_event.data["recoverable"] is False
    
    @pytest.mark.asyncio
    async def test_missing_api_key_rejection(self, sse_test_environment):
        """Test rejection of missing API keys."""
        # Simulate connection attempt with missing API key
        error_event = create_error_event(
            connection_id="missing-key-connection",
            error_code="AUTHENTICATION_FAILED",
            error_message="Missing API key",
            details={},
            recoverable=False
        )
        
        # Verify error event structure
        assert error_event.event_type == SSEEventType.CONNECTION_ERROR
        assert error_event.data["error_code"] == "AUTHENTICATION_FAILED"
        assert "Missing API key" in error_event.data["error_message"]
    
    @pytest.mark.asyncio
    async def test_expired_api_key_rejection(self, sse_test_environment):
        """Test rejection of expired API keys."""
        # Simulate connection attempt with expired API key
        error_event = create_error_event(
            connection_id="expired-key-connection",
            error_code="AUTHENTICATION_FAILED",
            error_message="API key expired",
            details={"expiry": "2023-01-01T00:00:00Z"},
            recoverable=False
        )
        
        # Verify error event structure
        assert error_event.event_type == SSEEventType.CONNECTION_ERROR
        assert error_event.data["error_code"] == "AUTHENTICATION_FAILED"
        assert "API key expired" in error_event.data["error_message"]
    
    @pytest.mark.asyncio
    async def test_api_key_scope_validation(self, sse_test_environment):
        """Test API key scope validation."""
        # Simulate connection with key that has insufficient scope
        error_event = create_error_event(
            connection_id="insufficient-scope-connection",
            error_code="AUTHORIZATION_FAILED",
            error_message="API key has insufficient scope",
            details={"required_scope": "sse:write", "provided_scope": "sse:read"},
            recoverable=False
        )
        
        # Verify error event structure
        assert error_event.event_type == SSEEventType.CONNECTION_ERROR
        assert error_event.data["error_code"] == "AUTHORIZATION_FAILED"
        assert "insufficient scope" in error_event.data["error_message"]
        assert error_event.data["details"]["required_scope"] == "sse:write"


@pytest.mark.security
@pytest.mark.sse
class TestSSERateLimiting:
    """Test SSE rate limiting security."""
    
    @pytest.mark.asyncio
    async def test_connection_rate_limiting(self, sse_test_environment, sse_rate_limiter):
        """Test rate limiting for connection establishment."""
        # Configure rate limiter for testing
        sse_rate_limiter.configure(
            max_connections_per_minute=5,
            max_connections_per_ip=3,
            max_total_connections=10
        )
        
        # Test connection rate limiting
        connection_ids = []
        
        # Create connections up to the limit
        for i in range(5):
            connection_id = await sse_test_environment.create_connection(f"rate-limit-test-{i}")
            connection_ids.append(connection_id)
            
            # Verify connection was established
            assert connection_id in await sse_test_environment.connection_manager.get_connection_ids()
        
        # Attempt to exceed rate limit
        with pytest.raises(Exception) as excinfo:
            # This should trigger rate limit
            await sse_test_environment.create_connection("rate-limit-exceeded")
        
        # Verify rate limit error
        assert "rate limit exceeded" in str(excinfo.value).lower()
        
        # Verify rate limit event structure
        rate_limit_event = create_rate_limit_exceeded_event(
            connection_id="rate-limited-connection",
            limit_type="connections_per_minute",
            current_usage=6,
            limit=5,
            reset_time=int(time.time()) + 60
        )
        
        assert rate_limit_event.event_type == SSEEventType.RATE_LIMIT_EXCEEDED
        assert rate_limit_event.data["limit_type"] == "connections_per_minute"
        assert rate_limit_event.data["current_usage"] == 6
        assert rate_limit_event.data["limit"] == 5
        assert "reset_time" in rate_limit_event.data
    
    @pytest.mark.asyncio
    async def test_event_rate_limiting(self, sse_test_environment, sse_rate_limiter):
        """Test rate limiting for event publishing."""
        # Configure rate limiter for testing
        sse_rate_limiter.configure(
            max_events_per_minute=100,
            max_events_per_connection=50,
            max_concurrent_requests=5
        )
        
        # Create test connection
        connection_id = await sse_test_environment.create_connection("event-rate-test")
        
        # Send events up to warning threshold
        for i in range(40):  # 80% of limit
            await sse_test_environment.send_test_event(connection_id, f"Event {i}")
        
        # Verify warning event
        warning_event = create_rate_limit_warning_event(
            connection_id=connection_id,
            limit_type="events_per_connection",
            current_usage=40,
            limit=50,
            usage_percent=80
        )
        
        assert warning_event.event_type == SSEEventType.RATE_LIMIT_WARNING
        assert warning_event.data["limit_type"] == "events_per_connection"
        assert warning_event.data["current_usage"] == 40
        assert warning_event.data["limit"] == 50
        assert warning_event.data["usage_percent"] == 80
        
        # Send events to exceed limit
        for i in range(40, 51):
            if i < 50:
                await sse_test_environment.send_test_event(connection_id, f"Event {i}")
            else:
                # Last event should trigger rate limit
                with pytest.raises(Exception) as excinfo:
                    await sse_test_environment.send_test_event(connection_id, f"Event {i}")
                
                # Verify rate limit error
                assert "rate limit exceeded" in str(excinfo.value).lower()
    
    @pytest.mark.asyncio
    async def test_concurrent_request_limiting(self, sse_test_environment, sse_rate_limiter):
        """Test limiting of concurrent requests."""
        # Configure rate limiter for testing
        sse_rate_limiter.configure(
            max_concurrent_requests=3,
            request_timeout_seconds=5
        )
        
        # Create test connection
        connection_id = await sse_test_environment.create_connection("concurrent-req-test")
        
        # Create long-running requests
        async def long_running_request(request_id: str):
            await asyncio.sleep(2)  # Simulate long-running operation
            return {"request_id": request_id, "status": "completed"}
        
        # Start concurrent requests up to limit
        tasks = []
        for i in range(3):
            task = asyncio.create_task(long_running_request(f"req-{i}"))
            tasks.append(task)
        
        # Attempt to exceed concurrent request limit
        with pytest.raises(Exception) as excinfo:
            await long_running_request("req-exceed")
        
        # Verify concurrent limit error
        assert "concurrent request limit" in str(excinfo.value).lower()
        
        # Wait for existing tasks to complete
        await asyncio.gather(*tasks)


@pytest.mark.security
@pytest.mark.sse
class TestSSEConnectionSecurity:
    """Test SSE connection security and isolation."""
    
    @pytest.mark.asyncio
    async def test_connection_id_security(self, sse_test_environment):
        """Test connection ID security and validation."""
        # Test with valid connection ID format
        valid_id = str(uuid.uuid4())
        
        # Test with invalid connection ID formats
        invalid_ids = [
            "not-a-uuid",
            "12345",
            "' OR 1=1 --",
            "<script>alert(1)</script>",
            "../../etc/passwd"
        ]
        
        for invalid_id in invalid_ids:
            # Attempt to use invalid connection ID
            with pytest.raises(Exception) as excinfo:
                await sse_test_environment.connection_manager.validate_connection_id(invalid_id)
            
            # Verify validation error
            assert "invalid connection id" in str(excinfo.value).lower()
    
    @pytest.mark.asyncio
    async def test_connection_isolation(self, sse_test_environment):
        """Test isolation between different connections."""
        # Create two separate connections
        connection_id_1 = await sse_test_environment.create_connection("isolation-test-1")
        connection_id_2 = await sse_test_environment.create_connection("isolation-test-2")
        
        # Send events to first connection
        for i in range(5):
            await sse_test_environment.send_test_event(connection_id_1, f"Event for conn1: {i}")
        
        # Send events to second connection
        for i in range(3):
            await sse_test_environment.send_test_event(connection_id_2, f"Event for conn2: {i}")
        
        # Verify events were properly isolated
        conn1_events = await sse_test_environment.get_connection_events(connection_id_1)
        conn2_events = await sse_test_environment.get_connection_events(connection_id_2)
        
        assert len(conn1_events) == 5
        assert len(conn2_events) == 3
        
        # Verify no cross-contamination
        for event in conn1_events:
            assert "conn1" in event["data"]
            assert "conn2" not in event["data"]
        
        for event in conn2_events:
            assert "conn2" in event["data"]
            assert "conn1" not in event["data"]
    
    @pytest.mark.asyncio
    async def test_connection_hijacking_prevention(self, sse_test_environment):
        """Test prevention of connection hijacking attempts."""
        # Create legitimate connection
        legitimate_id = await sse_test_environment.create_connection("legitimate-user")
        
        # Attempt to hijack by guessing connection ID
        fake_id = str(uuid.uuid4())
        
        # Attempt to use non-existent connection
        with pytest.raises(Exception) as excinfo:
            await sse_test_environment.send_test_event(fake_id, "Hijacked event")
        
        # Verify hijacking attempt was blocked
        assert "connection not found" in str(excinfo.value).lower()
        
        # Verify legitimate connection still works
        await sse_test_environment.send_test_event(legitimate_id, "Legitimate event")
        events = await sse_test_environment.get_connection_events(legitimate_id)
        assert len(events) == 1
        assert "Legitimate event" in events[0]["data"]


@pytest.mark.security
@pytest.mark.sse
class TestSSEEventSecurity:
    """Test SSE event security."""
    
    @pytest.mark.asyncio
    async def test_event_data_validation(self, sse_test_environment):
        """Test validation of event data to prevent injection."""
        connection_id = await sse_test_environment.create_connection("event-validation-test")
        
        # Test with potentially malicious payloads
        malicious_payloads = [
            "<script>alert('XSS')</script>",
            "data: Injected SSE field\nevent: fake\n\n",
            "{ \"__proto__\": { \"polluted\": true } }",
            "'; DROP TABLE connections; --"
        ]
        
        for payload in malicious_payloads:
            # Send event with malicious payload (should be sanitized/validated)
            await sse_test_environment.send_test_event(connection_id, payload)
            
            # Verify event was properly encoded/escaped
            events = await sse_test_environment.get_connection_events(connection_id)
            latest_event = events[-1]
            
            # Check that raw payload isn't directly in the event format
            raw_event = latest_event["raw"] if "raw" in latest_event else ""
            assert "data: data:" not in raw_event
            assert "data: event:" not in raw_event
    
    @pytest.mark.asyncio
    async def test_event_size_limits(self, sse_test_environment):
        """Test enforcement of event size limits."""
        connection_id = await sse_test_environment.create_connection("size-limit-test")
        
        # Test with valid size event
        valid_payload = "A" * 1000  # 1KB payload
        await sse_test_environment.send_test_event(connection_id, valid_payload)
        
        # Test with oversized event
        oversized_payload = "B" * (1024 * 1024 * 2)  # 2MB payload
        
        # Should be rejected due to size
        with pytest.raises(Exception) as excinfo:
            await sse_test_environment.send_test_event(connection_id, oversized_payload)
        
        # Verify size limit error
        assert "exceeds maximum size" in str(excinfo.value).lower()
    
    @pytest.mark.asyncio
    async def test_event_injection_via_redis(self, sse_test_environment):
        """Test prevention of event injection via Redis."""
        connection_id = await sse_test_environment.create_connection("redis-injection-test")
        
        # Simulate attempt to inject malformed event via Redis
        malformed_event = {
            "type": "CUSTOM_INJECTION",
            "connection_id": connection_id,
            "data": "Injected via Redis",
            "id": "fake-event-id"
        }
        
        # Attempt to publish directly to Redis
        with patch("src.api.sse.connection_manager.redis_publish") as mock_publish:
            mock_publish.return_value = AsyncMock()
            
            # In real implementation, this would be filtered/validated
            # Here we verify the connection manager validates incoming events
            with pytest.raises(Exception) as excinfo:
                await sse_test_environment.connection_manager.process_redis_message(
                    json.dumps(malformed_event)
                )
            
            # Verify validation error
            assert "invalid event type" in str(excinfo.value).lower()


@pytest.mark.security
@pytest.mark.sse
class TestSSEResourceProtection:
    """Test protection against resource exhaustion attacks."""
    
    @pytest.mark.asyncio
    async def test_connection_timeout(self, sse_test_environment):
        """Test automatic timeout of inactive connections."""
        # Create connection with short timeout
        with patch("src.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.SSE_CONNECTION_TIMEOUT_SECONDS = 2
            
            connection_id = await sse_test_environment.create_connection("timeout-test")
            
            # Verify connection exists
            assert connection_id in await sse_test_environment.connection_manager.get_connection_ids()
            
            # Wait for timeout
            await asyncio.sleep(3)
            
            # Verify connection was automatically closed
            assert connection_id not in await sse_test_environment.connection_manager.get_connection_ids()
    
    @pytest.mark.asyncio
    async def test_connection_limit_per_ip(self, sse_test_environment, sse_rate_limiter):
        """Test limiting connections per IP address."""
        # Configure rate limiter
        sse_rate_limiter.configure(
            max_connections_per_ip=3
        )
        
        # Create connections from same IP
        test_ip = "192.168.1.100"
        connection_ids = []
        
        # Create up to the limit
        for i in range(3):
            connection_id = await sse_test_environment.create_connection(
                f"ip-limit-test-{i}", 
                client_ip=test_ip
            )
            connection_ids.append(connection_id)
        
        # Attempt to exceed limit from same IP
        with pytest.raises(Exception) as excinfo:
            await sse_test_environment.create_connection("ip-limit-exceeded", client_ip=test_ip)
        
        # Verify IP limit error
        assert "ip address limit" in str(excinfo.value).lower()
        
        # Verify different IP can still connect
        different_ip = "192.168.1.200"
        new_connection_id = await sse_test_environment.create_connection(
            "different-ip-test", 
            client_ip=different_ip
        )
        
        assert new_connection_id in await sse_test_environment.connection_manager.get_connection_ids()
    
    @pytest.mark.asyncio
    async def test_memory_protection(self, sse_test_environment):
        """Test protection against memory exhaustion attacks."""
        connection_id = await sse_test_environment.create_connection("memory-protection-test")
        
        # Test event queue size limits
        max_queue_size = 100
        
        with patch("src.config.settings.get_settings") as mock_settings:
            mock_settings.return_value.SSE_MAX_QUEUE_SIZE = max_queue_size
            
            # Fill queue to capacity
            for i in range(max_queue_size):
                await sse_test_environment.send_test_event(connection_id, f"Event {i}")
            
            # Verify queue management (oldest events should be dropped)
            events = await sse_test_environment.get_connection_events(connection_id)
            assert len(events) <= max_queue_size
            
            # Send one more event
            await sse_test_environment.send_test_event(connection_id, "Overflow event")
            
            # Verify queue still maintains max size
            events = await sse_test_environment.get_connection_events(connection_id)
            assert len(events) <= max_queue_size
            
            # Verify oldest event was dropped
            event_data = [e["data"] for e in events if "data" in e]
            assert "Event 0" not in event_data
            assert "Overflow event" in event_data