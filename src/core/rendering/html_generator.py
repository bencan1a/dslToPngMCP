"""
HTML Generator
==============

Convert DSL documents into HTML markup for browser rendering.
Supports responsive design, custom CSS, and component-based layouts.
"""

from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import jinja2
from abc import ABC, abstractmethod

from src.config.logging import get_logger
from src.models.schemas import DSLDocument, DSLElement, RenderOptions, ElementStyle, ElementLayout
from src.config.settings import get_settings

logger = get_logger(__name__)


class HTMLGenerationError(Exception):
    """Exception raised when HTML generation fails."""

    pass


class BaseHTMLGenerator(ABC):
    """Abstract base class for HTML generators."""

    @abstractmethod
    async def generate(self, document: DSLDocument, options: RenderOptions) -> str:
        """Generate HTML from DSL document."""
        pass


class Jinja2HTMLGenerator(BaseHTMLGenerator):
    """Jinja2-based HTML generator implementation."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.logger: Any = logger.bind(generator="jinja2")  # structlog.BoundLoggerBase
        self._setup_jinja2_environment()

    def _setup_jinja2_environment(self) -> None:
        """Setup Jinja2 template environment."""
        template_dir = Path(__file__).parent / "templates"
        self.env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            autoescape=jinja2.select_autoescape(["html", "xml"]),
            enable_async=True,
        )

        # Add custom filters and functions
        self._register_template_functions()

    def _register_template_functions(self) -> None:
        """Register custom Jinja2 functions and filters."""

        def px(value: float) -> str:
            """Convert numeric value to CSS pixels."""
            return f"{value}px"

        def css_safe(value: str) -> str:
            """Make string safe for use in CSS."""
            return value.replace('"', '\\"').replace("'", "\\'")

        def render_element(element: DSLElement, index: int = 0) -> str:
            """Render a DSL element to HTML."""
            return self._render_element_html(element, index)

        def style_to_css(style: Optional[ElementStyle]) -> str:
            """Convert ElementStyle to CSS string."""
            if not style:
                return ""

            css_rules: List[str] = []

            # Basic styles
            if style.background:
                css_rules.append(f"background: {style.background}")
            if style.color:
                css_rules.append(f"color: {style.color}")
            if style.font_size:
                css_rules.append(
                    f"font-size: {style.font_size}{'px' if isinstance(style.font_size, int) else ''}"
                )
            if style.font_weight:
                css_rules.append(f"font-weight: {style.font_weight}")
            if style.font_family:
                css_rules.append(f"font-family: {style.font_family}")
            if style.border:
                css_rules.append(f"border: {style.border}")
            if style.border_radius:
                css_rules.append(
                    f"border-radius: {style.border_radius}{'px' if isinstance(style.border_radius, int) else ''}"
                )
            if style.margin:
                css_rules.append(
                    f"margin: {style.margin}{'px' if isinstance(style.margin, int) else ''}"
                )
            if style.padding:
                css_rules.append(
                    f"padding: {style.padding}{'px' if isinstance(style.padding, int) else ''}"
                )
            if style.opacity is not None:
                css_rules.append(f"opacity: {style.opacity}")
            if style.z_index is not None:
                css_rules.append(f"z-index: {style.z_index}")

            # Layout styles
            if style.display:
                css_rules.append(f"display: {style.display}")
            if style.position:
                css_rules.append(f"position: {style.position}")
            if style.flex_direction:
                css_rules.append(f"flex-direction: {style.flex_direction}")
            if style.justify_content:
                css_rules.append(f"justify-content: {style.justify_content}")
            if style.align_items:
                css_rules.append(f"align-items: {style.align_items}")

            # Animation styles
            if style.transition:
                css_rules.append(f"transition: {style.transition}")
            if style.transform:
                css_rules.append(f"transform: {style.transform}")

            return "; ".join(css_rules)

        def layout_to_css(layout: Optional[ElementLayout]) -> str:
            """Convert ElementLayout to CSS string."""
            if not layout:
                return ""

            css_rules: List[str] = []

            if layout.x is not None:
                css_rules.append(f"left: {layout.x}px")
            if layout.y is not None:
                css_rules.append(f"top: {layout.y}px")
            if layout.width is not None:
                css_rules.append(f"width: {layout.width}px")
            if layout.height is not None:
                css_rules.append(f"height: {layout.height}px")
            if layout.min_width is not None:
                css_rules.append(f"min-width: {layout.min_width}px")
            if layout.max_width is not None:
                css_rules.append(f"max-width: {layout.max_width}px")
            if layout.min_height is not None:
                css_rules.append(f"min-height: {layout.min_height}px")
            if layout.max_height is not None:
                css_rules.append(f"max-height: {layout.max_height}px")

            return "; ".join(css_rules)

        # Register filters and functions
        self.env.filters["px"] = px
        self.env.filters["css_safe"] = css_safe
        self.env.filters["style_to_css"] = style_to_css
        self.env.filters["layout_to_css"] = layout_to_css
        # Use a lambda to work around Jinja2 type inference issues
        self.env.globals["render_element"] = lambda element, index=0: render_element(element, index)  # type: ignore

        # Store function references for direct use
        self._style_to_css = style_to_css
        self._layout_to_css = layout_to_css

    async def generate(self, document: DSLDocument, options: RenderOptions) -> str:
        """
        Generate HTML from DSL document using Jinja2 templates.

        Args:
            document: Parsed DSL document
            options: Rendering options

        Returns:
            Generated HTML string

        Raises:
            HTMLGenerationError: If HTML generation fails
        """
        try:
            self.logger.info("Generating HTML from DSL document")

            # Select appropriate template
            template_name = self._get_template_name(document, options)
            template = self.env.get_template(template_name)

            # Prepare template context
            context = await self._prepare_context(document, options)

            # Render HTML
            html = await template.render_async(**context)

            self.logger.info(
                "HTML generation completed", template=template_name, html_length=len(html)
            )

            return html

        except jinja2.TemplateError as e:
            error_msg = f"Template rendering failed: {e}"
            self.logger.error("HTML generation failed", error=error_msg)
            raise HTMLGenerationError(error_msg)
        except Exception as e:
            error_msg = f"Unexpected HTML generation error: {e}"
            self.logger.error("HTML generation failed", error=error_msg)
            raise HTMLGenerationError(error_msg)

    def _get_template_name(self, document: DSLDocument, options: RenderOptions) -> str:
        """
        Determine appropriate template name based on document and options.

        Args:
            document: DSL document
            options: Render options

        Returns:
            Template filename
        """
        # TODO: Implement template selection logic based on document type
        # For now, use base template
        return "base.html"

    async def _prepare_context(
        self, document: DSLDocument, options: RenderOptions
    ) -> Dict[str, Any]:
        """
        Prepare template rendering context.

        Args:
            document: DSL document
            options: Render options

        Returns:
            Template context dictionary
        """
        return {
            "document": document,
            "options": options,
            "width": document.width,
            "height": document.height,
            "elements": document.elements,
            "custom_css": document.css,
            "settings": self.settings,
        }

    def _render_element_html(self, element: DSLElement, index: int = 0) -> str:
        """
        Render a DSL element to HTML string.

        Args:
            element: DSL element to render
            index: Element index for unique IDs

        Returns:
            HTML string for the element
        """
        # Build CSS classes
        css_classes = ["dsl-element", f"dsl-{element.type.value}"]
        if element.class_name:
            css_classes.append(element.class_name)

        # Build inline styles
        inline_styles: List[str] = []

        # Layout styles
        if element.layout:
            layout_css = self._layout_to_css(element.layout)
            if layout_css:
                inline_styles.append(layout_css)

        # Element styles
        if element.style:
            style_css = self._style_to_css(element.style)
            if style_css:
                inline_styles.append(style_css)

        # Build attributes
        attributes = {
            "class": " ".join(css_classes),
            "id": element.id or f"element-{index}",
            "data-type": element.type.value,
        }

        if inline_styles:
            attributes["style"] = "; ".join(inline_styles)

        # Add custom attributes
        if element.custom_attributes:
            attributes.update(element.custom_attributes)

        # Render based on element type
        if element.type.value == "button":
            return self._render_button(element, attributes)
        elif element.type.value == "text":
            return self._render_text(element, attributes)
        elif element.type.value == "input":
            return self._render_input(element, attributes)
        elif element.type.value == "image":
            return self._render_image(element, attributes)
        elif element.type.value in [
            "container",
            "grid",
            "flex",
            "card",
            "modal",
            "navbar",
            "sidebar",
        ]:
            return self._render_container(element, attributes)
        else:
            return self._render_generic(element, attributes)

    def _render_button(self, element: DSLElement, attributes: Dict[str, str]) -> str:
        """Render button element."""
        attrs_str = self._build_attributes(attributes)
        label = element.label or element.text or "Button"
        onclick = f' onclick="{element.onClick}"' if element.onClick else ""
        return f"<button{attrs_str}{onclick}>{self._escape_html(label)}</button>"

    def _render_text(self, element: DSLElement, attributes: Dict[str, str]) -> str:
        """Render text element."""
        attrs_str = self._build_attributes(attributes)
        text = element.text or ""
        return f"<div{attrs_str}>{self._escape_html(text)}</div>"

    def _render_input(self, element: DSLElement, attributes: Dict[str, str]) -> str:
        """Render input element."""
        attrs_str = self._build_attributes(attributes)
        placeholder = (
            f' placeholder="{self._escape_html(element.placeholder)}"'
            if element.placeholder
            else ""
        )
        onchange = f' onchange="{element.onChange}"' if element.onChange else ""
        return f'<input type="text"{attrs_str}{placeholder}{onchange}>'

    def _render_image(self, element: DSLElement, attributes: Dict[str, str]) -> str:
        """Render image element."""
        attrs_str = self._build_attributes(attributes)
        src = element.src or ""
        alt = element.alt or ""
        return f'<img{attrs_str} src="{self._escape_html(src)}" alt="{self._escape_html(alt)}">'

    def _render_container(self, element: DSLElement, attributes: Dict[str, str]) -> str:
        """Render container element with children."""
        attrs_str = self._build_attributes(attributes)

        # Render children
        children_html = ""
        if element.children:
            for i, child in enumerate(element.children):
                children_html += self._render_element_html(child, i)

        tag = "div"
        if element.type.value == "navbar":
            tag = "nav"
        elif element.type.value == "sidebar":
            tag = "aside"

        return f"<{tag}{attrs_str}>{children_html}</{tag}>"

    def _render_generic(self, element: DSLElement, attributes: Dict[str, str]) -> str:
        """Render generic element."""
        attrs_str = self._build_attributes(attributes)
        content = element.text or ""
        return f"<div{attrs_str}>{self._escape_html(content)}</div>"

    def _build_attributes(self, attributes: Dict[str, str]) -> str:
        """Build HTML attributes string."""
        if not attributes:
            return ""

        attr_pairs: List[str] = []
        for key, value in attributes.items():
            if value:
                escaped_value = self._escape_html(str(value))
                attr_pairs.append(f'{key}="{escaped_value}"')

        return " " + " ".join(attr_pairs) if attr_pairs else ""

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )


class ComponentHTMLGenerator(BaseHTMLGenerator):
    """Component-based HTML generator for complex layouts."""

    def __init__(self) -> None:
        self.logger: Any = logger.bind(generator="component")  # structlog.BoundLoggerBase
        self.component_registry = self._setup_component_registry()

    def _setup_component_registry(self) -> Dict[str, Callable[[DSLElement], str]]:
        """Setup component registry with render functions."""
        return {
            "button": self._render_button_component,
            "text": self._render_text_component,
            "input": self._render_input_component,
            "image": self._render_image_component,
            "container": self._render_container_component,
            "grid": self._render_grid_component,
            "flex": self._render_flex_component,
            "card": self._render_card_component,
            "modal": self._render_modal_component,
            "navbar": self._render_navbar_component,
            "sidebar": self._render_sidebar_component,
        }

    async def generate(self, document: DSLDocument, options: RenderOptions) -> str:
        """
        Generate HTML using component-based approach.

        Args:
            document: DSL document
            options: Render options

        Returns:
            Generated HTML string
        """
        try:
            self.logger.info("Generating HTML using component approach")

            # Build document header
            html_parts = [
                "<!DOCTYPE html>",
                '<html lang="en">',
                "<head>",
                '<meta charset="UTF-8">',
                '<meta name="viewport" content="width=device-width, initial-scale=1.0">',
                f'<title>{self._escape_html(document.title or "DSL Generated UI")}</title>',
                self._generate_base_styles(),
                f"<style>{document.css}</style>" if document.css else "",
                "</head>",
                "<body>",
                f'<div class="dsl-canvas" style="width:{document.width}px;height:{document.height}px;position:relative;overflow:hidden;">',
            ]

            # Render elements
            for element in document.elements:
                component_html = await self._render_component(element)
                html_parts.append(component_html)

            # Close document
            html_parts.extend(
                [
                    "</div>",
                    '<script>document.body.setAttribute("data-render-complete", "true");</script>',
                    "</body>",
                    "</html>",
                ]
            )

            html = "\n".join(html_parts)
            self.logger.info("Component-based HTML generation completed", html_length=len(html))

            return html

        except Exception as e:
            error_msg = f"Component-based HTML generation failed: {e}"
            self.logger.error("HTML generation failed", error=error_msg)
            raise HTMLGenerationError(error_msg)

    async def _render_component(self, element: DSLElement) -> str:
        """Render a single component."""
        component_type = element.type.value

        if component_type in self.component_registry:
            return self.component_registry[component_type](element)
        else:
            return self._render_generic_component(element)

    def _generate_base_styles(self) -> str:
        """Generate base CSS styles."""
        return """
        <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }
        .dsl-element { position: absolute; }
        .dsl-button { background: #007bff; color: white; border: none; border-radius: 4px; padding: 8px 16px; cursor: pointer; }
        .dsl-input { border: 1px solid #ddd; border-radius: 4px; padding: 8px 12px; background: white; }
        .dsl-card { background: white; border: 1px solid #e0e0e0; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); padding: 16px; }
        </style>
        """

    def _render_button_component(self, element: DSLElement) -> str:
        """Render button component."""
        style = self._build_element_style(element)
        label = element.label or element.text or "Button"
        return f'<button class="dsl-element dsl-button" style="{style}">{label}</button>'

    def _render_text_component(self, element: DSLElement) -> str:
        """Render text component."""
        style = self._build_element_style(element)
        text = self._escape_html(element.text or "")
        return f'<div class="dsl-element dsl-text" style="{style}">{text}</div>'

    def _render_input_component(self, element: DSLElement) -> str:
        """Render input component."""
        style = self._build_element_style(element)
        placeholder = f'placeholder="{element.placeholder}"' if element.placeholder else ""
        return f'<input type="text" class="dsl-element dsl-input" style="{style}" {placeholder}>'

    def _render_image_component(self, element: DSLElement) -> str:
        """Render image component."""
        style = self._build_element_style(element)
        src = element.src or ""
        alt = element.alt or ""
        return f'<img class="dsl-element dsl-image" style="{style}" src="{src}" alt="{alt}">'

    def _render_container_component(self, element: DSLElement) -> str:
        """Render container component."""
        style = self._build_element_style(element)
        children_html = "".join(
            [
                self.component_registry.get(child.type.value, self._render_generic_component)(child)
                for child in element.children or []
            ]
        )
        return f'<div class="dsl-element dsl-container" style="{style}">{children_html}</div>'

    def _render_grid_component(self, element: DSLElement) -> str:
        """Render grid component."""
        style = self._build_element_style(element) + "; display: grid; gap: 8px;"
        children_html = "".join(
            [
                self.component_registry.get(child.type.value, self._render_generic_component)(child)
                for child in element.children or []
            ]
        )
        return f'<div class="dsl-element dsl-grid" style="{style}">{children_html}</div>'

    def _render_flex_component(self, element: DSLElement) -> str:
        """Render flex component."""
        style = self._build_element_style(element) + "; display: flex; gap: 8px;"
        children_html = "".join(
            [
                self.component_registry.get(child.type.value, self._render_generic_component)(child)
                for child in element.children or []
            ]
        )
        return f'<div class="dsl-element dsl-flex" style="{style}">{children_html}</div>'

    def _render_card_component(self, element: DSLElement) -> str:
        """Render card component."""
        style = self._build_element_style(element)
        children_html = "".join(
            [
                self.component_registry.get(child.type.value, self._render_generic_component)(child)
                for child in element.children or []
            ]
        )
        return f'<div class="dsl-element dsl-card" style="{style}">{children_html}</div>'

    def _render_modal_component(self, element: DSLElement) -> str:
        """Render modal component."""
        style = (
            self._build_element_style(element)
            + "; background: white; border-radius: 8px; box-shadow: 0 4px 20px rgba(0,0,0,0.15);"
        )
        children_html = "".join(
            [
                self.component_registry.get(child.type.value, self._render_generic_component)(child)
                for child in element.children or []
            ]
        )
        return f'<div class="dsl-element dsl-modal" style="{style}">{children_html}</div>'

    def _render_navbar_component(self, element: DSLElement) -> str:
        """Render navbar component."""
        style = (
            self._build_element_style(element)
            + "; background: #f8f9fa; border-bottom: 1px solid #e0e0e0; display: flex; align-items: center;"
        )
        children_html = "".join(
            [
                self.component_registry.get(child.type.value, self._render_generic_component)(child)
                for child in element.children or []
            ]
        )
        return f'<nav class="dsl-element dsl-navbar" style="{style}">{children_html}</nav>'

    def _render_sidebar_component(self, element: DSLElement) -> str:
        """Render sidebar component."""
        style = (
            self._build_element_style(element)
            + "; background: #f8f9fa; border-right: 1px solid #e0e0e0;"
        )
        children_html = "".join(
            [
                self.component_registry.get(child.type.value, self._render_generic_component)(child)
                for child in element.children or []
            ]
        )
        return f'<aside class="dsl-element dsl-sidebar" style="{style}">{children_html}</aside>'

    def _render_generic_component(self, element: DSLElement) -> str:
        """Render generic component."""
        style = self._build_element_style(element)
        content = element.text or ""
        return f'<div class="dsl-element" style="{style}">{content}</div>'

    def _build_element_style(self, element: DSLElement) -> str:
        """Build CSS style string for element."""
        styles: List[str] = []

        # Layout styles
        if element.layout:
            if element.layout.x is not None:
                styles.append(f"left: {element.layout.x}px")
            if element.layout.y is not None:
                styles.append(f"top: {element.layout.y}px")
            if element.layout.width is not None:
                styles.append(f"width: {element.layout.width}px")
            if element.layout.height is not None:
                styles.append(f"height: {element.layout.height}px")

        # Element styles
        if element.style:
            if element.style.background:
                styles.append(f"background: {element.style.background}")
            if element.style.color:
                styles.append(f"color: {element.style.color}")
            if element.style.font_size:
                styles.append(
                    f"font-size: {element.style.font_size}{'px' if isinstance(element.style.font_size, int) else ''}"
                )
            # Add more style properties as needed

        return "; ".join(styles)

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters."""
        if not text:
            return ""
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
        )


class HTMLGeneratorFactory:
    """Factory for creating HTML generators."""

    _generators = {
        "jinja2": Jinja2HTMLGenerator,
        "component": ComponentHTMLGenerator,
    }

    @classmethod
    def create_generator(cls, generator_type: str = "jinja2") -> BaseHTMLGenerator:
        """
        Create HTML generator instance.

        Args:
            generator_type: Type of generator

        Returns:
            HTML generator instance

        Raises:
            ValueError: If generator type is not supported
        """
        if generator_type not in cls._generators:
            raise ValueError(f"Unsupported generator type: {generator_type}")

        return cls._generators[generator_type]()


async def generate_html(
    document: DSLDocument, options: RenderOptions, generator_type: str = "jinja2"
) -> str:
    """
    Generate HTML from DSL document.

    Args:
        document: Parsed DSL document
        options: Rendering options
        generator_type: HTML generator type

    Returns:
        Generated HTML string
    """
    generator = HTMLGeneratorFactory.create_generator(generator_type)
    return await generator.generate(document, options)


# Alias for integration tests compatibility
HTMLGenerator = ComponentHTMLGenerator
