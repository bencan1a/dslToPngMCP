"""
Browser Service Client
======================

HTTP client for connecting to the centralized browser service.
Used by Celery workers to access the shared browser pool.
"""

import aiohttp
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class BrowserServiceError(Exception):
    """Exception raised when browser service communication fails."""

    pass


class BrowserServiceClient:
    """Client for communicating with the centralized browser service."""

    def __init__(self, service_url: str = "http://playwright-browsers:8080"):
        self.service_url = service_url
        self.settings = get_settings()
        self.logger: Any = logger.bind(
            component="browser_service_client"
        )  # structlog.BoundLoggerBase
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    async def health_check(self) -> bool:
        """Check if the browser service is healthy."""
        try:
            session = await self._get_session()
            async with session.get(f"{self.service_url}/health") as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.debug(
                        "Browser service health check successful",
                        status=data.get("status"),
                        available_browsers=data.get("available_browsers"),
                    )
                    return True
                else:
                    self.logger.warning(
                        "Browser service health check failed",
                        status=response.status,
                        response=await response.text(),
                    )
                    return False
        except Exception as e:
            self.logger.error("Browser service health check error", error=str(e))
            return False

    async def acquire_browser(self) -> Dict[str, Any]:
        """Acquire a browser instance from the service."""
        try:
            session = await self._get_session()
            async with session.post(f"{self.service_url}/acquire") as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.debug(
                        "Browser acquired from service", browser_id=data.get("browser_id")
                    )
                    return data
                else:
                    error_text = await response.text()
                    raise BrowserServiceError(
                        f"Failed to acquire browser: {response.status} - {error_text}"
                    )
        except Exception as e:
            error_msg = f"Browser acquisition failed: {e}"
            self.logger.error("Browser acquisition error", error=error_msg)
            raise BrowserServiceError(error_msg)

    async def release_browser(self, browser_id: str) -> bool:
        """Release a browser instance back to the service."""
        try:
            session = await self._get_session()
            async with session.post(
                f"{self.service_url}/release", json={"browser_id": browser_id}
            ) as response:
                if response.status == 200:
                    self.logger.debug("Browser released to service", browser_id=browser_id)
                    return True
                else:
                    error_text = await response.text()
                    self.logger.warning(
                        "Browser release failed",
                        browser_id=browser_id,
                        status=response.status,
                        response=error_text,
                    )
                    return False
        except Exception as e:
            self.logger.error("Browser release error", browser_id=browser_id, error=str(e))
            return False

    async def generate_screenshot(
        self, html_content: str, options: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate a screenshot using the browser service."""
        try:
            session = await self._get_session()
            payload = {"html_content": html_content, "options": options}

            async with session.post(f"{self.service_url}/screenshot", json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    self.logger.debug(
                        "Screenshot generated via service", file_size=data.get("file_size")
                    )
                    return data
                else:
                    error_text = await response.text()
                    raise BrowserServiceError(
                        f"Screenshot generation failed: {response.status} - {error_text}"
                    )
        except Exception as e:
            error_msg = f"Screenshot generation failed: {e}"
            self.logger.error("Screenshot generation error", error=error_msg)
            raise BrowserServiceError(error_msg)

    @asynccontextmanager
    async def browser_context(self):
        """Context manager for acquiring and releasing a browser."""
        browser_data = None
        try:
            browser_data = await self.acquire_browser()
            yield browser_data
        finally:
            if browser_data and "browser_id" in browser_data:
                await self.release_browser(browser_data["browser_id"])


def is_celery_worker_context() -> bool:
    """Detect if we're running in a Celery worker context."""
    import sys
    import os

    # Check command line arguments
    argv_contains_celery = any("celery" in arg.lower() for arg in sys.argv)

    # Check environment variables
    celery_task_env = os.environ.get("CELERY_CURRENT_TASK")
    worker_id_env = os.environ.get("WORKER_ID")

    # Check if we're in a Celery worker process
    is_celery_worker = (
        argv_contains_celery or celery_task_env is not None or worker_id_env is not None
    )

    logger.info(
        "🔍 CELERY WORKER DETECTION: Browser service client context check",
        argv_contains_celery=argv_contains_celery,
        celery_task_env=celery_task_env,
        worker_id_env=worker_id_env,
        is_celery_worker=is_celery_worker,
        argv_content=sys.argv,
    )

    return is_celery_worker


# Global client instance
_browser_service_client: Optional[BrowserServiceClient] = None


async def get_browser_service_client() -> BrowserServiceClient:
    """Get or create the global browser service client."""
    global _browser_service_client
    if _browser_service_client is None:
        _browser_service_client = BrowserServiceClient()
    return _browser_service_client


async def close_browser_service_client() -> None:
    """Close the global browser service client."""
    global _browser_service_client
    if _browser_service_client:
        await _browser_service_client.close()
        _browser_service_client = None
