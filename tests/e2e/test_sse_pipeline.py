"""
E2E SSE Pipeline Tests
=====================

End-to-end tests for the SSE (Server-Sent Events) pipeline functionality.
Converted from the standalone test_e2e_sse.py script to proper pytest format.

These tests:
1. Start the Docker Compose development environment
2. Connect via SSE
3. Submit DSL for rendering
4. Receive real-time progress updates
5. Validate PNG output generation
6. Save results to test-results/ directory

Tests run from the HOST environment and manage the development environment
defined in docker-compose.yaml as part of the test lifecycle.
"""

import asyncio
import pytest
import pytest_asyncio
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

from tests.e2e.conftest import (
    E2EEnvironmentManager,
    E2ESSEClient,
    DockerComposeManager,
    save_png_result,
    validate_sse_event,
    wait_for_render_completion,
)


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.e2e_sse
@pytest.mark.e2e_pipeline
@pytest.mark.slow
class TestSSEPipeline:
    """Test suite for SSE pipeline functionality."""

    async def test_sse_connection_establishment(
        self, e2e_environment: E2EEnvironmentManager, e2e_test_timeout: int
    ):
        """Test basic SSE connection establishment."""
        sse_client = await e2e_environment.get_sse_client()

        # Test connection
        response = await sse_client.connect(client_id="test-connection-client")

        assert response.status_code == 200
        assert sse_client.connection_id is not None
        # Check for content-type (could be text/event-stream or text/event-stream; charset=utf-8)
        content_type = response.headers.get("content-type", "")
        assert "text/event-stream" in content_type

        # Optionally wait briefly to see if we get initial events
        try:
            events_received = []
            async for event in sse_client.parse_events(response, timeout=5):  # Short timeout
                events_received.append(event)
                # Break after first event or if we get connection.opened
                if event.get("event") == "connection.opened" or len(events_received) >= 1:
                    break

            # We should get at least a connection event
            print(f"Received {len(events_received)} events during connection test")

        except asyncio.TimeoutError:
            # Timeout is acceptable for basic connection test
            print("Connection established but no events received within timeout (this is ok)")

        await sse_client.close()

    async def test_sse_simple_button_pipeline(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_dsl_examples: Dict[str, str],
        e2e_render_options: Dict[str, Any],
        e2e_test_results_dir: Path,
        e2e_test_timeout: int,
    ):
        """Test complete SSE pipeline with simple_button example."""
        # Get DSL content
        assert "simple_button" in e2e_dsl_examples
        dsl_content = e2e_dsl_examples["simple_button"]

        # Validate DSL content
        dsl_data = json.loads(dsl_content)
        assert "elements" in dsl_data
        assert len(dsl_data["elements"]) > 0

        sse_client = await e2e_environment.get_sse_client()

        # Step 1: Connect to SSE
        response = await sse_client.connect(client_id="simple-button-test")
        assert response.status_code == 200
        assert sse_client.connection_id is not None

        # Wait for connection to be fully registered
        await asyncio.sleep(3)

        # Step 2: Submit render request
        await sse_client.submit_render_request(dsl_content, e2e_render_options)

        # Step 3: Wait for render completion
        completion_event = await wait_for_render_completion(
            sse_client, response, timeout=e2e_test_timeout
        )

        # Step 4: Validate results
        assert validate_sse_event(completion_event, "render.completed")

        data = completion_event.get("data", {})
        result = data.get("result", {})

        # Extract PNG data
        png_data = None
        if "png_data" in result:
            png_data = result["png_data"]
        elif "png_result" in result:
            png_result = result["png_result"]
            png_data = (
                png_result.get("png_data")
                or png_result.get("data")
                or png_result.get("base64_data")
            )

        assert png_data is not None, "No PNG data received in completion event"

        # Step 5: Save PNG output
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"simple_button_sse_{timestamp}.png"
        output_path = save_png_result(png_data, filename, e2e_test_results_dir)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        await sse_client.close()

    async def test_sse_event_sequence_validation(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_dsl_examples: Dict[str, str],
        e2e_render_options: Dict[str, Any],
        e2e_test_timeout: int,
    ):
        """Test that SSE events are received in the correct sequence."""
        dsl_content = e2e_dsl_examples["simple_button"]
        sse_client = await e2e_environment.get_sse_client()

        # Connect and submit request
        response = await sse_client.connect(client_id="event-sequence-test")
        await asyncio.sleep(3)
        await sse_client.submit_render_request(dsl_content, e2e_render_options)

        # Track events received
        events_received = []
        expected_event_types = [
            "connection.opened",
            "render.started",
            "render.progress",
            "render.completed",
        ]

        async for event in sse_client.parse_events(response, timeout=e2e_test_timeout):
            events_received.append(event)
            event_type = event.get("event")

            if event_type == "render.completed":
                break
            elif event_type == "render.failed":
                pytest.fail(f"Render failed: {event.get('data', {}).get('error')}")

        # Validate event sequence
        event_types = [event.get("event") for event in events_received]

        # Check that we got connection.opened
        assert "connection.opened" in event_types

        # Check that render.started comes before render.completed
        if "render.started" in event_types and "render.completed" in event_types:
            start_idx = event_types.index("render.started")
            complete_idx = event_types.index("render.completed")
            assert start_idx < complete_idx

        # Check final event is completion
        assert event_types[-1] == "render.completed"

        await sse_client.close()

    async def test_sse_connection_timeout_handling(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_dsl_examples: Dict[str, str],
        e2e_render_options: Dict[str, Any],
    ):
        """Test SSE connection timeout handling."""
        dsl_content = e2e_dsl_examples["simple_button"]
        sse_client = await e2e_environment.get_sse_client()

        # Connect and submit request
        response = await sse_client.connect(client_id="timeout-test")
        await asyncio.sleep(3)
        await sse_client.submit_render_request(dsl_content, e2e_render_options)

        # Test with very short timeout to trigger timeout condition
        short_timeout = 5  # 5 seconds

        events_received = []
        timeout_occurred = False

        try:
            async for event in sse_client.parse_events(response, timeout=short_timeout):
                events_received.append(event)
                event_type = event.get("event")

                if event_type in ["render.completed", "render.failed"]:
                    break

        except asyncio.TimeoutError:
            timeout_occurred = True

        # Either we should complete quickly or timeout should occur
        assert len(events_received) > 0 or timeout_occurred

        await sse_client.close()

    async def test_sse_error_handling_invalid_dsl(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_render_options: Dict[str, Any],
        e2e_test_timeout: int,
    ):
        """Test SSE error handling with invalid DSL content."""
        # Invalid JSON DSL
        invalid_dsl = '{"invalid": "json", "missing": "required_fields"'

        sse_client = await e2e_environment.get_sse_client()

        # Connect and submit invalid request
        response = await sse_client.connect(client_id="error-test")
        await asyncio.sleep(3)
        await sse_client.submit_render_request(invalid_dsl, e2e_render_options)

        # Should receive error event
        error_received = False

        async for event in sse_client.parse_events(response, timeout=e2e_test_timeout):
            event_type = event.get("event")

            if event_type == "render.failed":
                error_received = True
                data = event.get("data", {})
                assert "error" in data
                break
            elif event_type == "render.completed":
                pytest.fail("Should not complete with invalid DSL")

        assert error_received, "Expected render.failed event for invalid DSL"

        await sse_client.close()

    async def test_sse_multiple_concurrent_connections(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_dsl_examples: Dict[str, str],
        e2e_render_options: Dict[str, Any],
        e2e_test_timeout: int,
    ):
        """Test multiple concurrent SSE connections."""
        dsl_content = e2e_dsl_examples["simple_button"]
        num_clients = 3

        clients = []
        tasks = []

        async def run_client(client_id: str):
            client = E2ESSEClient("http://localhost")
            clients.append(client)

            response = await client.connect(client_id=client_id)
            await asyncio.sleep(2)
            await client.submit_render_request(dsl_content, e2e_render_options)

            completion_event = await wait_for_render_completion(
                client, response, timeout=e2e_test_timeout
            )

            assert validate_sse_event(completion_event, "render.completed")
            return completion_event

        try:
            # Start concurrent clients
            for i in range(num_clients):
                task = asyncio.create_task(run_client(f"concurrent-test-{i}"))
                tasks.append(task)

            # Wait for all to complete
            results = await asyncio.gather(*tasks)

            # Validate all completed successfully
            assert len(results) == num_clients
            for result in results:
                assert validate_sse_event(result, "render.completed")

        finally:
            # Cleanup all clients
            for client in clients:
                await client.close()


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.e2e_sse
@pytest.mark.smoke
class TestSSESmoke:
    """Smoke tests for SSE pipeline - fast validation of core functionality."""

    async def test_sse_basic_connectivity(self, e2e_environment: E2EEnvironmentManager):
        """Smoke test: Basic SSE endpoint connectivity."""
        sse_client = await e2e_environment.get_sse_client()

        response = await sse_client.connect(client_id="smoke-test")

        assert response.status_code == 200
        assert sse_client.connection_id is not None

        await sse_client.close()

    async def test_sse_simple_render_smoke(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_dsl_examples: Dict[str, str],
        e2e_render_options: Dict[str, Any],
    ):
        """Smoke test: Simple render request completes."""
        dsl_content = e2e_dsl_examples["simple_button"]
        sse_client = await e2e_environment.get_sse_client()

        response = await sse_client.connect(client_id="smoke-render")
        await asyncio.sleep(2)
        await sse_client.submit_render_request(dsl_content, e2e_render_options)

        # Just verify we get some events and eventual completion
        completed = False
        event_count = 0

        async for event in sse_client.parse_events(response, timeout=30):
            event_count += 1
            event_type = event.get("event")

            if event_type == "render.completed":
                completed = True
                break
            elif event_type == "render.failed":
                pytest.fail("Smoke test render failed")

        assert completed, "Smoke test should complete successfully"
        assert event_count > 0, "Should receive at least one event"

        await sse_client.close()
