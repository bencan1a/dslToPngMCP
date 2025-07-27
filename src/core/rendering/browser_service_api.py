"""
Browser Service HTTP API
========================

FastAPI-based HTTP API for the centralized browser service.
This runs in the playwright-browsers Docker container and provides
HTTP endpoints for Celery workers to access browser functionality.
"""

import asyncio
import base64
from typing import Dict, Any, Optional
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from src.config.logging import get_logger
from src.core.rendering.png_generator import BrowserPool

logger = get_logger(__name__)


class BrowserServiceState:
    """Global state for the browser service."""

    def __init__(self):
        self.browser_pool: Optional[BrowserPool] = None
        self.active_browsers: Dict[str, Any] = {}
        self.logger: Any = logger.bind(component="browser_service_api")  # structlog.BoundLoggerBase

    async def initialize(self):
        """Initialize the browser pool."""
        if self.browser_pool is None:
            self.browser_pool = BrowserPool()
            await self.browser_pool.initialize()
            self.logger.info("Browser service initialized", pool_size=self.browser_pool.pool_size)

    async def cleanup(self):
        """Cleanup the browser pool."""
        if self.browser_pool:
            await self.browser_pool.close()
            self.browser_pool = None
            self.active_browsers.clear()
            self.logger.info("Browser service cleaned up")


# Global service state
service_state = BrowserServiceState()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager."""
    # Startup
    await service_state.initialize()
    yield
    # Shutdown
    await service_state.cleanup()


# Create FastAPI app
app = FastAPI(
    title="DSL Browser Service",
    description="Centralized browser automation service for PNG generation",
    version="1.0.0",
    lifespan=lifespan,
)


# Request/Response models
class ScreenshotRequest(BaseModel):
    html_content: str
    options: Dict[str, Any]


class ScreenshotResponse(BaseModel):
    success: bool
    png_data: Optional[str] = None  # Base64 encoded
    file_size: Optional[int] = None
    error: Optional[str] = None


class BrowserAcquireResponse(BaseModel):
    success: bool
    browser_id: Optional[str] = None
    error: Optional[str] = None


class BrowserReleaseRequest(BaseModel):
    browser_id: str


class BrowserReleaseResponse(BaseModel):
    success: bool
    error: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    available_browsers: int
    total_browsers: int
    active_browser_sessions: int


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    try:
        if not service_state.browser_pool:
            return HealthResponse(
                status="unhealthy",
                available_browsers=0,
                total_browsers=0,
                active_browser_sessions=0,
            )

        total = service_state.browser_pool.pool_size
        available = len(service_state.browser_pool.browsers)
        active_sessions = len(service_state.active_browsers)

        status = "healthy" if available > 0 else "busy"

        return HealthResponse(
            status=status,
            available_browsers=available,
            total_browsers=total,
            active_browser_sessions=active_sessions,
        )
    except Exception as e:
        service_state.logger.error("Health check failed", error=str(e))
        return HealthResponse(
            status="error", available_browsers=0, total_browsers=0, active_browser_sessions=0
        )


@app.post("/screenshot", response_model=ScreenshotResponse)
async def generate_screenshot(request: ScreenshotRequest):
    """Generate a screenshot from HTML content."""
    try:
        if not service_state.browser_pool:
            raise HTTPException(status_code=503, detail="Browser service not initialized")

        service_state.logger.debug(
            "Screenshot request received",
            html_length=len(request.html_content),
            options=request.options,
        )

        # Import the PNG generator function
        from src.core.rendering.png_generator import generate_png_from_html
        from src.models.schemas import RenderOptions

        # Convert options dict to RenderOptions object
        render_options = RenderOptions(**request.options)

        # Use the global PNG generator function
        result = await generate_png_from_html(request.html_content, render_options)
        png_data = result.png_data

        # Encode as base64 for JSON response
        png_base64 = base64.b64encode(png_data).decode("utf-8")

        service_state.logger.debug("Screenshot generated successfully", file_size=len(png_data))

        return ScreenshotResponse(success=True, png_data=png_base64, file_size=len(png_data))

    except Exception as e:
        error_msg = f"Screenshot generation failed: {e}"
        service_state.logger.error("Screenshot generation error", error=error_msg)
        return ScreenshotResponse(success=False, error=error_msg)


@app.post("/acquire", response_model=BrowserAcquireResponse)
async def acquire_browser():
    """Acquire a browser instance (placeholder for future use)."""
    try:
        if not service_state.browser_pool:
            raise HTTPException(status_code=503, detail="Browser service not initialized")

        # Generate a unique browser session ID
        browser_id = str(uuid.uuid4())

        # For now, we don't actually reserve a browser, just track the session
        service_state.active_browsers[browser_id] = {
            "acquired_at": asyncio.get_event_loop().time(),
            "status": "active",
        }

        service_state.logger.debug("Browser session acquired", browser_id=browser_id)

        return BrowserAcquireResponse(success=True, browser_id=browser_id)

    except Exception as e:
        error_msg = f"Browser acquisition failed: {e}"
        service_state.logger.error("Browser acquisition error", error=error_msg)
        return BrowserAcquireResponse(success=False, error=error_msg)


@app.post("/release", response_model=BrowserReleaseResponse)
async def release_browser(request: BrowserReleaseRequest):
    """Release a browser instance."""
    try:
        browser_id = request.browser_id

        if browser_id in service_state.active_browsers:
            del service_state.active_browsers[browser_id]
            service_state.logger.debug("Browser session released", browser_id=browser_id)
        else:
            service_state.logger.warning(
                "Attempted to release unknown browser session", browser_id=browser_id
            )

        return BrowserReleaseResponse(success=True)

    except Exception as e:
        error_msg = f"Browser release failed: {e}"
        service_state.logger.error("Browser release error", error=error_msg)
        return BrowserReleaseResponse(success=False, error=error_msg)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080, log_level="info")
