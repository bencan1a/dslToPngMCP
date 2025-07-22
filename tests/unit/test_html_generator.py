"""
Unit Tests for HTML Generator
=============================

Comprehensive unit tests for HTML generation, template rendering, and component-based layouts.
"""

import pytest
import jinja2
from unittest.mock import Mock, patch, AsyncMock, MagicMock
from typing import Dict, Any

from src.core.rendering.html_generator import (
    HTMLGenerationError, BaseHTMLGenerator, Jinja2HTMLGenerator,
    ComponentHTMLGenerator, HTMLGeneratorFactory, generate_html
)
from src.models.schemas import (
    DSLDocument, DSLElement, ElementType, ElementLayout, ElementStyle,
    RenderOptions
)

from tests.utils.assertions import (
    assert_valid_html_content, assert_html_contains_elements,
    assert_performance_within_threshold
)
from tests.utils.data_generators import DSLDataGenerator, RenderOptionsGenerator
from tests.utils.helpers import create_temp_file, TestTimer


class TestHTMLGenerationError:
    """Test HTML generation error handling."""
    
    def test_html_generation_error_creation(self):
        """Test creating HTML generation error."""
        error = HTMLGenerationError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)
    
    def test_html_generation_error_inheritance(self):
        """Test error inheritance."""
        error = HTMLGenerationError("Test")
        assert isinstance(error, Exception)


