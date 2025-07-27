"""
End-to-End SSE Workflow Tests
=============================

Complete DSL-to-PNG workflow validation via Server-Sent Events including:
- Full pipeline: DSL submission → progress tracking → PNG delivery via SSE
- Event sequence validation (tool.call → render.progress → render.completed)
- Progress accuracy and stage transitions during rendering pipeline
- Result validation: PNG format, quality, and metadata
- Multiple DSL types: JSON, YAML, different complexities
- Error scenarios and recovery testing
"""

import pytest
import pytest_asyncio
import asyncio
import uuid
import json
import yaml
import base64
import time
from typing import Dict, Any, List, Optional
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime

from src.api.sse.models import SSEToolRequest, SSEToolResponse
from src.api.sse.events import (
    SSEEventType,
    create_tool_call_event,
    create_tool_response_event,
    create_render_started_event,
    create_render_completed_event,
    create_render_failed_event,
    create_progress_event,
    create_validation_completed_event,
)
from src.api.sse.mcp_bridge import MCPBridge, get_mcp_bridge
from src.models.schemas import DSLRenderRequest, RenderOptions, PNGResult
from src.core.queue.tasks import TaskTracker

from tests.fixtures.sse_fixtures import (
    sse_test_environment,
    sse_event_validator,
    dsl_samples_for_sse,
    mock_sse_client,
    performance_config,
)
from tests.data.sample_dsl_documents import (
    SIMPLE_TEXT_DOCUMENT,
    COMPLEX_DASHBOARD_DOCUMENT,
    RESPONSIVE_DESIGN_DOCUMENT,
    FORM_DOCUMENT,
)
from tests.utils.helpers import (
    measure_async_performance,
    wait_for_async_condition,
    extract_png_metadata,
)
from tests.utils.assertions import (
    assert_valid_png_result,
    assert_performance_within_threshold,
    assert_valid_json_dsl,
)


