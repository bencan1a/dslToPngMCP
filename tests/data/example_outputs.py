"""
Example Outputs
===============

Example expected outputs and validation patterns for testing DSL to PNG conversion results.
"""

import hashlib
from typing import Dict, Any, List, Optional
from dataclasses import dataclass


@dataclass
class ExpectedOutput:
    """Represents expected output characteristics for validation."""
    min_file_size: int
    max_file_size: int
    width: int
    height: int
    format: str
    quality_range: tuple[int, int]
    content_patterns: List[str]
    color_patterns: List[str]
    metadata: Dict[str, Any]


# Expected outputs for simple documents
SIMPLE_TEXT_EXPECTED = ExpectedOutput(
    min_file_size=800,
    max_file_size=15000,
    width=800,
    height=600,
    format="png",
    quality_range=(80, 100),
    content_patterns=["text_content", "basic_styling"],
    color_patterns=["#333333", "white_background"],
    metadata={
        "contains_text": True,
        "text_count": 1,
        "element_count": 1,
        "has_styling": True
    }
)

SIMPLE_LAYOUT_EXPECTED = ExpectedOutput(
    min_file_size=2000,
    max_file_size=50000,
    width=1024,
    height=768,
    format="png",
    quality_range=(80, 100),
    content_patterns=["container_layout", "flex_structure", "text_content"],
    color_patterns=["#f0f0f0", "#e8f4f8", "white"],
    metadata={
        "contains_layout": True,
        "container_count": 4,
        "text_elements": 3,
        "has_flex_layout": True
    }
)

# Expected outputs for complex documents
DASHBOARD_EXPECTED = ExpectedOutput(
    min_file_size=20000,
    max_file_size=500000,
    width=1440,
    height=900,
    format="png",
    quality_range=(85, 100),
    content_patterns=[
        "dashboard_header", "navigation_sidebar", "metrics_grid", 
        "chart_elements", "card_components"
    ],
    color_patterns=["#2563eb", "#64748b", "#f8fafc", "white"],
    metadata={
        "contains_dashboard": True,
        "has_navigation": True,
        "chart_count": 2,
        "card_count": 3,
        "grid_layout": True
    }
)

RESPONSIVE_DESKTOP_EXPECTED = ExpectedOutput(
    min_file_size=15000,
    max_file_size=300000,
    width=1200,
    height=800,
    format="png",
    quality_range=(85, 100),
    content_patterns=["hero_section", "features_grid", "responsive_layout"],
    color_patterns=["#667eea", "#764ba2", "#f8fafc", "white"],
    metadata={
        "is_responsive": True,
        "breakpoint": "desktop",
        "has_hero": True,
        "feature_cards": 3
    }
)

RESPONSIVE_MOBILE_EXPECTED = ExpectedOutput(
    min_file_size=8000,
    max_file_size=150000,
    width=375,
    height=667,
    format="png",
    quality_range=(80, 95),
    content_patterns=["hero_section", "stacked_layout", "mobile_responsive"],
    color_patterns=["#667eea", "#764ba2", "#f8fafc", "white"],
    metadata={
        "is_responsive": True,
        "breakpoint": "mobile",
        "has_hero": True,
        "stacked_layout": True
    }
)

# Expected outputs for performance test documents
LARGE_DOCUMENT_EXPECTED = ExpectedOutput(
    min_file_size=50000,
    max_file_size=2000000,
    width=1920,
    height=1080,
    format="png",
    quality_range=(80, 95),
    content_patterns=["grid_layout", "many_elements", "performance_test"],
    color_patterns=["hsl_colors", "gradient_backgrounds"],
    metadata={
        "element_count": 100,
        "is_performance_test": True,
        "grid_columns": 10,
        "has_many_colors": True
    }
)

NESTED_DOCUMENT_EXPECTED = ExpectedOutput(
    min_file_size=5000,
    max_file_size=100000,
    width=800,
    height=600,
    format="png",
    quality_range=(80, 95),
    content_patterns=["nested_containers", "border_styling", "deep_structure"],
    color_patterns=["#cccccc", "border_colors"],
    metadata={
        "nesting_depth": 15,
        "container_count": 15,
        "has_borders": True,
        "nested_structure": True
    }
)

