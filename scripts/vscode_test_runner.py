#!/usr/bin/env python3
"""
VS Code Test Runner for DSL to PNG MCP Project
==============================================

This script acts as a smart test runner that routes different test types
according to the project's two-tier testing approach:

- Unit/Integration tests: Run via Docker Compose (requires services)
- E2E tests: Run locally with venv (manage their own services)

This allows VS Code's test integration to work seamlessly while respecting
the project's testing architecture.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import List, Set, Optional


# Add src to Python path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# Test categorization
E2E_TEST_PATTERNS = {"tests/e2e/", "test_e2e_", "_e2e_test", "e2e_test"}

DOCKER_TEST_PATTERNS = {
    "tests/unit/",
    "tests/integration/",
    "tests/security/",
    "tests/api/",
    "tests/core/",
    "tests/models/",
    "tests/utils/",
    "test_unit_",
    "test_integration_",
    "test_security_",
    "test_api_",
}


def is_e2e_test(test_path: str) -> bool:
    """Check if a test should be run as E2E (locally)."""
    test_path_lower = test_path.lower()
    return any(pattern in test_path_lower for pattern in E2E_TEST_PATTERNS)


def is_docker_test(test_path: str) -> bool:
    """Check if a test should be run via Docker Compose."""
    test_path_lower = test_path.lower()
    return any(pattern in test_path_lower for pattern in DOCKER_TEST_PATTERNS)


def categorize_tests(test_args: List[str]) -> tuple[List[str], List[str]]:
    """
    Categorize test arguments into E2E and Docker tests.

    Returns:
        tuple: (e2e_tests, docker_tests)
    """
    e2e_tests = []
    docker_tests = []

    for arg in test_args:
        if arg.startswith("-"):
            # Skip pytest options
            continue
        if not arg.endswith(".py") and "::" not in arg and not os.path.exists(arg):
            # Skip non-file arguments that aren't test paths
            continue

        if is_e2e_test(arg):
            e2e_tests.append(arg)
        elif is_docker_test(arg):
            docker_tests.append(arg)
        else:
            # Default to Docker for unknown tests (safer for dependencies)
            docker_tests.append(arg)

    return e2e_tests, docker_tests


def run_e2e_tests(test_args: List[str], pytest_args: List[str]) -> int:
    """Run E2E tests locally with venv activation."""
    print("🚀 Running E2E tests locally...")

    # Ensure virtual environment is activated
    venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
    if not venv_python.exists():
        print("❌ Virtual environment not found. Run setup scripts first.")
        return 1

    cmd = [str(venv_python), "-m", "pytest"] + pytest_args + test_args

    print(f"📋 Command: {' '.join(cmd)}")
    print("📂 Working directory:", PROJECT_ROOT)

    try:
        result = subprocess.run(
            cmd,
            cwd=PROJECT_ROOT,
            env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
            text=True,
        )
        return result.returncode
    except Exception as e:
        print(f"❌ Error running E2E tests: {e}")
        return 1


def run_docker_tests(test_args: List[str], pytest_args: List[str]) -> int:
    """Run unit/integration tests via Docker Compose."""
    print("🐳 Running unit/integration tests via Docker Compose...")

    # Check if Docker Compose is available
    try:
        subprocess.run(["docker", "compose", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("❌ Docker Compose not available. Falling back to local execution.")
        return run_e2e_tests(test_args, pytest_args)

    # Prepare Docker Compose command
    compose_file = PROJECT_ROOT / "docker" / "docker-compose.test.yml"
    if not compose_file.exists():
        print("❌ Docker Compose test file not found. Falling back to local execution.")
        return run_e2e_tests(test_args, pytest_args)

    # Build the Docker Compose command
    # We'll run pytest inside the container with the specified test files
    test_command = ["python", "-m", "pytest"] + pytest_args + test_args

    cmd = ["docker", "compose", "-f", str(compose_file), "run", "--rm", "test", *test_command]

    print(f"📋 Command: {' '.join(cmd)}")
    print("📂 Working directory:", PROJECT_ROOT)

    try:
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True)
        return result.returncode
    except Exception as e:
        print(f"❌ Error running Docker tests: {e}")
        print("🔄 Falling back to local execution...")
        return run_e2e_tests(test_args, pytest_args)


def run_mixed_tests(e2e_tests: List[str], docker_tests: List[str], pytest_args: List[str]) -> int:
    """Run both E2E and Docker tests, combining results."""
    print("🔀 Running mixed test types...")

    results = []

    if docker_tests:
        print("\n" + "=" * 50)
        print("🐳 Running Docker-based tests first...")
        print("=" * 50)
        docker_result = run_docker_tests(docker_tests, pytest_args)
        results.append(docker_result)

    if e2e_tests:
        print("\n" + "=" * 50)
        print("🚀 Running E2E tests...")
        print("=" * 50)
        e2e_result = run_e2e_tests(e2e_tests, pytest_args)
        results.append(e2e_result)

    # Return non-zero if any tests failed
    return max(results) if results else 0


def main():
    """Main entry point for the VS Code test runner."""
    parser = argparse.ArgumentParser(description="Smart test runner for DSL to PNG MCP")
    parser.add_argument("tests", nargs="*", help="Test files or directories to run")
    parser.add_argument(
        "--collect-only", action="store_true", help="Only collect tests, don't run them"
    )
    parser.add_argument("--discovery", action="store_true", help="Run in discovery mode")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--tb", default="short", help="Traceback style")
    parser.add_argument("--no-cov", action="store_true", help="Disable coverage")

    # Parse known args to handle pytest-specific options
    args, unknown_args = parser.parse_known_args()

    # Combine all test-related arguments
    all_test_args = args.tests + unknown_args

    # Standard pytest arguments for VS Code integration
    pytest_args = []
    if args.collect_only:
        pytest_args.append("--collect-only")
    if args.verbose:
        pytest_args.append("-v")
    if args.no_cov:
        pytest_args.append("--no-cov")
    if args.tb:
        pytest_args.extend(["--tb", args.tb])

    # Special handling for discovery mode
    if args.discovery or args.collect_only:
        print("🔍 Running in discovery mode...")
        # For discovery, we run locally to avoid Docker overhead
        venv_python = PROJECT_ROOT / "venv" / "bin" / "python"
        if venv_python.exists():
            cmd = [str(venv_python), "-m", "pytest"] + pytest_args + all_test_args
        else:
            cmd = ["python", "-m", "pytest"] + pytest_args + all_test_args

        try:
            result = subprocess.run(
                cmd,
                cwd=PROJECT_ROOT,
                env={**os.environ, "PYTHONPATH": str(PROJECT_ROOT / "src")},
                text=True,
            )
            return result.returncode
        except Exception as e:
            print(f"❌ Error in discovery mode: {e}")
            return 1

    # Filter out pytest options from test categorization
    test_files = [arg for arg in all_test_args if not arg.startswith("-")]

    # If no specific test files given, discover all tests
    if not test_files:
        test_files = ["tests/"]

    print(f"🎯 Test runner starting...")
    print(f"📁 Project root: {PROJECT_ROOT}")
    print(f"🧪 Test files: {test_files}")

    # Categorize tests
    e2e_tests, docker_tests = categorize_tests(test_files)

    print(f"🚀 E2E tests: {e2e_tests}")
    print(f"🐳 Docker tests: {docker_tests}")

    # Run appropriate test strategy
    if e2e_tests and docker_tests:
        return run_mixed_tests(e2e_tests, docker_tests, pytest_args)
    elif e2e_tests:
        return run_e2e_tests(e2e_tests, pytest_args)
    elif docker_tests:
        return run_docker_tests(docker_tests, pytest_args)
    else:
        print("⚠️  No tests to run")
        return 0


if __name__ == "__main__":
    sys.exit(main())
