"""
Test Data Package
================

Comprehensive test data package for the DSL to PNG conversion system.
Provides sample documents, render options, test scenarios, and utilities
for loading and managing test data.
"""

from .sample_dsl_documents import (
    ALL_TEST_DOCUMENTS,
    get_test_document,
    get_all_valid_documents,
    get_invalid_documents,
    SIMPLE_TEXT_DOCUMENT,
    SIMPLE_LAYOUT_DOCUMENT,
    COMPLEX_DASHBOARD_DOCUMENT,
    RESPONSIVE_DESIGN_DOCUMENT,
    LARGE_DOCUMENT_FOR_PERFORMANCE,
    DEEPLY_NESTED_DOCUMENT,
    EMPTY_DOCUMENT,
    MINIMAL_DOCUMENT,
    MAXIMUM_SIZE_DOCUMENT,
    FORM_DOCUMENT,
    TABLE_DOCUMENT,
    ANIMATED_DOCUMENT
)

from .sample_render_options import (
    ALL_RENDER_OPTIONS,
    get_render_options,
    get_mobile_options,
    get_desktop_options,
    get_quality_options,
    get_performance_options,
    get_browser_options,
    create_custom_options,
    BASIC_RENDER_OPTIONS,
    MOBILE_PORTRAIT_OPTIONS,
    MOBILE_LANDSCAPE_OPTIONS,
    TABLET_OPTIONS,
    DESKTOP_LARGE_OPTIONS,
    HIGH_DPI_RENDER_OPTIONS,
    RETINA_RENDER_OPTIONS
)

from .test_scenarios import (
    TestScenario,
    ALL_SCENARIOS,
    SMOKE_TEST_SCENARIOS,
    CRITICAL_SCENARIOS,
    HIGH_PRIORITY_SCENARIOS,
    PERFORMANCE_TEST_SCENARIOS,
    REGRESSION_TEST_SCENARIOS,
    get_scenario_by_name,
    get_scenarios_by_tag,
    get_scenarios_by_priority,
    get_estimated_test_duration,
    create_test_suite
)

__all__ = [
    # Documents
    'ALL_TEST_DOCUMENTS',
    'get_test_document',
    'get_all_valid_documents',
    'get_invalid_documents',
    'SIMPLE_TEXT_DOCUMENT',
    'SIMPLE_LAYOUT_DOCUMENT',
    'COMPLEX_DASHBOARD_DOCUMENT',
    'RESPONSIVE_DESIGN_DOCUMENT',
    'LARGE_DOCUMENT_FOR_PERFORMANCE',
    'DEEPLY_NESTED_DOCUMENT',
    'EMPTY_DOCUMENT',
    'MINIMAL_DOCUMENT',
    'MAXIMUM_SIZE_DOCUMENT',
    'FORM_DOCUMENT',
    'TABLE_DOCUMENT',
    'ANIMATED_DOCUMENT',
    
    # Render Options
    'ALL_RENDER_OPTIONS',
    'get_render_options',
    'get_mobile_options',
    'get_desktop_options',
    'get_quality_options',
    'get_performance_options',
    'get_browser_options',
    'create_custom_options',
    'BASIC_RENDER_OPTIONS',
    'MOBILE_PORTRAIT_OPTIONS',
    'MOBILE_LANDSCAPE_OPTIONS',
    'TABLET_OPTIONS',
    'DESKTOP_LARGE_OPTIONS',
    'HIGH_DPI_RENDER_OPTIONS',
    'RETINA_RENDER_OPTIONS',
    
    # Test Scenarios
    'TestScenario',
    'ALL_SCENARIOS',
    'SMOKE_TEST_SCENARIOS',
    'CRITICAL_SCENARIOS',
    'HIGH_PRIORITY_SCENARIOS',
    'PERFORMANCE_TEST_SCENARIOS',
    'REGRESSION_TEST_SCENARIOS',
    'get_scenario_by_name',
    'get_scenarios_by_tag',
    'get_scenarios_by_priority',
    'get_estimated_test_duration',
    'create_test_suite'
]