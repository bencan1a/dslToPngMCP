#!/usr/bin/env python3
"""
VS Code pytest wrapper
======================

This script is specifically designed to work with VS Code's Python test discovery.
It acts as a drop-in replacement for pytest while intelligently routing tests.
"""

import sys
import os
from pathlib import Path

# Add the actual test runner to the path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Import and run the main test runner
from scripts.vscode_test_runner import main

if __name__ == "__main__":
    sys.exit(main())