# Expected outputs for edge cases
EMPTY_DOCUMENT_EXPECTED = ExpectedOutput(
    min_file_size=200,
    max_file_size=5000,
    width=800,
    height=600,
    format="png",
    quality_range=(70, 100),
    content_patterns=["empty_content", "blank_canvas"],
    color_patterns=["white", "transparent"],
    metadata={
        "is_empty": True,
        "element_count": 0,
        "content_length": 0
    }
)

MINIMAL_DOCUMENT_EXPECTED = ExpectedOutput(
    min_file_size=200,
    max_file_size=3000,
    width=100,
    height=100,
    format="png",
    quality_range=(70, 100),
    content_patterns=["minimal_content", "single_character"],
    color_patterns=["black", "white"],
    metadata={
        "is_minimal": True,
        "element_count": 1,
        "content_length": 1
    }
)

MAXIMUM_SIZE_EXPECTED = ExpectedOutput(
    min_file_size=500000,
    max_file_size=50000000,  # 50MB
    width=4096,
    height=4096,
    format="png",
    quality_range=(85, 100),
    content_patterns=["large_canvas", "maximum_resolution"],
    color_patterns=["#f0f0f0", "large_text"],
    metadata={
        "is_maximum_size": True,
        "high_resolution": True,
        "large_file": True
    }
)

# Expected outputs for specialized content
FORM_EXPECTED = ExpectedOutput(
    min_file_size=10000,
    max_file_size=200000,
    width=800,
    height=1000,
    format="png",
    quality_range=(85, 100),
    content_patterns=["form_elements", "input_fields", "button_styling"],
    color_patterns=["#2563eb", "form_backgrounds", "input_borders"],
    metadata={
        "contains_form": True,
        "input_count": 3,
        "has_button": True,
        "form_layout": True
    }
)

TABLE_EXPECTED = ExpectedOutput(
    min_file_size=15000,
    max_file_size=300000,
    width=1200,
    height=800,
    format="png",
    quality_range=(85, 100),
    content_patterns=["table_structure", "data_rows", "header_styling"],
    color_patterns=["#f9fafb", "#e5e7eb", "table_borders"],
    metadata={
        "contains_table": True,
        "row_count": 5,
        "column_count": 4,
        "has_headers": True
    }
)

ANIMATED_EXPECTED = ExpectedOutput(
    min_file_size=8000,
    max_file_size=150000,
    width=800,
    height=600,
    format="png",
    quality_range=(85, 100),
    content_patterns=["animated_elements", "css_animations", "keyframes"],
    color_patterns=["#1e293b", "#3b82f6", "#ef4444", "white"],
    metadata={
        "contains_animations": True,
        "animated_elements": 3,
        "animation_types": ["fadeIn", "bounce", "spin"]
    }
)

# Quality-specific expected outputs
LOW_QUALITY_EXPECTED = ExpectedOutput(
    min_file_size=1000,
    max_file_size=25000,
    width=800,
    height=600,
    format="png",
    quality_range=(50, 70),
    content_patterns=["compressed_content", "reduced_quality"],
    color_patterns=["basic_colors"],
    metadata={
        "quality_level": "low",
        "compression": True,
        "fast_processing": True
    }
)

HIGH_QUALITY_EXPECTED = ExpectedOutput(
    min_file_size=5000,
    max_file_size=200000,
    width=800,
    height=600,
    format="png",
    quality_range=(90, 100),
    content_patterns=["high_quality_content", "detailed_rendering"],
    color_patterns=["precise_colors", "smooth_gradients"],
    metadata={
        "quality_level": "high",
        "high_detail": True,
        "premium_rendering": True
    }
)

# High DPI expected outputs
HIGH_DPI_EXPECTED = ExpectedOutput(
    min_file_size=10000,
    max_file_size=400000,
    width=1600,  # 2x scale
    height=1200,  # 2x scale
    format="png",
    quality_range=(85, 100),
    content_patterns=["high_dpi_content", "retina_quality", "sharp_text"],
    color_patterns=["crisp_colors", "smooth_lines"],
    metadata={
        "device_scale_factor": 2.0,
        "high_dpi": True,
        "retina_quality": True
    }
)

