"""
DSL Parser
==========

Core DSL parsing engine for converting Domain Specific Language
definitions into intermediate representations for HTML generation.
Supports JSON and YAML formats with comprehensive validation.
"""

from typing import Dict, List, Any, Optional
import json
import yaml  # type: ignore[import-untyped]
import time
from abc import ABC, abstractmethod
from cerberus import Validator  # type: ignore[import-untyped]

from src.config.logging import get_logger
from src.models.schemas import (
    DSLDocument,
    DSLElement,
    ParseResult,
    ElementType,
    ElementStyle,
    ElementLayout,
)

logger = get_logger(__name__)


class DSLParseError(Exception):
    """Exception raised when DSL parsing fails."""

    pass


class DSLValidator:
    """Comprehensive DSL validation using Cerberus schemas."""

    def __init__(self) -> None:
        self.logger: Any = logger.bind(component="validator")  # structlog.BoundLoggerBase
        self._setup_schemas()

    def _setup_schemas(self) -> None:
        """Setup validation schemas."""
        # Element layout schema
        self.layout_schema = {
            "x": {"type": "number", "min": 0},
            "y": {"type": "number", "min": 0},
            "width": {"type": "number", "min": 1, "max": 4000},
            "height": {"type": "number", "min": 1, "max": 4000},
            "minWidth": {"type": "number", "min": 0},
            "maxWidth": {"type": "number", "min": 0},
            "minHeight": {"type": "number", "min": 0},
            "maxHeight": {"type": "number", "min": 0},
        }

        # Element style schema
        self.style_schema = {
            "background": {"type": "string"},
            "color": {"type": "string"},
            "fontSize": {"type": ["integer", "string"]},
            "fontWeight": {"type": ["integer", "string"]},
            "fontFamily": {"type": "string"},
            "border": {"type": "string"},
            "borderRadius": {"type": ["integer", "string"]},
            "margin": {"type": ["integer", "string"]},
            "padding": {"type": ["integer", "string"]},
            "opacity": {"type": "number", "min": 0.0, "max": 1.0},
            "zIndex": {"type": "integer"},
            "display": {"type": "string"},
            "position": {"type": "string"},
            "flexDirection": {"type": "string"},
            "justifyContent": {"type": "string"},
            "alignItems": {"type": "string"},
            "transition": {"type": "string"},
            "transform": {"type": "string"},
        }

        # Element schema (recursive definition using Cerberus approach)
        element_base = {
            "type": {"type": "string", "required": True, "allowed": [e.value for e in ElementType]},
            "id": {"type": "string", "nullable": True},
            "layout": {"type": "dict", "schema": self.layout_schema, "nullable": True},
            "style": {"type": "dict", "schema": self.style_schema, "nullable": True},
            "text": {"type": "string", "nullable": True},
            "label": {"type": "string", "nullable": True},
            "placeholder": {"type": "string", "nullable": True},
            "src": {"type": "string", "nullable": True},
            "alt": {"type": "string", "nullable": True},
            "href": {"type": "string", "nullable": True},
            "onClick": {"type": "string", "nullable": True},
            "onChange": {"type": "string", "nullable": True},
            "onHover": {"type": "string", "nullable": True},
            "className": {"type": "string", "nullable": True},
            "customAttributes": {"type": "dict", "nullable": True},
            "responsive": {"type": "dict", "nullable": True},
        }

        # Create a copy for element schema to avoid circular reference
        self.element_schema = element_base.copy()
        self.element_schema["children"] = {  # type: ignore[assignment]
            "type": "list",
            "schema": {"type": "dict", "schema": element_base},
        }

        # Document schema
        self.document_schema: Dict[str, Any] = {
            "title": {"type": "string", "nullable": True},
            "description": {"type": "string", "nullable": True},
            "width": {"type": "integer", "min": 100, "max": 4000, "default": 800},
            "height": {"type": "integer", "min": 100, "max": 4000, "default": 600},
            "elements": {
                "type": "list",
                "required": True,
                "schema": {"type": "dict", "schema": self.element_schema},
            },
            "css": {"type": "string", "default": ""},
            "theme": {"type": "string", "nullable": True},
            "metadata": {"type": "dict", "default": {}},
            "version": {"type": "string", "default": "1.0"},
            "responsiveBreakpoints": {"type": "dict", "nullable": True},
        }

    def validate_document(self, data: Dict[str, Any]) -> tuple[bool, List[str], List[str]]:
        """
        Validate DSL document structure.

        Args:
            data: Document data to validate

        Returns:
            Tuple of (is_valid, errors, warnings)
        """
        validator = Validator(self.document_schema)  # type: ignore[misc]
        validator.allow_unknown = True  # Allow extra fields  # type: ignore[attr-defined]

        is_valid = validator.validate(data)  # type: ignore[misc]
        errors: List[str] = []
        warnings: List[str] = []

        if not is_valid:
            errors.extend(self._format_validation_errors(validator.errors))  # type: ignore[attr-defined]

        # Additional custom validations
        custom_errors, custom_warnings = self._perform_custom_validations(data)
        errors.extend(custom_errors)
        warnings.extend(custom_warnings)

        return is_valid and len(custom_errors) == 0, errors, warnings  # type: ignore[misc]

    def _format_validation_errors(self, errors: Any, path: str = "") -> List[str]:  # type: ignore[misc]
        """Format Cerberus validation errors into readable messages."""
        formatted_errors: List[str] = []

        for field, error_info in errors.items():  # type: ignore[misc]
            current_path = f"{path}.{field}" if path else field

            if isinstance(error_info, list):
                for error in error_info:  # type: ignore[misc]
                    formatted_errors.append(f"{current_path}: {error}")  # type: ignore[misc]
            elif isinstance(error_info, dict):
                formatted_errors.extend(  # type: ignore[misc]
                    self._format_validation_errors(error_info, current_path)  # type: ignore[misc]
                )

        return formatted_errors  # type: ignore[misc]

    def _perform_custom_validations(self, data: Dict[str, Any]) -> tuple[List[str], List[str]]:
        """Perform custom validation logic."""
        errors: List[str] = []
        warnings: List[str] = []

        # Validate element hierarchy
        if "elements" in data:
            for i, element in enumerate(data["elements"]):
                element_errors, element_warnings = self._validate_element(element, f"elements[{i}]")
                errors.extend(element_errors)  # type: ignore[misc]
                warnings.extend(element_warnings)  # type: ignore[misc]

        # Check for reasonable canvas size
        width = data.get("width", 800)
        height = data.get("height", 600)

        if width > 1920 or height > 1080:
            warnings.append(f"Large canvas size ({width}x{height}) may impact performance")  # type: ignore[misc]

        return errors, warnings  # type: ignore[misc]

    def _validate_element(self, element: Dict[str, Any], path: str) -> tuple[List[str], List[str]]:
        """Validate individual element."""
        errors: List[str] = []
        warnings: List[str] = []

        # Ensure element is a dictionary - simplified check
        if not element or not hasattr(element, "get"):  # type: ignore[misc]
            errors.append(f"{path}: Element must be a dictionary/object, got {type(element).__name__}: {repr(element)}")  # type: ignore[misc]
            return errors, warnings

        element_type = element.get("type")
        children = element.get("children", [])

        # Check if element type can have children
        container_types = {
            ElementType.CONTAINER,
            ElementType.GRID,
            ElementType.FLEX,
            ElementType.CARD,
            ElementType.NAVBAR,
            ElementType.SIDEBAR,
            ElementType.MODAL,
        }
        if children and ElementType(element_type) not in container_types:
            errors.append(f"{path}: Element type '{element_type}' cannot have children")  # type: ignore[misc]

        # Validate children recursively
        for i, child in enumerate(children):
            child_errors, child_warnings = self._validate_element(child, f"{path}.children[{i}]")
            errors.extend(child_errors)  # type: ignore[misc]
            warnings.extend(child_warnings)  # type: ignore[misc]

        # Check for required properties based on element type
        if element_type == ElementType.IMAGE.value and not element.get("src"):
            warnings.append(f"{path}: Image element should have 'src' property")  # type: ignore[misc]

        if element_type == ElementType.BUTTON.value and not element.get("label"):
            warnings.append(f"{path}: Button element should have 'label' property")  # type: ignore[misc]

        return errors, warnings  # type: ignore[misc]


