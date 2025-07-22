"""
Test Mocks
===========

Mock implementations for testing various components.
"""

import asyncio
import base64
from typing import Any, Dict, List, Optional, Union, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock, Mock
from datetime import datetime, timedelta
import uuid
import json

from src.models.schemas import (
    DSLDocument, DSLElement, ElementType, ParseResult, PNGResult,
    RenderOptions, TaskResult, TaskStatus, DSLValidationResponse
)


class MockRedisClient:
    """Mock Redis client for testing."""
    
    def __init__(self):
        self._data: Dict[str, Any] = {}
        self._expiry: Dict[str, datetime] = {}
    
    async def hset(self, key: str, mapping: Dict[str, Any]) -> int:
        """Mock hset operation."""
        if key not in self._data:
            self._data[key] = {}
        self._data[key].update(mapping)
        return len(mapping)
    
    async def hgetall(self, key: str) -> Dict[str, Any]:
        """Mock hgetall operation."""
        # Check expiry
        if key in self._expiry and datetime.utcnow() > self._expiry[key]:
            if key in self._data:
                del self._data[key]
            del self._expiry[key]
            return {}
        
        return self._data.get(key, {})
    
    async def expire(self, key: str, seconds: int) -> bool:
        """Mock expire operation."""
        self._expiry[key] = datetime.utcnow() + timedelta(seconds=seconds)
        return True
    
    async def exists(self, key: str) -> bool:
        """Mock exists operation."""
        # Check expiry first
        if key in self._expiry and datetime.utcnow() > self._expiry[key]:
            if key in self._data:
                del self._data[key]
            del self._expiry[key]
            return False
        
        return key in self._data
    
    async def delete(self, key: str) -> int:
        """Mock delete operation."""
        deleted = 0
        if key in self._data:
            del self._data[key]
            deleted += 1
        if key in self._expiry:
            del self._expiry[key]
        return deleted
    
    async def flushdb(self) -> bool:
        """Mock flushdb operation."""
        self._data.clear()
        self._expiry.clear()
        return True
    
    async def close(self) -> None:
        """Mock close operation."""
        pass
    
    def clear(self) -> None:
        """Clear all data."""
        self._data.clear()
        self._expiry.clear()


class MockBrowserPool:
    """Mock browser pool for testing."""
    
    def __init__(self, pool_size: int = 2):
        self.pool_size = pool_size
        self.initialized = False
        self.closed = False
    
    async def initialize(self) -> None:
        """Mock initialize."""
        self.initialized = True
    
    async def close(self) -> None:
        """Mock close."""
        self.closed = True
        self.initialized = False
    
    async def get_browser(self):
        """Mock get browser context manager."""
        return MockBrowserContext()


class MockBrowserContext:
    """Mock browser context manager."""
    
    async def __aenter__(self):
        return MockBrowser()
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


class MockBrowser:
    """Mock browser for testing."""
    
    async def new_context(self, **kwargs) -> "MockBrowserContextInstance":
        """Create new browser context."""
        return MockBrowserContextInstance()


class MockBrowserContextInstance:
    """Mock browser context instance."""
    
    async def new_page(self) -> "MockPage":
        """Create new page."""
        return MockPage()
    
    async def close(self) -> None:
        """Close context."""
        pass


class MockPage:
    """Mock browser page."""
    
    def __init__(self):
        self._content = ""
        self._viewport = {"width": 800, "height": 600}
    
    def set_default_timeout(self, timeout: int) -> None:
        """Set default timeout."""
        pass
    
    async def set_content(self, content: str, **kwargs) -> None:
        """Set page content."""
        self._content = content
    
    async def wait_for_load_state(self, state: str) -> None:
        """Wait for load state."""
        pass
    
    async def route(self, pattern: str, handler) -> None:
        """Set up route handling."""
        pass
    
    async def screenshot(self, **kwargs) -> bytes:
        """Take screenshot."""
        # Generate fake PNG data
        fake_png = b"\x89PNG\r\n\x1a\n" + b"fake_image_data" + str(uuid.uuid4()).encode()
        return fake_png
    
    async def wait_for_selector(self, selector: str, **kwargs) -> "MockElement":
        """Wait for selector."""
        return MockElement()


class MockElement:
    """Mock page element."""
    
    async def screenshot(self, **kwargs) -> bytes:
        """Take element screenshot."""
        fake_png = b"\x89PNG\r\n\x1a\n" + b"fake_element_data" + str(uuid.uuid4()).encode()
        return fake_png
    
    async def bounding_box(self) -> Dict[str, float]:
        """Get element bounding box."""
        return {"x": 100, "y": 100, "width": 200, "height": 150}


