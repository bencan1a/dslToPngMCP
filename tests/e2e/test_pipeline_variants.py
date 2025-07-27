"""
E2E Pipeline Variants Tests
==========================

End-to-end tests for different DSL input scenarios and pipeline variations.
Tests the complete SSE pipeline with various DSL examples and configurations.

These tests validate:
- Different DSL file formats (JSON, YAML)
- Various UI component types and combinations
- Different render options and configurations
- Edge cases and error conditions
- Performance with complex DSL structures

All tests run from the HOST environment and manage the Docker Compose
development environment automatically.
"""

import asyncio
import pytest
import pytest_asyncio
import time
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List

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
@pytest.mark.e2e_pipeline
@pytest.mark.slow
class TestPipelineVariants:
    """Test suite for different DSL pipeline scenarios."""

    @pytest.mark.parametrize(
        "example_name", ["simple_button", "login_form", "dashboard", "minimal"]
    )
    async def test_pipeline_with_different_examples(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_dsl_examples: Dict[str, str],
        e2e_render_options: Dict[str, Any],
        e2e_test_results_dir: Path,
        e2e_test_timeout: int,
        example_name: str,
    ):
        """Test pipeline with different DSL examples."""
        if example_name not in e2e_dsl_examples:
            pytest.skip(f"Example {example_name} not found in examples directory")

        dsl_content = e2e_dsl_examples[example_name]

        # Validate DSL content
        try:
            dsl_data = json.loads(dsl_content)
        except json.JSONDecodeError:
            pytest.skip(f"Example {example_name} is not valid JSON")

        sse_client = await e2e_environment.get_sse_client()

        # Execute pipeline
        response = await sse_client.connect(client_id=f"variant-{example_name}")
        await asyncio.sleep(3)
        await sse_client.submit_render_request(dsl_content, e2e_render_options)

        completion_event = await wait_for_render_completion(
            sse_client, response, timeout=e2e_test_timeout
        )

        # Validate results
        assert validate_sse_event(completion_event, "render.completed")

        data = completion_event.get("data", {})
        result = data.get("result", {})

        # Extract and save PNG
        png_data = self._extract_png_data(result)
        assert png_data is not None, f"No PNG data for {example_name}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{example_name}_variant_{timestamp}.png"
        output_path = save_png_result(png_data, filename, e2e_test_results_dir)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        await sse_client.close()

    @pytest.mark.parametrize(
        "render_config",
        [
            {"width": 400, "height": 300, "device_scale_factor": 1.0},
            {"width": 800, "height": 600, "device_scale_factor": 1.5},
            {"width": 1200, "height": 800, "device_scale_factor": 2.0},
            {"width": 320, "height": 568, "device_scale_factor": 1.0},  # Mobile
        ],
    )
    async def test_pipeline_different_render_options(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_dsl_examples: Dict[str, str],
        e2e_test_results_dir: Path,
        e2e_test_timeout: int,
        render_config: Dict[str, Any],
    ):
        """Test pipeline with different render configurations."""
        dsl_content = e2e_dsl_examples["simple_button"]

        # Merge with base options
        render_options = {"optimize_png": False, "timeout": 30, **render_config}

        sse_client = await e2e_environment.get_sse_client()

        response = await sse_client.connect(client_id="render-options-test")
        await asyncio.sleep(3)
        await sse_client.submit_render_request(dsl_content, render_options)

        completion_event = await wait_for_render_completion(
            sse_client, response, timeout=e2e_test_timeout
        )

        # Validate completion
        assert validate_sse_event(completion_event, "render.completed")

        # Save result with config in filename
        data = completion_event.get("data", {})
        result = data.get("result", {})
        png_data = self._extract_png_data(result)
        assert png_data is not None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        config_str = f"{render_config['width']}x{render_config['height']}_scale{render_config['device_scale_factor']}"
        filename = f"render_options_{config_str}_{timestamp}.png"
        output_path = save_png_result(png_data, filename, e2e_test_results_dir)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        await sse_client.close()

    async def test_pipeline_complex_dsl_structure(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_render_options: Dict[str, Any],
        e2e_test_results_dir: Path,
        e2e_test_timeout: int,
    ):
        """Test pipeline with complex DSL structure."""
        # Create a complex DSL with multiple elements
        complex_dsl = {
            "title": "Complex UI Test",
            "description": "Testing complex DSL structure",
            "width": 800,
            "height": 600,
            "elements": [
                {
                    "type": "button",
                    "id": "btn1",
                    "layout": {"x": 50, "y": 50, "width": 120, "height": 40},
                    "style": {"background": "#007bff", "color": "white"},
                    "label": "Button 1",
                },
                {
                    "type": "button",
                    "id": "btn2",
                    "layout": {"x": 200, "y": 50, "width": 120, "height": 40},
                    "style": {"background": "#28a745", "color": "white"},
                    "label": "Button 2",
                },
                {
                    "type": "text",
                    "id": "title",
                    "layout": {"x": 50, "y": 20, "width": 300, "height": 20},
                    "style": {"fontSize": 18, "fontWeight": "bold"},
                    "content": "Complex UI Example",
                },
            ],
            "css": """
            .complex-container { 
                background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
                padding: 20px;
            }
            """,
        }

        dsl_content = json.dumps(complex_dsl, indent=2)
        sse_client = await e2e_environment.get_sse_client()

        response = await sse_client.connect(client_id="complex-dsl-test")
        await asyncio.sleep(3)
        await sse_client.submit_render_request(dsl_content, e2e_render_options)

        completion_event = await wait_for_render_completion(
            sse_client, response, timeout=e2e_test_timeout
        )

        assert validate_sse_event(completion_event, "render.completed")

        # Save complex DSL result
        data = completion_event.get("data", {})
        result = data.get("result", {})
        png_data = self._extract_png_data(result)
        assert png_data is not None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"complex_dsl_{timestamp}.png"
        output_path = save_png_result(png_data, filename, e2e_test_results_dir)

        assert output_path.exists()
        assert output_path.stat().st_size > 0

        await sse_client.close()

    async def test_pipeline_minimal_dsl(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_render_options: Dict[str, Any],
        e2e_test_results_dir: Path,
        e2e_test_timeout: int,
    ):
        """Test pipeline with minimal DSL structure."""
        minimal_dsl = {"title": "Minimal Test", "width": 200, "height": 100, "elements": []}

        dsl_content = json.dumps(minimal_dsl)
        sse_client = await e2e_environment.get_sse_client()

        response = await sse_client.connect(client_id="minimal-dsl-test")
        await asyncio.sleep(3)
        await sse_client.submit_render_request(dsl_content, e2e_render_options)

        completion_event = await wait_for_render_completion(
            sse_client, response, timeout=e2e_test_timeout
        )

        assert validate_sse_event(completion_event, "render.completed")

        # Save minimal DSL result
        data = completion_event.get("data", {})
        result = data.get("result", {})
        png_data = self._extract_png_data(result)
        assert png_data is not None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"minimal_dsl_{timestamp}.png"
        output_path = save_png_result(png_data, filename, e2e_test_results_dir)

        assert output_path.exists()

        await sse_client.close()

    async def test_pipeline_error_recovery(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_dsl_examples: Dict[str, str],
        e2e_render_options: Dict[str, Any],
        e2e_test_timeout: int,
    ):
        """Test pipeline error recovery - submit invalid then valid DSL."""
        sse_client = await e2e_environment.get_sse_client()

        # First, submit invalid DSL
        invalid_dsl = '{"invalid": "json", "missing": "bracket"'

        response = await sse_client.connect(client_id="error-recovery-test")
        await asyncio.sleep(3)
        await sse_client.submit_render_request(invalid_dsl, e2e_render_options)

        # Should get error
        error_received = False
        async for event in sse_client.parse_events(response, timeout=30):
            event_type = event.get("event")
            if event_type == "render.failed":
                error_received = True
                break
            elif event_type == "render.completed":
                pytest.fail("Should not complete with invalid DSL")

        assert error_received, "Should receive error for invalid DSL"

        # Close and reconnect for valid DSL
        await sse_client.close()

        # Now submit valid DSL
        valid_dsl = e2e_dsl_examples["simple_button"]
        sse_client = await e2e_environment.get_sse_client()

        response = await sse_client.connect(client_id="error-recovery-valid")
        await asyncio.sleep(3)
        await sse_client.submit_render_request(valid_dsl, e2e_render_options)

        completion_event = await wait_for_render_completion(
            sse_client, response, timeout=e2e_test_timeout
        )

        assert validate_sse_event(completion_event, "render.completed")

        await sse_client.close()

    def _extract_png_data(self, result: Dict[str, Any]) -> str:
        """Extract PNG data from result."""
        if "png_data" in result:
            return result["png_data"]
        elif "png_result" in result:
            png_result = result["png_result"]
            return (
                png_result.get("png_data")
                or png_result.get("data")
                or png_result.get("base64_data")
            )
        return None


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.e2e_pipeline
@pytest.mark.performance
class TestPipelinePerformance:
    """Performance-focused pipeline tests."""

    async def test_pipeline_performance_large_dsl(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_render_options: Dict[str, Any],
        e2e_test_timeout: int,
    ):
        """Test pipeline performance with large DSL structure."""
        # Generate large DSL with many elements
        elements = []
        for i in range(50):  # 50 buttons
            elements.append(
                {
                    "type": "button",
                    "id": f"btn_{i}",
                    "layout": {
                        "x": (i % 10) * 80,
                        "y": (i // 10) * 50 + 50,
                        "width": 70,
                        "height": 40,
                    },
                    "style": {"background": f"hsl({i * 7}, 70%, 50%)", "color": "white"},
                    "label": f"Btn {i}",
                }
            )

        large_dsl = {
            "title": "Performance Test - Large DSL",
            "width": 800,
            "height": 400,
            "elements": elements,
        }

        dsl_content = json.dumps(large_dsl)
        sse_client = await e2e_environment.get_sse_client()

        start_time = time.time()

        response = await sse_client.connect(client_id="performance-large")
        await asyncio.sleep(3)
        await sse_client.submit_render_request(dsl_content, e2e_render_options)

        completion_event = await wait_for_render_completion(
            sse_client, response, timeout=e2e_test_timeout
        )

        total_time = time.time() - start_time

        assert validate_sse_event(completion_event, "render.completed")
        assert total_time < 60, f"Large DSL rendering took too long: {total_time}s"

        print(f"Large DSL performance: {total_time:.2f}s for {len(elements)} elements")

        await sse_client.close()

    async def test_pipeline_concurrent_performance(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_dsl_examples: Dict[str, str],
        e2e_render_options: Dict[str, Any],
        e2e_test_timeout: int,
    ):
        """Test concurrent pipeline performance."""
        dsl_content = e2e_dsl_examples["simple_button"]
        num_concurrent = 5

        async def run_concurrent_request(request_id: int):
            client = E2ESSEClient("http://localhost")
            start_time = time.time()

            response = await client.connect(client_id=f"perf-concurrent-{request_id}")
            await asyncio.sleep(2)
            await client.submit_render_request(dsl_content, e2e_render_options)

            completion_event = await wait_for_render_completion(
                client, response, timeout=e2e_test_timeout
            )

            end_time = time.time()
            await client.close()

            return {
                "request_id": request_id,
                "duration": end_time - start_time,
                "success": validate_sse_event(completion_event, "render.completed"),
            }

        # Run concurrent requests
        start_time = time.time()
        tasks = [run_concurrent_request(i) for i in range(num_concurrent)]
        results = await asyncio.gather(*tasks)
        total_time = time.time() - start_time

        # Validate all succeeded
        for result in results:
            assert result["success"], f"Request {result['request_id']} failed"

        # Performance assertions
        avg_duration = sum(r["duration"] for r in results) / len(results)
        assert total_time < 120, f"Concurrent requests took too long: {total_time}s"
        assert avg_duration < 60, f"Average request time too high: {avg_duration}s"

        print(f"Concurrent performance: {num_concurrent} requests in {total_time:.2f}s")
        print(f"Average request duration: {avg_duration:.2f}s")


@pytest.mark.asyncio
@pytest.mark.e2e
@pytest.mark.e2e_pipeline
@pytest.mark.smoke
class TestPipelineSmoke:
    """Smoke tests for pipeline variants."""

    async def test_pipeline_smoke_all_examples(
        self,
        e2e_environment: E2EEnvironmentManager,
        e2e_dsl_examples: Dict[str, str],
        e2e_render_options: Dict[str, Any],
    ):
        """Smoke test: Verify all examples can be processed."""
        if not e2e_dsl_examples:
            pytest.skip("No DSL examples found")

        for example_name, dsl_content in e2e_dsl_examples.items():
            try:
                # Quick validation that DSL is valid JSON
                json.loads(dsl_content)
            except json.JSONDecodeError:
                continue  # Skip non-JSON examples in smoke test

            sse_client = await e2e_environment.get_sse_client()

            response = await sse_client.connect(client_id=f"smoke-{example_name}")
            await asyncio.sleep(2)
            await sse_client.submit_render_request(dsl_content, e2e_render_options)

            # Just verify completion within timeout
            completed = False
            async for event in sse_client.parse_events(response, timeout=30):
                event_type = event.get("event")
                if event_type == "render.completed":
                    completed = True
                    break
                elif event_type == "render.failed":
                    pytest.fail(f"Example {example_name} failed in smoke test")

            assert completed, f"Example {example_name} did not complete in smoke test"
            await sse_client.close()