class BaseDSLParser(ABC):
    """Abstract base class for DSL parsers."""

    @abstractmethod
    async def parse(self, content: str) -> ParseResult:
        """Parse DSL content into structured format."""
        pass

    @abstractmethod
    async def validate_syntax(self, content: str) -> bool:
        """Validate DSL syntax without full parsing."""
        pass


class JSONDSLParser(BaseDSLParser):
    """JSON-based DSL parser implementation."""

    def __init__(self) -> None:
        self.logger: Any = logger.bind(parser="json")  # structlog.BoundLoggerBase
        self.validator = DSLValidator()

    async def parse(self, content: str) -> ParseResult:
        """
        Parse JSON DSL content into structured DSLDocument.

        Args:
            content: Raw DSL content as string

        Returns:
            ParseResult containing parsed document or errors
        """
        start_time = time.time()

        try:
            self.logger.info("Parsing JSON DSL content")
            raw_data = json.loads(content)

            # Validate the parsed data
            is_valid, errors, warnings = self.validator.validate_document(raw_data)

            if not is_valid:
                return ParseResult(
                    success=False,
                    document=None,
                    errors=errors,
                    warnings=warnings,
                    processing_time=time.time() - start_time,
                )

            # Convert to DSLDocument
            document = await self._convert_to_dsl_document(raw_data)

            return ParseResult(
                success=True,
                document=document,
                errors=[],
                warnings=warnings,
                processing_time=time.time() - start_time,
            )

        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON syntax at line {e.lineno}, column {e.colno}: {e.msg}"
            self.logger.error("JSON parsing failed", error=error_msg)
            return ParseResult(
                success=False,
                document=None,
                errors=[error_msg],
                processing_time=time.time() - start_time,
            )
        except Exception as e:
            error_msg = f"Unexpected parsing error: {e}"
            self.logger.error("Parsing failed", error=error_msg)
            return ParseResult(
                success=False,
                document=None,
                errors=[error_msg],
                processing_time=time.time() - start_time,
            )

    async def validate_syntax(self, content: str) -> bool:
        """
        Validate JSON DSL syntax.

        Args:
            content: Raw DSL content as string

        Returns:
            True if syntax is valid, False otherwise
        """
        try:
            json.loads(content)
            return True
        except json.JSONDecodeError:
            return False

    async def _convert_to_dsl_document(self, raw_data: Dict[str, Any]) -> DSLDocument:
        """
        Convert raw JSON data to DSLDocument.

        Args:
            raw_data: Parsed JSON data

        Returns:
            DSLDocument instance
        """
        # Convert elements
        elements: List[DSLElement] = []
        for i, element_data in enumerate(raw_data.get("elements", [])):
            # Ensure element_data is a dictionary
            if not isinstance(element_data, dict):
                raise ValueError(
                    f"Element at index {i} must be a dictionary/object, got {type(element_data).__name__}: {repr(element_data)}"
                )
            element = await self._convert_to_dsl_element(element_data)  # type: ignore[misc]
            elements.append(element)  # type: ignore[misc]

        # Create document
        return DSLDocument(
            title=raw_data.get("title"),
            description=raw_data.get("description"),
            width=raw_data.get("width", 800),
            height=raw_data.get("height", 600),
            elements=elements,
            css=raw_data.get("css", ""),
            theme=raw_data.get("theme"),
            metadata=raw_data.get("metadata", {}),
            version=raw_data.get("version", "1.0"),
            responsiveBreakpoints=raw_data.get(
                "responsiveBreakpoints", {"sm": 640, "md": 768, "lg": 1024, "xl": 1280}
            ),
        )

    async def _convert_to_dsl_element(self, element_data: Dict[str, Any]) -> DSLElement:
        """
        Convert raw element data to DSLElement.

        Args:
            element_data: Raw element data

        Returns:
            DSLElement instance
        """
        # Convert layout
        layout = None
        if "layout" in element_data:
            layout_data = element_data["layout"]

            # DIAGNOSTIC: Log layout data before ElementLayout creation
            self.logger.debug(
                "🔍 DIAGNOSTIC: Creating ElementLayout",
                element_type=element_data.get("type"),
                element_id=element_data.get("id"),
                layout_data=layout_data,
                x_type=type(layout_data.get("x")),
                y_type=type(layout_data.get("y")),
                width_type=type(layout_data.get("width")),
                height_type=type(layout_data.get("height")),
            )

            layout = ElementLayout(
                x=layout_data.get("x"),
                y=layout_data.get("y"),
                width=layout_data.get("width"),
                height=layout_data.get("height"),
                minWidth=layout_data.get("minWidth"),
                maxWidth=layout_data.get("maxWidth"),
                minHeight=layout_data.get("minHeight"),
                maxHeight=layout_data.get("maxHeight"),
            )

        # Convert style
        style = None
        if "style" in element_data:
            style_data = element_data["style"]
            style = ElementStyle(**style_data)

        # Convert children recursively
        children: List[DSLElement] = []
        for child_data in element_data.get("children", []):
            child = await self._convert_to_dsl_element(child_data)  # type: ignore[misc]
            children.append(child)  # type: ignore[misc]

        # Create element - use direct constructor with type ignores where needed
        return DSLElement(  # type: ignore[misc]
            type=ElementType(element_data["type"]),
            layout=layout,
            style=style,
            text=element_data.get("text"),
            label=element_data.get("label"),
            placeholder=element_data.get("placeholder"),
            src=element_data.get("src"),
            alt=element_data.get("alt"),
            href=element_data.get("href"),
            onClick=element_data.get("onClick"),
            onChange=element_data.get("onChange"),
            onHover=element_data.get("onHover"),
            children=children,
            className=element_data.get("className"),
            customAttributes=element_data.get("customAttributes", {}),
            responsive=element_data.get("responsive", {}),
        )


