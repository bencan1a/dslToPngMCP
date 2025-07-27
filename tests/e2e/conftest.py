"""
E2E Test Configuration
======================

End-to-end test specific fixtures and configuration.
Extends the base conftest.py with E2E-specific setup for:
- Docker Compose development environment management
- Service health checking
- SSE testing
- Real browser automation
- Environment lifecycle management
"""

import asyncio
import pytest
import pytest_asyncio
import subprocess
import time
import signal
import os
import httpx
import json
import base64
import warnings
from pathlib import Path
from typing import AsyncGenerator, Generator, Dict, Any, List
from unittest.mock import patch

# Suppress warnings
warnings.filterwarnings("ignore", category=UserWarning)
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message="Unknown pytest.mark.*")
warnings.filterwarnings("ignore", message="Support for class-based.*config.*is deprecated.*")

# Import base fixtures from parent conftest
from tests.conftest import *  # noqa: F403, F401


class DockerComposeManager:
    """Manages Docker Compose development environment for E2E tests."""

    def __init__(self):
        self.compose_file = "docker-compose.yaml"
        self.project_name = "dsl-e2e-test"
        self.is_running = False
        self.services_started = []

        # Service configuration from docker-compose.yaml
        self.services = {
            "redis": {"port": 6379, "health_endpoint": None},
            "mcp-server": {"port": 3001, "health_endpoint": None},
            "fastapi-server-1": {"port": 8000, "health_endpoint": "/health"},
            "fastapi-server-2": {"port": 8000, "health_endpoint": "/health"},
            "celery-worker-1": {"port": None, "health_endpoint": None},
            "celery-worker-2": {"port": None, "health_endpoint": None},
            "celery-worker-3": {"port": None, "health_endpoint": None},
            "celery-worker-4": {"port": None, "health_endpoint": None},
            "playwright-browsers": {"port": 8080, "health_endpoint": "/health"},
            "nginx-proxy": {"port": 80, "health_endpoint": "/health"},
        }

        # Service startup order for dependencies
        self.startup_order = [
            ["redis"],
            ["mcp-server"],
            ["fastapi-server-1", "fastapi-server-2"],
            ["celery-worker-1", "celery-worker-2", "celery-worker-3", "celery-worker-4"],
            ["playwright-browsers"],
            ["nginx-proxy"],
        ]

    async def start_environment(self, timeout: int = 300):
        """Start the complete Docker Compose environment."""
        if self.is_running:
            return

        print("🚀 Starting Docker Compose development environment...")

        try:
            # Stop any existing containers including those with conflicting names
            print("🧹 Cleaning up existing containers...")
            await self._cleanup_existing_containers()

            # Stop any existing containers from our project
            await self._run_compose_command(["down", "--remove-orphans"], check=False)

            # Start services in dependency order
            for service_group in self.startup_order:
                print(f"🔄 Starting services: {', '.join(service_group)}")

                # Start the service group
                cmd = ["up", "-d"] + service_group
                await self._run_compose_command(cmd)

                # Wait for health checks
                await self._wait_for_services_health(service_group, timeout=60)

                self.services_started.extend(service_group)
                print(f"✅ Services started: {', '.join(service_group)}")

            self.is_running = True
            print("🎉 Docker Compose environment ready!")

            # Wait for full system stabilization
            await asyncio.sleep(10)

        except Exception as e:
            print(f"❌ Failed to start environment: {e}")
            await self.stop_environment()
            raise

    async def stop_environment(self):
        """Stop the Docker Compose environment."""
        if not self.is_running:
            return

        print("🛑 Stopping Docker Compose environment...")

        try:
            # Stop all services
            await self._run_compose_command(["down", "--remove-orphans"])
            self.is_running = False
            self.services_started = []
            print("✅ Environment stopped successfully")
        except Exception as e:
            print(f"⚠️ Error during environment shutdown: {e}")

    async def _run_compose_command(self, args: List[str], check: bool = True):
        """Run a docker-compose command."""
        cmd = ["docker", "compose", "-f", self.compose_file, "-p", self.project_name] + args

        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await proc.communicate()

        if check and proc.returncode != 0:
            raise RuntimeError(
                f"Docker compose command failed: {' '.join(cmd)}\n"
                f"Return code: {proc.returncode}\n"
                f"Stdout: {stdout.decode()}\n"
                f"Stderr: {stderr.decode()}"
            )

        return stdout.decode(), stderr.decode(), proc.returncode

    async def _wait_for_services_health(self, services: List[str], timeout: int = 60):
        """Wait for services to be healthy."""
        start_time = time.time()

        while time.time() - start_time < timeout:
            all_healthy = True

            for service in services:
                if not await self._check_service_health(service):
                    all_healthy = False
                    break

            if all_healthy:
                return

            await asyncio.sleep(2)

        raise TimeoutError(f"Services not healthy after {timeout}s: {services}")

    async def _check_service_health(self, service: str) -> bool:
        """Check if a service is healthy."""
        service_config = self.services.get(service)
        if not service_config:
            return False

        # For services without HTTP endpoints, check docker health
        if not service_config["health_endpoint"]:
            return await self._check_docker_health(service)

        # For HTTP services, check endpoint
        port = service_config["port"]
        endpoint = service_config["health_endpoint"]

        try:
            # For nginx-proxy, use exposed port 80
            if service == "nginx-proxy":
                url = f"http://localhost:{port}{endpoint}"
            else:
                # For internal services, check via docker or skip if not exposed
                return await self._check_docker_health(service)

            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(url)
                return response.status_code == 200

        except Exception:
            return False

    async def _check_docker_health(self, service: str) -> bool:
        """Check service health via Docker."""
        try:
            stdout, stderr, returncode = await self._run_compose_command(
                ["ps", "--format", "json", service], check=False
            )

            if returncode != 0:
                return False

            # Parse docker compose ps output
            lines = stdout.strip().split("\n")
            for line in lines:
                if line.strip():
                    try:
                        container_info = json.loads(line)
                        state = container_info.get("State", "").lower()
                        health = container_info.get("Health", "").lower()

                        # Service is healthy if running and either no health check or healthy
                        if state == "running":
                            if not health or health in ["", "healthy"]:
                                return True

                    except json.JSONDecodeError:
                        continue

            return False

        except Exception:
            return False

    async def get_service_logs(self, service: str, lines: int = 50) -> str:
        """Get logs for a specific service."""
        try:
            stdout, stderr, returncode = await self._run_compose_command(
                ["logs", "--tail", str(lines), service], check=False
            )
            return stdout
        except Exception as e:
            return f"Failed to get logs: {e}"

    async def _cleanup_existing_containers(self):
        """Remove any existing containers that might conflict with our service names."""
        # Container names that might conflict
        container_names = [
            "dsl-redis-dev",
            "dsl-mcp-server-dev",
            "dsl-fastapi-1-dev",
            "dsl-fastapi-2-dev",
            "dsl-celery-1-dev",
            "dsl-celery-2-dev",
            "dsl-celery-3-dev",
            "dsl-celery-4-dev",
            "dsl-browsers-dev",
            "dsl-nginx-dev",
        ]

        for container_name in container_names:
            try:
                # Stop and remove container if it exists
                proc = await asyncio.create_subprocess_exec(
                    "docker",
                    "rm",
                    "-f",
                    container_name,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                await proc.communicate()
                # Ignore errors - container might not exist
            except Exception:
                pass  # Ignore errors

        print("🧹 Cleaned up potentially conflicting containers")


class E2ESSEClient:
    """Enhanced SSE client for E2E testing."""

    def __init__(self, base_url: str = "http://localhost"):
        self.base_url = base_url
        self.client = None
        self.connection_id = None

    async def connect(self, client_id: str = "e2e-test-client", api_key: str = "test-api-key-123"):
        """Connect to SSE endpoint."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url, timeout=httpx.Timeout(30.0, read=None)
        )

        headers = {"Accept": "text/event-stream", "Cache-Control": "no-cache", "X-API-Key": api_key}

        params = {"client_id": client_id}

        # Use streaming request for SSE connection
        request = self.client.build_request("GET", "/sse/connect", headers=headers, params=params)
        response = await self.client.send(request, stream=True)

        # Check status without reading body
        if response.status_code != 200:
            await response.aclose()
            raise httpx.HTTPStatusError(
                f"SSE connection failed with status {response.status_code}",
                request=request,
                response=response,
            )

        self.connection_id = response.headers.get("X-Connection-ID") or response.headers.get(
            "x-connection-id"
        )
        return response

    async def submit_render_request(self, dsl_content: str, options: Dict[str, Any] = None):
        """Submit a render request via SSE."""
        if not self.client or not self.connection_id:
            raise RuntimeError("Must connect first")

        if options is None:
            options = {
                "width": 800,
                "height": 600,
                "device_scale_factor": 1.0,
                "optimize_png": True,
                "timeout": 30,
            }

        payload = {
            "dsl_content": dsl_content,
            "options": options,
            "connection_id": self.connection_id,
            "request_id": f"e2e-test-{int(time.time())}",
            "progress_updates": True,
        }

        headers = {"Content-Type": "application/json", "X-API-Key": "test-api-key-123"}

        # Use fire-and-forget pattern like original script
        asyncio.create_task(self._send_render_request(payload, headers))

    async def _send_render_request(self, payload: Dict[str, Any], headers: Dict[str, str]):
        """Send render request in background."""
        try:
            async with httpx.AsyncClient(base_url=self.base_url, timeout=30.0) as client:
                response = await client.post("/sse/render", json=payload, headers=headers)
                response.raise_for_status()
        except Exception as e:
            print(f"Background render request failed: {e}")

    async def parse_events(self, response, timeout: int = 60):
        """Parse SSE events from response stream."""
        events = []
        start_time = time.time()
        buffer = ""

        async for data in response.aiter_bytes(1024):
            if time.time() - start_time > timeout:
                break

            buffer += data.decode("utf-8")

            while "\n\n" in buffer:
                event_data, buffer = buffer.split("\n\n", 1)

                if event_data.strip():
                    event = self._parse_event(event_data)
                    events.append(event)
                    yield event

                    # Break on completion or error
                    event_type = event.get("event")
                    if event_type in ["render.completed", "render.failed", "connection.error"]:
                        return

    def _parse_event(self, event_data: str) -> Dict[str, Any]:
        """Parse a single SSE event."""
        event = {"id": None, "event": None, "data": None, "retry": None}

        for line in event_data.split("\n"):
            if ":" in line:
                field, value = line.split(":", 1)
                field = field.strip()
                value = value.strip()

                if field in event:
                    event[field] = value

        # Parse JSON data if present
        if event["data"]:
            try:
                event["data"] = json.loads(event["data"])
            except json.JSONDecodeError:
                pass

        return event

    async def close(self):
        """Close SSE client."""
        if self.client:
            await self.client.aclose()
            self.client = None
            self.connection_id = None


class E2EEnvironmentManager:
    """Main manager for E2E test environment."""

    def __init__(self):
        self.docker_manager = DockerComposeManager()
        self.sse_client = None

    async def start_environment(self):
        """Start the complete E2E environment."""
        await self.docker_manager.start_environment()

    async def stop_environment(self):
        """Stop the E2E environment."""
        if self.sse_client:
            await self.sse_client.close()
        await self.docker_manager.stop_environment()

    async def get_sse_client(self) -> E2ESSEClient:
        """Get configured SSE client."""
        if not self.sse_client:
            self.sse_client = E2ESSEClient("http://localhost")
        return self.sse_client


# =============================================================================
# PYTEST FIXTURES
# =============================================================================


@pytest_asyncio.fixture(scope="session")
async def e2e_environment() -> AsyncGenerator[E2EEnvironmentManager, None]:
    """Session-scoped E2E environment manager."""
    manager = E2EEnvironmentManager()

    try:
        await manager.start_environment()
        yield manager
    finally:
        await manager.stop_environment()


@pytest_asyncio.fixture(scope="session")
async def e2e_docker_manager(e2e_environment: E2EEnvironmentManager) -> DockerComposeManager:
    """Docker Compose manager for E2E tests."""
    return e2e_environment.docker_manager


@pytest_asyncio.fixture
async def e2e_sse_client(
    e2e_environment: E2EEnvironmentManager,
) -> AsyncGenerator[E2ESSEClient, None]:
    """SSE client for E2E testing."""
    client = await e2e_environment.get_sse_client()
    yield client
    # Client cleanup handled by environment manager


@pytest.fixture
def e2e_dsl_examples() -> Dict[str, str]:
    """Load real DSL examples for E2E testing."""
    examples = {}
    examples_dir = Path("examples")

    if examples_dir.exists():
        for file_path in examples_dir.glob("*.json"):
            examples[file_path.stem] = file_path.read_text()
        for file_path in examples_dir.glob("*.yaml"):
            examples[file_path.stem] = file_path.read_text()

    return examples


@pytest.fixture
def e2e_render_options() -> Dict[str, Any]:
    """Default render options for E2E testing."""
    return {
        "width": 800,
        "height": 600,
        "device_scale_factor": 1.0,
        "wait_for_load": True,
        "optimize_png": False,  # Faster for testing
        "timeout": 30,
    }


@pytest.fixture
def e2e_test_timeout() -> int:
    """Timeout for E2E tests in seconds."""
    return 90


@pytest_asyncio.fixture
async def e2e_test_results_dir() -> AsyncGenerator[Path, None]:
    """Test results directory for E2E tests."""
    results_dir = Path("test-results")
    results_dir.mkdir(exist_ok=True)

    yield results_dir

    # Cleanup - optionally preserve results for debugging
    # results_dir cleanup can be disabled for debugging


@pytest_asyncio.fixture
async def e2e_cleanup():
    """Cleanup fixture for E2E tests."""
    # Setup
    yield

    # Cleanup - remove any test files created during E2E tests
    test_storage = Path("test_storage")
    if test_storage.exists():
        import shutil

        shutil.rmtree(test_storage, ignore_errors=True)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================


def save_png_result(png_data: str, filename: str, results_dir: Path) -> Path:
    """Save PNG data to file in results directory."""
    filepath = results_dir / filename

    # Decode base64 if needed
    if isinstance(png_data, str):
        try:
            png_bytes = base64.b64decode(png_data)
        except Exception:
            png_bytes = png_data.encode()
    else:
        png_bytes = png_data

    with open(filepath, "wb") as f:
        f.write(png_bytes)

    return filepath


def validate_sse_event(event: Dict[str, Any], expected_type: str) -> bool:
    """Validate an SSE event structure."""
    if not isinstance(event, dict):
        return False

    if event.get("event") != expected_type:
        return False

    if "data" not in event:
        return False

    return True


async def wait_for_render_completion(
    sse_client: E2ESSEClient, response, timeout: int = 60
) -> Dict[str, Any]:
    """Wait for render completion and return the final event."""
    async for event in sse_client.parse_events(response, timeout=timeout):
        event_type = event.get("event")

        if event_type == "render.completed":
            return event
        elif event_type == "render.failed":
            data = event.get("data", {})
            error = data.get("error", "Unknown render error")
            raise RuntimeError(f"Render failed: {error}")
        elif event_type == "connection.error":
            data = event.get("data", {})
            error = data.get("error_message", "Unknown connection error")
            raise RuntimeError(f"Connection error: {error}")

    raise TimeoutError(f"Render did not complete within {timeout} seconds")


# =============================================================================
# E2E-SPECIFIC MARKER CONFIGURATION
# =============================================================================


def pytest_configure(config):
    """Configure E2E-specific pytest settings."""
    # Register E2E markers to avoid warnings
    config.addinivalue_line("markers", "e2e: End-to-end tests")
    config.addinivalue_line("markers", "e2e_sse: SSE-specific end-to-end tests")
    config.addinivalue_line("markers", "e2e_pipeline: Complete pipeline end-to-end tests")
    config.addinivalue_line("markers", "slow: Tests that take a long time to run")
    config.addinivalue_line("markers", "smoke: Quick smoke tests for basic functionality")


def pytest_collection_modifyitems(config, items):
    """Auto-mark E2E tests."""
    for item in items:
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
            item.add_marker(pytest.mark.slow)

            # Add specific markers based on test name
            if "sse" in item.name.lower():
                item.add_marker(pytest.mark.e2e_sse)
            if "pipeline" in item.name.lower():
                item.add_marker(pytest.mark.e2e_pipeline)
