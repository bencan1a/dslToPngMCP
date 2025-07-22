"""
Unit Tests for DSL Parser
=========================

Comprehensive unit tests for DSL parsing, validation, and transformation.
"""

import pytest
import json
import yaml
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List

from src.core.dsl.parser import (
    DSLValidator, JSONDSLParser, YAMLDSLParser, DSLParserFactory,
    parse_dsl, validate_dsl_syntax, get_validation_suggestions,
    DSLParseError
)
from src.models.schemas import (
    DSLDocument, DSLElement, ElementType, ElementLayout, ElementStyle,
    ParseResult
)

from tests.utils.assertions import (
    assert_successful_parse_result, assert_failed_parse_result,
    assert_valid_dsl_document, assert_valid_json_dsl, assert_valid_yaml_dsl
)
from tests.utils.data_generators import DSLDataGenerator


class TestDSLValidator:
    """Test DSL validation functionality."""
    
    @pytest.fixture
    def validator(self):
        """Create DSL validator instance."""
        return DSLValidator()
    
    def test_validator_initialization(self, validator):
        """Test validator initializes with proper schemas."""
        assert validator.document_schema is not None
        assert validator.element_schema is not None
        assert validator.layout_schema is not None
        assert validator.style_schema is not None
        
        # Check key schema components
        assert 'elements' in validator.document_schema
        assert 'type' in validator.element_schema
        assert 'width' in validator.layout_schema
        assert 'background' in validator.style_schema
    
    def test_validate_valid_document(self, validator):
        """Test validation of valid document."""
        valid_doc = DSLDataGenerator.generate_simple_button()
        is_valid, errors, warnings = validator.validate_document(valid_doc)
        
        assert is_valid is True
        assert len(errors) == 0
        assert isinstance(warnings, list)
    
    def test_validate_document_missing_elements(self, validator):
        """Test validation fails when elements are missing."""
        invalid_doc = {"title": "Test", "width": 800, "height": 600}
        is_valid, errors, warnings = validator.validate_document(invalid_doc)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("elements" in error for error in errors)
    
    def test_validate_document_invalid_element_type(self, validator):
        """Test validation fails with invalid element type."""
        invalid_doc = {
            "width": 800,
            "height": 600,
            "elements": [{"type": "invalid_type", "id": "test"}]
        }
        is_valid, errors, warnings = validator.validate_document(invalid_doc)
        
        assert is_valid is False
        assert len(errors) > 0
    
    def test_validate_document_negative_dimensions(self, validator):
        """Test validation fails with negative dimensions."""
        invalid_doc = {
            "width": -100,
            "height": -50,
            "elements": []
        }
        is_valid, errors, warnings = validator.validate_document(invalid_doc)
        
        assert is_valid is False
        assert len(errors) > 0
    
    def test_validate_element_invalid_children(self, validator):
        """Test validation of element with invalid children."""
        # Text elements cannot have children
        invalid_data = {
            "width": 800,
            "height": 600,
            "elements": [
                {
                    "type": "text",
                    "text": "Invalid",
                    "children": [{"type": "button", "label": "Child"}]
                }
            ]
        }
        is_valid, errors, warnings = validator.validate_document(invalid_data)
        
        assert is_valid is False
        assert len(errors) > 0
        assert any("cannot have children" in error for error in errors)
    
    def test_validate_large_canvas_warning(self, validator):
        """Test warning for large canvas size."""
        large_doc = {
            "width": 2500,
            "height": 1500,
            "elements": []
        }
        is_valid, errors, warnings = validator.validate_document(large_doc)
        
        assert is_valid is True
        assert len(warnings) > 0
        assert any("Large canvas size" in warning for warning in warnings)
    
    def test_validate_element_required_properties(self, validator):
        """Test warnings for missing required element properties."""
        doc_with_warnings = {
            "width": 800,
            "height": 600,
            "elements": [
                {"type": "image", "id": "img1"},  # Missing src
                {"type": "button", "id": "btn1"}  # Missing label
            ]
        }
        is_valid, errors, warnings = validator.validate_document(doc_with_warnings)
        
        assert is_valid is True
        assert len(warnings) >= 2
        assert any("should have 'src'" in warning for warning in warnings)
        assert any("should have 'label'" in warning for warning in warnings)