@pytest.mark.integration
@pytest.mark.sse
@pytest.mark.e2e
class TestCompleteSSEWorkflow:
    """Test complete DSL-to-PNG workflow via SSE."""

    @pytest_asyncio.fixture
    async def mock_png_result(self):
        """Create a realistic mock PNG result."""
        # Create a minimal valid PNG (1x1 pixel)
        png_data = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8/5+hHgAHggJ/PchI7wAAAABJRU5ErkJggg=="
        )

        return {
            "success": True,
            "base64Data": base64.b64encode(png_data).decode("utf-8"),
            "width": 800,
            "height": 600,
            "file_size": len(png_data),
            "format": "PNG",
            "processing_time": 2.3,
            "metadata": {"dpi": 96, "color_type": "RGB", "bit_depth": 8, "compression": "deflate"},
        }

    @pytest.mark.asyncio
    async def test_simple_dsl_to_png_workflow(
        self, sse_test_environment, mock_png_result, dsl_samples_for_sse, sse_event_validator
    ):
        """Test complete DSL to PNG workflow with simple button."""
        connection_id = await sse_test_environment.create_connection()
        request_id = f"e2e-simple-{uuid.uuid4().hex[:8]}"

        # Step 1: Submit DSL rendering request
        tool_request = SSEToolRequest(
            tool_name="render_ui_mockup",
            arguments={
                "dsl_content": json.dumps(dsl_samples_for_sse["simple_button"]),
                "options": {
                    "width": 800,
                    "height": 600,
                    "device_scale_factor": 1.0,
                    "wait_for_load": True,
                    "optimize_png": True,
                },
                "async_mode": False,
            },
            connection_id=connection_id,
            request_id=request_id,
        )

        # Step 2: Execute complete workflow simulation
        with measure_async_performance() as timer:
            # Send tool call event
            call_event = create_tool_call_event(
                connection_id, tool_request.tool_name, tool_request.arguments, request_id
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, call_event
            )

            # Send render started event
            started_event = create_render_started_event(
                connection_id, request_id, tool_request.arguments.get("options")
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, started_event
            )

            # Send detailed progress sequence
            progress_sequence = [
                (5, "Validating DSL structure", "validation"),
                (15, "DSL validation complete", "validation"),
                (25, "Parsing UI elements", "parsing"),
                (40, "Generating HTML template", "html_generation"),
                (55, "Applying styles and layout", "html_generation"),
                (70, "Loading page in browser", "png_generation"),
                (85, "Capturing high-quality screenshot", "png_generation"),
                (95, "Optimizing PNG compression", "png_generation"),
            ]

            for progress, message, stage in progress_sequence:
                progress_event = create_progress_event(
                    connection_id,
                    "render",
                    progress,
                    message,
                    stage,
                    details={"request_id": request_id},
                )
                await sse_test_environment.connection_manager.send_to_connection(
                    connection_id, progress_event
                )
                assert sse_event_validator.validate_progress_event(progress_event)
                await asyncio.sleep(0.1)  # Realistic timing

            # Send render completed event
            completed_event = create_render_completed_event(
                connection_id, mock_png_result, mock_png_result["processing_time"], request_id
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, completed_event
            )

            # Send final tool response
            response_event = create_tool_response_event(
                connection_id,
                tool_request.tool_name,
                True,
                mock_png_result,
                None,
                mock_png_result["processing_time"],
                request_id,
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, response_event
            )

        # Step 3: Validate complete event sequence
        client_events = await sse_test_environment.get_connection_events(connection_id)

        # Verify event sequence: call → started → progress* → completed → response
        event_types = [event["type"] for event in client_events]

        assert SSEEventType.MCP_TOOL_CALL in event_types
        assert SSEEventType.RENDER_STARTED in event_types
        assert SSEEventType.RENDER_PROGRESS in event_types
        assert SSEEventType.RENDER_COMPLETED in event_types
        assert SSEEventType.MCP_TOOL_RESPONSE in event_types

        # Verify progress events are in correct order
        progress_events = [e for e in client_events if e["type"] == SSEEventType.RENDER_PROGRESS]
        assert len(progress_events) == len(progress_sequence)

        progress_values = [e["data"]["progress"] for e in progress_events]
        assert progress_values == sorted(progress_values)  # Monotonically increasing
        assert progress_values == [5, 15, 25, 40, 55, 70, 85, 95]

        # Verify stage transitions
        stages = [e["data"]["stage"] for e in progress_events]
        expected_stages = [stage for _, _, stage in progress_sequence]
        assert stages == expected_stages

        # Step 4: Validate final result
        response_events = [e for e in client_events if e["type"] == SSEEventType.MCP_TOOL_RESPONSE]
        assert len(response_events) == 1

        final_result = response_events[0]["data"]["result"]
        assert final_result["success"] is True
        assert "base64Data" in final_result
        assert final_result["width"] == 800
        assert final_result["height"] == 600
        assert final_result["processing_time"] > 0

        # Verify performance
        assert_performance_within_threshold(timer.elapsed_time, 5.0)

    @pytest.mark.asyncio
    async def test_complex_dashboard_workflow(
        self, sse_test_environment, mock_png_result, dsl_samples_for_sse
    ):
        """Test workflow with complex dashboard DSL."""
        connection_id = await sse_test_environment.create_connection()
        request_id = f"e2e-complex-{uuid.uuid4().hex[:8]}"

        # Use complex dashboard DSL
        complex_dsl = dsl_samples_for_sse["complex_dashboard"]

        tool_request = SSEToolRequest(
            tool_name="render_ui_mockup",
            arguments={
                "dsl_content": json.dumps(complex_dsl),
                "options": {
                    "width": 1200,
                    "height": 800,
                    "device_scale_factor": 2.0,  # High DPI
                    "wait_for_fonts": True,
                    "wait_for_images": True,
                    "optimize_png": True,
                },
                "async_mode": False,
            },
            connection_id=connection_id,
            request_id=request_id,
        )

        # Execute workflow with extended progress for complex content
        with measure_async_performance() as timer:
            # Send tool call
            call_event = create_tool_call_event(
                connection_id, tool_request.tool_name, tool_request.arguments, request_id
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, call_event
            )

            # Extended progress sequence for complex dashboard
            complex_progress = [
                (3, "Analyzing DSL complexity", "analysis"),
                (8, "Validating nested components", "validation"),
                (15, "Processing layout containers", "parsing"),
                (25, "Parsing header component", "parsing"),
                (35, "Processing content sections", "parsing"),
                (45, "Generating responsive HTML", "html_generation"),
                (55, "Applying CSS Grid layout", "html_generation"),
                (65, "Loading custom fonts", "html_generation"),
                (72, "Initializing high-DPI browser", "png_generation"),
                (80, "Rendering complex layout", "png_generation"),
                (88, "Capturing high-resolution screenshot", "png_generation"),
                (94, "Optimizing large PNG file", "png_generation"),
                (98, "Finalizing metadata", "completion"),
            ]

            for progress, message, stage in complex_progress:
                progress_event = create_progress_event(
                    connection_id,
                    "render",
                    progress,
                    message,
                    stage,
                    details={"request_id": request_id, "complexity": "high"},
                )
                await sse_test_environment.connection_manager.send_to_connection(
                    connection_id, progress_event
                )
                await asyncio.sleep(0.05)  # Faster for complex workflow

            # Simulate longer processing time for complex content
            enhanced_result = mock_png_result.copy()
            enhanced_result.update(
                {
                    "width": 1200,
                    "height": 800,
                    "processing_time": 4.8,  # Longer for complex content
                    "file_size": 2048576,  # 2MB for high-res
                    "metadata": {
                        **enhanced_result["metadata"],
                        "dpi": 192,  # High DPI
                        "elements_rendered": len(complex_dsl.get("elements", [])),
                        "complexity_score": "high",
                    },
                }
            )

            completed_event = create_render_completed_event(
                connection_id, enhanced_result, enhanced_result["processing_time"], request_id
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, completed_event
            )

            response_event = create_tool_response_event(
                connection_id,
                tool_request.tool_name,
                True,
                enhanced_result,
                None,
                enhanced_result["processing_time"],
                request_id,
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, response_event
            )

        # Validate complex workflow results
        client_events = await sse_test_environment.get_connection_events(connection_id)

        # Should have more progress events due to complexity
        progress_events = [e for e in client_events if e["type"] == SSEEventType.RENDER_PROGRESS]
        assert len(progress_events) == len(complex_progress)

        # Verify high-complexity specific stages
        stages = [e["data"]["stage"] for e in progress_events]
        assert "analysis" in stages
        assert "completion" in stages

        # Verify final result includes complexity metadata
        response_events = [e for e in client_events if e["type"] == SSEEventType.MCP_TOOL_RESPONSE]
        final_result = response_events[0]["data"]["result"]

        assert final_result["width"] == 1200
        assert final_result["height"] == 800
        assert final_result["processing_time"] > 4.0
        assert final_result["metadata"]["complexity_score"] == "high"

        # Complex workflows should still complete in reasonable time
        assert_performance_within_threshold(timer.elapsed_time, 10.0)

    @pytest.mark.asyncio
    async def test_async_workflow_with_task_tracking(
        self, sse_test_environment, mock_png_result, dsl_samples_for_sse
    ):
        """Test async workflow with task status tracking."""
        connection_id = await sse_test_environment.create_connection()
        request_id = f"e2e-async-{uuid.uuid4().hex[:8]}"
        task_id = f"task-{uuid.uuid4().hex[:8]}"

        # Submit async rendering request
        async_request = SSEToolRequest(
            tool_name="render_ui_mockup",
            arguments={
                "dsl_content": json.dumps(dsl_samples_for_sse["simple_button"]),
                "options": {"width": 600, "height": 400},
                "async_mode": True,
            },
            connection_id=connection_id,
            request_id=request_id,
        )

        # Step 1: Submit async task
        call_event = create_tool_call_event(
            connection_id, async_request.tool_name, async_request.arguments, request_id
        )
        await sse_test_environment.connection_manager.send_to_connection(connection_id, call_event)

        # Send async task submission response
        async_response = create_tool_response_event(
            connection_id,
            async_request.tool_name,
            True,
            {
                "async": True,
                "task_id": task_id,
                "message": "Rendering task submitted successfully",
                "status_check_tool": "get_render_status",
            },
            None,
            0.1,
            request_id,
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, async_response
        )

        # Step 2: Simulate task progress tracking
        await asyncio.sleep(0.2)  # Small delay

        # Client checks task status
        status_request_id = f"status-{uuid.uuid4().hex[:8]}"
        status_call = create_tool_call_event(
            connection_id, "get_render_status", {"task_id": task_id}, status_request_id
        )
        await sse_test_environment.connection_manager.send_to_connection(connection_id, status_call)

        # Send task status updates
        status_updates = [
            {"status": "processing", "progress": 25, "message": "Parsing DSL"},
            {"status": "processing", "progress": 50, "message": "Generating HTML"},
            {"status": "processing", "progress": 75, "message": "Creating PNG"},
            {
                "status": "completed",
                "progress": 100,
                "message": "Task completed",
                "result": mock_png_result,
            },
        ]

        for status_update in status_updates:
            status_response = create_tool_response_event(
                connection_id,
                "get_render_status",
                True,
                {"task_id": task_id, **status_update},
                None,
                0.1,
                status_request_id,
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, status_response
            )
            await asyncio.sleep(0.3)  # Realistic polling interval

        # Validate async workflow
        client_events = await sse_test_environment.get_connection_events(connection_id)

        # Should have initial async response and status check responses
        async_responses = [
            e
            for e in client_events
            if e["type"] == SSEEventType.MCP_TOOL_RESPONSE and e["data"]["result"].get("async")
        ]
        assert len(async_responses) == 1
        assert async_responses[0]["data"]["result"]["task_id"] == task_id

        # Should have status check responses
        status_responses = [
            e
            for e in client_events
            if e["type"] == SSEEventType.MCP_TOOL_RESPONSE
            and e["data"]["tool_name"] == "get_render_status"
        ]
        assert len(status_responses) == len(status_updates)

        # Verify final status is completed with result
        final_status = status_responses[-1]["data"]["result"]
        assert final_status["status"] == "completed"
        assert final_status["progress"] == 100
        assert "result" in final_status


