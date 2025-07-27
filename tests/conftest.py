"""
Test Configuration
==================

Pytest configuration with fixtures for all test types.
Provides test database setup, mock services, and test data.
"""

import asyncio
import pytest
import pytest_asyncio
import tempfile
import shutil
from pathlib import Path
from typing import AsyncGenerator, Generator, Dict, Any
from unittest.mock import AsyncMock, MagicMock, patch
import json
import yaml
import os
import redis.asyncio as redis
from fastapi.testclient import TestClient
from playwright.async_api import async_playwright

# Import application modules
from src.config.settings import Settings, get_settings
from pydantic_settings import SettingsConfigDict
from src.config.logging import get_logger
from src.config.database import get_redis_client
from src.api.main import app
from src.models.schemas import (
    DSLDocument,
    DSLElement,
    ElementType,
    ElementLayout,
    ElementStyle,
    RenderOptions,
    PNGResult,
    ParseResult,
    DSLRenderRequest,
)
from src.core.rendering.png_generator import BrowserPool
from src.core.dsl.parser import DSLParserFactory


# Test settings override
class TestSettings(Settings):
    """Test-specific settings."""

    environment: str = "testing"
    debug: bool = True
    redis_url: str = "redis://localhost:6379/15"  # Use test database
    celery_broker_url: str = "redis://localhost:6379/14"
    celery_result_backend: str = "redis://localhost:6379/14"
    storage_path: Path = Path("./test_storage")
    temp_path: Path = Path("./test_tmp")
    browser_pool_size: int = 2  # Smaller pool for tests
    playwright_headless: bool = True
    log_level: str = "DEBUG"

    model_config = SettingsConfigDict(env_file=".env.test")


@pytest.fixture(scope="session")
def test_settings() -> TestSettings:
    """Test settings fixture."""
    return TestSettings()


@pytest.fixture(scope="session", autouse=True)
def override_settings(test_settings: TestSettings):
    """Override application settings for testing."""
    with patch("src.config.settings.get_settings", return_value=test_settings):
        yield test_settings


