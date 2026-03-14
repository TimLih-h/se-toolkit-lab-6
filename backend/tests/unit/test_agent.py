"""Regression tests for agent.py."""

import json
import subprocess
from pathlib import Path


def test_agent_outputs_valid_json() -> None:
    """Test that agent.py outputs valid JSON with required fields.
    
    This test runs agent.py as a subprocess with a simple question,
    parses the stdout as JSON, and verifies that:
    - The output is valid JSON
    - The 'answer' field exists and is non-empty
    - The 'tool_calls' field exists and is an array
    """
    # Get the project root directory (backend/tests/unit -> backend -> project root)
    project_root = Path(__file__).parent.parent.parent.parent
    
    # Path to agent.py in project root
    agent_path = project_root / "agent.py"
    
    # Run agent.py with a simple question using uv from PATH
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(agent_path),
            "What is 2+2? Answer with just the number.",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=60,
    )
    
    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"
    
    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout}") from e
    
    # Verify 'answer' field exists and is non-empty
    assert "answer" in output, "Missing 'answer' field in output"
    assert isinstance(output["answer"], str), "'answer' must be a string"
    assert len(output["answer"].strip()) > 0, "'answer' must be non-empty"
    
    # Verify 'tool_calls' field exists and is an array
    assert "tool_calls" in output, "Missing 'tool_calls' field in output"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"