class TestJSONDSLParser:
    """Test JSON DSL parser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create JSON DSL parser instance."""
        return JSONDSLParser()
    
    @pytest.mark.asyncio
    async def test_parse_valid_json(self, parser):
        """Test parsing valid JSON DSL."""
        valid_json = json.dumps(DSLDataGenerator.generate_simple_button())
        result = await parser.parse(valid_json)
        
        assert_successful_parse_result(result)
        assert result.document.title == "Simple Button"
        assert len(result.document.elements) == 1
        assert result.document.elements[0].type == ElementType.BUTTON
    
    @pytest.mark.asyncio
    async def test_parse_complex_json(self, parser):
        """Test parsing complex JSON DSL with nested elements."""
        complex_json = json.dumps(DSLDataGenerator.generate_login_form())
        result = await parser.parse(complex_json)
        
        assert_successful_parse_result(result)
        assert result.document.title == "Login Form"
        
        # Find container element
        container = result.document.elements[0]
        assert container.type == ElementType.CONTAINER
        assert len(container.children) == 4  # title, username, password, button
    
    @pytest.mark.asyncio
    async def test_parse_invalid_json_syntax(self, parser):
        """Test parsing invalid JSON syntax."""
        invalid_json = '{"title": "Invalid", "elements": [}'  # Missing closing bracket
        result = await parser.parse(invalid_json)
        
        assert_failed_parse_result(result, ["Invalid JSON syntax"])
    
    @pytest.mark.asyncio
    async def test_parse_json_with_validation_errors(self, parser):
        """Test parsing JSON that fails validation."""
        invalid_content = json.dumps({
            "title": "Invalid",
            "width": 800,
            "height": 600,
            "elements": [{"type": "invalid_type"}]
        })
        result = await parser.parse(invalid_content)
        
        assert_failed_parse_result(result)
        assert len(result.errors) > 0
    
    @pytest.mark.asyncio
    async def test_validate_syntax_valid_json(self, parser):
        """Test syntax validation for valid JSON."""
        valid_json = '{"test": true}'
        is_valid = await parser.validate_syntax(valid_json)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_syntax_invalid_json(self, parser):
        """Test syntax validation for invalid JSON."""
        invalid_json = '{"test": true'  # Missing closing brace
        is_valid = await parser.validate_syntax(invalid_json)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_convert_to_dsl_document(self, parser):
        """Test conversion of raw data to DSLDocument."""
        raw_data = DSLDataGenerator.generate_simple_button()
        document = await parser._convert_to_dsl_document(raw_data)
        
        assert_valid_dsl_document(document)
        assert document.title == raw_data["title"]
        assert document.width == raw_data["width"]
        assert document.height == raw_data["height"]
    
    @pytest.mark.asyncio
    async def test_convert_element_with_layout_and_style(self, parser):
        """Test conversion of element with layout and style."""
        element_data = {
            "type": "button",
            "id": "test-button",
            "layout": {"x": 100, "y": 50, "width": 150, "height": 40},
            "style": {"background": "#007bff", "color": "white", "fontSize": 16},
            "label": "Test Button"
        }
        
        element = await parser._convert_to_dsl_element(element_data)
        
        assert element.type == ElementType.BUTTON
        assert element.id == "test-button"
        assert element.label == "Test Button"
        
        # Check layout conversion
        assert element.layout is not None
        assert element.layout.x == 100
        assert element.layout.y == 50
        assert element.layout.width == 150
        assert element.layout.height == 40
        
        # Check style conversion
        assert element.style is not None
        assert element.style.background == "#007bff"
        assert element.style.color == "white"
        assert element.style.font_size == 16
    
    @pytest.mark.asyncio
    async def test_convert_nested_elements(self, parser):
        """Test conversion of nested elements."""
        container_data = {
            "type": "container",
            "id": "main-container",
            "children": [
                {
                    "type": "text",
                    "id": "title",
                    "text": "Hello World"
                },
                {
                    "type": "button",
                    "id": "action-btn",
                    "label": "Click Me"
                }
            ]
        }
        
        element = await parser._convert_to_dsl_element(container_data)
        
        assert element.type == ElementType.CONTAINER
        assert len(element.children) == 2
        assert element.children[0].type == ElementType.TEXT
        assert element.children[1].type == ElementType.BUTTON