@pytest.fixture(scope="session")
def temp_dir() -> Generator[Path, None, None]:
    """Create temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp(prefix="dsl_png_test_"))
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(scope="session")
async def redis_client(test_settings: TestSettings) -> AsyncGenerator[redis.Redis, None]:
    """Redis client for testing."""
    client = redis.from_url(test_settings.redis_url)

    # Clear test database
    await client.flushdb()

    yield client

    # Cleanup
    await client.flushdb()
    await client.close()


@pytest.fixture
async def clean_redis(redis_client: redis.Redis):
    """Clean Redis before each test."""
    await redis_client.flushdb()
    yield
    await redis_client.flushdb()


@pytest.fixture(scope="session")
def fastapi_client() -> Generator[TestClient, None, None]:
    """FastAPI test client."""
    with TestClient(app) as client:
        yield client


@pytest.fixture(scope="session")
async def browser_pool() -> AsyncGenerator[BrowserPool, None]:
    """Browser pool for testing."""
    pool = BrowserPool(pool_size=2)
    await pool.initialize()
    yield pool
    await pool.close()


@pytest.fixture
async def mock_browser_pool() -> AsyncMock:
    """Mock browser pool for unit tests."""
    mock_pool = AsyncMock(spec=BrowserPool)
    mock_browser = AsyncMock()
    mock_pool.get_browser.return_value.__aenter__.return_value = mock_browser
    return mock_pool


@pytest.fixture
def sample_dsl_json() -> str:
    """Sample JSON DSL document."""
    return json.dumps(
        {
            "title": "Test UI",
            "width": 800,
            "height": 600,
            "elements": [
                {
                    "type": "button",
                    "id": "test-button",
                    "layout": {"x": 100, "y": 100, "width": 150, "height": 40},
                    "style": {"background": "#007bff", "color": "white"},
                    "label": "Click Me",
                },
                {
                    "type": "text",
                    "id": "test-text",
                    "layout": {"x": 100, "y": 160, "width": 200, "height": 30},
                    "text": "Hello World",
                    "style": {"fontSize": 16},
                },
            ],
        }
    )


@pytest.fixture
def sample_dsl_yaml() -> str:
    """Sample YAML DSL document."""
    return yaml.dump(
        {
            "title": "YAML Test UI",
            "width": 400,
            "height": 300,
            "elements": [
                {
                    "type": "container",
                    "id": "main-container",
                    "layout": {"x": 0, "y": 0, "width": 400, "height": 300},
                    "children": [
                        {
                            "type": "input",
                            "id": "username",
                            "layout": {"x": 50, "y": 50, "width": 300, "height": 35},
                            "placeholder": "Enter username",
                        },
                        {
                            "type": "button",
                            "id": "submit",
                            "layout": {"x": 50, "y": 100, "width": 100, "height": 35},
                            "label": "Submit",
                        },
                    ],
                }
            ],
        }
    )


@pytest.fixture
def invalid_dsl_json() -> str:
    """Invalid JSON DSL for error testing."""
    return '{"title": "Invalid", "elements": [{"type": "invalid_type"}]'  # Missing closing brace


@pytest.fixture
def invalid_dsl_semantic() -> str:
    """Semantically invalid DSL for validation testing."""
    return json.dumps(
        {
            "title": "Invalid Semantic",
            "width": 800,
            "height": 600,
            "elements": [
                {
                    "type": "text",
                    "children": [  # Text elements cannot have children
                        {"type": "button", "label": "Invalid"}
                    ],
                }
            ],
        }
    )


@pytest.fixture
def sample_dsl_document() -> DSLDocument:
    """Sample DSL document object."""
    return DSLDocument(
        title="Test Document",
        width=800,
        height=600,
        elements=[
            DSLElement(
                type=ElementType.BUTTON,
                id="test-button",
                layout=ElementLayout(x=100, y=100, width=150, height=40),
                style=ElementStyle(background="#007bff", color="white"),
                label="Test Button",
            ),
            DSLElement(
                type=ElementType.TEXT,
                id="test-text",
                layout=ElementLayout(x=100, y=160, width=200, height=30),
                text="Test Text",
                style=ElementStyle(font_size=16),
            ),
        ],
    )


@pytest.fixture
def sample_render_options() -> RenderOptions:
    """Sample render options."""
    return RenderOptions(
        width=800,
        height=600,
        device_scale_factor=1.0,
        wait_for_load=True,
        optimize_png=True,
        timeout=30,
    )


@pytest.fixture
def sample_render_request(
    sample_dsl_json: str, sample_render_options: RenderOptions
) -> DSLRenderRequest:
    """Sample render request."""
    return DSLRenderRequest(dsl_content=sample_dsl_json, options=sample_render_options)


@pytest.fixture
def mock_png_result() -> PNGResult:
    """Mock PNG result for testing."""
    png_data = b"fake_png_data"
    return PNGResult(
        png_data=png_data,
        base64_data="ZmFrZV9wbmdfZGF0YQ==",  # base64 of "fake_png_data"
        width=800,
        height=600,
        file_size=len(png_data),
        metadata={"test": True},
    )


@pytest.fixture
def mock_parse_result(sample_dsl_document: DSLDocument) -> ParseResult:
    """Mock parse result for testing."""
    return ParseResult(
        success=True, document=sample_dsl_document, errors=[], warnings=[], processing_time=0.1
    )


@pytest.fixture
def complex_dsl_document() -> DSLDocument:
    """Complex DSL document for advanced testing."""
    return DSLDocument(
        title="Complex Layout",
        description="A complex layout with nested containers",
        width=1200,
        height=800,
        elements=[
            DSLElement(
                type=ElementType.NAVBAR,
                id="navbar",
                layout=ElementLayout(x=0, y=0, width=1200, height=60),
                style=ElementStyle(background="#f8f9fa", border_bottom="1px solid #dee2e6"),
                children=[
                    DSLElement(
                        type=ElementType.TEXT,
                        id="nav-title",
                        layout=ElementLayout(x=20, y=15, width=200, height=30),
                        text="My App",
                        style=ElementStyle(font_size=20, font_weight="bold"),
                    ),
                    DSLElement(
                        type=ElementType.BUTTON,
                        id="nav-button",
                        layout=ElementLayout(x=1050, y=10, width=80, height=40),
                        label="Login",
                        style=ElementStyle(background="#007bff", color="white"),
                    ),
                ],
            ),
            DSLElement(
                type=ElementType.CONTAINER,
                id="main-content",
                layout=ElementLayout(x=0, y=60, width=1200, height=740),
                children=[
                    DSLElement(
                        type=ElementType.SIDEBAR,
                        id="sidebar",
                        layout=ElementLayout(x=0, y=0, width=250, height=740),
                        style=ElementStyle(background="#f8f9fa", border_right="1px solid #dee2e6"),
                        children=[
                            DSLElement(
                                type=ElementType.TEXT,
                                id="sidebar-title",
                                layout=ElementLayout(x=20, y=20, width=200, height=30),
                                text="Navigation",
                                style=ElementStyle(font_size=16, font_weight="bold"),
                            )
                        ],
                    ),
                    DSLElement(
                        type=ElementType.CONTAINER,
                        id="content-area",
                        layout=ElementLayout(x=250, y=0, width=950, height=740),
                        children=[
                            DSLElement(
                                type=ElementType.CARD,
                                id="info-card",
                                layout=ElementLayout(x=50, y=50, width=400, height=300),
                                style=ElementStyle(
                                    background="white",
                                    border="1px solid #dee2e6",
                                    border_radius="8px",
                                    padding="20px",
                                ),
                                children=[
                                    DSLElement(
                                        type=ElementType.TEXT,
                                        id="card-title",
                                        layout=ElementLayout(x=0, y=0, width=360, height=40),
                                        text="Information Card",
                                        style=ElementStyle(font_size=18, font_weight="bold"),
                                    ),
                                    DSLElement(
                                        type=ElementType.TEXT,
                                        id="card-content",
                                        layout=ElementLayout(x=0, y=50, width=360, height=200),
                                        text="This is a sample card with some content to demonstrate complex layouts.",
                                        style=ElementStyle(font_size=14, color="#666"),
                                    ),
                                ],
                            )
                        ],
                    ),
                ],
            ),
        ],
        css="body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; }",
        theme="modern",
        responsive_breakpoints={"sm": 640, "md": 768, "lg": 1024, "xl": 1280},
    )


@pytest.fixture
async def mock_storage_manager():
    """Mock storage manager for testing."""
    mock_manager = AsyncMock()
    mock_manager.store_png.return_value = "test_hash_12345"
    mock_manager.retrieve_png.return_value = b"fake_png_data"
    mock_manager.get_storage_stats.return_value = {
        "total_files": 10,
        "total_size": 1024000,
        "hot_storage": 5,
        "cold_storage": 5,
    }
    return mock_manager


@pytest.fixture
def mock_celery_task():
    """Mock Celery task for testing."""
    mock_task = MagicMock()
    mock_task.apply_async.return_value.id = "test_task_id_12345"
    return mock_task


# Pytest configuration
def pytest_configure(config):
    """Configure pytest."""
    # All markers are now defined in pyproject.toml [tool.pytest.ini_options]
    # This function is kept for any future pytest configuration needs
    pass


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file paths."""
    for item in items:
        # Add markers based on file path
        if "unit" in str(item.fspath):
            item.add_marker(pytest.mark.unit)
        elif "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)
        elif "api" in str(item.fspath):
            item.add_marker(pytest.mark.api)
        elif "mcp" in str(item.fspath):
            item.add_marker(pytest.mark.mcp)
        elif "docker" in str(item.fspath):
            item.add_marker(pytest.mark.docker)
        elif "performance" in str(item.fspath):
            item.add_marker(pytest.mark.performance)
        elif "security" in str(item.fspath):
            item.add_marker(pytest.mark.security)