RETINA_EXPECTED = ExpectedOutput(
    min_file_size=20000,
    max_file_size=800000,
    width=3072,  # 3x scale
    height=2304,  # 3x scale
    format="png",
    quality_range=(90, 100),
    content_patterns=["retina_content", "ultra_sharp", "high_resolution"],
    color_patterns=["ultra_crisp_colors", "perfect_gradients"],
    metadata={
        "device_scale_factor": 3.0,
        "retina_display": True,
        "ultra_high_quality": True
    }
)

# Collection of all expected outputs
ALL_EXPECTED_OUTPUTS = {
    "simple_text": SIMPLE_TEXT_EXPECTED,
    "simple_layout": SIMPLE_LAYOUT_EXPECTED,
    "dashboard": DASHBOARD_EXPECTED,
    "responsive_desktop": RESPONSIVE_DESKTOP_EXPECTED,
    "responsive_mobile": RESPONSIVE_MOBILE_EXPECTED,
    "large_document": LARGE_DOCUMENT_EXPECTED,
    "nested_document": NESTED_DOCUMENT_EXPECTED,
    "empty_document": EMPTY_DOCUMENT_EXPECTED,
    "minimal_document": MINIMAL_DOCUMENT_EXPECTED,
    "maximum_size": MAXIMUM_SIZE_EXPECTED,
    "form": FORM_EXPECTED,
    "table": TABLE_EXPECTED,
    "animated": ANIMATED_EXPECTED,
    "low_quality": LOW_QUALITY_EXPECTED,
    "high_quality": HIGH_QUALITY_EXPECTED,
    "high_dpi": HIGH_DPI_EXPECTED,
    "retina": RETINA_EXPECTED
}


def get_expected_output(scenario_name: str) -> Optional[ExpectedOutput]:
    """Get expected output for a specific scenario."""
    return ALL_EXPECTED_OUTPUTS.get(scenario_name)


def validate_output_size(actual_size: int, expected: ExpectedOutput) -> bool:
    """Validate that output file size is within expected range."""
    return expected.min_file_size <= actual_size <= expected.max_file_size


def validate_output_dimensions(actual_width: int, actual_height: int, expected: ExpectedOutput) -> bool:
    """Validate that output dimensions match expected values."""
    return actual_width == expected.width and actual_height == expected.height


def validate_output_format(actual_format: str, expected: ExpectedOutput) -> bool:
    """Validate that output format matches expected format."""
    return actual_format.lower() == expected.format.lower()


def validate_content_patterns(content: str, expected: ExpectedOutput) -> Dict[str, bool]:
    """Validate that content contains expected patterns."""
    results = {}
    for pattern in expected.content_patterns:
        results[pattern] = pattern in content
    return results


def validate_color_patterns(content: str, expected: ExpectedOutput) -> Dict[str, bool]:
    """Validate that content contains expected color patterns."""
    results = {}
    for color in expected.color_patterns:
        results[color] = color in content
    return results


def generate_content_hash(content: bytes) -> str:
    """Generate SHA-256 hash of content for integrity verification."""
    return hashlib.sha256(content).hexdigest()


