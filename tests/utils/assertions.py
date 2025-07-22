"""
Test Assertions
===============

Custom assertion helpers for testing DSL to PNG conversion.
"""

from typing import Any, Dict, List, Optional, Union
import json
import yaml
from pathlib import Path

from src.models.schemas import (
    DSLDocument, DSLElement, ParseResult, PNGResult, 
    RenderResponse, TaskResult, ElementType
)


def assert_valid_dsl_document(document: DSLDocument) -> None:
    """Assert that a DSL document is valid."""
    assert isinstance(document, DSLDocument)
    assert document.width > 0
    assert document.height > 0
    assert isinstance(document.elements, list)
    
    # Validate each element
    for element in document.elements:
        assert_valid_dsl_element(element)


def assert_valid_dsl_element(element: DSLElement) -> None:
    """Assert that a DSL element is valid."""
    assert isinstance(element, DSLElement)
    assert isinstance(element.type, ElementType)
    
    # Check layout constraints
    if element.layout:
        if element.layout.width is not None:
            assert element.layout.width > 0
        if element.layout.height is not None:
            assert element.layout.height > 0
    
    # Check container elements have valid children
    container_types = {
        ElementType.CONTAINER,
        ElementType.GRID,
        ElementType.FLEX,
        ElementType.CARD,
        ElementType.NAVBAR,
        ElementType.SIDEBAR,
        ElementType.MODAL
    }
    if element.children:
        assert element.type in container_types, f"Element type {element.type} cannot have children"
        for child in element.children:
            assert_valid_dsl_element(child)


def assert_successful_parse_result(result: ParseResult) -> None:
    """Assert that a parse result is successful."""
    assert isinstance(result, ParseResult)
    assert result.success is True
    assert result.document is not None
    assert len(result.errors) == 0
    assert_valid_dsl_document(result.document)


def assert_failed_parse_result(result: ParseResult, expected_errors: Optional[List[str]] = None) -> None:
    """Assert that a parse result failed with expected errors."""
    assert isinstance(result, ParseResult)
    assert result.success is False
    assert result.document is None
    assert len(result.errors) > 0
    
    if expected_errors:
        for expected_error in expected_errors:
            assert any(expected_error in error for error in result.errors), \
                f"Expected error '{expected_error}' not found in {result.errors}"


def assert_valid_png_result(result: PNGResult) -> None:
    """Assert that a PNG result is valid."""
    assert isinstance(result, PNGResult)
    assert isinstance(result.png_data, bytes)
    assert len(result.png_data) > 0
    assert isinstance(result.base64_data, str)
    assert len(result.base64_data) > 0
    assert result.width > 0
    assert result.height > 0
    assert result.file_size == len(result.png_data)
    assert isinstance(result.metadata, dict)


def assert_successful_render_response(response: RenderResponse) -> None:
    """Assert that a render response is successful."""
    assert isinstance(response, RenderResponse)
    assert response.success is True
    assert response.png_result is not None
    assert response.error is None
    assert response.processing_time >= 0
    assert_valid_png_result(response.png_result)


def assert_failed_render_response(response: RenderResponse, expected_error: Optional[str] = None) -> None:
    """Assert that a render response failed."""
    assert isinstance(response, RenderResponse)
    assert response.success is False
    assert response.png_result is None
    assert response.error is not None
    assert response.processing_time >= 0
    
    if expected_error:
        assert expected_error in response.error, \
            f"Expected error '{expected_error}' not found in '{response.error}'"


def assert_valid_html_content(html: str) -> None:
    """Assert that HTML content is valid."""
    assert isinstance(html, str)
    assert len(html) > 0
    assert "<!DOCTYPE html>" in html or "<html" in html
    assert "</html>" in html
    assert "<body" in html
    assert "</body>" in html


def assert_html_contains_elements(html: str, element_count: int) -> None:
    """Assert that HTML contains expected number of DSL elements."""
    assert_valid_html_content(html)
    # Count elements with dsl-element class
    dsl_element_count = html.count('class="dsl-element')
    assert dsl_element_count >= element_count, \
        f"Expected at least {element_count} DSL elements, found {dsl_element_count}"


def assert_html_contains_styles(html: str, styles: List[str]) -> None:
    """Assert that HTML contains expected styles."""
    assert_valid_html_content(html)
    for style in styles:
        assert style in html, f"Expected style '{style}' not found in HTML"


def assert_task_result_successful(result: TaskResult) -> None:
    """Assert that a task result is successful."""
    assert isinstance(result, TaskResult)
    assert result.status.value == "completed"
    assert result.png_result is not None
    assert result.error is None
    assert result.processing_time >= 0
    assert_valid_png_result(result.png_result)


def assert_task_result_failed(result: TaskResult, expected_error: Optional[str] = None) -> None:
    """Assert that a task result failed."""
    assert isinstance(result, TaskResult)
    assert result.status.value == "failed"
    assert result.png_result is None
    assert result.error is not None
    assert result.processing_time >= 0
    
    if expected_error:
        assert expected_error in result.error, \
            f"Expected error '{expected_error}' not found in '{result.error}'"


