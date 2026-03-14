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
    
    # Backend API configuration
    lms_api_key: str = ""
    agent_api_base_url: str = "http://localhost:42002"

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


def query_api(method: str, path: str, body: str | None = None, api_key: str = "", base_url: str = "http://localhost:42002") -> str:
    """Call the backend API and return the response.

    Args:
        method: HTTP method (GET, POST, etc.)
        path: API endpoint path
        body: Optional JSON request body
        api_key: LMS API key for authentication (empty = no auth)
        base_url: Base URL of the backend API

    Returns:
        JSON string with status_code and body, or error message
    """
    import os

    # Read from environment if not provided and env exists
    env_api_key = os.environ.get("LMS_API_KEY")
    env_base_url = os.environ.get("AGENT_API_BASE_URL")
    
    # Use env if available, otherwise use provided value
    if env_api_key:
        api_key = env_api_key
    if env_base_url:
        base_url = env_base_url

    url = f"{base_url}{path}"

    headers = {
        "Content-Type": "application/json",
    }

    # Add authentication if API key is provided
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    
    try:
        with httpx.Client(timeout=30.0) as client:
            if method.upper() == "GET":
                response = client.get(url, headers=headers)
            elif method.upper() == "POST":
                json_body = json.loads(body) if body else {}
                response = client.post(url, headers=headers, json=json_body)
            elif method.upper() == "PUT":
                json_body = json.loads(body) if body else {}
                response = client.put(url, headers=headers, json=json_body)
            elif method.upper() == "DELETE":
                response = client.delete(url, headers=headers)
            elif method.upper() == "PATCH":
                json_body = json.loads(body) if body else {}
                response = client.patch(url, headers=headers, json=json_body)
            else:
                return f"Error: Unknown HTTP method: {method}"
            
            result = {
                "status_code": response.status_code,
                "body": response.text,
            }
            return json.dumps(result)
            
    except httpx.HTTPStatusError as e:
        return json.dumps({"status_code": e.response.status_code, "body": e.response.text})
    except httpx.RequestError as e:
        return f"Error: Request failed: {e}"
    except json.JSONDecodeError as e:
        return f"Error: Invalid JSON body: {e}"
    except Exception as e:
        return f"Error: {e}"


def get_tool_definitions() -> list[dict[str, Any]]:
    """Return tool definitions for LLM API."""
    return [
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a file from the project repository. Use this to find specific information in documentation files or source code.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Relative path from project root (e.g., 'wiki/git-workflow.md', 'backend/app/main.py')"
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
                            "description": "Relative directory path from project root (e.g., 'wiki', 'backend/app/routers')"
                        }
                    },
                    "required": ["path"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "query_api",
                "description": "Call the deployed backend API to get current system state or data. Use this for questions about database contents, API responses, status codes, or system behavior. Do NOT use for documentation questions.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "method": {
                            "type": "string",
                            "description": "HTTP method (GET, POST, PUT, DELETE, PATCH)",
                            "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
                        },
                        "path": {
                            "type": "string",
                            "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate?lab=lab-01')"
                        },
                        "body": {
                            "type": "string",
                            "description": "Optional JSON request body for POST/PUT/PATCH requests"
                        }
                    },
                    "required": ["method", "path"]
                }
            }
        }
    ]


def execute_tool(name: str, args: dict[str, Any], project_root: Path, settings: AgentSettings | None = None) -> str:
    """Execute a tool and return the result.

    Args:
        name: Tool name ('read_file', 'list_files', or 'query_api')
        args: Tool arguments
        project_root: Project root directory
        settings: Optional agent settings for API configuration

    Returns:
        Tool result as string
    """
    if name == "read_file":
        path = args.get("path", "")
        return read_file(path, project_root)
    elif name == "list_files":
        path = args.get("path", "")
        return list_files(path, project_root)
    elif name == "query_api":
        method = args.get("method", "GET")
        path = args.get("path", "")
        body = args.get("body")
        api_key = settings.lms_api_key if settings else ""
        base_url = settings.agent_api_base_url if settings else "http://localhost:42002"
        return query_api(method, path, body, api_key, base_url)
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
    system_prompt = """You are a system documentation assistant for a software engineering toolkit.

You have access to these tools:
1. list_files(path) — List files in a directory
2. read_file(path) — Read file contents from the repository
3. query_api(method, path, body) — Call the deployed backend API

Use these tools strategically:

**Use read_file/list_files when:**
- Asked about documentation ("How do I...?", "What are the steps...")
- Asked about source code ("What framework...", "Show me the code...")
- Asked to explain architecture or configuration
- Asked to find bugs in source code

**Use query_api when:**
- Asked about current data ("How many items...", "What is the score...")
- Asked about API behavior ("What status code...", "Test this endpoint...")
- Asked to diagnose errors in the running system
- Asked for real-time system state

**Common paths:**
- Documentation: `wiki/git.md`, `wiki/docker.md`, etc.
- Backend code: `backend/app/main.py`, `backend/app/routers/items.py`
- Config: `docker-compose.yml`, `pyproject.toml`, `Dockerfile`

**Workflow:**
1. For wiki questions: list_files("wiki") → read_file → answer with source
2. For code questions: list_files("backend/app") → read_file → answer with source  
3. For data questions: query_api → answer with data
4. For bug diagnosis: query_api (to see error) → read_file (to find bug) → explain

**Important:**
- LIMIT: Use at most 5 tool calls total
- After gathering information, provide a FINAL ANSWER immediately
- Do not keep reading files indefinitely
- For "list all" questions: list_files once, then read 2-3 key files, then summarize
- Use full paths from project root (e.g., "backend/app/main.py", not "app/main.py")

Always cite your sources when using read_file (e.g., "wiki/git.md" or "backend/app/main.py").
For query_api questions, no source citation is needed.

Be concise and accurate. Provide complete answers."""

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

        # Check if LLM is stalling (saying "let me continue" without tool calls)
        content = assistant_message.get("content") or ""
        if not tool_calls and ("let me" in content.lower() or "continue" in content.lower()):
            # LLM is stalling - force it to provide final answer
            messages.append({
                "role": "user",
                "content": "Provide your FINAL ANSWER now based on the information you have already gathered. Do not use any more tools. Summarize what you found."
            })
            # Call again without tools
            response = call_llm(messages, settings, tools=[])
            if "choices" in response and len(response["choices"]) > 0:
                assistant_message = response["choices"][0]["message"]
                messages.append(assistant_message)
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
            result = execute_tool(tool_name, tool_args, project_root, settings)
            
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

    # Max iterations reached - force final answer
    print(f"Warning: Max iterations ({max_iterations}) reached", file=sys.stderr)
    
    # Add a user message asking for final answer based on collected information
    messages.append({
        "role": "user",
        "content": "You have reached the maximum number of tool calls. Based on the information you have gathered from the files you read, provide a complete final answer now. Summarize all the information you found. Do NOT use any more tools - just provide your answer directly."
    })
    
    # Call LLM one more time WITHOUT tools to force text-only response
    response = call_llm(messages, settings, tools=[])  # Empty tools array = no tools available
    
    if "choices" in response and len(response["choices"]) > 0:
        final_message = response["choices"][0]["message"]
        answer = final_message.get("content", "")
        # Handle case where content might be None
        if answer is None:
            answer = ""
    else:
        answer = "Error: Could not generate final answer"
    
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
