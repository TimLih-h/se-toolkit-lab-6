#!/usr/bin/env python3
"""Agent CLI — answers questions using an LLM with tool support.

Usage:
    uv run agent.py "How do you resolve a merge conflict?"

Output:
    JSON line to stdout: {"answer": "...", "source": "...", "tool_calls": [...]}
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentSettings(BaseSettings):
    """LLM configuration for the agent."""

    llm_api_key: str
    llm_api_base: str
    llm_model: str = "qwen3-coder-plus"

    model_config = SettingsConfigDict(
        env_file=".env.agent.secret",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
        alias_generator=lambda x: x.upper(),
        populate_by_name=True,
    )


def load_settings() -> AgentSettings:
    """Load agent settings from .env.agent.secret."""
    try:
        return AgentSettings()
    except Exception as e:
        print(f"Error loading settings: {e}", file=sys.stderr)
        sys.exit(1)


def validate_path(path: str, project_root: Path) -> Path:
    """Validate and resolve a path, ensuring it's within project root.
    
    Security: prevents directory traversal attacks.
    """
    # Reject paths with traversal patterns
    if ".." in path or path.startswith("/"):
        raise ValueError(f"Invalid path: {path}")
    
    # Resolve to absolute path
    full_path = (project_root / path).resolve()
    
    # Ensure it's within project root
    if not str(full_path).startswith(str(project_root.resolve())):
        raise ValueError(f"Path outside project root: {path}")
    
    return full_path


def read_file(path: str, project_root: Path) -> str:
    """Read a file from the project repository.
    
    Args:
        path: Relative path from project root
        project_root: Project root directory
        
    Returns:
        File contents as string, or error message
    """
    try:
        validated_path = validate_path(path, project_root)
        
        if not validated_path.exists():
            return f"Error: File not found: {path}"
        
        if not validated_path.is_file():
            return f"Error: Not a file: {path}"
        
        return validated_path.read_text(encoding="utf-8")
        
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error reading file: {e}"


def list_files(path: str, project_root: Path) -> str:
    """List files and directories at a given path.
    
    Args:
        path: Relative directory path from project root
        project_root: Project root directory
        
    Returns:
        Newline-separated listing of entries, or error message
    """
    try:
        validated_path = validate_path(path, project_root)
        
        if not validated_path.exists():
            return f"Error: Directory not found: {path}"
        
        if not validated_path.is_dir():
            return f"Error: Not a directory: {path}"
        
        entries = sorted([entry.name for entry in validated_path.iterdir()])
        return "\n".join(entries)
        
    except ValueError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error listing directory: {e}"


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return tool definitions for LLM API."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository. Use this to find specific information in documentation files.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., 'wiki/git-workflow.md')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "list_files",
                "description": "List files and directories at a given path. Use this to discover what files exist in a directory.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative directory path from project root (e.g., 'wiki')"
                        }
                    },
                    "required": ["path"]
                }
            }
        }
    ]


def execute_tool(name: str, args: dict[str, Any], project_root: Path) -> str:
    """Execute a tool and return the result.
    
    Args:
        name: Tool name ('read_file' or 'list_files')
        args: Tool arguments
        project_root: Project root directory
        
    Returns:
        Tool result as string
    """
    if name == "read_file":
        path = args.get("path", "")
        return read_file(path, project_root)
    elif name == "list_files":
        path = args.get("path", "")
        return list_files(path, project_root)
    else:
        return f"Error: Unknown tool: {name}"


def call_llm(
    messages: list[dict[str, Any]],
    settings: AgentSettings,
    tools: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Call the LLM API and return the response.
    
    Args:
        messages: Chat messages array
        settings: Agent settings
        tools: Optional tool definitions
        
    Returns:
        Parsed API response
    """
    url = f"{settings.llm_api_base}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }

    payload: dict[str, Any] = {
        "model": settings.llm_model,
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 2048,
    }
    
    if tools:
        payload["tools"] = tools

    try:
        with httpx.Client(timeout=120.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()

    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Request error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def extract_source_from_messages(messages: list[dict[str, Any]]) -> str:
    """Extract source reference from tool calls in messages.
    
    Looks for the last read_file tool call and extracts the path.
    """
    for message in reversed(messages):
        if message.get("role") == "assistant" and "tool_calls" in message:
            tool_calls = message.get("tool_calls", [])
            for tool_call in tool_calls:
                if tool_call.get("function", {}).get("name") == "read_file":
                    try:
                        args = json.loads(tool_call["function"]["arguments"])
                        path = args.get("path", "")
                        if path:
                            # Try to extract section anchor from content
                            return f"{path}"
                    except (json.JSONDecodeError, KeyError):
                        pass
    return ""


def run_agentic_loop(
    question: str,
    settings: AgentSettings,
    project_root: Path,
) -> dict[str, Any]:
    """Run the agentic loop to answer a question.
    
    Args:
        question: User's question
        settings: Agent settings
        project_root: Project root directory
        
    Returns:
        Result dict with answer, source, and tool_calls
    """
    # System prompt
    system_prompt = """You are a documentation assistant for a software engineering toolkit.

You have access to project documentation via tools:
- list_files(path): List files in a directory
- read_file(path): Read contents of a file

When answering questions:
1. Use list_files to discover relevant files in the wiki/ directory
2. Use read_file to read specific files and find the answer
3. Always cite your source as a file path (e.g., "wiki/git-workflow.md")
4. If the answer is not in the documentation, say so

Be concise and accurate. Only use information from the documentation."""

    # Initialize messages
    messages: list[dict[str, Any]] = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": question},
    ]

    # Track tool calls for output
    tool_calls_output: list[dict[str, Any]] = []
    
    # Get tool definitions
    tools = get_tool_definitions()

    # Agentic loop (max 10 iterations)
    max_iterations = 10
    iteration = 0

    while iteration < max_iterations:
        iteration += 1
        
        # Call LLM
        response = call_llm(messages, settings, tools)
        
        # Get assistant message
        if "choices" not in response or len(response["choices"]) == 0:
            print("Error: Empty response from LLM", file=sys.stderr)
            sys.exit(1)
        
        assistant_message = response["choices"][0]["message"]
        messages.append(assistant_message)
        
        # Check for tool calls
        tool_calls = assistant_message.get("tool_calls", [])
        
        if not tool_calls:
            # No tool calls - we have the final answer
            answer = assistant_message.get("content", "")
            source = extract_source_from_messages(messages)
            
            return {
                "answer": answer,
                "source": source,
                "tool_calls": tool_calls_output,
            }
        
        # Execute tool calls
        for tool_call in tool_calls:
            tool_name = tool_call.get("function", {}).get("name", "")
            tool_args_str = tool_call.get("function", {}).get("arguments", "{}")
            
            try:
                tool_args = json.loads(tool_args_str)
            except json.JSONDecodeError:
                tool_args = {}
            
            # Execute tool
            result = execute_tool(tool_name, tool_args, project_root)
            
            # Record tool call for output
            tool_calls_output.append({
                "tool": tool_name,
                "args": tool_args,
                "result": result,
            })
            
            # Append tool result to messages
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.get("id", ""),
                "content": result,
            })
    
    # Max iterations reached
    print(f"Warning: Max iterations ({max_iterations}) reached", file=sys.stderr)
    
    # Try to extract partial answer
    last_message = messages[-1] if messages else {}
    answer = last_message.get("content", "Error: Max iterations reached")
    source = extract_source_from_messages(messages)
    
    return {
        "answer": answer,
        "source": source,
        "tool_calls": tool_calls_output,
    }


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Agent CLI — answers questions using an LLM with tool support"
    )
    parser.add_argument("question", help="The question to answer")
    args = parser.parse_args()

    # Load settings
    settings = load_settings()

    # Get project root (parent of agent.py)
    project_root = Path(__file__).parent.resolve()

    # Run agentic loop
    result = run_agentic_loop(args.question, settings, project_root)

    # Output result as JSON
    print(json.dumps(result))


if __name__ == "__main__":
    main()