class MockStorageManager:
    """Mock storage manager for testing."""
    
    def __init__(self):
        self._stored_files: Dict[str, bytes] = {}
        self._metadata: Dict[str, Dict[str, Any]] = {}
    
    async def store_png(self, png_result: PNGResult, task_id: Optional[str] = None) -> str:
        """Mock store PNG."""
        content_hash = f"mock_hash_{uuid.uuid4().hex[:8]}"
        self._stored_files[content_hash] = png_result.png_data
        self._metadata[content_hash] = {
            "task_id": task_id,
            "file_size": png_result.file_size,
            "width": png_result.width,
            "height": png_result.height,
            "stored_at": datetime.utcnow().isoformat()
        }
        return content_hash
    
    async def retrieve_png(self, content_hash: str) -> Optional[bytes]:
        """Mock retrieve PNG."""
        return self._stored_files.get(content_hash)
    
    async def get_storage_stats(self) -> Dict[str, Any]:
        """Mock get storage stats."""
        total_size = sum(len(data) for data in self._stored_files.values())
        return {
            "total_files": len(self._stored_files),
            "total_size": total_size,
            "hot_storage": len(self._stored_files),
            "cold_storage": 0,
            "cache_hits": 0,
            "cache_misses": 0
        }
    
    async def cleanup_expired(self) -> Dict[str, int]:
        """Mock cleanup expired files."""
        return {"deleted_files": 0, "freed_bytes": 0}


class MockCeleryTask:
    """Mock Celery task for testing."""
    
    def __init__(self, task_id: Optional[str] = None):
        self.task_id = task_id or str(uuid.uuid4())
        self.result = None
        self.state = "PENDING"
    
    def apply_async(self, args: List[Any], **kwargs) -> "MockAsyncResult":
        """Mock apply_async."""
        task_id = kwargs.get("task_id", str(uuid.uuid4()))
        return MockAsyncResult(task_id)
    
    def delay(self, *args, **kwargs) -> "MockAsyncResult":
        """Mock delay."""
        return MockAsyncResult(self.task_id)


class MockAsyncResult:
    """Mock Celery AsyncResult."""
    
    def __init__(self, task_id: str):
        self.id = task_id
        self._result = None
        self._state = "PENDING"
        self._ready = False
    
    def ready(self) -> bool:
        """Check if result is ready."""
        return self._ready
    
    def get(self, timeout: Optional[float] = None) -> Any:
        """Get result."""
        if not self._ready:
            raise Exception("Result not ready")
        return self._result
    
    def set_result(self, result: Any, state: str = "SUCCESS") -> None:
        """Set mock result."""
        self._result = result
        self._state = state
        self._ready = True


class MockDSLParser:
    """Mock DSL parser for testing."""
    
    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.parse_calls = []
        self.validate_calls = []
    
    async def parse(self, content: str) -> ParseResult:
        """Mock parse method."""
        self.parse_calls.append(content)
        
        if not self.should_succeed:
            return ParseResult(
                success=False,
                document=None,
                errors=["Mock parsing error"],
                processing_time=0.1
            )
        
        # Create a simple mock document
        from tests.utils.data_generators import DSLDataGenerator
        simple_dsl = DSLDataGenerator.generate_simple_button()
        
        # Convert to DSLDocument (simplified)
        mock_document = DSLDocument(
            title=simple_dsl.get("title", "Mock Document"),
            width=simple_dsl.get("width", 800),
            height=simple_dsl.get("height", 600),
            elements=[]  # Simplified for mock
        )
        
        return ParseResult(
            success=True,
            document=mock_document,
            errors=[],
            warnings=[],
            processing_time=0.1
        )
    
    async def validate_syntax(self, content: str) -> bool:
        """Mock validate syntax."""
        self.validate_calls.append(content)
        return self.should_succeed


class MockHTMLGenerator:
    """Mock HTML generator for testing."""
    
    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.generate_calls = []
    
    async def generate(self, document: DSLDocument, options: RenderOptions) -> str:
        """Mock generate HTML."""
        self.generate_calls.append((document, options))
        
        if not self.should_succeed:
            raise Exception("Mock HTML generation error")
        
        return f"""<!DOCTYPE html>
<html>
<head>
    <title>{document.title or 'Mock Document'}</title>
    <style>
        .dsl-element {{ position: absolute; }}
        .dsl-button {{ background: #007bff; color: white; }}
    </style>
</head>
<body>
    <div class="dsl-canvas" style="width:{document.width}px;height:{document.height}px;">
        <button class="dsl-element dsl-button" style="left:100px;top:100px;width:150px;height:40px;">
            Mock Button
        </button>
    </div>
    <script>document.body.setAttribute("data-render-complete", "true");</script>
</body>
</html>"""