class TestYAMLDSLParser:
    """Test YAML DSL parser functionality."""
    
    @pytest.fixture
    def parser(self):
        """Create YAML DSL parser instance."""
        return YAMLDSLParser()
    
    @pytest.mark.asyncio
    async def test_parse_valid_yaml(self, parser):
        """Test parsing valid YAML DSL."""
        yaml_data = DSLDataGenerator.generate_mobile_layout()
        valid_yaml = yaml.dump(yaml_data)
        result = await parser.parse(valid_yaml)
        
        assert_successful_parse_result(result)
        assert result.document.title == "Mobile App Layout"
        assert result.document.width == 375
        assert result.document.height == 667
    
    @pytest.mark.asyncio
    async def test_parse_empty_yaml(self, parser):
        """Test parsing empty YAML content."""
        result = await parser.parse("")
        
        assert_failed_parse_result(result, ["Empty YAML document"])
    
    @pytest.mark.asyncio
    async def test_parse_invalid_yaml_syntax(self, parser):
        """Test parsing invalid YAML syntax."""
        # Use actually invalid YAML syntax - unmatched quotes
        invalid_yaml = """
        title: "Test with unmatched quote
        elements:
          - type: button
            label: Test
        """
        result = await parser.parse(invalid_yaml)
        
        assert_failed_parse_result(result, ["Invalid YAML syntax"])
    
    @pytest.mark.asyncio
    async def test_validate_syntax_valid_yaml(self, parser):
        """Test syntax validation for valid YAML."""
        valid_yaml = "title: Test\nelements: []"
        is_valid = await parser.validate_syntax(valid_yaml)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_syntax_invalid_yaml(self, parser):
        """Test syntax validation for invalid YAML."""
        # Use actually invalid YAML - tab instead of spaces (mixed indentation)
        invalid_yaml = "title: Test\nelements:\n\t- type: button\n  label: Invalid"
        is_valid = await parser.validate_syntax(invalid_yaml)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_yaml_reuses_json_conversion(self, parser):
        """Test that YAML parser reuses JSON parser conversion logic."""
        yaml_data = DSLDataGenerator.generate_simple_button()
        valid_yaml = yaml.dump(yaml_data)
        
        with patch.object(JSONDSLParser, '_convert_to_dsl_document') as mock_convert:
            mock_convert.return_value = Mock(spec=DSLDocument)
            await parser.parse(valid_yaml)
            mock_convert.assert_called_once()


