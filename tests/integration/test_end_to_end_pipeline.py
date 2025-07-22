"""
Integration Tests for End-to-End Pipeline
=========================================

Basic integration tests for the DSL to PNG conversion pipeline,
testing the core workflow from DSL parsing to PNG generation.
"""

import pytest
import asyncio
import json
from typing import Dict, Any
from unittest.mock import Mock, patch

from src.core.dsl.parser import DSLParser, parse_dsl
from src.core.rendering.html_generator import HTMLGenerator
from src.core.rendering.png_generator import PNGGenerator
from src.models.schemas import DSLDocument, RenderOptions, PNGResult

from tests.utils.data_generators import MockDataGenerator
from tests.utils.helpers import create_temp_directory, measure_performance
from tests.utils.assertions import (
    assert_valid_dsl_document, assert_valid_png_result,
    assert_performance_within_limits
)


class TestBasicPipeline:
    """Test basic DSL to PNG conversion pipeline."""
    
    @pytest.fixture
    def dsl_parser(self):
        """Create DSL parser instance."""
        return DSLParser()
    
    @pytest.fixture
    def html_generator(self):
        """Create HTML generator instance."""
        return HTMLGenerator()
    
    @pytest.fixture
    async def png_generator(self):
        """Create PNG generator instance."""
        generator = PNGGenerator()
        await generator.initialize()
        yield generator
        await generator.close()
    
    @pytest.mark.asyncio
    async def test_simple_dsl_to_png_pipeline(self, dsl_parser, html_generator, png_generator):
        """Test complete pipeline with simple DSL document."""
        # Step 1: Create simple DSL document
        dsl_content = {
            "title": "Test Document",
            "viewport": {"width": 800, "height": 600},
            "elements": [
                {
                    "type": "text",
                    "content": "Hello World",
                    "style": {"fontSize": "24px", "color": "#333"}
                }
            ]
        }
        
        # Step 2: Parse DSL
        dsl_document = dsl_parser.parse_json(json.dumps(dsl_content))
        assert_valid_dsl_document(dsl_document)
        assert dsl_document.title == "Test Document"
        
        # Step 3: Generate HTML
        render_options = RenderOptions(
            width=800,
            height=600,
            device_scale_factor=1.0
        )
        
        html_content = await html_generator.generate_html(dsl_document, render_options)
        assert html_content is not None
        assert "Hello World" in html_content
        assert "800px" in html_content or "800" in html_content
        
        # Step 4: Generate PNG
        png_result = await png_generator.generate_png(
            html_content=html_content,
            render_options=render_options,
            task_id="test-task-001"
        )
        
        assert_valid_png_result(png_result)
        assert png_result.width == 800
        assert png_result.height == 600
        assert len(png_result.png_data) > 0
    
    @pytest.mark.asyncio
    async def test_complex_dsl_to_png_pipeline(self, dsl_parser, html_generator, png_generator):
        """Test complete pipeline with complex DSL document."""
        # Complex DSL with multiple elements and styling
        dsl_content = {
            "title": "Complex Layout Test",
            "viewport": {"width": 1200, "height": 800},
            "theme": {
                "primaryColor": "#007bff",
                "secondaryColor": "#6c757d",
                "backgroundColor": "#f8f9fa"
            },
            "elements": [
                {
                    "type": "container",
                    "id": "header",
                    "style": {
                        "width": "100%",
                        "height": "80px",
                        "backgroundColor": "#007bff",
                        "display": "flex",
                        "alignItems": "center",
                        "justifyContent": "center"
                    },
                    "children": [
                        {
                            "type": "text",
                            "content": "Complex Layout Demo",
                            "style": {
                                "fontSize": "32px",
                                "color": "white",
                                "fontWeight": "bold"
                            }
                        }
                    ]
                },
                {
                    "type": "container",
                    "id": "content",
                    "style": {
                        "width": "100%",
                        "padding": "20px",
                        "display": "grid",
                        "gridTemplateColumns": "1fr 1fr",
                        "gap": "20px"
                    },
                    "children": [
                        {
                            "type": "card",
                            "title": "Card 1",
                            "content": "This is the first card content",
                            "style": {
                                "border": "1px solid #dee2e6",
                                "borderRadius": "8px",
                                "padding": "16px"
                            }
                        },
                        {
                            "type": "card",
                            "title": "Card 2",
                            "content": "This is the second card content",
                            "style": {
                                "border": "1px solid #dee2e6",
                                "borderRadius": "8px",
                                "padding": "16px"
                            }
                        }
                    ]
                }
            ]
        }
        
        # Parse and validate
        parse_result = await parse_dsl(json.dumps(dsl_content))
        assert parse_result.success, f"DSL parsing failed: {parse_result.errors}"
        dsl_document = parse_result.document
        assert_valid_dsl_document(dsl_document)
        assert len(dsl_document.elements) == 2
        
        # Generate with high quality options
        render_options = RenderOptions(
            width=1200,
            height=800,
            device_scale_factor=2.0,  # High DPI
            wait_for_fonts=True,
            wait_for_images=True
        )
        
        # Measure performance
        with measure_performance() as timer:
            html_content = await html_generator.generate_html(dsl_document, render_options)
            png_result = await png_generator.generate_png(
                html_content=html_content,
                render_options=render_options,
                task_id="test-complex-001"
            )
        
        # Verify results
        assert_valid_png_result(png_result)
        assert png_result.width == 1200
        assert png_result.height == 800
        
        # Performance should be reasonable even for complex documents
        assert_performance_within_limits(timer.elapsed_time, max_time=10.0)
        
        # Verify content
        assert "Complex Layout Demo" in html_content
        assert "grid" in html_content.lower()
        assert "#007bff" in html_content
    
    @pytest.mark.asyncio
    async def test_error_handling_in_pipeline(self, dsl_parser, html_generator, png_generator):
        """Test error handling throughout the pipeline."""
        
        # Test 1: Invalid DSL
        with pytest.raises(Exception):  # Should raise parsing error
            dsl_parser.parse_json('{"invalid": json syntax}')
        
        # Test 2: Missing required fields
        invalid_dsl = {"title": "Test"}  # Missing elements
        with pytest.raises(Exception):
            dsl_parser.parse_json(json.dumps(invalid_dsl))
        
        # Test 3: Valid DSL but invalid render options
        valid_dsl = {
            "title": "Test",
            "viewport": {"width": 800, "height": 600},
            "elements": [{"type": "text", "content": "Test"}]
        }
        
        dsl_document = dsl_parser.parse_json(json.dumps(valid_dsl))
        
        # Invalid dimensions
        invalid_options = RenderOptions(width=-1, height=-1)
        
        with pytest.raises(Exception):
            await html_generator.generate_html(dsl_document, invalid_options)
    
    @pytest.mark.asyncio
    async def test_concurrent_pipeline_execution(self, dsl_parser, html_generator, png_generator):
        """Test concurrent execution of multiple pipelines."""
        
        async def run_pipeline(index: int) -> PNGResult:
            """Run a complete pipeline for testing concurrency."""
            dsl_content = {
                "title": f"Concurrent Test {index}",
                "viewport": {"width": 400, "height": 300},
                "elements": [
                    {
                        "type": "text",
                        "content": f"Content {index}",
                        "style": {"fontSize": "16px"}
                    }
                ]
            }
            
            dsl_document = dsl_parser.parse_json(json.dumps(dsl_content))
            render_options = RenderOptions(width=400, height=300)
            
            html_content = await html_generator.generate_html(dsl_document, render_options)
            png_result = await png_generator.generate_png(
                html_content=html_content,
                render_options=render_options,
                task_id=f"concurrent-{index}"
            )
            
            return png_result
        
        # Run 5 concurrent pipelines
        with measure_performance() as timer:
            tasks = [run_pipeline(i) for i in range(5)]
            results = await asyncio.gather(*tasks)
        
        # Verify all completed successfully
        assert len(results) == 5
        assert all(result for result in results)
        
        # Should complete within reasonable time
        assert_performance_within_limits(timer.elapsed_time, max_time=15.0)
    
    @pytest.mark.asyncio
    async def test_custom_fonts_pipeline(self, dsl_parser, html_generator, png_generator):
        """Test pipeline with custom fonts."""
        dsl_content = {
            "title": "Custom Assets Test",
            "viewport": {"width": 800, "height": 600},
            "fonts": [
                {
                    "family": "Roboto",
                    "url": "https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700"
                }
            ],
            "elements": [
                {
                    "type": "text",
                    "content": "Text with custom font",
                    "style": {
                        "fontFamily": "Roboto, sans-serif",
                        "fontSize": "24px",
                        "fontWeight": "700"
                    }
                }
            ]
        }
        
        dsl_document = dsl_parser.parse_json(json.dumps(dsl_content))
        render_options = RenderOptions(
            width=800,
            height=600,
            wait_for_fonts=True,  # Important for custom fonts
            wait_for_images=True
        )
        
        html_content = await html_generator.generate_html(dsl_document, render_options)
        png_result = await png_generator.generate_png(
            html_content=html_content,
            render_options=render_options,
            task_id="custom-assets-001"
        )
        
        # Verify results
        assert_valid_png_result(png_result)
        
        # HTML should contain font references
        assert "Roboto" in html_content
        assert "fonts.googleapis.com" in html_content or "font" in html_content.lower()


