"""
Test Scenarios
==============

Comprehensive test scenarios for validating DSL to PNG conversion functionality
across different use cases, edge cases, and performance requirements.
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from tests.data.sample_dsl_documents import ALL_TEST_DOCUMENTS
from tests.data.sample_render_options import ALL_RENDER_OPTIONS


@dataclass
class TestScenario:
    """Represents a complete test scenario with DSL document, render options, and expected outcomes."""
    name: str
    description: str
    dsl_document: Dict[str, Any]
    render_options: Dict[str, Any]
    expected_outcomes: Dict[str, Any]
    tags: List[str]
    priority: str  # "low", "medium", "high", "critical"
    estimated_duration: float  # seconds
    
    def __post_init__(self):
        """Validate scenario data after initialization."""
        if not self.name:
            raise ValueError("Scenario name is required")
        if not self.dsl_document:
            raise ValueError("DSL document is required")
        if not self.render_options:
            raise ValueError("Render options are required")


# Basic Functionality Scenarios
BASIC_SCENARIOS = [
    TestScenario(
        name="simple_text_rendering",
        description="Render a simple text document with basic styling",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["text"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 1000,  # bytes
            "max_file_size": 50000,  # bytes
            "width": 800,
            "height": 600,
            "contains_text": True,
            "processing_time_max": 5.0  # seconds
        },
        tags=["basic", "text", "smoke"],
        priority="critical",
        estimated_duration=2.0
    ),
    
    TestScenario(
        name="simple_layout_rendering",
        description="Render a simple layout with containers and styled elements",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["layout"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 2000,
            "max_file_size": 100000,
            "width": 800,
            "height": 600,
            "contains_layout": True,
            "processing_time_max": 5.0
        },
        tags=["basic", "layout", "smoke"],
        priority="critical",
        estimated_duration=3.0
    )
]

# Complex Scenarios
COMPLEX_SCENARIOS = [
    TestScenario(
        name="dashboard_rendering",
        description="Render a complex dashboard with multiple components",
        dsl_document=ALL_TEST_DOCUMENTS["complex"]["dashboard"],
        render_options=ALL_RENDER_OPTIONS["large"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 10000,
            "max_file_size": 500000,
            "width": 1920,
            "height": 1080,
            "contains_charts": True,
            "contains_navigation": True,
            "processing_time_max": 15.0
        },
        tags=["complex", "dashboard", "charts"],
        priority="high",
        estimated_duration=10.0
    ),
    
    TestScenario(
        name="responsive_design_desktop",
        description="Render responsive design at desktop resolution",
        dsl_document=ALL_TEST_DOCUMENTS["complex"]["responsive"],
        render_options=ALL_RENDER_OPTIONS["desktop_large"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 5000,
            "max_file_size": 300000,
            "width": 1920,
            "height": 1080,
            "responsive_layout": "desktop",
            "processing_time_max": 10.0
        },
        tags=["complex", "responsive", "desktop"],
        priority="high",
        estimated_duration=8.0
    ),
    
    TestScenario(
        name="responsive_design_mobile",
        description="Render responsive design at mobile resolution",
        dsl_document=ALL_TEST_DOCUMENTS["complex"]["responsive"],
        render_options=ALL_RENDER_OPTIONS["mobile_portrait"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 2000,
            "max_file_size": 150000,
            "width": 375,
            "height": 667,
            "responsive_layout": "mobile",
            "processing_time_max": 8.0
        },
        tags=["complex", "responsive", "mobile"],
        priority="high",
        estimated_duration=6.0
    )
]

# Performance Scenarios
PERFORMANCE_SCENARIOS = [
    TestScenario(
        name="large_document_performance",
        description="Test performance with large document containing many elements",
        dsl_document=ALL_TEST_DOCUMENTS["performance"]["large"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 20000,
            "max_file_size": 1000000,
            "width": 800,
            "height": 600,
            "processing_time_max": 30.0,
            "memory_usage_max": 500 * 1024 * 1024  # 500MB
        },
        tags=["performance", "large", "stress"],
        priority="medium",
        estimated_duration=25.0
    ),
    
    TestScenario(
        name="nested_structure_performance",
        description="Test performance with deeply nested document structure",
        dsl_document=ALL_TEST_DOCUMENTS["performance"]["nested"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 1000,
            "max_file_size": 100000,
            "width": 800,
            "height": 600,
            "processing_time_max": 20.0,
            "nested_depth_max": 20
        },
        tags=["performance", "nested", "stress"],
        priority="medium",
        estimated_duration=15.0
    ),
    
    TestScenario(
        name="high_dpi_performance",
        description="Test performance with high DPI rendering",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["layout"],
        render_options=ALL_RENDER_OPTIONS["retina"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 50000,
            "max_file_size": 2000000,
            "width": 1024,
            "height": 768,
            "device_scale_factor": 3.0,
            "processing_time_max": 15.0
        },
        tags=["performance", "high_dpi", "retina"],
        priority="medium",
        estimated_duration=12.0
    )
]

# Error Handling Scenarios
ERROR_SCENARIOS = [
    TestScenario(
        name="invalid_document_structure",
        description="Test handling of invalid DSL document structure",
        dsl_document=ALL_TEST_DOCUMENTS["invalid"]["structure"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": False,
            "error_type": "ValidationError",
            "error_message_contains": ["validation", "invalid"],
            "processing_time_max": 1.0
        },
        tags=["error", "validation", "invalid"],
        priority="high",
        estimated_duration=1.0
    ),
    
    TestScenario(
        name="malformed_style_handling",
        description="Test handling of malformed CSS styles",
        dsl_document=ALL_TEST_DOCUMENTS["invalid"]["style"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": False,
            "error_type": "StyleError",
            "error_message_contains": ["style", "invalid"],
            "processing_time_max": 2.0
        },
        tags=["error", "style", "css"],
        priority="high",
        estimated_duration=1.5
    )
]

# Edge Case Scenarios
EDGE_CASE_SCENARIOS = [
    TestScenario(
        name="empty_document",
        description="Test rendering of completely empty document",
        dsl_document=ALL_TEST_DOCUMENTS["edge_cases"]["empty"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 500,
            "max_file_size": 10000,
            "width": 800,
            "height": 600,
            "is_empty": True,
            "processing_time_max": 3.0
        },
        tags=["edge_case", "empty", "minimal"],
        priority="medium",
        estimated_duration=2.0
    ),
    
    TestScenario(
        name="minimal_document",
        description="Test rendering of minimal document with single character",
        dsl_document=ALL_TEST_DOCUMENTS["edge_cases"]["minimal"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 500,
            "max_file_size": 5000,
            "width": 100,
            "height": 100,
            "processing_time_max": 2.0
        },
        tags=["edge_case", "minimal"],
        priority="low",
        estimated_duration=1.5
    ),
    
    TestScenario(
        name="maximum_size_document",
        description="Test rendering at maximum supported resolution",
        dsl_document=ALL_TEST_DOCUMENTS["edge_cases"]["maximum"],
        render_options=ALL_RENDER_OPTIONS["desktop_4k"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 100000,
            "max_file_size": 50000000,  # 50MB
            "width": 3840,
            "height": 2160,
            "processing_time_max": 60.0,
            "memory_usage_max": 2 * 1024 * 1024 * 1024  # 2GB
        },
        tags=["edge_case", "maximum", "4k"],
        priority="low",
        estimated_duration=45.0
    ),
    
    TestScenario(
        name="extreme_aspect_ratio_wide",
        description="Test rendering with extremely wide aspect ratio",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["text"],
        render_options=ALL_RENDER_OPTIONS["wide_aspect"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 2000,
            "max_file_size": 50000,
            "width": 1600,
            "height": 400,
            "aspect_ratio": 4.0,
            "processing_time_max": 8.0
        },
        tags=["edge_case", "aspect_ratio", "wide"],
        priority="low",
        estimated_duration=5.0
    ),
    
    TestScenario(
        name="extreme_aspect_ratio_tall",
        description="Test rendering with extremely tall aspect ratio",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["text"],
        render_options=ALL_RENDER_OPTIONS["tall_aspect"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 2000,
            "max_file_size": 50000,
            "width": 400,
            "height": 1600,
            "aspect_ratio": 0.25,
            "processing_time_max": 8.0
        },
        tags=["edge_case", "aspect_ratio", "tall"],
        priority="low",
        estimated_duration=5.0
    )
]

# Browser Compatibility Scenarios
BROWSER_SCENARIOS = [
    TestScenario(
        name="chrome_compatibility",
        description="Test rendering with Chrome user agent",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["layout"],
        render_options=ALL_RENDER_OPTIONS["chrome"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 2000,
            "max_file_size": 100000,
            "width": 1280,
            "height": 720,
            "browser_compatibility": "chrome",
            "processing_time_max": 5.0
        },
        tags=["browser", "chrome", "compatibility"],
        priority="medium",
        estimated_duration=3.0
    ),
    
    TestScenario(
        name="firefox_compatibility",
        description="Test rendering with Firefox user agent",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["layout"],
        render_options=ALL_RENDER_OPTIONS["firefox"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 2000,
            "max_file_size": 100000,
            "width": 1280,
            "height": 720,
            "browser_compatibility": "firefox",
            "processing_time_max": 5.0
        },
        tags=["browser", "firefox", "compatibility"],
        priority="medium",
        estimated_duration=3.0
    ),
    
    TestScenario(
        name="safari_compatibility",
        description="Test rendering with Safari user agent",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["layout"],
        render_options=ALL_RENDER_OPTIONS["safari"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 2000,
            "max_file_size": 100000,
            "width": 1280,
            "height": 720,
            "browser_compatibility": "safari",
            "processing_time_max": 5.0
        },
        tags=["browser", "safari", "compatibility"],
        priority="medium",
        estimated_duration=3.0
    )
]

# Specialized Content Scenarios
SPECIALIZED_SCENARIOS = [
    TestScenario(
        name="form_rendering",
        description="Test rendering of form elements and inputs",
        dsl_document=ALL_TEST_DOCUMENTS["specialized"]["form"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 5000,
            "max_file_size": 200000,
            "width": 800,
            "height": 600,
            "contains_form": True,
            "contains_inputs": True,
            "processing_time_max": 8.0
        },
        tags=["specialized", "form", "inputs"],
        priority="medium",
        estimated_duration=6.0
    ),
    
    TestScenario(
        name="table_rendering",
        description="Test rendering of complex table structures",
        dsl_document=ALL_TEST_DOCUMENTS["specialized"]["table"],
        render_options=ALL_RENDER_OPTIONS["large"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 8000,
            "max_file_size": 300000,
            "width": 1920,
            "height": 1080,
            "contains_table": True,
            "table_rows": 5,
            "table_columns": 4,
            "processing_time_max": 10.0
        },
        tags=["specialized", "table", "data"],
        priority="medium",
        estimated_duration=7.0
    ),
    
    TestScenario(
        name="animation_rendering",
        description="Test rendering of animated elements (static snapshot)",
        dsl_document=ALL_TEST_DOCUMENTS["specialized"]["animated"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 3000,
            "max_file_size": 150000,
            "width": 800,
            "height": 600,
            "contains_animations": True,
            "processing_time_max": 8.0
        },
        tags=["specialized", "animation", "css"],
        priority="low",
        estimated_duration=5.0
    )
]

# Quality Scenarios
QUALITY_SCENARIOS = [
    TestScenario(
        name="low_quality_rendering",
        description="Test low quality rendering for fast processing",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["layout"],
        render_options=ALL_RENDER_OPTIONS["low_quality"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 1000,
            "max_file_size": 30000,
            "width": 800,
            "height": 600,
            "quality": 60,
            "processing_time_max": 3.0
        },
        tags=["quality", "low", "fast"],
        priority="medium",
        estimated_duration=2.0
    ),
    
    TestScenario(
        name="high_quality_rendering",
        description="Test high quality rendering for best output",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["layout"],
        render_options=ALL_RENDER_OPTIONS["high_quality"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "min_file_size": 5000,
            "max_file_size": 200000,
            "width": 800,
            "height": 600,
            "quality": 95,
            "processing_time_max": 8.0
        },
        tags=["quality", "high", "detailed"],
        priority="medium",
        estimated_duration=6.0
    )
]

# Concurrent Processing Scenarios
CONCURRENT_SCENARIOS = [
    TestScenario(
        name="concurrent_basic_requests",
        description="Test concurrent processing of multiple basic requests",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["text"],
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "concurrent_requests": 5,
            "individual_processing_time_max": 10.0,
            "total_processing_time_max": 15.0,
            "success_rate_min": 0.8  # 80% success rate minimum
        },
        tags=["concurrent", "basic", "scalability"],
        priority="high",
        estimated_duration=12.0
    ),
    
    TestScenario(
        name="concurrent_mixed_requests",
        description="Test concurrent processing of different document types",
        dsl_document=ALL_TEST_DOCUMENTS["simple"]["layout"],  # Base document
        render_options=ALL_RENDER_OPTIONS["basic"].__dict__,
        expected_outcomes={
            "success": True,
            "output_format": "png",
            "concurrent_requests": 10,
            "mixed_document_types": True,
            "individual_processing_time_max": 15.0,
            "total_processing_time_max": 25.0,
            "success_rate_min": 0.7  # 70% success rate minimum
        },
        tags=["concurrent", "mixed", "stress"],
        priority="medium",
        estimated_duration=20.0
    )
]

# All scenarios organized by category
ALL_SCENARIOS = {
    "basic": BASIC_SCENARIOS,
    "complex": COMPLEX_SCENARIOS,
    "performance": PERFORMANCE_SCENARIOS,
    "error": ERROR_SCENARIOS,
    "edge_case": EDGE_CASE_SCENARIOS,
    "browser": BROWSER_SCENARIOS,
    "specialized": SPECIALIZED_SCENARIOS,
    "quality": QUALITY_SCENARIOS,
    "concurrent": CONCURRENT_SCENARIOS
}

# Scenario collections for different test suites
SMOKE_TEST_SCENARIOS = [
    scenario for category in ALL_SCENARIOS.values()
    for scenario in category
    if "smoke" in scenario.tags
]

CRITICAL_SCENARIOS = [
    scenario for category in ALL_SCENARIOS.values()
    for scenario in category
    if scenario.priority == "critical"
]

HIGH_PRIORITY_SCENARIOS = [
    scenario for category in ALL_SCENARIOS.values()
    for scenario in category
    if scenario.priority in ["critical", "high"]
]

PERFORMANCE_TEST_SCENARIOS = [
    scenario for category in ALL_SCENARIOS.values()
    for scenario in category
    if "performance" in scenario.tags or "stress" in scenario.tags
]

REGRESSION_TEST_SCENARIOS = [
    scenario for category in ALL_SCENARIOS.values()
    for scenario in category
    if scenario.priority in ["critical", "high"]
]


def get_scenario_by_name(name: str) -> Optional[TestScenario]:
    """Get a test scenario by name."""
    for category in ALL_SCENARIOS.values():
        for scenario in category:
            if scenario.name == name:
                return scenario
    return None


def get_scenarios_by_tag(tag: str) -> List[TestScenario]:
    """Get all scenarios that have a specific tag."""
    return [
        scenario for category in ALL_SCENARIOS.values()
        for scenario in category
        if tag in scenario.tags
    ]


def get_scenarios_by_priority(priority: str) -> List[TestScenario]:
    """Get all scenarios with a specific priority."""
    return [
        scenario for category in ALL_SCENARIOS.values()
        for scenario in category
        if scenario.priority == priority
    ]


def get_estimated_test_duration(scenarios: List[TestScenario]) -> float:
    """Calculate estimated total duration for a list of scenarios."""
    return sum(scenario.estimated_duration for scenario in scenarios)


def create_test_suite(
    include_tags: List[str] = None,
    exclude_tags: List[str] = None,
    priority: str = None,
    max_duration: float = None
) -> List[TestScenario]:
    """Create a custom test suite based on criteria."""
    all_scenarios = [
        scenario for category in ALL_SCENARIOS.values()
        for scenario in category
    ]
    
    # Filter by include tags
    if include_tags:
        all_scenarios = [
            scenario for scenario in all_scenarios
            if any(tag in scenario.tags for tag in include_tags)
        ]
    
    # Filter by exclude tags
    if exclude_tags:
        all_scenarios = [
            scenario for scenario in all_scenarios
            if not any(tag in scenario.tags for tag in exclude_tags)
        ]
    
    # Filter by priority
    if priority:
        all_scenarios = [
            scenario for scenario in all_scenarios
            if scenario.priority == priority
        ]
    
    # Filter by duration if specified
    if max_duration:
        sorted_scenarios = sorted(all_scenarios, key=lambda s: s.estimated_duration)
        selected_scenarios = []
        total_duration = 0.0
        
        for scenario in sorted_scenarios:
            if total_duration + scenario.estimated_duration <= max_duration:
                selected_scenarios.append(scenario)
                total_duration += scenario.estimated_duration
            else:
                break
        
        return selected_scenarios
    
    return all_scenarios