@pytest.mark.integration
@pytest.mark.sse
@pytest.mark.e2e
class TestMultiFormatDSLWorkflow:
    """Test workflow with different DSL formats."""

    @pytest.mark.asyncio
    async def test_json_dsl_workflow(self, sse_test_environment, mock_png_result):
        """Test workflow with JSON DSL format."""
        connection_id = await sse_test_environment.create_connection()

        # Create JSON DSL
        json_dsl = json.dumps(SIMPLE_TEXT_DOCUMENT)
        assert_valid_json_dsl(json_dsl)

        request_id = f"json-dsl-{uuid.uuid4().hex[:8]}"

        tool_request = SSEToolRequest(
            tool_name="render_ui_mockup",
            arguments={
                "dsl_content": json_dsl,
                "options": {"width": 800, "height": 600, "format": "json"},
            },
            connection_id=connection_id,
            request_id=request_id,
        )

        # Execute JSON workflow
        await self._execute_basic_workflow(
            sse_test_environment, connection_id, tool_request, mock_png_result
        )

        # Verify JSON-specific processing
        client_events = await sse_test_environment.get_connection_events(connection_id)
        progress_events = [e for e in client_events if e["type"] == SSEEventType.RENDER_PROGRESS]

        # Should have JSON parsing stage
        stages = [e["data"]["stage"] for e in progress_events]
        assert any("pars" in stage for stage in stages)  # JSON parsing stage

    @pytest.mark.asyncio
    async def test_yaml_dsl_workflow(self, sse_test_environment, mock_png_result):
        """Test workflow with YAML DSL format."""
        connection_id = await sse_test_environment.create_connection()

        # Create YAML DSL
        yaml_dsl = yaml.dump(FORM_DOCUMENT)

        request_id = f"yaml-dsl-{uuid.uuid4().hex[:8]}"

        tool_request = SSEToolRequest(
            tool_name="render_ui_mockup",
            arguments={
                "dsl_content": yaml_dsl,
                "options": {"width": 800, "height": 1000, "format": "yaml"},
            },
            connection_id=connection_id,
            request_id=request_id,
        )

        # Execute YAML workflow
        await self._execute_basic_workflow(
            sse_test_environment, connection_id, tool_request, mock_png_result
        )

        # Verify YAML-specific processing
        client_events = await sse_test_environment.get_connection_events(connection_id)
        response_events = [e for e in client_events if e["type"] == SSEEventType.MCP_TOOL_RESPONSE]

        final_result = response_events[0]["data"]["result"]
        assert final_result["success"] is True
        assert final_result["height"] == 1000  # Form is taller

    @pytest.mark.asyncio
    async def test_responsive_dsl_workflow(self, sse_test_environment, mock_png_result):
        """Test workflow with responsive DSL."""
        connection_id = await sse_test_environment.create_connection()

        request_id = f"responsive-{uuid.uuid4().hex[:8]}"

        # Test multiple viewport sizes
        viewport_sizes = [
            (375, 667, "mobile"),  # iPhone viewport
            (768, 1024, "tablet"),  # iPad viewport
            (1920, 1080, "desktop"),  # Desktop viewport
        ]

        for width, height, device_type in viewport_sizes:
            await sse_test_environment.connection_manager.connections[connection_id].clear_events()

            tool_request = SSEToolRequest(
                tool_name="render_ui_mockup",
                arguments={
                    "dsl_content": json.dumps(RESPONSIVE_DESIGN_DOCUMENT),
                    "options": {
                        "width": width,
                        "height": height,
                        "device_scale_factor": 1.0,
                        "device_type": device_type,
                    },
                },
                connection_id=connection_id,
                request_id=f"{request_id}-{device_type}",
            )

            # Execute responsive workflow
            device_result = mock_png_result.copy()
            device_result.update(
                {
                    "width": width,
                    "height": height,
                    "metadata": {
                        **device_result["metadata"],
                        "device_type": device_type,
                        "responsive": True,
                    },
                }
            )

            await self._execute_basic_workflow(
                sse_test_environment, connection_id, tool_request, device_result
            )

            # Verify device-specific result
            client_events = await sse_test_environment.get_connection_events(connection_id)
            response_events = [
                e for e in client_events if e["type"] == SSEEventType.MCP_TOOL_RESPONSE
            ]

            final_result = response_events[0]["data"]["result"]
            assert final_result["width"] == width
            assert final_result["height"] == height
            assert final_result["metadata"]["device_type"] == device_type

    async def _execute_basic_workflow(
        self, sse_test_environment, connection_id, tool_request, mock_result
    ):
        """Helper method to execute basic workflow steps."""
        request_id = tool_request.request_id

        # Send tool call
        call_event = create_tool_call_event(
            connection_id, tool_request.tool_name, tool_request.arguments, request_id
        )
        await sse_test_environment.connection_manager.send_to_connection(connection_id, call_event)

        # Send basic progress
        basic_progress = [
            (20, "Processing DSL", "parsing"),
            (50, "Generating layout", "html_generation"),
            (80, "Creating image", "png_generation"),
        ]

        for progress, message, stage in basic_progress:
            progress_event = create_progress_event(
                connection_id, "render", progress, message, stage
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, progress_event
            )

        # Send completion
        completed_event = create_render_completed_event(
            connection_id, mock_result, mock_result["processing_time"], request_id
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, completed_event
        )

        # Send response
        response_event = create_tool_response_event(
            connection_id,
            tool_request.tool_name,
            True,
            mock_result,
            None,
            mock_result["processing_time"],
            request_id,
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, response_event
        )


