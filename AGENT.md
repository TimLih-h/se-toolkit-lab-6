# Agent Documentation

## Overview

This project includes a CLI agent (`agent.py`) that answers questions using an LLM (Large Language Model) with tool support. The agent can read files and list directories to find answers in project documentation.

## Architecture

```
Question → LLM (with tools) → tool_calls? 
    ├─ YES → Execute tools → Feed results back → LLM
    └─ NO  → Final answer → JSON output
```

### Components

1. **`agent.py`** — Main CLI entry point
   - Parses command-line arguments
   - Loads LLM configuration from `.env.agent.secret`
   - Implements agentic loop with tool execution
   - Outputs structured JSON response

2. **Tools:**
   - `read_file(path)` — Read a file from the project
   - `list_files(path)` — List files in a directory

3. **`.env.agent.secret`** — LLM configuration
   - API key for authentication
   - API base URL (OpenAI-compatible endpoint)
   - Model name

4. **LLM Provider** — Qwen Code API
   - Deployed on VM at `http://10.93.25.233:42005/v1`
   - Model: `qwen3-coder-plus`
   - 1000 free requests per day

## Usage

### Basic Usage

```bash
# Run with a question
uv run agent.py "How do you resolve a merge conflict?"
```

### Output Format

The agent outputs a single JSON line to stdout:

```json
{
  "answer": "Edit the conflicting file, choose which changes to keep, then stage and commit.",
  "source": "wiki/git.md",
  "tool_calls": [
    {
      "tool": "list_files",
      "args": {"path": "wiki"},
      "result": "git.md\ngit-workflow.md\n..."
    },
    {
      "tool": "read_file",
      "args": {"path": "wiki/git.md"},
      "result": "..."
    }
  ]
}
```

**Fields:**
- `answer` (string, required): The LLM's answer to the question
- `source` (string, required): File path where the answer was found (e.g., `wiki/git.md`)
- `tool_calls` (array, required): List of all tool calls made during execution

### Exit Codes

- `0` — Success (valid JSON output)
- `1` — Failure (API error, missing config, etc.)

## Configuration

### Environment File

Create `.env.agent.secret` by copying `.env.agent.example`:

```bash
cp .env.agent.example .env.agent.secret
```

Edit `.env.agent.secret`:

```env
# LLM API configuration
LLM_API_KEY=my-secret-qwen-key
LLM_API_BASE=http://10.93.25.233:42005/v1
LLM_MODEL=qwen3-coder-plus
```

### Configuration Options

| Variable | Description | Example |
|----------|-------------|---------|
| `LLM_API_KEY` | API key for authentication | `my-secret-qwen-key` |
| `LLM_API_BASE` | Base URL of LLM API | `http://10.93.25.233:42005/v1` |
| `LLM_MODEL` | Model name to use | `qwen3-coder-plus` |

## Tools

### `read_file`

Read a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root

**Returns:** File contents as string, or error message

**Security:**
- Validates path doesn't contain `../` traversal
- Ensures resolved path is within project root

**Example:**
```json
{"tool": "read_file", "args": {"path": "wiki/git.md"}, "result": "..."}
```

### `list_files`

List files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root

**Returns:** Newline-separated listing of entries

**Security:**
- Validates path doesn't contain `../` traversal
- Ensures resolved path is within project root

**Example:**
```json
{"tool": "list_files", "args": {"path": "wiki"}, "result": "git.md\ngit-workflow.md\n..."}
```

## Agentic Loop

### Flow

1. **Initial request:**
   - Build messages with system prompt + user question
   - Include tool definitions in API request
   - Send to LLM

2. **Parse response:**
   - If `tool_calls` present → execute tools
   - If no `tool_calls` → extract answer and source

3. **Execute tools:**
   - For each tool call:
     - Call the appropriate function
     - Store result in `tool_calls` array for output
     - Append tool result as `"role": "tool"` message

4. **Loop back:**
   - Send updated messages to LLM
   - Repeat until no tool calls or max 10 iterations

5. **Output:**
   - JSON with `answer`, `source`, and `tool_calls`

### System Prompt

The system prompt instructs the LLM to:
1. Use `list_files` to discover relevant wiki files
2. Use `read_file` to read specific files and find the answer
3. Always cite the source as a file path
4. Be concise and accurate

### Iteration Limit

Maximum 10 tool call iterations per question to prevent infinite loops.

## Testing

Run the regression tests:

```bash
uv run pytest backend/tests/unit/test_agent.py -v
```

Tests verify:
- Agent outputs valid JSON
- `answer`, `source`, and `tool_calls` fields are present
- Tool calls are executed correctly
- Source field contains expected file paths

## Implementation Details

### Request Flow

1. User provides a question as command-line argument
2. Agent loads settings from `.env.agent.secret`
3. Agent builds initial messages with system prompt
4. Agent sends HTTP POST to `{LLM_API_BASE}/chat/completions` with tool definitions
5. Agent parses response for tool calls
6. If tool calls present:
   - Execute each tool
   - Record results
   - Append tool results as messages
   - Loop back to step 4
7. If no tool calls:
   - Extract answer and source
   - Output JSON

### Error Handling

- Missing or invalid configuration → exit code 1
- HTTP errors (4xx, 5xx) → exit code 1 with error message to stderr
- Network errors → exit code 1 with error message to stderr
- Path traversal attempts → error message in tool result
- Max iterations reached → warning to stderr, partial answer returned

### Security

**Path validation:**
- Rejects paths containing `..`
- Rejects absolute paths starting with `/`
- Resolves to absolute path and verifies it's within project root

### Dependencies

- `httpx` — HTTP client for API requests
- `pydantic-settings` — Configuration loading from environment
- Standard library: `argparse`, `json`, `sys`, `pathlib`

## LLM Provider Setup

### Qwen Code API (Recommended)

1. Deploy Qwen Code API on your VM following [wiki/qwen.md](wiki/qwen.md)
2. Set up `qwen-code-oai-proxy` to expose OpenAI-compatible endpoint
3. Configure `.env.agent.secret` with your VM IP and port

### OpenRouter (Alternative)

1. Register at https://openrouter.ai/keys
2. Get a free API key
3. Configure `.env.agent.secret`:

```env
LLM_API_KEY=your-openrouter-key
LLM_API_BASE=https://openrouter.ai/api/v1
LLM_MODEL=meta-llama/llama-3.3-70b-instruct:free
```

## Troubleshooting

### "Error loading settings"

Ensure `.env.agent.secret` exists and contains all required variables:
```bash
cat .env.agent.secret
```

### "HTTP error: 401"

Check that `LLM_API_KEY` is correct in `.env.agent.secret`.

### "Request error"

Verify that the LLM API is accessible:
```bash
curl http://10.93.25.233:42005/health
```

### "Error: File not found"

The file path doesn't exist. Use `list_files` to discover available files.

### "Warning: Max iterations reached"

The agent hit the 10 iteration limit. The answer may be incomplete. Try a more specific question.

### Agent doesn't find the answer

- The documentation may not contain the answer
- Try using different keywords in your question
- Check that the wiki files exist using `list_files("wiki")`