class YAMLDSLParser(BaseDSLParser):
    """YAML-based DSL parser implementation."""

    def __init__(self) -> None:
        self.logger: Any = logger.bind(parser="yaml")  # structlog.BoundLoggerBase
        self.validator = DSLValidator()

    async def parse(self, content: str) -> ParseResult:
        """
        Parse YAML DSL content into structured DSLDocument.

        Args:
            content: Raw DSL content as string

        Returns:
            ParseResult containing parsed document or errors
        """
        start_time = time.time()

        try:
            self.logger.info("Parsing YAML DSL content")
            raw_data = yaml.safe_load(content)

            if raw_data is None:
                return ParseResult(
                    success=False,
                    document=None,
                    errors=["Empty YAML document"],
                    processing_time=time.time() - start_time,
                )

            # Ensure raw_data is a dictionary (YAML can return strings, lists, etc.)
            if not isinstance(raw_data, dict):
                return ParseResult(
                    success=False,
                    document=None,
                    errors=[
                        f"YAML content must be a dictionary/object, got {type(raw_data).__name__}"
                    ],
                    processing_time=time.time() - start_time,
                )

            # Validate the parsed data
            is_valid, errors, warnings = self.validator.validate_document(raw_data)  # type: ignore[misc]

            # DIAGNOSTIC: Log validation results
            self.logger.debug(
                "🔍 DIAGNOSTIC: YAML document validation",
                is_valid=is_valid,
                error_count=len(errors),
                errors=errors[:3],  # First 3 errors for brevity
                raw_data_keys=list(raw_data.keys()) if isinstance(raw_data, dict) else "not_dict",  # type: ignore[misc]
            )

            if not is_valid:
                return ParseResult(
                    success=False,
                    document=None,
                    errors=errors,
                    warnings=warnings,
                    processing_time=time.time() - start_time,
                )

            # Convert to DSLDocument (reuse JSON parser's conversion)
            json_parser = JSONDSLParser()
            document = await json_parser._convert_to_dsl_document(raw_data)  # type: ignore[misc,misc]

            return ParseResult(
                success=True,
                document=document,
                errors=[],
                warnings=warnings,
                processing_time=time.time() - start_time,
            )

        except yaml.YAMLError as e:
            error_msg = f"Invalid YAML syntax: {e}"
            self.logger.error("YAML parsing failed", error=error_msg)
            return ParseResult(
                success=False,
                document=None,
                errors=[error_msg],
                processing_time=time.time() - start_time,
            )
        except Exception as e:
            error_msg = f"Unexpected parsing error: {e}"
            self.logger.error("Parsing failed", error=error_msg)
            return ParseResult(
                success=False,
                document=None,
                errors=[error_msg],
                processing_time=time.time() - start_time,
            )

    async def validate_syntax(self, content: str) -> bool:
        """
        Validate YAML DSL syntax.

        Args:
            content: Raw DSL content as string

        Returns:
            True if syntax is valid, False otherwise
        """
        try:
            # Only check if YAML can be parsed - structure validation belongs in full parsing
            yaml.safe_load(content)
            return True
        except yaml.YAMLError:
            return False


