#!/usr/bin/env python3
"""
Run Isolation Tests with Development Browser Infrastructure
==========================================================

This script runs the existing isolation tests from the host, but leverages
the Playwright browser service from the development infrastructure.

Key Points:
- STILL BYPASSES: nginx, redis, fastapi (pure isolation testing)
- USES: Only the browser service for PNG generation (if needed)
- RUNS: All existing isolation scripts from the host environment

Prerequisites:
1. Run: docker compose up -d (only for browser service access)
2. Install Python dependencies on host
3. Run this script from the host

The isolation tests will:
✅ Mock Redis, FastAPI, infrastructure
✅ Test components in complete isolation
✅ Use development browsers only for PNG generation
❌ NOT use real Redis/FastAPI/nginx (that's integration testing)
"""

import asyncio
import sys
import os
import subprocess
from pathlib import Path

# Add src to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))


def setup_isolation_environment():
    """Configure environment for isolation testing with dev browser access."""
    os.environ.update(
        {
            "DSL_PNG_ENVIRONMENT": "isolation_testing",
            "DSL_PNG_DEBUG": "true",
            "DSL_PNG_LOG_LEVEL": "DEBUG",
            # Browser access through development infrastructure
            "DSL_PNG_PLAYWRIGHT_HEADLESS": "true",
            "PLAYWRIGHT_BROWSERS_PATH": "/ms-playwright",  # If available
            # Mock/isolation settings - bypass all infrastructure
            "DSL_PNG_REDIS_URL": "mock://localhost:6379/0",  # Signals mocking
            "DSL_PNG_MCP_HOST": "mock",  # Signals mocking
            "DSL_PNG_USE_MOCK_INFRASTRUCTURE": "true",
        }
    )


def print_header(title: str, char: str = "=", width: int = 60):
    """Print a formatted header."""
    print(f"\n{char * width}")
    print(f"{title:^{width}}")
    print(f"{char * width}")


def print_step(step: str, status: str = "INFO"):
    """Print a step with status."""
    status_symbols = {"INFO": "ℹ️", "PASS": "✅", "FAIL": "❌", "WARN": "⚠️"}
    symbol = status_symbols.get(status, "📝")
    print(f"{symbol} {step}")


def check_browser_service():
    """Check if the browser service from development infrastructure is available."""
    try:
        result = subprocess.run(
            [
                "docker",
                "ps",
                "--filter",
                "name=dsl-browsers-dev",
                "--filter",
                "status=running",
                "-q",
            ],
            capture_output=True,
            text=True,
        )

        if result.stdout.strip():
            print_step("Browser service is running (for PNG generation)", "PASS")
            return True
        else:
            print_step("Browser service not running (PNG tests may fail)", "WARN")
            print_step("Run 'docker compose up -d' to start browser service", "INFO")
            return False

    except Exception as e:
        print_step(f"Cannot check browser service: {e}", "WARN")
        return False


def run_isolation_script(script_name: str):
    """Run an individual isolation test script."""
    script_path = project_root / "debug_scripts" / script_name

    if not script_path.exists():
        print_step(f"Script not found: {script_name}", "FAIL")
        return False

    try:
        print_step(f"Running {script_name}...", "INFO")

        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(project_root),
            capture_output=True,
            text=True,
        )

        print("=" * 50)
        print(f"OUTPUT FROM {script_name}:")
        print("=" * 50)
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        if result.returncode == 0:
            print_step(f"{script_name} completed successfully", "PASS")
            return True
        else:
            print_step(f"{script_name} failed with exit code {result.returncode}", "FAIL")
            return False

    except Exception as e:
        print_step(f"Failed to run {script_name}: {e}", "FAIL")
        return False


def main():
    """Main execution."""
    print_header("🧪 Isolation Testing with Development Browser Access", "=", 70)
    print_step("Running ISOLATION tests (bypassing nginx/redis/fastapi)", "INFO")
    print_step("Using development browser service only for PNG generation", "INFO")

    # Setup isolation environment
    setup_isolation_environment()
    print_step("Environment configured for isolation testing", "PASS")

    # Check browser service availability
    check_browser_service()

    # Define isolation test scripts in order of complexity
    isolation_scripts = [
        "test_component_isolation.py",  # Basic component tests
        "test_mcp_tool_direct.py",  # MCP tool isolation
        "test_sse_server_direct.py",  # SSE server isolation
        "test_sse_mock_infrastructure.py",  # Full mock infrastructure
    ]

    print_header("🔬 Running Isolation Test Scripts")

    results = {}

    for script in isolation_scripts:
        print_header(f"Running {script}", "-", 50)
        result = run_isolation_script(script)
        results[script] = result

    # Summary
    print_header("📊 Isolation Test Results Summary")

    passed = sum(results.values())
    total = len(results)

    for script, result in results.items():
        status = "PASS" if result else "FAIL"
        print_step(f"{script}: {status}", status)

    print_step(f"Tests passed: {passed}/{total}", "INFO")

    if passed == total:
        print_step("All isolation tests passed!", "PASS")
    else:
        print_step("Some isolation tests failed.", "FAIL")
        print_step("Check individual test output above for details.", "INFO")

    print_header("🎯 Isolation Testing Analysis")
    print("These tests isolate components by:")
    print("✅ Mocking Redis, FastAPI, nginx infrastructure")
    print("✅ Testing components in complete isolation")
    print("✅ Using only development browsers for PNG generation")
    print("✅ Bypassing all HTTP/networking layers")
    print()
    print("If NoneType errors are reproduced here, the issue is in:")
    print("• Core component logic (not infrastructure)")
    print("• DSL parsing/processing pipeline")
    print("• MCP tool implementation")
    print("• SSE server internal logic")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print_step("Testing interrupted by user", "WARN")
    except Exception as e:
        print_step(f"Test execution failed: {e}", "FAIL")
        import traceback

        print(f"Traceback: {traceback.format_exc()}")
