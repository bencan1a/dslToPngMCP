"""
Pydantic Models and Schemas
===========================

Core data models for DSL documents, API requests/responses, and internal data structures.
All models include comprehensive validation and type hints.
"""

from typing import Optional, List, Dict, Any, Union, Literal
from datetime import datetime
from enum import Enum
from pathlib import Path
import uuid

from pydantic import BaseModel, Field, validator, root_validator
from pydantic.types import StrictStr, StrictInt, StrictFloat, StrictBool


# Enums
class ElementType(str, Enum):
    """DSL element types."""
    BUTTON = "button"
    TEXT = "text"
    INPUT = "input"
    IMAGE = "image"
    CONTAINER = "container"
    GRID = "grid"
    FLEX = "flex"
    CARD = "card"
    MODAL = "modal"
    NAVBAR = "navbar"
    SIDEBAR = "sidebar"


class TaskStatus(str, Enum):
    """Task processing status."""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class LogLevel(str, Enum):
    """Logging levels."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


# Base Models
class BaseTimestamped(BaseModel):
    """Base model with timestamp fields."""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class BaseIdentified(BaseModel):
    """Base model with ID field."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))


# DSL Models
class ElementStyle(BaseModel):
    """CSS style properties for DSL elements."""
    background: Optional[str] = None
    color: Optional[str] = None
    font_size: Optional[Union[int, str]] = Field(None, alias="fontSize")
    font_weight: Optional[Union[int, str]] = Field(None, alias="fontWeight")
    font_family: Optional[str] = Field(None, alias="fontFamily")
    border: Optional[str] = None
    border_radius: Optional[Union[int, str]] = Field(None, alias="borderRadius")
    margin: Optional[Union[int, str]] = None
    padding: Optional[Union[int, str]] = None
    opacity: Optional[float] = Field(None, ge=0.0, le=1.0)
    z_index: Optional[int] = Field(None, alias="zIndex")
    
    # Layout properties
    display: Optional[str] = None
    position: Optional[str] = None
    flex_direction: Optional[str] = Field(None, alias="flexDirection")
    justify_content: Optional[str] = Field(None, alias="justifyContent")
    align_items: Optional[str] = Field(None, alias="alignItems")
    
    # Animation properties
    transition: Optional[str] = None
    transform: Optional[str] = None
    
    class Config:
        allow_population_by_field_name = True


class ElementLayout(BaseModel):
    """Layout properties for DSL elements."""
    x: Optional[float] = Field(None, description="X position in pixels")
    y: Optional[float] = Field(None, description="Y position in pixels")
    width: Optional[float] = Field(None, gt=0, description="Width in pixels")
    height: Optional[float] = Field(None, gt=0, description="Height in pixels")
    
    # Responsive properties
    min_width: Optional[float] = Field(None, gt=0, alias="minWidth")
    max_width: Optional[float] = Field(None, gt=0, alias="maxWidth")
    min_height: Optional[float] = Field(None, gt=0, alias="minHeight")
    max_height: Optional[float] = Field(None, gt=0, alias="maxHeight")
    
    class Config:
        allow_population_by_field_name = True


class DSLElement(BaseIdentified):
    """DSL element model with full type safety."""
    # Override id to make it optional (None allowed)
    id: Optional[str] = Field(None, description="Element identifier")
    type: ElementType = Field(..., description="Element type")
    layout: Optional[ElementLayout] = None
    style: Optional[ElementStyle] = None
    
    # Content properties
    text: Optional[str] = Field(None, description="Text content")
    label: Optional[str] = Field(None, description="Button/input label")
    placeholder: Optional[str] = Field(None, description="Input placeholder")
    src: Optional[str] = Field(None, description="Image source URL")
    alt: Optional[str] = Field(None, description="Image alt text")
    href: Optional[str] = Field(None, description="Link URL")
    
    # Interaction properties
    onClick: Optional[str] = Field(None, description="Click handler")
    onChange: Optional[str] = Field(None, description="Change handler")
    onHover: Optional[str] = Field(None, description="Hover handler")
    
    # Container properties
    children: Optional[List['DSLElement']] = Field(default_factory=list)
    
    # CSS classes and custom attributes
    class_name: Optional[str] = Field(None, alias="className")
    custom_attributes: Optional[Dict[str, str]] = Field(default_factory=dict, alias="customAttributes")
    
    # Responsive breakpoints
    responsive: Optional[Dict[str, 'DSLElement']] = Field(default_factory=dict)
    
    class Config:
        allow_population_by_field_name = True
    
    @validator('children')
    def validate_children(cls, v, values):
        """Validate that container elements can have children."""
        element_type = values.get('type')
        # Include all logical container types that can have children
        allowed_containers = [
            ElementType.CONTAINER,
            ElementType.GRID,
            ElementType.FLEX,
            ElementType.CARD,
            ElementType.NAVBAR,
            ElementType.SIDEBAR,
            ElementType.MODAL
        ]
        
        if v and element_type not in allowed_containers:
            raise ValueError(f"Element type {element_type} cannot have children")
        return v


