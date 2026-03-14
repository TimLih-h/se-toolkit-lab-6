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


def test_agent_uses_list_files_tool() -> None:
    """Test that agent.py uses list_files tool for wiki directory questions.

    This test verifies that when asked about wiki files, the agent
    uses the list_files tool and populates tool_calls correctly.
    """
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"

    # Run agent.py asking about wiki files
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(agent_path),
            "What files are in the wiki directory?",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout}") from e

    # Verify required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"
    assert isinstance(output["tool_calls"], list), "'tool_calls' must be an array"

    # Verify list_files was used
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0, "Expected at least one tool call"

    tool_names = [tc.get("tool") for tc in tool_calls]
    assert "list_files" in tool_names, f"Expected list_files tool, got: {tool_names}"

    # Verify the tool call has correct structure
    list_files_call = next(tc for tc in tool_calls if tc.get("tool") == "list_files")
    assert "args" in list_files_call, "list_files missing 'args'"
    assert "result" in list_files_call, "list_files missing 'result'"
    assert list_files_call["args"].get("path") == "wiki", "list_files should be called with path='wiki'"


def test_agent_uses_read_file_for_merge_conflict() -> None:
    """Test that agent.py uses read_file tool for merge conflict questions.

    This test verifies that when asked about merge conflicts, the agent
    uses the read_file tool and includes a source reference.
    """
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"

    # Run agent.py asking about merge conflicts
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(agent_path),
            "How do you resolve a merge conflict?",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout}") from e

    # Verify required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "source" in output, "Missing 'source' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"

    # Verify answer is non-empty
    assert len(output["answer"].strip()) > 0, "'answer' must be non-empty"

    # Verify tool_calls is populated
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0, "Expected at least one tool call"

    # Verify read_file was used
    tool_names = [tc.get("tool") for tc in tool_calls]
    assert "read_file" in tool_names, f"Expected read_file tool, got: {tool_names}"

    # Verify source contains wiki path
    source = output["source"]
    assert isinstance(source, str), "'source' must be a string"
    assert "wiki/" in source, f"Source should reference wiki/, got: {source}"


def test_agent_uses_query_api_for_item_count() -> None:
    """Test that agent.py uses query_api tool for database count questions.

    This test verifies that when asked about item count, the agent
    uses the query_api tool.
    """
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"

    # Run agent.py asking about item count
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(agent_path),
            "How many items are currently stored in the database?",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout}") from e

    # Verify required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"

    # Verify tool_calls is populated with query_api
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0, "Expected at least one tool call"

    tool_names = [tc.get("tool") for tc in tool_calls]
    assert "query_api" in tool_names, f"Expected query_api tool, got: {tool_names}"

    # Verify the answer contains a number
    answer = output["answer"]
    import re
    numbers = re.findall(r'\d+', answer)
    assert len(numbers) > 0, "Answer should contain a number for item count"


def test_agent_uses_query_api_for_status_code() -> None:
    """Test that agent.py uses query_api tool for HTTP status code questions.

    This test verifies that when asked about status codes, the agent
    uses the query_api tool and reports the status code.
    """
    # Get the project root directory
    project_root = Path(__file__).parent.parent.parent.parent
    agent_path = project_root / "agent.py"

    # Run agent.py asking about status code
    result = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(agent_path),
            "What HTTP status code does the API return when you request /items/ without authentication?",
        ],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=120,
    )

    # Check exit code
    assert result.returncode == 0, f"Agent failed: {result.stderr}"

    # Parse stdout as JSON
    try:
        output = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise AssertionError(f"Agent output is not valid JSON: {result.stdout}") from e

    # Verify required fields
    assert "answer" in output, "Missing 'answer' field"
    assert "tool_calls" in output, "Missing 'tool_calls' field"

    # Verify query_api was used
    tool_calls = output["tool_calls"]
    assert len(tool_calls) > 0, "Expected at least one tool call"

    tool_names = [tc.get("tool") for tc in tool_calls]
    assert "query_api" in tool_names, f"Expected query_api tool, got: {tool_names}"

    # Verify the answer mentions a status code (401, 403, or 200)
    answer = output["answer"].lower()
    assert any(code in answer for code in ["401", "403", "200", "status"]), \
        f"Answer should mention a status code, got: {answer[:200]}"