class DSLParserFactory:
    """Factory for creating DSL parsers based on content type."""

    _parsers = {
        "json": JSONDSLParser,
        "yaml": YAMLDSLParser,
    }

    @classmethod
    def create_parser(cls, parser_type: str) -> BaseDSLParser:
        """
        Create a DSL parser instance.

        Args:
            parser_type: Type of parser ("json", "yaml")

        Returns:
            DSL parser instance

        Raises:
            ValueError: If parser type is not supported
        """
        if parser_type not in cls._parsers:
            raise ValueError(f"Unsupported parser type: {parser_type}")

        return cls._parsers[parser_type]()

    @classmethod
    def detect_parser_type(cls, content: str) -> str:
        """
        Detect DSL parser type from content.

        Args:
            content: Raw DSL content

        Returns:
            Detected parser type
        """
        content = content.strip()
        if content.startswith(("{", "[")):
            return "json"
        elif content.startswith(("---", "- ")) or "\n-" in content[:100]:
            return "yaml"
        else:
            # Try to parse as JSON first, fallback to YAML
            try:
                json.loads(content)
                return "json"
            except json.JSONDecodeError:
                return "yaml"


async def parse_dsl(content: str, parser_type: Optional[str] = None) -> ParseResult:
    """
    Parse DSL content using appropriate parser.

    Args:
        content: Raw DSL content
        parser_type: Optional parser type override

    Returns:
        ParseResult containing parsed document or errors
    """
    if not content or not content.strip():
        return ParseResult(
            success=False, document=None, errors=["Empty DSL content provided"], processing_time=0.0
        )

    if not parser_type:
        parser_type = DSLParserFactory.detect_parser_type(content)

    try:
        parser = DSLParserFactory.create_parser(parser_type)
        return await parser.parse(content)
    except ValueError as e:
        return ParseResult(success=False, document=None, errors=[str(e)], processing_time=0.0)