# Update forward reference
DSLElement.model_rebuild()


class DSLDocument(BaseTimestamped):
    """Complete DSL document model."""
    title: Optional[str] = Field(None, description="Document title")
    description: Optional[str] = Field(None, description="Document description")
    
    # Canvas properties
    width: int = Field(800, gt=0, le=4000, description="Canvas width in pixels")
    height: int = Field(600, gt=0, le=4000, description="Canvas height in pixels")
    
    # Elements
    elements: List[DSLElement] = Field(default_factory=list, description="Document elements")
    
    # Styling
    css: str = Field("", description="Custom CSS styles")
    theme: Optional[str] = Field(None, description="Theme name")
    
    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    version: str = Field("1.0", description="DSL version")
    
    # Responsive settings
    responsive_breakpoints: Optional[Dict[str, int]] = Field(
        default_factory=lambda: {"sm": 640, "md": 768, "lg": 1024, "xl": 1280},
        alias="responsiveBreakpoints"
    )
    
    class Config:
        allow_population_by_field_name = True


# Parsing Results
class ParseResult(BaseModel):
    """Result of DSL parsing operation."""
    success: bool = Field(..., description="Whether parsing succeeded")
    document: Optional[DSLDocument] = Field(None, description="Parsed document")
    errors: List[str] = Field(default_factory=list, description="Parsing errors")
    warnings: List[str] = Field(default_factory=list, description="Parsing warnings")
    processing_time: Optional[float] = Field(None, description="Parsing time in seconds")


# Rendering Models
class RenderOptions(BaseModel):
    """Options for rendering DSL to PNG."""
    width: int = Field(800, gt=0, le=4000, description="Render width")
    height: int = Field(600, gt=0, le=4000, description="Render height")
    
    # Browser options
    device_scale_factor: float = Field(1.0, gt=0, le=3.0, description="Device pixel ratio")
    user_agent: Optional[str] = Field(None, description="Custom user agent")
    wait_for_load: bool = Field(True, description="Wait for page load completion")
    full_page: bool = Field(False, description="Capture full page instead of viewport")
    
    # Image options
    png_quality: Optional[int] = Field(None, ge=0, le=100, description="PNG quality (0-100)")
    optimize_png: bool = Field(True, description="Optimize PNG file size")
    
    # Performance options
    timeout: int = Field(30, gt=0, le=300, description="Render timeout in seconds")
    block_resources: bool = Field(False, description="Block non-essential resources")
    
    # Background options
    background_color: Optional[str] = Field(None, description="Background color override")
    transparent_background: bool = Field(False, description="Transparent background")


class PNGResult(BaseModel):
    """Result of PNG generation."""
    png_data: bytes = Field(..., description="PNG binary data", exclude=True)
    base64_data: str = Field(..., description="Base64 encoded PNG data")
    width: int = Field(..., description="Image width")
    height: int = Field(..., description="Image height")
    file_size: int = Field(..., description="File size in bytes")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Generation metadata")