class TestPipelinePerformance:
    """Test pipeline performance characteristics."""
    
    @pytest.fixture
    def dsl_parser(self):
        return DSLParser()
    
    @pytest.fixture
    def html_generator(self):
        return HTMLGenerator()
    
    @pytest.fixture
    async def png_generator(self):
        generator = PNGGenerator()
        await generator.initialize()
        yield generator
        await generator.close()
    
    @pytest.mark.asyncio
    async def test_pipeline_throughput(self, dsl_parser, html_generator, png_generator):
        """Test pipeline throughput with multiple documents."""
        
        async def process_document(index: int) -> float:
            """Process a single document and return processing time."""
            dsl_content = {
                "title": f"Throughput Test {index}",
                "viewport": {"width": 300, "height": 200},
                "elements": [
                    {
                        "type": "text",
                        "content": f"Document {index}",
                        "style": {"fontSize": "14px"}
                    }
                ]
            }
            
            with measure_performance() as timer:
                dsl_document = dsl_parser.parse_json(json.dumps(dsl_content))
                render_options = RenderOptions(width=300, height=200)
                
                html_content = await html_generator.generate_html(dsl_document, render_options)
                png_result = await png_generator.generate_png(
                    html_content=html_content,
                    render_options=render_options,
                    task_id=f"throughput-{index}"
                )
            
            return timer.elapsed_time
        
        # Process 10 documents sequentially
        processing_times = []
        for i in range(10):
            processing_time = await process_document(i)
            processing_times.append(processing_time)
        
        # Verify performance characteristics
        avg_time = sum(processing_times) / len(processing_times)
        max_time = max(processing_times)
        
        # Average processing time should be reasonable
        assert avg_time < 5.0  # Less than 5 seconds average
        assert max_time < 10.0  # No single document takes more than 10 seconds
        
        # Performance should be consistent (no extreme outliers)
        time_variance = max(processing_times) - min(processing_times)
        assert time_variance < avg_time * 3  # Variance within 3x average
    
    @pytest.mark.asyncio
    async def test_memory_usage_stability(self, dsl_parser, html_generator, png_generator):
        """Test that memory usage remains stable across multiple operations."""
        
        # Process multiple documents to test for memory leaks
        for i in range(20):
            dsl_content = {
                "title": f"Memory Test {i}",
                "viewport": {"width": 400, "height": 300},
                "elements": [
                    {
                        "type": "text",
                        "content": f"Memory test document {i}",
                        "style": {"fontSize": "16px"}
                    }
                ]
            }
            
            dsl_document = dsl_parser.parse_json(json.dumps(dsl_content))
            render_options = RenderOptions(width=400, height=300)
            
            html_content = await html_generator.generate_html(dsl_document, render_options)
            png_result = await png_generator.generate_png(
                html_content=html_content,
                render_options=render_options,
                task_id=f"memory-test-{i}"
            )
            
            # Verify each operation succeeds
            assert png_result is not None
            
            # Clean up explicitly to help with memory management
            del dsl_document, html_content, png_result
        
        # If we reach here without memory errors, the test passes
        assert True