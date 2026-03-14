"""Regression tests for agent.py — Task 1.

This test file is placed in the project root for easy discovery by autocheckers.
It imports the actual tests from backend/tests/unit/test_agent.py.
"""

# Import tests from the main test file
# The actual test implementation is in backend/tests/unit/test_agent.py
# This file exists for autochecker compatibility

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

# Import and re-export the test
from tests.unit.test_agent import test_agent_outputs_valid_json

# Make the test available at this level
__all__ = ["test_agent_outputs_valid_json"]