# API Request/Response Models
class DSLRenderRequest(BaseModel):
    """Request model for DSL to PNG rendering."""
    dsl_content: str = Field(..., min_length=1, description="DSL content to render")
    options: RenderOptions = Field(default_factory=RenderOptions, description="Render options")
    callback_url: Optional[str] = Field(None, description="Webhook URL for async completion")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Request metadata")
    
    @validator('dsl_content')
    def validate_dsl_content(cls, v):
        """Validate DSL content is not empty."""
        if not v.strip():
            raise ValueError("DSL content cannot be empty")
        return v


class DSLValidationRequest(BaseModel):
    """Request model for DSL validation."""
    dsl_content: str = Field(..., min_length=1, description="DSL content to validate")
    strict: bool = Field(False, description="Enable strict validation")


class DSLValidationResponse(BaseModel):
    """Response model for DSL validation."""
    valid: bool = Field(..., description="Whether DSL is valid")
    errors: List[str] = Field(default_factory=list, description="Validation errors")
    warnings: List[str] = Field(default_factory=list, description="Validation warnings")
    suggestions: List[str] = Field(default_factory=list, description="Improvement suggestions")


class RenderResponse(BaseModel):
    """Response model for synchronous rendering."""
    success: bool = Field(..., description="Whether rendering succeeded")
    png_result: Optional[PNGResult] = Field(None, description="PNG generation result")
    error: Optional[str] = Field(None, description="Error message if failed")
    processing_time: float = Field(..., description="Total processing time")


class AsyncRenderResponse(BaseModel):
    """Response model for asynchronous rendering."""
    task_id: str = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Initial task status")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")


# Task Models
class TaskResult(BaseTimestamped):
    """Task execution result."""
    task_id: str = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Task status")
    png_result: Optional[PNGResult] = Field(None, description="PNG result if successful")
    error: Optional[str] = Field(None, description="Error message if failed")
    processing_time: float = Field(0.0, description="Processing time in seconds")
    completed_at: Optional[datetime] = Field(None, description="Completion timestamp")


class TaskStatusResponse(BaseModel):
    """Response model for task status queries."""
    task_id: str = Field(..., description="Task identifier")
    status: TaskStatus = Field(..., description="Current status")
    progress: Optional[int] = Field(None, ge=0, le=100, description="Progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    result: Optional[TaskResult] = Field(None, description="Task result if completed")
    created_at: datetime = Field(..., description="Task creation time")
    updated_at: datetime = Field(..., description="Last update time")


# Health Check Models
class HealthStatus(BaseModel):
    """Health check status."""
    status: Literal["healthy", "unhealthy", "degraded"] = Field(..., description="Overall status")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Check timestamp")
    version: str = Field(..., description="Application version")
    
    # Component statuses
    database: bool = Field(..., description="Database connectivity")
    redis: bool = Field(..., description="Redis connectivity")
    browser_pool: bool = Field(..., description="Browser pool status")
    celery: bool = Field(..., description="Celery worker status")
    
    # Performance metrics
    active_tasks: int = Field(0, ge=0, description="Number of active tasks")
    queue_size: int = Field(0, ge=0, description="Task queue size")
    memory_usage: Optional[float] = Field(None, description="Memory usage percentage")
    cpu_usage: Optional[float] = Field(None, description="CPU usage percentage")


# Error Models
class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error message")
    error_code: Optional[str] = Field(None, description="Error code")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Error timestamp")
    request_id: Optional[str] = Field(None, description="Request identifier for tracking")


# DSL Request Models
class DSLRequest(BaseModel):
    """Request model for DSL rendering requests via MCP protocol."""
    dsl_content: str = Field(..., description="DSL content to render")
    render_options: Optional[RenderOptions] = None
    output_format: str = Field(default="png", description="Output format")
    metadata: Optional[Dict[str, Any]] = None


# MCP Tool Models (for MCP server integration)
class MCPToolRequest(BaseModel):
    """Base model for MCP tool requests."""
    tool_name: str = Field(..., description="Tool name")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool parameters")


class MCPToolResponse(BaseModel):
    """Base model for MCP tool responses."""
    success: bool = Field(..., description="Whether tool execution succeeded")
    result: Optional[Any] = Field(None, description="Tool execution result")
    error: Optional[str] = Field(None, description="Error message if failed")