def assert_json_structure_matches(actual: Dict[str, Any], expected_structure: Dict[str, Any]) -> None:
    """Assert that JSON structure matches expected pattern."""
    for key, expected_type in expected_structure.items():
        assert key in actual, f"Expected key '{key}' not found in actual data"
        
        if expected_type == "string":
            assert isinstance(actual[key], str)
        elif expected_type == "int":
            assert isinstance(actual[key], int)
        elif expected_type == "float":
            assert isinstance(actual[key], (int, float))
        elif expected_type == "bool":
            assert isinstance(actual[key], bool)
        elif expected_type == "list":
            assert isinstance(actual[key], list)
        elif expected_type == "dict":
            assert isinstance(actual[key], dict)
        elif expected_type == "optional":
            # Can be None or any type
            pass
        elif isinstance(expected_type, dict):
            # Nested structure
            assert isinstance(actual[key], dict)
            assert_json_structure_matches(actual[key], expected_type)


def assert_valid_json_dsl(content: str) -> None:
    """Assert that content is valid JSON DSL."""
    try:
        data = json.loads(content)
        assert isinstance(data, dict)
        assert "elements" in data
        assert isinstance(data["elements"], list)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Invalid JSON DSL: {e}")


def assert_valid_yaml_dsl(content: str) -> None:
    """Assert that content is valid YAML DSL."""
    try:
        data = yaml.safe_load(content)
        assert isinstance(data, dict)
        assert "elements" in data
        assert isinstance(data["elements"], list)
    except yaml.YAMLError as e:
        raise AssertionError(f"Invalid YAML DSL: {e}")


def assert_png_dimensions(png_data: bytes, expected_width: int, expected_height: int) -> None:
    """Assert PNG has expected dimensions."""
    # Simple PNG header check for dimensions
    # PNG header: 8 bytes signature + 4 bytes length + 4 bytes "IHDR" + width(4) + height(4)
    if len(png_data) >= 24:
        # Extract width and height from PNG header
        width = int.from_bytes(png_data[16:20], byteorder='big')
        height = int.from_bytes(png_data[20:24], byteorder='big')
        
        assert width == expected_width, f"Expected width {expected_width}, got {width}"
        assert height == expected_height, f"Expected height {expected_height}, got {height}"


def assert_file_exists_and_valid(file_path: Union[str, Path], min_size: int = 0) -> None:
    """Assert that file exists and has minimum size."""
    path = Path(file_path)
    assert path.exists(), f"File {path} does not exist"
    assert path.is_file(), f"Path {path} is not a file"
    assert path.stat().st_size >= min_size, f"File {path} is smaller than {min_size} bytes"


def assert_response_time_acceptable(processing_time: float, max_time: float = 30.0) -> None:
    """Assert that processing time is within acceptable limits."""
    assert processing_time >= 0, "Processing time cannot be negative"
    assert processing_time <= max_time, f"Processing time {processing_time}s exceeds limit {max_time}s"


def assert_memory_usage_reasonable(memory_mb: float, max_memory_mb: float = 1000.0) -> None:
    """Assert that memory usage is reasonable."""
    assert memory_mb >= 0, "Memory usage cannot be negative"
    assert memory_mb <= max_memory_mb, f"Memory usage {memory_mb}MB exceeds limit {max_memory_mb}MB"


def assert_redis_key_exists(redis_client, key: str) -> None:
    """Assert that Redis key exists."""
    # This will be used in async context
    # The actual implementation will use await redis_client.exists(key)
    pass


def assert_redis_key_not_exists(redis_client, key: str) -> None:
    """Assert that Redis key does not exist."""
    # This will be used in async context
    # The actual implementation will use await redis_client.exists(key)
    pass


def assert_performance_within_threshold(elapsed_time: float, max_time: float = 5.0) -> None:
    """Assert that performance time is within acceptable threshold."""
    assert elapsed_time >= 0, "Elapsed time cannot be negative"
    assert elapsed_time <= max_time, f"Performance time {elapsed_time}s exceeds threshold {max_time}s"


def assert_contains_sensitive_data(content: str, should_contain: bool = False) -> None:
    """Assert whether content contains sensitive data."""
    sensitive_patterns = [
        "password", "secret", "key", "token", "api_key",
        "database_url", "redis_url", "private"
    ]
    
    contains_sensitive = any(pattern.lower() in content.lower() for pattern in sensitive_patterns)
    
    if should_contain:
        assert contains_sensitive, "Expected content to contain sensitive data"
    else:
        assert not contains_sensitive, f"Content should not contain sensitive data: {content}"


def assert_performance_within_limits(execution_time: float, max_allowed_time: float, test_name: str = "Test") -> None:
    """Assert that performance time is within acceptable limits."""
    if execution_time > max_allowed_time:
        raise AssertionError(f"{test_name} exceeded time limit: {execution_time:.2f}s > {max_allowed_time:.2f}s")