class MockPNGGenerator:
    """Mock PNG generator for testing."""
    
    def __init__(self, should_succeed: bool = True):
        self.should_succeed = should_succeed
        self.generate_calls = []
        self.initialized = False
        self.closed = False
    
    async def initialize(self) -> None:
        """Mock initialize."""
        self.initialized = True
    
    async def close(self) -> None:
        """Mock close."""
        self.closed = True
        self.initialized = False
    
    async def generate_png(self, html_content: str, options: RenderOptions) -> PNGResult:
        """Mock generate PNG."""
        self.generate_calls.append((html_content, options))
        
        if not self.should_succeed:
            raise Exception("Mock PNG generation error")
        
        # Generate fake PNG data
        fake_png_data = b"\x89PNG\r\n\x1a\n" + b"mock_png_data_" + str(uuid.uuid4()).encode()[:16]
        
        return PNGResult(
            png_data=fake_png_data,
            base64_data=base64.b64encode(fake_png_data).decode('utf-8'),
            width=options.width,
            height=options.height,
            file_size=len(fake_png_data),
            metadata={
                "generator": "mock",
                "test": True,
                "created_at": datetime.utcnow().isoformat()
            }
        )


class MockMCPServer:
    """Mock MCP server for testing."""
    
    def __init__(self):
        self.tool_calls = []
        self.resource_reads = []
    
    async def handle_tool_call(self, name: str, arguments: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Mock handle tool call."""
        self.tool_calls.append((name, arguments))
        
        if name == "render_ui_mockup":
            return [{
                "type": "text",
                "text": json.dumps({
                    "success": True,
                    "png_result": {
                        "base64_data": "ZmFrZV9wbmdfZGF0YQ==",
                        "width": 800,
                        "height": 600,
                        "file_size": 1024
                    }
                })
            }]
        elif name == "validate_dsl":
            return [{
                "type": "text", 
                "text": json.dumps({
                    "valid": True,
                    "errors": [],
                    "warnings": [],
                    "suggestions": []
                })
            }]
        elif name == "get_render_status":
            return [{
                "type": "text",
                "text": json.dumps({
                    "success": True,
                    "task_id": arguments.get("task_id"),
                    "status": "completed",
                    "result": {"success": True}
                })
            }]
        
        return [{"type": "text", "text": "Mock response"}]
    
    async def handle_resource_read(self, uri: str) -> str:
        """Mock handle resource read."""
        self.resource_reads.append(uri)
        
        if uri == "dsl://schemas/element-types":
            return json.dumps({
                "element_types": ["button", "text", "input", "container"],
                "schema_version": "1.0"
            })
        elif uri == "dsl://examples/basic":
            return json.dumps({
                "simple_button": {
                    "width": 300,
                    "height": 200,
                    "elements": [{"type": "button", "label": "Test"}]
                }
            })
        
        return json.dumps({"mock": "resource"})


def create_mock_dependencies() -> Dict[str, Any]:
    """Create a complete set of mock dependencies."""
    return {
        "redis_client": MockRedisClient(),
        "browser_pool": MockBrowserPool(),
        "storage_manager": MockStorageManager(),
        "dsl_parser": MockDSLParser(),
        "html_generator": MockHTMLGenerator(),
        "png_generator": MockPNGGenerator(),
        "mcp_server": MockMCPServer(),
        "celery_task": MockCeleryTask()
    }


def create_failing_mocks() -> Dict[str, Any]:
    """Create mocks that simulate failures."""
    return {
        "redis_client": MockRedisClient(),  # This one works
        "browser_pool": MockBrowserPool(),  # This one works
        "storage_manager": MockStorageManager(),  # This one works
        "dsl_parser": MockDSLParser(should_succeed=False),
        "html_generator": MockHTMLGenerator(should_succeed=False),
        "png_generator": MockPNGGenerator(should_succeed=False),
        "mcp_server": MockMCPServer(),  # This one works
        "celery_task": MockCeleryTask()  # This one works
    }


# Async context manager helpers
class AsyncContextManager:
    """Helper for creating async context managers in tests."""
    
    def __init__(self, return_value: Any):
        self.return_value = return_value
    
    async def __aenter__(self):
        return self.return_value
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def mock_async_context_manager(return_value: Any):
    """Create a mock async context manager."""
    return AsyncContextManager(return_value)