# Async test helpers
@pytest_asyncio.fixture
async def async_client():
    """Async HTTP client for API testing."""
    import httpx

    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client


# Test data directories
@pytest.fixture(scope="session")
def test_data_dir() -> Path:
    """Test data directory."""
    return Path(__file__).parent / "data"


@pytest.fixture(scope="session")
def example_dsls(test_data_dir: Path) -> Dict[str, str]:
    """Load example DSL files."""
    examples = {}
    examples_dir = Path("examples")

    if examples_dir.exists():
        for file_path in examples_dir.glob("*.json"):
            examples[file_path.stem] = file_path.read_text()
        for file_path in examples_dir.glob("*.yaml"):
            examples[file_path.stem] = file_path.read_text()

    return examples


# Performance test fixtures
@pytest.fixture
def performance_dsl_large() -> str:
    """Large DSL document for performance testing."""
    elements = []
    for i in range(100):
        elements.append(
            {
                "type": "button",
                "id": f"button-{i}",
                "layout": {"x": (i % 10) * 80, "y": (i // 10) * 50, "width": 70, "height": 40},
                "label": f"Button {i}",
                "style": {"background": f"hsl({i * 3.6}, 70%, 50%)", "color": "white"},
            }
        )

    return json.dumps(
        {"title": "Large Performance Test", "width": 800, "height": 1000, "elements": elements}
    )


# Error simulation fixtures
@pytest.fixture
def error_simulation():
    """Helper for simulating various error conditions."""

    class ErrorSimulator:
        @staticmethod
        def redis_connection_error():
            return redis.ConnectionError("Connection refused")

        @staticmethod
        def browser_timeout_error():
            from playwright.async_api import TimeoutError

            return TimeoutError("Page timeout")

        @staticmethod
        def invalid_json_error():
            return json.JSONDecodeError("Invalid JSON", "", 0)

        @staticmethod
        def file_not_found_error():
            return FileNotFoundError("File not found")

    return ErrorSimulator()