class TestDSLParserFactory:
    """Test DSL parser factory functionality."""
    
    def test_create_json_parser(self):
        """Test creating JSON parser."""
        parser = DSLParserFactory.create_parser("json")
        assert isinstance(parser, JSONDSLParser)
    
    def test_create_yaml_parser(self):
        """Test creating YAML parser."""
        parser = DSLParserFactory.create_parser("yaml")
        assert isinstance(parser, YAMLDSLParser)
    
    def test_create_invalid_parser_type(self):
        """Test creating parser with invalid type."""
        with pytest.raises(ValueError, match="Unsupported parser type"):
            DSLParserFactory.create_parser("xml")
    
    def test_detect_json_content(self):
        """Test detecting JSON content type."""
        json_content = '{"title": "Test"}'
        parser_type = DSLParserFactory.detect_parser_type(json_content)
        assert parser_type == "json"
    
    def test_detect_json_array_content(self):
        """Test detecting JSON array content."""
        json_content = '[{"type": "button"}]'
        parser_type = DSLParserFactory.detect_parser_type(json_content)
        assert parser_type == "json"
    
    def test_detect_yaml_content_with_dashes(self):
        """Test detecting YAML content starting with dashes."""
        yaml_content = '---\ntitle: Test\nelements: []'
        parser_type = DSLParserFactory.detect_parser_type(yaml_content)
        assert parser_type == "yaml"
    
    def test_detect_yaml_content_with_list(self):
        """Test detecting YAML content with list syntax."""
        yaml_content = 'elements:\n  - type: button'
        parser_type = DSLParserFactory.detect_parser_type(yaml_content)
        assert parser_type == "yaml"
    
    def test_detect_fallback_to_yaml(self):
        """Test fallback to YAML for ambiguous content."""
        ambiguous_content = 'title: Test without quotes'
        parser_type = DSLParserFactory.detect_parser_type(ambiguous_content)
        assert parser_type == "yaml"
    
    def test_detect_json_fallback(self):
        """Test detecting valid JSON that doesn't start with brace."""
        # This should parse as JSON successfully
        json_content = '  {"title": "Test with leading spaces"}'
        parser_type = DSLParserFactory.detect_parser_type(json_content)
        assert parser_type == "json"