async def validate_dsl_syntax(content: str, parser_type: Optional[str] = None) -> bool:
    """
    Validate DSL syntax without full parsing.

    Args:
        content: Raw DSL content
        parser_type: Optional parser type override

    Returns:
        True if syntax is valid, False otherwise
    """
    if not content or not content.strip():
        return False

    if not parser_type:
        parser_type = DSLParserFactory.detect_parser_type(content)

    try:
        parser = DSLParserFactory.create_parser(parser_type)
        return await parser.validate_syntax(content)
    except ValueError:
        return False


async def get_validation_suggestions(content: str, errors: List[str]) -> List[str]:
    """
    Generate validation suggestions based on content and errors.

    Args:
        content: Raw DSL content
        errors: List of validation errors

    Returns:
        List of suggestions for fixing errors
    """
    suggestions: List[str] = []

    # Analyze common error patterns
    for error in errors:
        if "JSON syntax" in error:
            suggestions.extend(
                [  # type: ignore[misc]
                    "Check for missing commas between object properties",
                    "Ensure all strings are properly quoted",
                    "Verify bracket and brace matching",
                ]
            )
        elif "YAML syntax" in error:
            suggestions.extend(
                [  # type: ignore[misc]
                    "Check indentation consistency (use spaces, not tabs)",
                    "Ensure proper key-value separator usage (:)",
                    "Verify list item format (- item)",
                ]
            )
        elif "cannot have children" in error:
            suggestions.append("Only container, grid, flex, and card elements can have children")  # type: ignore[misc]
        elif "required" in error.lower():
            suggestions.append("Ensure all required fields are present: type for elements")  # type: ignore[misc]

    # Content-based suggestions
    if "{" in content and "}" in content:
        if content.count("{") != content.count("}"):
            suggestions.append("Check for unmatched curly braces in JSON")  # type: ignore[misc]

    if "elements" not in content:
        suggestions.append("DSL document should contain an 'elements' array")  # type: ignore[misc]

    # Remove duplicates while preserving order
    unique_suggestions: List[str] = []
    for suggestion in suggestions:  # type: ignore[misc]
        if suggestion not in unique_suggestions:
            unique_suggestions.append(suggestion)  # type: ignore[misc]

    return unique_suggestions[:5]  # Limit to 5 most relevant suggestions  # type: ignore[misc]


def get_supported_element_types() -> List[str]:
    """
    Get list of supported DSL element types.

    Returns:
        List of supported element type strings
    """
    return [e.value for e in ElementType]


def get_dsl_schema_info() -> Dict[str, Any]:
    """
    Get DSL schema information for documentation/tooling.

    Returns:
        Dictionary containing schema information
    """
    validator = DSLValidator()

    return {
        "version": "1.0",
        "supported_formats": ["json", "yaml"],
        "element_types": get_supported_element_types(),
        "document_schema": validator.document_schema,
        "element_schema": validator.element_schema,
        "style_properties": list(validator.style_schema.keys()),
        "layout_properties": list(validator.layout_schema.keys()),
        "example_minimal": {
            "width": 400,
            "height": 300,
            "elements": [
                {
                    "type": "text",
                    "text": "Hello World",
                    "layout": {"x": 100, "y": 100, "width": 200, "height": 50},
                }
            ],
        },
    }


# Alias for integration tests compatibility
DSLParser = DSLParserFactory