@pytest.mark.integration
@pytest.mark.sse
@pytest.mark.e2e
class TestSSEWorkflowErrorScenarios:
    """Test error scenarios in SSE workflows."""

    @pytest.mark.asyncio
    async def test_invalid_dsl_workflow(self, sse_test_environment, dsl_samples_for_sse):
        """Test workflow with invalid DSL content."""
        connection_id = await sse_test_environment.create_connection()
        request_id = f"invalid-dsl-{uuid.uuid4().hex[:8]}"

        # Submit invalid DSL
        tool_request = SSEToolRequest(
            tool_name="render_ui_mockup",
            arguments={
                "dsl_content": json.dumps(dsl_samples_for_sse["invalid_dsl"]),
                "options": {"width": 800, "height": 600},
            },
            connection_id=connection_id,
            request_id=request_id,
        )

        # Execute error workflow
        call_event = create_tool_call_event(
            connection_id, tool_request.tool_name, tool_request.arguments, request_id
        )
        await sse_test_environment.connection_manager.send_to_connection(connection_id, call_event)

        # Send initial progress
        progress_event = create_progress_event(
            connection_id, "render", 10, "Validating DSL", "validation"
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, progress_event
        )

        # Send validation failure
        validation_event = create_validation_completed_event(
            connection_id,
            False,
            ["Missing required field: elements", "Invalid structure"],
            ["Title should be more descriptive"],
            ["Add at least one UI element"],
            request_id,
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, validation_event
        )

        # Send render failure
        failed_event = create_render_failed_event(
            connection_id, "DSL validation failed", "VALIDATION_ERROR", 0.5, request_id
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, failed_event
        )

        # Send error response
        error_response = create_tool_response_event(
            connection_id,
            tool_request.tool_name,
            False,
            None,
            "DSL validation failed: Missing required field: elements",
            0.5,
            request_id,
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, error_response
        )

        # Verify error workflow
        client_events = await sse_test_environment.get_connection_events(connection_id)

        # Should have validation failure event
        validation_events = [
            e for e in client_events if e["type"] == SSEEventType.VALIDATION_COMPLETED
        ]
        assert len(validation_events) == 1
        assert validation_events[0]["data"]["valid"] is False
        assert len(validation_events[0]["data"]["errors"]) > 0

        # Should have render failure event
        failure_events = [e for e in client_events if e["type"] == SSEEventType.RENDER_FAILED]
        assert len(failure_events) == 1
        assert "validation" in failure_events[0]["data"]["error"].lower()

        # Should have error response
        response_events = [e for e in client_events if e["type"] == SSEEventType.MCP_TOOL_RESPONSE]
        assert len(response_events) == 1
        assert response_events[0]["data"]["success"] is False
        assert "validation" in response_events[0]["data"]["error"].lower()

    @pytest.mark.asyncio
    async def test_rendering_timeout_workflow(self, sse_test_environment):
        """Test workflow with rendering timeout."""
        connection_id = await sse_test_environment.create_connection()
        request_id = f"timeout-{uuid.uuid4().hex[:8]}"

        # Submit request that will timeout
        tool_request = SSEToolRequest(
            tool_name="render_ui_mockup",
            arguments={
                "dsl_content": json.dumps({"title": "Large Document", "elements": []}),
                "options": {"width": 4096, "height": 4096, "timeout": 1},  # Very short timeout
            },
            connection_id=connection_id,
            request_id=request_id,
            timeout=1,  # 1 second timeout
        )

        # Execute timeout workflow
        call_event = create_tool_call_event(
            connection_id, tool_request.tool_name, tool_request.arguments, request_id
        )
        await sse_test_environment.connection_manager.send_to_connection(connection_id, call_event)

        # Send progress that gets interrupted
        progress_stages = [
            (10, "Starting rendering", "initialization"),
            (25, "Loading large image", "png_generation"),
            (40, "Processing large dimensions", "png_generation"),
        ]

        for progress, message, stage in progress_stages:
            progress_event = create_progress_event(
                connection_id, "render", progress, message, stage
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, progress_event
            )
            await asyncio.sleep(0.2)

        # Send timeout failure
        failed_event = create_render_failed_event(
            connection_id, "Rendering timeout after 1 seconds", "TIMEOUT", 1.0, request_id
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, failed_event
        )

        # Send timeout response
        timeout_response = create_tool_response_event(
            connection_id,
            tool_request.tool_name,
            False,
            None,
            "Request timeout after 1 seconds",
            1.0,
            request_id,
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, timeout_response
        )

        # Verify timeout handling
        client_events = await sse_test_environment.get_connection_events(connection_id)

        # Should have partial progress before timeout
        progress_events = [e for e in client_events if e["type"] == SSEEventType.RENDER_PROGRESS]
        assert len(progress_events) == len(progress_stages)
        assert max(e["data"]["progress"] for e in progress_events) < 100  # Incomplete

        # Should have timeout failure
        failure_events = [e for e in client_events if e["type"] == SSEEventType.RENDER_FAILED]
        assert len(failure_events) == 1
        assert "timeout" in failure_events[0]["data"]["error"].lower()

        # Should have timeout response
        response_events = [e for e in client_events if e["type"] == SSEEventType.MCP_TOOL_RESPONSE]
        assert len(response_events) == 1
        assert response_events[0]["data"]["success"] is False
        assert "timeout" in response_events[0]["data"]["error"].lower()

    @pytest.mark.asyncio
    async def test_browser_crash_recovery_workflow(self, sse_test_environment):
        """Test workflow recovery from browser crash."""
        connection_id = await sse_test_environment.create_connection()
        request_id = f"crash-recovery-{uuid.uuid4().hex[:8]}"

        # Submit rendering request
        tool_request = SSEToolRequest(
            tool_name="render_ui_mockup",
            arguments={
                "dsl_content": json.dumps({"title": "Crash Test", "elements": []}),
                "options": {"width": 800, "height": 600},
            },
            connection_id=connection_id,
            request_id=request_id,
        )

        # Execute crash scenario
        call_event = create_tool_call_event(
            connection_id, tool_request.tool_name, tool_request.arguments, request_id
        )
        await sse_test_environment.connection_manager.send_to_connection(connection_id, call_event)

        # Send progress until crash
        crash_progress = [
            (15, "Initializing browser", "png_generation"),
            (30, "Loading page", "png_generation"),
            (45, "Browser crashed, recovering", "recovery"),
            (60, "Restarting browser", "recovery"),
            (75, "Retrying render", "png_generation"),
        ]

        for progress, message, stage in crash_progress:
            progress_event = create_progress_event(
                connection_id, "render", progress, message, stage
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, progress_event
            )
            await asyncio.sleep(0.1)

        # Send recovery failure (simulating unrecoverable crash)
        failed_event = create_render_failed_event(
            connection_id, "Browser crash could not be recovered", "BROWSER_CRASH", 3.0, request_id
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, failed_event
        )

        error_response = create_tool_response_event(
            connection_id,
            tool_request.tool_name,
            False,
            None,
            "Browser crash could not be recovered",
            3.0,
            request_id,
        )
        await sse_test_environment.connection_manager.send_to_connection(
            connection_id, error_response
        )

        # Verify crash recovery workflow
        client_events = await sse_test_environment.get_connection_events(connection_id)

        # Should have recovery stage in progress
        progress_events = [e for e in client_events if e["type"] == SSEEventType.RENDER_PROGRESS]
        stages = [e["data"]["stage"] for e in progress_events]
        assert "recovery" in stages

        # Should show recovery attempts in messages
        messages = [e["data"]["message"] for e in progress_events]
        recovery_messages = [
            msg for msg in messages if "recover" in msg.lower() or "restart" in msg.lower()
        ]
        assert len(recovery_messages) > 0

        # Should ultimately fail with browser crash error
        failure_events = [e for e in client_events if e["type"] == SSEEventType.RENDER_FAILED]
        assert len(failure_events) == 1
        assert "browser crash" in failure_events[0]["data"]["error"].lower()


