"""
Test Data Generators
====================

Generate test data for comprehensive testing scenarios.
"""

import json
import yaml
import random
import string
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
import uuid

from src.models.schemas import (
    DSLDocument, DSLElement, ElementType, ElementLayout, ElementStyle,
    RenderOptions, DSLRenderRequest, PNGResult, TaskResult, TaskStatus
)


class DSLDataGenerator:
    """Generate DSL test data."""
    
    @staticmethod
    def generate_simple_button() -> Dict[str, Any]:
        """Generate simple button DSL."""
        return {
            "title": "Simple Button",
            "width": 300,
            "height": 200,
            "elements": [
                {
                    "type": "button",
                    "id": "simple-button",
                    "layout": {"x": 100, "y": 80, "width": 100, "height": 40},
                    "label": "Click Me",
                    "style": {"background": "#007bff", "color": "white"}
                }
            ]
        }
    
    @staticmethod
    def generate_login_form() -> Dict[str, Any]:
        """Generate login form DSL."""
        return {
            "title": "Login Form",
            "width": 400,
            "height": 350,
            "elements": [
                {
                    "type": "container",
                    "id": "login-container",
                    "layout": {"x": 50, "y": 50, "width": 300, "height": 250},
                    "style": {"padding": "20px", "border": "1px solid #ddd", "borderRadius": "8px"},
                    "children": [
                        {
                            "type": "text",
                            "id": "title",
                            "layout": {"x": 0, "y": 0, "width": 260, "height": 40},
                            "text": "Login",
                            "style": {"fontSize": "24px", "fontWeight": "bold", "textAlign": "center"}
                        },
                        {
                            "type": "input",
                            "id": "username",
                            "layout": {"x": 0, "y": 60, "width": 260, "height": 35},
                            "placeholder": "Username",
                            "style": {"border": "1px solid #ccc", "borderRadius": "4px", "padding": "8px"}
                        },
                        {
                            "type": "input",
                            "id": "password",
                            "layout": {"x": 0, "y": 105, "width": 260, "height": 35},
                            "placeholder": "Password",
                            "style": {"border": "1px solid #ccc", "borderRadius": "4px", "padding": "8px"}
                        },
                        {
                            "type": "button",
                            "id": "login-btn",
                            "layout": {"x": 0, "y": 160, "width": 260, "height": 40},
                            "label": "Login",
                            "style": {"background": "#28a745", "color": "white", "border": "none", "borderRadius": "4px"}
                        }
                    ]
                }
            ]
        }
    
    @staticmethod
    def generate_dashboard() -> Dict[str, Any]:
        """Generate complex dashboard DSL."""
        return {
            "title": "Admin Dashboard",
            "description": "Complex dashboard layout with multiple components",
            "width": 1200,
            "height": 800,
            "elements": [
                {
                    "type": "navbar",
                    "id": "top-navbar",
                    "layout": {"x": 0, "y": 0, "width": 1200, "height": 60},
                    "style": {"background": "#343a40", "color": "white"},
                    "children": [
                        {
                            "type": "text",
                            "id": "nav-brand",
                            "layout": {"x": 20, "y": 15, "width": 200, "height": 30},
                            "text": "Admin Panel",
                            "style": {"fontSize": "20px", "fontWeight": "bold", "color": "white"}
                        },
                        {
                            "type": "button",
                            "id": "user-menu",
                            "layout": {"x": 1050, "y": 10, "width": 100, "height": 40},
                            "label": "Profile",
                            "style": {"background": "#6c757d", "color": "white", "border": "none"}
                        }
                    ]
                },
                {
                    "type": "sidebar",
                    "id": "main-sidebar",
                    "layout": {"x": 0, "y": 60, "width": 250, "height": 740},
                    "style": {"background": "#f8f9fa", "borderRight": "1px solid #dee2e6"},
                    "children": [
                        {
                            "type": "text",
                            "id": "nav-title",
                            "layout": {"x": 20, "y": 20, "width": 200, "height": 30},
                            "text": "Navigation",
                            "style": {"fontSize": "16px", "fontWeight": "bold"}
                        }
                    ]
                },
                {
                    "type": "container",
                    "id": "main-content",
                    "layout": {"x": 250, "y": 60, "width": 950, "height": 740},
                    "children": [
                        {
                            "type": "grid",
                            "id": "stats-grid",
                            "layout": {"x": 20, "y": 20, "width": 910, "height": 200},
                            "style": {"display": "grid", "gridTemplateColumns": "repeat(4, 1fr)", "gap": "20px"},
                            "children": [
                                {
                                    "type": "card",
                                    "id": "stat-1",
                                    "layout": {"x": 0, "y": 0, "width": 200, "height": 150},
                                    "style": {"background": "white", "border": "1px solid #dee2e6", "borderRadius": "8px", "padding": "20px"},
                                    "children": [
                                        {
                                            "type": "text",
                                            "id": "stat-1-title",
                                            "layout": {"x": 0, "y": 0, "width": 160, "height": 30},
                                            "text": "Total Users",
                                            "style": {"fontSize": "14px", "color": "#6c757d"}
                                        },
                                        {
                                            "type": "text",
                                            "id": "stat-1-value",
                                            "layout": {"x": 0, "y": 40, "width": 160, "height": 50},
                                            "text": "1,234",
                                            "style": {"fontSize": "32px", "fontWeight": "bold", "color": "#007bff"}
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            "css": "body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }",
            "theme": "admin"
        }
    
    @staticmethod
    def generate_mobile_layout() -> Dict[str, Any]:
        """Generate mobile-optimized layout DSL."""
        return {
            "title": "Mobile App Layout",
            "width": 375,
            "height": 667,
            "elements": [
                {
                    "type": "container",
                    "id": "mobile-container",
                    "layout": {"x": 0, "y": 0, "width": 375, "height": 667},
                    "style": {"background": "#f8f9fa"},
                    "children": [
                        {
                            "type": "navbar",
                            "id": "mobile-header",
                            "layout": {"x": 0, "y": 0, "width": 375, "height": 80},
                            "style": {"background": "#007bff", "color": "white", "padding": "20px"},
                            "children": [
                                {
                                    "type": "text",
                                    "id": "header-title",
                                    "layout": {"x": 20, "y": 20, "width": 335, "height": 40},
                                    "text": "My Mobile App",
                                    "style": {"fontSize": "18px", "fontWeight": "bold", "color": "white", "textAlign": "center"}
                                }
                            ]
                        },
                        {
                            "type": "container",
                            "id": "content-area",
                            "layout": {"x": 20, "y": 100, "width": 335, "height": 547},
                            "children": [
                                {
                                    "type": "card",
                                    "id": "welcome-card",
                                    "layout": {"x": 0, "y": 0, "width": 335, "height": 200},
                                    "style": {"background": "white", "borderRadius": "12px", "padding": "20px", "marginBottom": "20px"},
                                    "children": [
                                        {
                                            "type": "text",
                                            "id": "welcome-title",
                                            "layout": {"x": 0, "y": 0, "width": 295, "height": 40},
                                            "text": "Welcome!",
                                            "style": {"fontSize": "24px", "fontWeight": "bold"}
                                        },
                                        {
                                            "type": "text",
                                            "id": "welcome-text",
                                            "layout": {"x": 0, "y": 50, "width": 295, "height": 80},
                                            "text": "This is a mobile-optimized layout designed for smaller screens.",
                                            "style": {"fontSize": "16px", "color": "#6c757d", "lineHeight": "1.5"}
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ],
            "responsiveBreakpoints": {"sm": 375, "md": 768, "lg": 1024}
        }
    
    @staticmethod
    def generate_invalid_dsl_missing_type() -> Dict[str, Any]:
        """Generate invalid DSL missing element type."""
        return {
            "title": "Invalid DSL",
            "width": 400,
            "height": 300,
            "elements": [
                {
                    "id": "invalid-element",
                    "layout": {"x": 100, "y": 100, "width": 200, "height": 100},
                    "text": "Missing type"
                }
            ]
        }
    
    @staticmethod
    def generate_invalid_dsl_invalid_children() -> Dict[str, Any]:
        """Generate invalid DSL with invalid children hierarchy."""
        return {
            "title": "Invalid Children",
            "width": 400,
            "height": 300,
            "elements": [
                {
                    "type": "text",
                    "id": "text-with-children",
                    "layout": {"x": 100, "y": 100, "width": 200, "height": 100},
                    "text": "Text cannot have children",
                    "children": [
                        {
                            "type": "button",
                            "id": "invalid-child",
                            "label": "Invalid"
                        }
                    ]
                }
            ]
        }
    
    @staticmethod
    def generate_edge_case_large_layout() -> Dict[str, Any]:
        """Generate edge case with very large layout."""
        return {
            "title": "Large Layout",
            "width": 3000,
            "height": 2000,
            "elements": [
                {
                    "type": "container",
                    "id": "large-container",
                    "layout": {"x": 0, "y": 0, "width": 3000, "height": 2000},
                    "style": {"background": "white"}
                }
            ]
        }
    
    @staticmethod
    def generate_performance_test_dsl(element_count: int = 100) -> Dict[str, Any]:
        """Generate DSL with many elements for performance testing."""
        elements = []
        grid_size = int(element_count ** 0.5) + 1
        
        for i in range(element_count):
            row = i // grid_size
            col = i % grid_size
            
            elements.append({
                "type": "button",
                "id": f"perf-button-{i}",
                "layout": {
                    "x": col * 120 + 10,
                    "y": row * 60 + 10,
                    "width": 100,
                    "height": 40
                },
                "label": f"Button {i}",
                "style": {
                    "background": f"hsl({(i * 360 / element_count) % 360}, 70%, 50%)",
                    "color": "white",
                    "border": "none",
                    "borderRadius": "4px"
                }
            })
        
        canvas_width = grid_size * 120 + 20
        canvas_height = ((element_count // grid_size) + 1) * 60 + 20
        
        return {
            "title": f"Performance Test - {element_count} Elements",
            "width": min(canvas_width, 2000),
            "height": min(canvas_height, 2000),
            "elements": elements
        }
    
    @staticmethod
    def generate_random_color() -> str:
        """Generate random hex color."""
        return f"#{random.randint(0, 0xFFFFFF):06x}"
    
    @staticmethod
    def generate_random_text(length: int = 10) -> str:
        """Generate random text."""
        return ''.join(random.choices(string.ascii_letters + string.digits + ' ', k=length))
    
    @staticmethod
    def generate_dsl_variations(base_dsl: Dict[str, Any], count: int = 5) -> List[Dict[str, Any]]:
        """Generate variations of a base DSL."""
        variations = []
        
        for i in range(count):
            variation = json.loads(json.dumps(base_dsl))  # Deep copy
            
            # Vary dimensions
            variation["width"] = base_dsl["width"] + random.randint(-100, 100)
            variation["height"] = base_dsl["height"] + random.randint(-100, 100)
            
            # Vary title
            variation["title"] = f"{base_dsl.get('title', 'Test')} - Variation {i+1}"
            
            # Vary element positions slightly
            for element in variation.get("elements", []):
                if "layout" in element:
                    layout = element["layout"]
                    if "x" in layout:
                        layout["x"] = max(0, layout["x"] + random.randint(-20, 20))
                    if "y" in layout:
                        layout["y"] = max(0, layout["y"] + random.randint(-20, 20))
            
            variations.append(variation)
        
        return variations


class RenderOptionsGenerator:
    """Generate render options for testing."""
    
    @staticmethod
    def generate_default() -> RenderOptions:
        """Generate default render options."""
        return RenderOptions()
    
    @staticmethod
    def generate_high_quality() -> RenderOptions:
        """Generate high quality render options."""
        return RenderOptions(
            width=1920,
            height=1080,
            device_scale_factor=2.0,
            wait_for_load=True,
            optimize_png=True,
            timeout=60
        )
    
    @staticmethod
    def generate_mobile() -> RenderOptions:
        """Generate mobile render options."""
        return RenderOptions(
            width=375,
            height=667,
            device_scale_factor=3.0,
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X)",
            wait_for_load=True
        )
    
    @staticmethod
    def generate_fast() -> RenderOptions:
        """Generate fast render options."""
        return RenderOptions(
            width=800,
            height=600,
            device_scale_factor=1.0,
            wait_for_load=False,
            optimize_png=False,
            block_resources=True,
            timeout=10
        )
    
    @staticmethod
    def generate_transparent_background() -> RenderOptions:
        """Generate options with transparent background."""
        return RenderOptions(
            width=800,
            height=600,
            transparent_background=True,
            optimize_png=True
        )
    
    @staticmethod
    def generate_basic_options() -> RenderOptions:
        """Generate basic render options for testing."""
        return RenderOptions(
            width=800,
            height=600,
            device_scale_factor=1.0,
            wait_for_load=True,
            optimize_png=False,
            timeout=30
        )


class MockDataGenerator:
    """Generate mock data for testing."""
    
    @staticmethod
    def generate_png_result(width: int = 800, height: int = 600) -> PNGResult:
        """Generate mock PNG result."""
        fake_png_data = b"fake_png_data_" + str(uuid.uuid4()).encode()
        return PNGResult(
            png_data=fake_png_data,
            base64_data="ZmFrZV9wbmdfZGF0YQ==",  # fake base64
            width=width,
            height=height,
            file_size=len(fake_png_data),
            metadata={
                "generator": "mock",
                "created_at": datetime.utcnow().isoformat(),
                "test_data": True
            }
        )
    
    @staticmethod
    def generate_task_result(status: TaskStatus = TaskStatus.COMPLETED) -> TaskResult:
        """Generate mock task result."""
        task_id = str(uuid.uuid4())
        created_at = datetime.utcnow()
        
        if status == TaskStatus.COMPLETED:
            return TaskResult(
                task_id=task_id,
                status=status,
                png_result=MockDataGenerator.generate_png_result(),
                processing_time=random.uniform(1.0, 5.0),
                created_at=created_at,
                completed_at=created_at + timedelta(seconds=2)
            )
        else:
            return TaskResult(
                task_id=task_id,
                status=status,
                error="Mock error for testing",
                processing_time=random.uniform(0.1, 1.0),
                created_at=created_at,
                completed_at=created_at + timedelta(seconds=1)
            )
    
    @staticmethod
    def generate_error_scenarios() -> List[Tuple[str, str]]:
        """Generate error scenarios for testing."""
        return [
            ("invalid_json", '{"invalid": json}'),
            ("missing_elements", '{"title": "Test"}'),
            ("invalid_element_type", '{"elements": [{"type": "invalid_type"}]}'),
            ("negative_dimensions", '{"width": -100, "height": -100, "elements": []}'),
            ("empty_content", ""),
            ("malformed_yaml", "invalid:\n  - yaml\n    structure"),
        ]


def generate_test_suite_data() -> Dict[str, Any]:
    """Generate comprehensive test suite data."""
    return {
        "simple_examples": {
            "button": DSLDataGenerator.generate_simple_button(),
            "login_form": DSLDataGenerator.generate_login_form(),
            "mobile_layout": DSLDataGenerator.generate_mobile_layout(),
        },
        "complex_examples": {
            "dashboard": DSLDataGenerator.generate_dashboard(),
        },
        "invalid_examples": {
            "missing_type": DSLDataGenerator.generate_invalid_dsl_missing_type(),
            "invalid_children": DSLDataGenerator.generate_invalid_dsl_invalid_children(),
        },
        "edge_cases": {
            "large_layout": DSLDataGenerator.generate_edge_case_large_layout(),
            "performance_100": DSLDataGenerator.generate_performance_test_dsl(100),
        },
        "render_options": {
            "default": RenderOptionsGenerator.generate_default().dict(),
            "high_quality": RenderOptionsGenerator.generate_high_quality().dict(),
            "mobile": RenderOptionsGenerator.generate_mobile().dict(),
            "fast": RenderOptionsGenerator.generate_fast().dict(),
        }
    }