class TestDSLHelperFunctions:
    """Test DSL helper functions."""
    
    @pytest.mark.asyncio
    async def test_parse_dsl_valid_json(self):
        """Test parse_dsl with valid JSON content."""
        json_content = json.dumps(DSLDataGenerator.generate_simple_button())
        result = await parse_dsl(json_content)
        
        assert_successful_parse_result(result)
        assert result.document is not None
    
    @pytest.mark.asyncio
    async def test_parse_dsl_valid_yaml(self):
        """Test parse_dsl with valid YAML content."""
        yaml_data = DSLDataGenerator.generate_mobile_layout()
        yaml_content = yaml.dump(yaml_data)
        result = await parse_dsl(yaml_content)
        
        assert_successful_parse_result(result)
        assert result.document is not None
    
    @pytest.mark.asyncio
    async def test_parse_dsl_empty_content(self):
        """Test parse_dsl with empty content."""
        result = await parse_dsl("")
        
        assert_failed_parse_result(result, ["Empty DSL content provided"])
    
    @pytest.mark.asyncio
    async def test_parse_dsl_whitespace_only(self):
        """Test parse_dsl with whitespace-only content."""
        result = await parse_dsl("   \n  \t  ")
        
        assert_failed_parse_result(result, ["Empty DSL content provided"])
    
    @pytest.mark.asyncio
    async def test_parse_dsl_with_parser_type_override(self):
        """Test parse_dsl with explicit parser type."""
        yaml_data = DSLDataGenerator.generate_simple_button()
        yaml_content = yaml.dump(yaml_data)
        
        # Force JSON parser on YAML content (should fail)
        result = await parse_dsl(yaml_content, parser_type="json")
        assert_failed_parse_result(result)
    
    @pytest.mark.asyncio
    async def test_parse_dsl_invalid_parser_type(self):
        """Test parse_dsl with invalid parser type."""
        content = '{"test": true}'
        result = await parse_dsl(content, parser_type="invalid")
        
        assert_failed_parse_result(result)
        assert "Unsupported parser type" in result.errors[0]
    
    @pytest.mark.asyncio
    async def test_validate_dsl_syntax_valid_json(self):
        """Test validate_dsl_syntax with valid JSON."""
        json_content = '{"title": "Test", "elements": []}'
        is_valid = await validate_dsl_syntax(json_content)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_dsl_syntax_valid_yaml(self):
        """Test validate_dsl_syntax with valid YAML."""
        yaml_content = "title: Test\nelements: []"
        is_valid = await validate_dsl_syntax(yaml_content)
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_validate_dsl_syntax_invalid_content(self):
        """Test validate_dsl_syntax with invalid content."""
        invalid_content = '{"invalid": json'
        is_valid = await validate_dsl_syntax(invalid_content)
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_validate_dsl_syntax_empty_content(self):
        """Test validate_dsl_syntax with empty content."""
        is_valid = await validate_dsl_syntax("")
        assert is_valid is False
    
    @pytest.mark.asyncio
    async def test_validate_dsl_syntax_with_parser_type(self):
        """Test validate_dsl_syntax with explicit parser type."""
        json_content = '{"title": "Test"}'
        is_valid = await validate_dsl_syntax(json_content, parser_type="json")
        assert is_valid is True
    
    @pytest.mark.asyncio
    async def test_get_validation_suggestions_json_errors(self):
        """Test get_validation_suggestions for JSON errors."""
        content = '{"test": true}'
        errors = ["Invalid JSON syntax at line 1"]
        
        suggestions = await get_validation_suggestions(content, errors)
        
        assert len(suggestions) > 0
        assert any("comma" in suggestion for suggestion in suggestions)
        assert any("quoted" in suggestion for suggestion in suggestions)
    
    @pytest.mark.asyncio
    async def test_get_validation_suggestions_yaml_errors(self):
        """Test get_validation_suggestions for YAML errors."""
        content = "title: Test"
        errors = ["Invalid YAML syntax"]
        
        suggestions = await get_validation_suggestions(content, errors)
        
        assert len(suggestions) > 0
        assert any("indentation" in suggestion for suggestion in suggestions)
    
    @pytest.mark.asyncio
    async def test_get_validation_suggestions_children_error(self):
        """Test get_validation_suggestions for children hierarchy error."""
        content = "{}"
        errors = ["Element type 'text' cannot have children"]
        
        suggestions = await get_validation_suggestions(content, errors)
        
        assert len(suggestions) > 0
        assert any("container" in suggestion for suggestion in suggestions)
    
    @pytest.mark.asyncio
    async def test_get_validation_suggestions_missing_elements(self):
        """Test get_validation_suggestions for missing elements."""
        content = '{"title": "Test"}'
        errors = ["Missing required field: elements"]
        
        suggestions = await get_validation_suggestions(content, errors)
        
        assert len(suggestions) > 0
        assert any("elements" in suggestion for suggestion in suggestions)
    
    @pytest.mark.asyncio
    async def test_get_validation_suggestions_unmatched_braces(self):
        """Test get_validation_suggestions for unmatched braces."""
        content = '{"title": "Test", "elements": []'  # Missing closing brace
        errors = ["JSON syntax error"]
        
        suggestions = await get_validation_suggestions(content, errors)
        
        assert len(suggestions) > 0
        assert any("brace" in suggestion for suggestion in suggestions)
    
    @pytest.mark.asyncio
    async def test_get_validation_suggestions_limit_five(self):
        """Test get_validation_suggestions limits to 5 suggestions."""
        content = "{}"
        errors = [
            "Invalid JSON syntax",
            "Invalid YAML syntax", 
            "Element cannot have children",
            "Missing required field",
            "Another error",
            "Yet another error"
        ]
        
        suggestions = await get_validation_suggestions(content, errors)
        
        assert len(suggestions) <= 5
    
    @pytest.mark.asyncio
    async def test_get_validation_suggestions_deduplication(self):
        """Test get_validation_suggestions removes duplicates."""
        content = "{}"
        errors = ["Invalid JSON syntax", "JSON error"]
        
        suggestions = await get_validation_suggestions(content, errors)
        
        # Should not have duplicate suggestions
        assert len(suggestions) == len(set(suggestions))