class TestBaseHTMLGenerator:
    """Test base HTML generator abstract class."""
    
    def test_base_html_generator_is_abstract(self):
        """Test that BaseHTMLGenerator cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseHTMLGenerator()
    
    def test_base_html_generator_abstract_method(self):
        """Test that generate method is abstract."""
        class ConcreteGenerator(BaseHTMLGenerator):
            pass
        
        with pytest.raises(TypeError):
            ConcreteGenerator()


class TestJinja2HTMLGenerator:
    """Test Jinja2-based HTML generator."""
    
    @pytest.fixture
    def generator(self):
        """Create Jinja2 HTML generator instance."""
        with patch('src.core.rendering.html_generator.get_settings') as mock_settings:
            mock_settings.return_value = Mock()
            return Jinja2HTMLGenerator()
    
    @pytest.fixture
    def sample_document(self):
        """Create sample DSL document."""
        doc_data = DSLDataGenerator.generate_simple_button()
        # Convert dictionary to DSLDocument object
        return DSLDocument(
            title=doc_data["title"],
            width=doc_data["width"],
            height=doc_data["height"],
            elements=[],  # Simplified for testing
            css=""  # Empty string instead of None to match Pydantic validation
        )
    
    @pytest.fixture
    def sample_options(self):
        """Create sample render options."""
        return RenderOptionsGenerator.generate_basic_options()
    
    def test_generator_initialization(self, generator):
        """Test generator initialization."""
        assert generator.env is not None
        assert isinstance(generator.env, jinja2.Environment)
        assert generator.settings is not None
        assert generator.logger is not None
    
    def test_jinja2_environment_setup(self, generator):
        """Test Jinja2 environment configuration."""
        env = generator.env
        
        # Check autoescape is configured (should be a function from select_autoescape)
        assert callable(env.autoescape), "Autoescape should be a callable function from select_autoescape"
        
        # Check async is enabled by creating a test template and verifying it has async methods
        test_template = env.from_string("test")
        assert hasattr(test_template, 'render_async'), "Template should have render_async method when async is enabled"
        
        # Check loader is configured
        assert isinstance(env.loader, jinja2.FileSystemLoader)
    
    def test_custom_filters_registration(self, generator):
        """Test custom filters are registered."""
        filters = generator.env.filters
        
        assert 'px' in filters
        assert 'css_safe' in filters
        assert 'style_to_css' in filters
        assert 'layout_to_css' in filters
        
        # Test globals
        globals_dict = generator.env.globals
        assert 'render_element' in globals_dict
    
    def test_px_filter(self, generator):
        """Test px filter functionality."""
        px_filter = generator.env.filters['px']
        
        assert px_filter(10) == "10px"
        assert px_filter(25.5) == "25.5px"
        assert px_filter(0) == "0px"
    
    def test_css_safe_filter(self, generator):
        """Test css_safe filter functionality."""
        css_safe = generator.env.filters['css_safe']
        
        assert css_safe('normal text') == 'normal text'
        assert css_safe('text with "quotes"') == 'text with \\"quotes\\"'
        assert css_safe("text with 'single quotes'") == "text with \\'single quotes\\'"
        assert css_safe('text with "both" and \'quotes\'') == 'text with \\"both\\" and \\\'quotes\\\''
    
    def test_style_to_css_filter_basic_styles(self, generator):
        """Test style_to_css filter with basic styles."""
        style_to_css = generator.env.filters['style_to_css']
        
        # Test with None
        assert style_to_css(None) == ""
        
        # Test with style object
        style = Mock()
        style.background = "#007bff"
        style.color = "white"
        style.font_size = 16
        style.font_weight = "bold"
        style.font_family = "Arial, sans-serif"
        style.border = "1px solid #ccc"
        style.border_radius = 4
        style.margin = 8
        style.padding = 12
        style.opacity = 0.8
        style.z_index = 10
        
        # Set attributes that don't exist to None
        for attr in ['display', 'position', 'flex_direction', 'justify_content', 'align_items', 'transition', 'transform']:
            setattr(style, attr, None)
        
        css = style_to_css(style)
        
        assert "background: #007bff" in css
        assert "color: white" in css
        assert "font-size: 16px" in css
        assert "font-weight: bold" in css
        assert "font-family: Arial, sans-serif" in css
        assert "border: 1px solid #ccc" in css
        assert "border-radius: 4px" in css
        assert "margin: 8px" in css
        assert "padding: 12px" in css
        assert "opacity: 0.8" in css
        assert "z-index: 10" in css
    
    def test_style_to_css_filter_layout_styles(self, generator):
        """Test style_to_css filter with layout styles."""
        style_to_css = generator.env.filters['style_to_css']
        
        style = Mock()
        # Set basic styles to None
        for attr in ['background', 'color', 'font_size', 'font_weight', 'font_family', 
                     'border', 'border_radius', 'margin', 'padding', 'opacity', 'z_index']:
            setattr(style, attr, None)
        
        # Set layout styles
        style.display = "flex"
        style.position = "relative"
        style.flex_direction = "column"
        style.justify_content = "center"
        style.align_items = "stretch"
        style.transition = "all 0.3s ease"
        style.transform = "scale(1.1)"
        
        css = style_to_css(style)
        
        assert "display: flex" in css
        assert "position: relative" in css
        assert "flex-direction: column" in css
        assert "justify-content: center" in css
        assert "align-items: stretch" in css
        assert "transition: all 0.3s ease" in css
        assert "transform: scale(1.1)" in css
    
    def test_layout_to_css_filter(self, generator):
        """Test layout_to_css filter functionality."""
        layout_to_css = generator.env.filters['layout_to_css']
        
        # Test with None
        assert layout_to_css(None) == ""
        
        # Test with layout object
        layout = Mock()
        layout.x = 100
        layout.y = 50
        layout.width = 200
        layout.height = 150
        layout.min_width = 100
        layout.max_width = 300
        layout.min_height = 75
        layout.max_height = 200
        
        css = layout_to_css(layout)
        
        assert "left: 100px" in css
        assert "top: 50px" in css
        assert "width: 200px" in css
        assert "height: 150px" in css
        assert "min-width: 100px" in css
        assert "max-width: 300px" in css
        assert "min-height: 75px" in css
        assert "max-height: 200px" in css
    
    @pytest.mark.asyncio
    async def test_generate_html_success(self, generator, sample_document, sample_options):
        """Test successful HTML generation."""
        # Mock template
        mock_template = AsyncMock()
        mock_template.render_async.return_value = "<html><body>Test</body></html>"
        
        with patch.object(generator.env, 'get_template', return_value=mock_template):
            html = await generator.generate(sample_document, sample_options)
            
            assert html == "<html><body>Test</body></html>"
            mock_template.render_async.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_generate_html_template_error(self, generator, sample_document, sample_options):
        """Test HTML generation with template error."""
        with patch.object(generator.env, 'get_template', side_effect=jinja2.TemplateNotFound("base.html")):
            with pytest.raises(HTMLGenerationError, match="Template rendering failed"):
                await generator.generate(sample_document, sample_options)
    
    @pytest.mark.asyncio
    async def test_generate_html_unexpected_error(self, generator, sample_document, sample_options):
        """Test HTML generation with unexpected error."""
        with patch.object(generator.env, 'get_template', side_effect=Exception("Unexpected error")):
            with pytest.raises(HTMLGenerationError, match="Unexpected HTML generation error"):
                await generator.generate(sample_document, sample_options)
    
    def test_get_template_name(self, generator, sample_document, sample_options):
        """Test template name selection."""
        template_name = generator._get_template_name(sample_document, sample_options)
        assert template_name == "base.html"
    
    @pytest.mark.asyncio
    async def test_prepare_context(self, generator, sample_document, sample_options):
        """Test template context preparation."""
        context = await generator._prepare_context(sample_document, sample_options)
        
        assert context["document"] == sample_document
        assert context["options"] == sample_options
        assert context["width"] == sample_document.width
        assert context["height"] == sample_document.height
        assert context["elements"] == sample_document.elements
        assert context["settings"] == generator.settings
    
    def test_render_button_element(self, generator):
        """Test rendering button element."""
        element = Mock()
        element.type.value = "button"
        element.id = "test-button"
        element.label = "Click Me"
        element.text = None
        element.onClick = "handleClick()"
        element.class_name = "custom-btn"
        element.layout = None
        element.style = None
        element.custom_attributes = None
        
        html = generator._render_element_html(element, 0)
        
        assert '<button' in html
        assert 'class="dsl-element dsl-button custom-btn"' in html
        assert 'id="test-button"' in html
        assert 'data-type="button"' in html
        assert 'onclick="handleClick()"' in html
        assert '>Click Me</button>' in html
    
    def test_render_text_element(self, generator):
        """Test rendering text element."""
        element = Mock()
        element.type.value = "text"
        element.id = "test-text"
        element.text = "Hello World"
        element.class_name = None
        element.layout = None
        element.style = None
        element.custom_attributes = None
        
        html = generator._render_element_html(element, 1)
        
        assert '<div' in html
        assert 'class="dsl-element dsl-text"' in html
        assert 'id="test-text"' in html
        assert '>Hello World</div>' in html
    
    def test_render_input_element(self, generator):
        """Test rendering input element."""
        element = Mock()
        element.type.value = "input"
        element.id = "test-input"
        element.placeholder = "Enter text"
        element.onChange = "handleChange()"
        element.class_name = None
        element.layout = None
        element.style = None
        element.custom_attributes = None
        
        html = generator._render_element_html(element, 2)
        
        assert '<input type="text"' in html
        assert 'class="dsl-element dsl-input"' in html
        assert 'id="test-input"' in html
        assert 'placeholder="Enter text"' in html
        assert 'onchange="handleChange()"' in html
    
    def test_render_image_element(self, generator):
        """Test rendering image element."""
        element = Mock()
        element.type.value = "image"
        element.id = "test-image"
        element.src = "https://example.com/image.jpg"
        element.alt = "Test Image"
        element.class_name = None
        element.layout = None
        element.style = None
        element.custom_attributes = None
        
        html = generator._render_element_html(element, 3)
        
        assert '<img' in html
        assert 'class="dsl-element dsl-image"' in html
        assert 'id="test-image"' in html
        assert 'src="https://example.com/image.jpg"' in html
        assert 'alt="Test Image"' in html
    
    def test_render_container_element(self, generator):
        """Test rendering container element with children."""
        # Create mock child elements
        child1 = Mock()
        child1.type.value = "text"
        child1.id = "child1"
        child1.text = "Child 1"
        child1.class_name = None
        child1.layout = None
        child1.style = None
        child1.custom_attributes = None
        
        child2 = Mock()
        child2.type.value = "button"
        child2.id = "child2"
        child2.label = "Child Button"
        child2.text = None
        child2.onClick = None
        child2.class_name = None
        child2.layout = None
        child2.style = None
        child2.custom_attributes = None
        
        element = Mock()
        element.type.value = "container"
        element.id = "test-container"
        element.children = [child1, child2]
        element.class_name = None
        element.layout = None
        element.style = None
        element.custom_attributes = None
        
        html = generator._render_element_html(element, 4)
        
        assert '<div' in html
        assert 'class="dsl-element dsl-container"' in html
        assert 'id="test-container"' in html
        assert 'Child 1' in html
        assert 'Child Button' in html
        assert '</div>' in html
    
    def test_render_navbar_element(self, generator):
        """Test rendering navbar element."""
        element = Mock()
        element.type.value = "navbar"
        element.id = "test-navbar"
        element.children = []
        element.class_name = None
        element.layout = None
        element.style = None
        element.custom_attributes = None
        
        html = generator._render_element_html(element, 5)
        
        assert '<nav' in html
        assert 'class="dsl-element dsl-navbar"' in html
        assert '</nav>' in html
    
    def test_render_sidebar_element(self, generator):
        """Test rendering sidebar element."""
        element = Mock()
        element.type.value = "sidebar"
        element.id = "test-sidebar"
        element.children = []
        element.class_name = None
        element.layout = None
        element.style = None
        element.custom_attributes = None
        
        html = generator._render_element_html(element, 6)
        
        assert '<aside' in html
        assert 'class="dsl-element dsl-sidebar"' in html
        assert '</aside>' in html
    
    def test_render_generic_element(self, generator):
        """Test rendering generic/unknown element."""
        element = Mock()
        element.type.value = "unknown"
        element.id = "test-generic"
        element.text = "Generic content"
        element.class_name = None
        element.layout = None
        element.style = None
        element.custom_attributes = None
        
        html = generator._render_element_html(element, 7)
        
        assert '<div' in html
        assert 'class="dsl-element dsl-unknown"' in html
        assert '>Generic content</div>' in html
    
    def test_build_attributes_empty(self, generator):
        """Test building attributes from empty dict."""
        attrs = generator._build_attributes({})
        assert attrs == ""
    
    def test_build_attributes_with_values(self, generator):
        """Test building attributes with values."""
        attributes = {
            'class': 'test-class',
            'id': 'test-id',
            'data-value': 'test-data'
        }
        
        attrs = generator._build_attributes(attributes)
        
        assert 'class="test-class"' in attrs
        assert 'id="test-id"' in attrs
        assert 'data-value="test-data"' in attrs
    
    def test_build_attributes_with_empty_values(self, generator):
        """Test building attributes with some empty values."""
        attributes = {
            'class': 'test-class',
            'id': '',
            'data-value': None
        }
        
        attrs = generator._build_attributes(attributes)
        
        assert 'class="test-class"' in attrs
        assert 'id=' not in attrs
        assert 'data-value=' not in attrs
    
    def test_escape_html(self, generator):
        """Test HTML escaping functionality."""
        escape = generator._escape_html
        
        assert escape("") == ""
        assert escape("normal text") == "normal text"
        assert escape("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
        assert escape('Text with "quotes" & <tags>') == 'Text with &quot;quotes&quot; &amp; &lt;tags&gt;'
        assert escape("&<>\"'") == "&amp;&lt;&gt;&quot;&#x27;"
    
    def test_render_element_with_layout_and_style(self, generator):
        """Test rendering element with layout and style."""
        layout = Mock()
        layout.x = 10
        layout.y = 20
        layout.width = 100
        layout.height = 50
        
        style = Mock()
        style.background = "#ff0000"
        style.color = "white"
        
        element = Mock()
        element.type.value = "button"
        element.id = "styled-button"
        element.label = "Styled"
        element.text = None
        element.onClick = None
        element.class_name = None
        element.layout = layout
        element.style = style
        element.custom_attributes = None
        
        # Mock the filter methods
        generator.env.filters['layout_to_css'] = Mock(return_value="left: 10px; top: 20px; width: 100px; height: 50px")
        generator.env.filters['style_to_css'] = Mock(return_value="background: #ff0000; color: white")
        
        html = generator._render_element_html(element, 0)
        
        assert 'style="left: 10px; top: 20px; width: 100px; height: 50px; background: #ff0000; color: white"' in html
    
    def test_render_element_with_custom_attributes(self, generator):
        """Test rendering element with custom attributes."""
        element = Mock()
        element.type.value = "button"
        element.id = "custom-button"
        element.label = "Custom"
        element.text = None
        element.onClick = None
        element.class_name = None
        element.layout = None
        element.style = None
        element.custom_attributes = {
            'data-custom': 'value',
            'aria-label': 'Custom button'
        }
        
        html = generator._render_element_html(element, 0)
        
        assert 'data-custom="value"' in html
        assert 'aria-label="Custom button"' in html


class TestComponentHTMLGenerator:
    """Test component-based HTML generator."""
    
    @pytest.fixture
    def generator(self):
        """Create component HTML generator instance."""
        return ComponentHTMLGenerator()
    
    @pytest.fixture
    def sample_document(self):
        """Create sample DSL document."""
        doc_data = DSLDataGenerator.generate_simple_button()
        # Convert to proper DSLDocument object
        document = Mock(spec=DSLDocument)
        document.title = doc_data["title"]
        document.width = doc_data["width"]
        document.height = doc_data["height"]
        document.css = ""
        
        # Create mock element with proper nested Mock structure
        element = Mock(spec=DSLElement)
        element.type = Mock()
        element.type.value = "button"
        element.layout = Mock()
        element.layout.x = 10
        element.layout.y = 20
        # Fix: Configure layout dimensions as actual integers, not Mock objects
        element.layout.width = 100
        element.layout.height = 30
        element.style = None
        
        # Add missing attributes that ComponentHTMLGenerator expects
        element.label = "Test Button"
        element.text = "Button Text"
        element.id = "test-button"
        element.class_name = None
        element.custom_attributes = {}
        
        document.elements = [element]
        
        return document
    
    @pytest.fixture
    def sample_options(self):
        """Create sample render options."""
        return RenderOptionsGenerator.generate_basic_options()
    
    def test_generator_initialization(self, generator):
        """Test generator initialization."""
        assert generator.logger is not None
        assert generator.component_registry is not None
        assert isinstance(generator.component_registry, dict)
    
    def test_component_registry_setup(self, generator):
        """Test component registry contains expected components."""
        registry = generator.component_registry
        
        expected_components = [
            "button", "text", "input", "image", "container",
            "grid", "flex", "card", "modal", "navbar", "sidebar"
        ]
        
        for component in expected_components:
            assert component in registry
            assert callable(registry[component])
    
    @pytest.mark.asyncio
    async def test_generate_html_success(self, generator, sample_document, sample_options):
        """Test successful HTML generation."""
        html = await generator.generate(sample_document, sample_options)
        
        assert_valid_html_content(html)
        assert '<!DOCTYPE html>' in html
        assert '<html lang="en">' in html
        assert '<meta charset="UTF-8">' in html
        assert '<meta name="viewport"' in html
        assert 'dsl-canvas' in html
        # Fix: data-render-complete is set via JavaScript, not in static HTML
        assert 'document.body.setAttribute("data-render-complete", "true")' in html
    
    @pytest.mark.asyncio
    async def test_generate_html_with_title(self, generator, sample_document, sample_options):
        """Test HTML generation with document title."""
        sample_document.title = "Test Document"
        
        html = await generator.generate(sample_document, sample_options)
        
        assert '<title>Test Document</title>' in html
    
    @pytest.mark.asyncio
    async def test_generate_html_with_custom_css(self, generator, sample_document, sample_options):
        """Test HTML generation with custom CSS."""
        sample_document.css = ".custom { color: red; }"
        
        html = await generator.generate(sample_document, sample_options)
        
        assert '<style>.custom { color: red; }</style>' in html
    
    @pytest.mark.asyncio
    async def test_generate_html_error_handling(self, generator, sample_document, sample_options):
        """Test HTML generation error handling."""
        # Mock an error in rendering
        with patch.object(generator, '_render_component', side_effect=Exception("Component error")):
            with pytest.raises(HTMLGenerationError, match="Component-based HTML generation failed"):
                await generator.generate(sample_document, sample_options)
    
    @pytest.mark.asyncio
    async def test_render_component_registered(self, generator):
        """Test rendering registered component."""
        element = Mock()
        element.type.value = "button"
        
        # Replace component registry with a dict that has the mock behavior
        mock_component_func = lambda e: "<button>Test</button>"
        original_registry = generator.component_registry.copy()
        generator.component_registry = {"button": mock_component_func}
        
        html = await generator._render_component(element)
        assert html == "<button>Test</button>"
        
        # Restore original registry
        generator.component_registry = original_registry
    
    @pytest.mark.asyncio
    async def test_render_component_unregistered(self, generator):
        """Test rendering unregistered component."""
        element = Mock()
        element.type.value = "unknown"
        element.text = "Unknown content"
        element.layout = None
        element.style = None
        
        html = await generator._render_component(element)
        
        assert 'dsl-element' in html
        assert 'Unknown content' in html
    
    def test_generate_base_styles(self, generator):
        """Test base styles generation."""
        styles = generator._generate_base_styles()
        
        assert '<style>' in styles
        assert '</style>' in styles
        assert 'box-sizing: border-box' in styles
        assert '.dsl-element' in styles
        assert '.dsl-button' in styles
        assert '.dsl-input' in styles
        assert '.dsl-card' in styles
    
    def test_render_button_component(self, generator):
        """Test button component rendering."""
        element = Mock()
        element.label = "Click Me"
        element.text = None
        element.layout = Mock()
        element.layout.x = 10
        element.layout.y = 20
        element.style = None
        
        html = generator._render_button_component(element)
        
        assert '<button' in html
        assert 'dsl-button' in html
        assert 'Click Me' in html
        assert 'left: 10px' in html
        assert 'top: 20px' in html
    
    def test_render_text_component(self, generator):
        """Test text component rendering."""
        element = Mock()
        element.text = "Hello World"
        element.layout = None
        element.style = None
        
        html = generator._render_text_component(element)
        
        assert '<div' in html
        assert 'dsl-text' in html
        assert 'Hello World' in html
    
    def test_render_input_component(self, generator):
        """Test input component rendering."""
        element = Mock()
        element.placeholder = "Enter text"
        element.layout = None
        element.style = None
        
        html = generator._render_input_component(element)
        
        assert '<input type="text"' in html
        assert 'dsl-input' in html
        assert 'placeholder="Enter text"' in html
    
    def test_render_image_component(self, generator):
        """Test image component rendering."""
        element = Mock()
        element.src = "test.jpg"
        element.alt = "Test Image"
        element.layout = None
        element.style = None
        
        html = generator._render_image_component(element)
        
        assert '<img' in html
        assert 'dsl-image' in html
        assert 'src="test.jpg"' in html
        assert 'alt="Test Image"' in html
    
    def test_render_container_component(self, generator):
        """Test container component rendering."""
        child = Mock()
        child.type.value = "text"
        child.text = "Child content"
        child.layout = None
        child.style = None
        
        element = Mock()
        element.children = [child]
        element.layout = None
        element.style = None
        
        # Replace component registry instead of patching dict.get
        mock_registry = Mock()
        mock_registry.get.return_value = generator._render_generic_component
        generator.component_registry = mock_registry
        
        html = generator._render_container_component(element)
        
        assert '<div' in html
        assert 'dsl-container' in html
        assert 'Child content' in html
    
    def test_render_grid_component(self, generator):
        """Test grid component rendering."""
        element = Mock()
        element.children = []
        element.layout = None
        element.style = None
        
        html = generator._render_grid_component(element)
        
        assert '<div' in html
        assert 'dsl-grid' in html
        assert 'display: grid' in html
        assert 'gap: 8px' in html
    
    def test_render_flex_component(self, generator):
        """Test flex component rendering."""
        element = Mock()
        element.children = []
        element.layout = None
        element.style = None
        
        html = generator._render_flex_component(element)
        
        assert '<div' in html
        assert 'dsl-flex' in html
        assert 'display: flex' in html
        assert 'gap: 8px' in html
    
    def test_render_card_component(self, generator):
        """Test card component rendering."""
        element = Mock()
        element.children = []
        element.layout = None
        element.style = None
        
        html = generator._render_card_component(element)
        
        assert '<div' in html
        assert 'dsl-card' in html
    
    def test_render_modal_component(self, generator):
        """Test modal component rendering."""
        element = Mock()
        element.children = []
        element.layout = None
        element.style = None
        
        html = generator._render_modal_component(element)
        
        assert '<div' in html
        assert 'dsl-modal' in html
        assert 'background: white' in html
        assert 'border-radius: 8px' in html
        assert 'box-shadow:' in html
    
    def test_render_navbar_component(self, generator):
        """Test navbar component rendering."""
        element = Mock()
        element.children = []
        element.layout = None
        element.style = None
        
        html = generator._render_navbar_component(element)
        
        assert '<nav' in html
        assert 'dsl-navbar' in html
        assert 'background: #f8f9fa' in html
        assert 'display: flex' in html
    
    def test_render_sidebar_component(self, generator):
        """Test sidebar component rendering."""
        element = Mock()
        element.children = []
        element.layout = None
        element.style = None
        
        html = generator._render_sidebar_component(element)
        
        assert '<aside' in html
        assert 'dsl-sidebar' in html
        assert 'background: #f8f9fa' in html
        assert 'border-right:' in html
    
    def test_render_generic_component(self, generator):
        """Test generic component rendering."""
        element = Mock()
        element.text = "Generic text"
        element.layout = None
        element.style = None
        
        html = generator._render_generic_component(element)
        
        assert '<div' in html
        assert 'dsl-element' in html
        assert 'Generic text' in html
    
    def test_build_element_style_with_layout(self, generator):
        """Test building element style with layout."""
        layout = Mock()
        layout.x = 10
        layout.y = 20
        layout.width = 100
        layout.height = 50
        
        element = Mock()
        element.layout = layout
        element.style = None
        
        style = generator._build_element_style(element)
        
        assert "left: 10px" in style
        assert "top: 20px" in style
        assert "width: 100px" in style
        assert "height: 50px" in style
    
    def test_build_element_style_with_style(self, generator):
        """Test building element style with style properties."""
        style_obj = Mock()
        style_obj.background = "#ff0000"
        style_obj.color = "white"
        style_obj.font_size = 16
        
        element = Mock()
        element.layout = None
        element.style = style_obj
        
        style = generator._build_element_style(element)
        
        assert "background: #ff0000" in style
        assert "color: white" in style
        assert "font-size: 16px" in style
    
    def test_build_element_style_empty(self, generator):
        """Test building element style with no layout or style."""
        element = Mock()
        element.layout = None
        element.style = None
        
        style = generator._build_element_style(element)
        
        assert style == ""


class TestHTMLGeneratorFactory:
    """Test HTML generator factory."""
    
    def test_create_jinja2_generator(self):
        """Test creating Jinja2 generator."""
        with patch('src.core.rendering.html_generator.get_settings'):
            generator = HTMLGeneratorFactory.create_generator("jinja2")
            assert isinstance(generator, Jinja2HTMLGenerator)
    
    def test_create_component_generator(self):
        """Test creating component generator."""
        generator = HTMLGeneratorFactory.create_generator("component")
        assert isinstance(generator, ComponentHTMLGenerator)
    
    def test_create_invalid_generator(self):
        """Test creating invalid generator type."""
        with pytest.raises(ValueError, match="Unsupported generator type"):
            HTMLGeneratorFactory.create_generator("invalid")
    
    def test_default_generator_type(self):
        """Test default generator type is jinja2."""
        with patch('src.core.rendering.html_generator.get_settings'):
            generator = HTMLGeneratorFactory.create_generator()
            assert isinstance(generator, Jinja2HTMLGenerator)


class TestGenerateHTMLFunction:
    """Test generate_html helper function."""
    
    @pytest.fixture
    def sample_document(self):
        """Create sample DSL document."""
        return Mock(spec=DSLDocument)
    
    @pytest.fixture
    def sample_options(self):
        """Create sample render options."""
        return Mock(spec=RenderOptions)
    
    @pytest.mark.asyncio
    async def test_generate_html_default_generator(self, sample_document, sample_options):
        """Test generate_html with default generator."""
        with patch('src.core.rendering.html_generator.HTMLGeneratorFactory.create_generator') as mock_create:
            mock_generator = AsyncMock()
            mock_generator.generate.return_value = "<html>Test</html>"
            mock_create.return_value = mock_generator
            
            html = await generate_html(sample_document, sample_options)
            
            assert html == "<html>Test</html>"
            mock_create.assert_called_once_with("jinja2")
            mock_generator.generate.assert_called_once_with(sample_document, sample_options)
    
    @pytest.mark.asyncio
    async def test_generate_html_custom_generator(self, sample_document, sample_options):
        """Test generate_html with custom generator type."""
        with patch('src.core.rendering.html_generator.HTMLGeneratorFactory.create_generator') as mock_create:
            mock_generator = AsyncMock()
            mock_generator.generate.return_value = "<html>Component</html>"
            mock_create.return_value = mock_generator
            
            html = await generate_html(sample_document, sample_options, "component")
            
            assert html == "<html>Component</html>"
            mock_create.assert_called_once_with("component")
            mock_generator.generate.assert_called_once_with(sample_document, sample_options)


class TestHTMLGeneratorPerformance:
    """Test HTML generator performance characteristics."""
    
    @pytest.mark.asyncio
    async def test_jinja2_generator_performance(self):
        """Test Jinja2 generator performance with complex document."""
        # Create complex document
        complex_doc = DSLDataGenerator.generate_dashboard()
        document = Mock(spec=DSLDocument)
        document.title = complex_doc["title"]
        document.width = complex_doc["width"]
        document.height = complex_doc["height"]
        document.css = None
        document.elements = []
        
        options = RenderOptionsGenerator.generate_basic_options()
        
        with patch('src.core.rendering.html_generator.get_settings'):
            generator = Jinja2HTMLGenerator()
            
            # Mock template rendering
            with patch.object(generator.env, 'get_template') as mock_get_template:
                mock_template = AsyncMock()
                mock_template.render_async.return_value = "<html>Complex</html>"
                mock_get_template.return_value = mock_template
                
                # Measure performance
                with TestTimer("Jinja2 generator performance") as timer:
                    await generator.generate(document, options)
                
                # Should complete within reasonable time
                assert timer.duration < 1.0
    
    @pytest.mark.asyncio
    async def test_component_generator_performance(self):
        """Test component generator performance with many elements."""
        # Create document with many elements
        document = Mock(spec=DSLDocument)
        document.title = "Performance Test"
        document.width = 800
        document.height = 600
        document.css = None
        
        # Create 50 button elements
        elements = []
        for i in range(50):
            element = Mock()
            element.type.value = "button"
            element.layout = Mock()
            element.layout.x = i * 10
            element.layout.y = 10
            element.style = None
            elements.append(element)
        
        document.elements = elements
        options = RenderOptionsGenerator.generate_basic_options()
        
        generator = ComponentHTMLGenerator()
        
        # Measure performance
        with TestTimer("Component generator performance") as timer:
            html = await generator.generate(document, options)
        
        # Should complete within reasonable time
        assert timer.duration < 2.0
        assert len(html) > 0


class TestHTMLGeneratorEdgeCases:
    """Test HTML generator edge cases and error conditions."""
    
    @pytest.mark.asyncio
    async def test_generate_html_with_unicode_content(self):
        """Test HTML generation with unicode characters."""
        document = Mock(spec=DSLDocument)
        document.title = "测试文档"
        document.width = 800
        document.height = 600
        document.css = None
        
        element = Mock()
        element.type.value = "text"
        element.text = "Hello 世界! 🌍"
        element.layout = None
        element.style = None
        
        document.elements = [element]
        options = RenderOptionsGenerator.generate_basic_options()
        
        generator = ComponentHTMLGenerator()
        html = await generator.generate(document, options)
        
        assert "测试文档" in html
        assert "Hello 世界! 🌍" in html
    
    @pytest.mark.asyncio
    async def test_generate_html_with_special_characters(self):
        """Test HTML generation with special characters."""
        document = Mock(spec=DSLDocument)
        document.title = "Special <Characters> & \"Quotes\""
        document.width = 800
        document.height = 600
        document.css = None
        
        element = Mock()
        element.type.value = "text"
        element.text = "Text with <script>alert('xss')</script>"
        element.layout = None
        element.style = None
        
        document.elements = [element]
        options = RenderOptionsGenerator.generate_basic_options()
        
        generator = ComponentHTMLGenerator()
        html = await generator.generate(document, options)
        
        # Should escape special characters
        assert "&lt;Characters&gt;" in html
        assert "&lt;script&gt;" in html
        assert "alert(&#x27;xss&#x27;)" in html
    
    def test_jinja2_generator_with_missing_template_directory(self):
        """Test Jinja2 generator with missing template directory."""
        with patch('src.core.rendering.html_generator.get_settings'):
            with patch('pathlib.Path.parent') as mock_parent:
                # Mock missing template directory
                mock_parent.__truediv__ = Mock(return_value=Mock())
                
                # Should not raise error during initialization
                generator = Jinja2HTMLGenerator()
                assert generator.env is not None
    
    @pytest.mark.asyncio
    async def test_render_component_with_none_values(self):
        """Test rendering components with None values."""
        generator = ComponentHTMLGenerator()
        
        element = Mock()
        element.type.value = "button"
        element.label = None
        element.text = None
        element.layout = None
        element.style = None
        
        html = generator._render_button_component(element)
        
        assert 'Button' in html  # Default label
        assert 'dsl-button' in html
    
    @pytest.mark.asyncio
    async def test_component_generator_with_empty_document(self):
        """Test component generator with empty document."""
        document = Mock(spec=DSLDocument)
        document.title = None
        document.width = 800
        document.height = 600
        document.css = None
        document.elements = []
        
        options = RenderOptionsGenerator.generate_basic_options()
        generator = ComponentHTMLGenerator()
        
        html = await generator.generate(document, options)
        
        assert "DSL Generated UI" in html  # Default title
        assert "dsl-canvas" in html
        assert len(document.elements) == 0
    
    def test_build_element_style_with_integer_font_size(self):
        """Test building element style with integer font size."""
        generator = ComponentHTMLGenerator()
        
        style_obj = Mock()
        style_obj.background = None
        style_obj.color = None
        style_obj.font_size = 16  # Integer value
        
        element = Mock()
        element.layout = None
        element.style = style_obj
        
        style = generator._build_element_style(element)
        
        assert "font-size: 16px" in style
    
    def test_build_element_style_with_string_font_size(self):
        """Test building element style with string font size."""
        generator = ComponentHTMLGenerator()
        
        style_obj = Mock()
        style_obj.background = None
        style_obj.color = None
        style_obj.font_size = "1.2em"  # String value
        
        element = Mock()
        element.layout = None
        element.style = style_obj
        
        style = generator._build_element_style(element)
        
        assert "font-size: 1.2em" in style
        assert "font-size: 1.2empx" not in style  # Should not add px to string values