def create_validation_report(
    actual_output: Dict[str, Any],
    expected: ExpectedOutput
) -> Dict[str, Any]:
    """Create comprehensive validation report comparing actual vs expected output."""
    report = {
        "overall_valid": True,
        "validations": {},
        "errors": [],
        "warnings": [],
        "metadata_comparison": {}
    }
    
    # Validate file size
    if "file_size" in actual_output:
        size_valid = validate_output_size(actual_output["file_size"], expected)
        report["validations"]["file_size"] = size_valid
        if not size_valid:
            report["overall_valid"] = False
            report["errors"].append(
                f"File size {actual_output['file_size']} not in range "
                f"[{expected.min_file_size}, {expected.max_file_size}]"
            )
    
    # Validate dimensions
    if "width" in actual_output and "height" in actual_output:
        dims_valid = validate_output_dimensions(
            actual_output["width"], 
            actual_output["height"], 
            expected
        )
        report["validations"]["dimensions"] = dims_valid
        if not dims_valid:
            report["overall_valid"] = False
            report["errors"].append(
                f"Dimensions {actual_output['width']}x{actual_output['height']} "
                f"do not match expected {expected.width}x{expected.height}"
            )
    
    # Validate format
    if "format" in actual_output:
        format_valid = validate_output_format(actual_output["format"], expected)
        report["validations"]["format"] = format_valid
        if not format_valid:
            report["overall_valid"] = False
            report["errors"].append(
                f"Format {actual_output['format']} does not match expected {expected.format}"
            )
    
    # Validate content patterns
    if "content" in actual_output:
        content_results = validate_content_patterns(actual_output["content"], expected)
        report["validations"]["content_patterns"] = content_results
        
        missing_patterns = [pattern for pattern, found in content_results.items() if not found]
        if missing_patterns:
            report["warnings"].extend([
                f"Missing content pattern: {pattern}" for pattern in missing_patterns
            ])
    
    # Validate color patterns
    if "content" in actual_output:
        color_results = validate_color_patterns(actual_output["content"], expected)
        report["validations"]["color_patterns"] = color_results
        
        missing_colors = [color for color, found in color_results.items() if not found]
        if missing_colors:
            report["warnings"].extend([
                f"Missing color pattern: {color}" for color in missing_colors
            ])
    
    # Compare metadata
    if "metadata" in actual_output:
        actual_metadata = actual_output["metadata"]
        for key, expected_value in expected.metadata.items():
            if key in actual_metadata:
                actual_value = actual_metadata[key]
                match = actual_value == expected_value
                report["metadata_comparison"][key] = {
                    "expected": expected_value,
                    "actual": actual_value,
                    "match": match
                }
                if not match:
                    report["warnings"].append(
                        f"Metadata mismatch for {key}: expected {expected_value}, got {actual_value}"
                    )
            else:
                report["metadata_comparison"][key] = {
                    "expected": expected_value,
                    "actual": None,
                    "match": False
                }
                report["warnings"].append(f"Missing metadata: {key}")
    
    return report


# Reference images and checksums for regression testing
REFERENCE_CHECKSUMS = {
    "simple_text_800x600": "abc123def456...",  # Would contain actual checksums
    "simple_layout_1024x768": "def456ghi789...",
    "dashboard_1440x900": "ghi789jkl012...",
    "responsive_desktop_1200x800": "jkl012mno345...",
    "responsive_mobile_375x667": "mno345pqr678...",
    # Add more reference checksums as needed
}


def get_reference_checksum(scenario_name: str, dimensions: str) -> Optional[str]:
    """Get reference checksum for regression testing."""
    key = f"{scenario_name}_{dimensions}"
    return REFERENCE_CHECKSUMS.get(key)


def compare_with_reference(content_hash: str, scenario_name: str, dimensions: str) -> bool:
    """Compare generated content hash with reference checksum."""
    reference = get_reference_checksum(scenario_name, dimensions)
    if reference is None:
        return True  # No reference available, assume valid
    return content_hash == reference


# Performance benchmarks
PERFORMANCE_BENCHMARKS = {
    "simple_text": {"max_time": 2.0, "max_memory": 50 * 1024 * 1024},  # 50MB
    "simple_layout": {"max_time": 3.0, "max_memory": 75 * 1024 * 1024},  # 75MB
    "dashboard": {"max_time": 15.0, "max_memory": 200 * 1024 * 1024},  # 200MB
    "large_document": {"max_time": 30.0, "max_memory": 500 * 1024 * 1024},  # 500MB
    "maximum_size": {"max_time": 60.0, "max_memory": 2 * 1024 * 1024 * 1024},  # 2GB
}


def get_performance_benchmark(scenario_name: str) -> Optional[Dict[str, float]]:
    """Get performance benchmark for a scenario."""
    return PERFORMANCE_BENCHMARKS.get(scenario_name)


def validate_performance(
    processing_time: float, 
    memory_usage: int, 
    scenario_name: str
) -> Dict[str, bool]:
    """Validate performance against benchmarks."""
    benchmark = get_performance_benchmark(scenario_name)
    if not benchmark:
        return {"time_valid": True, "memory_valid": True}
    
    return {
        "time_valid": processing_time <= benchmark["max_time"],
        "memory_valid": memory_usage <= benchmark["max_memory"]
    }