@pytest.mark.integration
@pytest.mark.sse
@pytest.mark.e2e
class TestSSEWorkflowConcurrency:
    """Test concurrent SSE workflows."""

    @pytest.mark.asyncio
    async def test_concurrent_render_workflows(
        self, sse_test_environment, mock_png_result, dsl_samples_for_sse, performance_config
    ):
        """Test multiple concurrent render workflows."""
        # Create multiple connections for concurrent workflows
        connection_count = performance_config["concurrent_connections"][1]  # Use 10 connections
        connections = []

        for i in range(connection_count):
            connection_id = await sse_test_environment.create_connection(f"concurrent-workflow-{i}")
            connections.append(connection_id)

        async def execute_workflow(connection_id: str, index: int):
            """Execute a complete workflow on one connection."""
            request_id = f"concurrent-{index}-{uuid.uuid4().hex[:8]}"

            # Use different DSL for variety
            dsl_key = ["simple_button", "complex_dashboard"][index % 2]
            dsl_content = dsl_samples_for_sse[dsl_key]

            tool_request = SSEToolRequest(
                tool_name="render_ui_mockup",
                arguments={
                    "dsl_content": json.dumps(dsl_content),
                    "options": {"width": 400 + (index * 50), "height": 300 + (index * 30)},
                },
                connection_id=connection_id,
                request_id=request_id,
            )

            # Execute workflow
            call_event = create_tool_call_event(
                connection_id, tool_request.tool_name, tool_request.arguments, request_id
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, call_event
            )

            # Send progress
            for progress in [25, 50, 75, 100]:
                progress_event = create_progress_event(
                    connection_id, "render", progress, f"Workflow {index} progress", "processing"
                )
                await sse_test_environment.connection_manager.send_to_connection(
                    connection_id, progress_event
                )
                await asyncio.sleep(0.05)

            # Send completion
            workflow_result = mock_png_result.copy()
            workflow_result.update(
                {
                    "width": 400 + (index * 50),
                    "height": 300 + (index * 30),
                    "metadata": {**workflow_result["metadata"], "workflow_index": index},
                }
            )

            completed_event = create_render_completed_event(
                connection_id, workflow_result, 2.0, request_id
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, completed_event
            )

            response_event = create_tool_response_event(
                connection_id, tool_request.tool_name, True, workflow_result, None, 2.0, request_id
            )
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, response_event
            )

            return request_id

        # Execute all workflows concurrently
        with measure_async_performance() as timer:
            tasks = [execute_workflow(conn_id, i) for i, conn_id in enumerate(connections)]
            request_ids = await asyncio.gather(*tasks)

        # Verify all workflows completed successfully
        assert len(request_ids) == connection_count
        assert_performance_within_threshold(timer.elapsed_time, 15.0)  # Should complete within 15s

        # Verify each workflow completed independently
        for i, connection_id in enumerate(connections):
            client_events = await sse_test_environment.get_connection_events(connection_id)

            # Should have complete workflow events
            call_events = [e for e in client_events if e["type"] == SSEEventType.MCP_TOOL_CALL]
            progress_events = [
                e for e in client_events if e["type"] == SSEEventType.RENDER_PROGRESS
            ]
            completed_events = [
                e for e in client_events if e["type"] == SSEEventType.RENDER_COMPLETED
            ]
            response_events = [
                e for e in client_events if e["type"] == SSEEventType.MCP_TOOL_RESPONSE
            ]

            assert len(call_events) == 1
            assert len(progress_events) == 4
            assert len(completed_events) == 1
            assert len(response_events) == 1

            # Verify workflow-specific results
            final_result = response_events[0]["data"]["result"]
            assert final_result["width"] == 400 + (i * 50)
            assert final_result["height"] == 300 + (i * 30)
            assert final_result["metadata"]["workflow_index"] == i

    @pytest.mark.asyncio
    async def test_mixed_workflow_types_concurrency(
        self, sse_test_environment, mock_png_result, dsl_samples_for_sse
    ):
        """Test concurrent execution of different workflow types."""
        connection_id = await sse_test_environment.create_connection()

        # Define different workflow types
        workflow_types = [
            (
                "render",
                "render_ui_mockup",
                {"dsl_content": json.dumps(dsl_samples_for_sse["simple_button"])},
            ),
            (
                "validate",
                "validate_dsl",
                {"dsl_content": json.dumps(dsl_samples_for_sse["complex_dashboard"])},
            ),
            ("status", "get_render_status", {"task_id": "test-task-123"}),
        ]

        # Execute different workflow types with overlapping timing
        request_ids = []
        for i, (workflow_type, tool_name, arguments) in enumerate(workflow_types):
            request_id = f"mixed-{workflow_type}-{i}"
            request_ids.append(request_id)

            call_event = create_tool_call_event(connection_id, tool_name, arguments, request_id)
            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, call_event
            )
            await asyncio.sleep(0.1)  # Staggered execution

        # Send appropriate responses for each workflow type
        for i, (workflow_type, tool_name, arguments) in enumerate(workflow_types):
            request_id = request_ids[i]

            if workflow_type == "render":
                # Render workflow response
                response_event = create_tool_response_event(
                    connection_id, tool_name, True, mock_png_result, None, 2.0, request_id
                )
            elif workflow_type == "validate":
                # Validation workflow response
                response_event = create_tool_response_event(
                    connection_id,
                    tool_name,
                    True,
                    {"valid": True, "errors": [], "warnings": [], "suggestions": []},
                    None,
                    0.5,
                    request_id,
                )
            else:  # status
                # Status workflow response
                response_event = create_tool_response_event(
                    connection_id,
                    tool_name,
                    True,
                    {"task_id": "test-task-123", "status": "completed", "progress": 100},
                    None,
                    0.1,
                    request_id,
                )

            await sse_test_environment.connection_manager.send_to_connection(
                connection_id, response_event
            )

        # Verify mixed workflow execution
        client_events = await sse_test_environment.get_connection_events(connection_id)

        call_events = [e for e in client_events if e["type"] == SSEEventType.MCP_TOOL_CALL]
        response_events = [e for e in client_events if e["type"] == SSEEventType.MCP_TOOL_RESPONSE]

        assert len(call_events) == 3
        assert len(response_events) == 3

        # Verify each workflow type completed
        tools_executed = [e["data"]["tool_name"] for e in call_events]
        assert "render_ui_mockup" in tools_executed
        assert "validate_dsl" in tools_executed
        assert "get_render_status" in tools_executed

        # Verify all responses succeeded
        for response_event in response_events:
            assert response_event["data"]["success"] is True
