#!/usr/bin/env python3
"""
E2E Test Runner Script
=====================

Test runner script to validate the new E2E pytest implementation.
This script activates the virtual environment and runs the E2E tests
as specified in the .roorules requirements.

Usage:
    python test_e2e_runner.py [--smoke-only] [--verbose]
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path
from typing import List


def activate_venv_and_run(
    cmd_args: List[str], verbose: bool = False
) -> subprocess.CompletedProcess:
    """Activate virtual environment and run command."""
    # Activate virtual environment as required by .roorules
    venv_activate = ". venv/bin/activate"

    # Build full command
    full_cmd = f"{venv_activate} && {' '.join(cmd_args)}"

    if verbose:
        print(f"🔧 Running command: {full_cmd}")

    # Execute with shell to handle activation
    result = subprocess.run(full_cmd, shell=True, capture_output=not verbose, text=True)

    return result


def main():
    """Main test runner."""
    parser = argparse.ArgumentParser(description="E2E Test Runner")
    parser.add_argument("--smoke-only", action="store_true", help="Run only smoke tests")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument("--specific-test", help="Run specific test file or test function")

    args = parser.parse_args()

    # Verify we're in the correct directory
    if not Path("docker-compose.yaml").exists():
        print("❌ Error: Must run from project root directory")
        sys.exit(1)

    if not Path("venv").exists():
        print("❌ Error: Virtual environment not found. Please create venv first.")
        sys.exit(1)

    # Build pytest command
    pytest_cmd = ["pytest"]

    if args.verbose:
        pytest_cmd.extend(["-v", "-s"])

    if args.smoke_only:
        pytest_cmd.extend(["-m", "smoke", "tests/e2e/"])
        print("🧪 Running E2E smoke tests...")
    elif args.specific_test:
        pytest_cmd.append(args.specific_test)
        print(f"🧪 Running specific test: {args.specific_test}")
    else:
        pytest_cmd.extend(["tests/e2e/"])
        print("🧪 Running all E2E tests...")

    # Add pytest options for better output
    pytest_cmd.extend(["--tb=short", "--maxfail=1", "-x"])  # Stop on first failure for E2E tests

    print("=" * 60)
    print("E2E Test Execution")
    print("=" * 60)
    print(f"Command: {' '.join(pytest_cmd)}")
    print(f"Verbose: {args.verbose}")
    print(f"Smoke only: {args.smoke_only}")
    print("=" * 60)

    # Run the tests
    result = activate_venv_and_run(pytest_cmd, verbose=args.verbose)

    if result.returncode == 0:
        print("\n✅ E2E tests completed successfully!")
    else:
        print(f"\n❌ E2E tests failed with return code: {result.returncode}")
        if not args.verbose and result.stdout:
            print("STDOUT:")
            print(result.stdout)
        if not args.verbose and result.stderr:
            print("STDERR:")
            print(result.stderr)

    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