class TestDSLParserPerformance:
    """Test DSL parser performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_parse_performance_large_document(self):
        """Test parsing performance with large document."""
        large_dsl = DSLDataGenerator.generate_performance_test_dsl(50)
        json_content = json.dumps(large_dsl)
        
        import time
        start_time = time.perf_counter()
        
        result = await parse_dsl(json_content)
        
        end_time = time.perf_counter()
        parsing_time = end_time - start_time
        
        assert_successful_parse_result(result)
        assert len(result.document.elements) == 50
        assert parsing_time < 5.0  # Should parse within 5 seconds
        assert result.processing_time is not None
        assert result.processing_time > 0
    
    @pytest.mark.asyncio
    async def test_validation_performance_complex_document(self):
        """Test validation performance with complex nested document."""
        complex_dsl = DSLDataGenerator.generate_dashboard()
        json_content = json.dumps(complex_dsl)
        
        import time
        start_time = time.perf_counter()
        
        # Validate syntax only (faster operation)
        is_valid = await validate_dsl_syntax(json_content)
        
        end_time = time.perf_counter()
        validation_time = end_time - start_time
        
        assert is_valid is True
        assert validation_time < 1.0  # Should validate within 1 second


class TestDSLParserEdgeCases:
    """Test DSL parser edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_parse_unicode_content(self):
        """Test parsing DSL with unicode characters."""
        unicode_dsl = {
            "title": "测试文档",  # Chinese characters
            "width": 800,
            "height": 600,
            "elements": [
                {
                    "type": "text",
                    "text": "Hello 世界! 🌍",
                    "id": "unicode-text"
                }
            ]
        }
        
        json_content = json.dumps(unicode_dsl, ensure_ascii=False)
        result = await parse_dsl(json_content)
        
        assert_successful_parse_result(result)
        assert result.document.title == "测试文档"
        assert "世界" in result.document.elements[0].text
    
    @pytest.mark.asyncio
    async def test_parse_very_large_numbers(self):
        """Test parsing with very large numbers."""
        large_number_dsl = {
            "width": 999999,
            "height": 999999,
            "elements": []
        }
        
        json_content = json.dumps(large_number_dsl)
        result = await parse_dsl(json_content)
        
        # Should fail validation due to size limits
        assert_failed_parse_result(result)
    
    @pytest.mark.asyncio
    async def test_parse_deeply_nested_elements(self):
        """Test parsing deeply nested element structure."""
        # Create deeply nested structure
        def create_nested_element(depth: int):
            if depth <= 0:
                return {"type": "text", "text": "Deep text"}
            return {
                "type": "container",
                "children": [create_nested_element(depth - 1)]
            }
        
        deep_dsl = {
            "width": 800,
            "height": 600,
            "elements": [create_nested_element(10)]  # 10 levels deep
        }
        
        json_content = json.dumps(deep_dsl)
        result = await parse_dsl(json_content)
        
        assert_successful_parse_result(result)
        
        # Verify nesting depth
        element = result.document.elements[0]
        depth = 0
        while element.children:
            element = element.children[0]
            depth += 1
        
        assert depth == 10
    
    @pytest.mark.asyncio
    async def test_parse_with_null_values(self):
        """Test parsing DSL with null values."""
        null_value_dsl = {
            "title": None,
            "description": None,
            "width": 800,
            "height": 600,
            "elements": [
                {
                    "type": "text",
                    "text": None,
                    "id": "null-text"
                }
            ]
        }
        
        json_content = json.dumps(null_value_dsl)
        result = await parse_dsl(json_content)
        
        assert_successful_parse_result(result)
        assert result.document.title is None
        assert result.document.description is None
    
    @pytest.mark.asyncio
    async def test_parse_with_extra_properties(self):
        """Test parsing DSL with extra unknown properties."""
        extra_props_dsl = {
            "title": "Test",
            "width": 800,
            "height": 600,
            "elements": [],
            "unknown_property": "should be ignored",
            "custom_metadata": {"version": "2.0"}
        }
        
        json_content = json.dumps(extra_props_dsl)
        result = await parse_dsl(json_content)
        
        # Should succeed (unknown properties are allowed)
        assert_successful_parse_result(result)