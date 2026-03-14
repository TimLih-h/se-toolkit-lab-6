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
   - `query_api(method, path, body)` — Call the backend API (Task 3)

3. **`.env.agent.secret`** — LLM and backend configuration
   - `LLM_API_KEY` — LLM provider API key
   - `LLM_API_BASE` — LLM API endpoint
   - `LLM_MODEL` — Model name
   - `LMS_API_KEY` — Backend API key for query_api (can be empty for unauthenticated requests)
   - `AGENT_API_BASE_URL` — Backend URL (default: http://localhost:42002)

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

### `query_api` (Task 3)

Call the deployed backend API to get current system state or data.

**Parameters:**
- `method` (string, required): HTTP method (GET, POST, PUT, DELETE, PATCH)
- `path` (string, required): API endpoint path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT/PATCH

**Returns:** JSON string with `status_code` and `body`, or error message

**Authentication:**
- Uses `LMS_API_KEY` from `.env.agent.secret` for Authorization header
- If `LMS_API_KEY` is empty, no auth header is sent (for testing auth errors)

**Example:**
```json
{"tool": "query_api", "args": {"method": "GET", "path": "/items/"}, "result": "{\"status_code\": 200, \"body\": \"[...]\"}"}
```

**Use cases:**
- Query database contents ("How many items...?")
- Test API endpoints ("What status code...?")
- Diagnose runtime errors

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

## Benchmark Results and Lessons Learned (Task 3)

### Final Evaluation Score

Local benchmark (`run_eval.py`): **5/10 passed**

**Passing questions:**
1. Wiki: Protect branch steps ✓
2. Wiki: SSH connection ✓
3. Code: Web framework (FastAPI) ✓
4. Code: API routers ✓
5. Data: Item count ✓

**Failing questions:**
6. API: Status code without auth — agent gets 200 instead of 401 (environment variable loading issue in subprocess)
7-10. Complex multi-step questions requiring deeper reasoning

### Architecture

The agent uses a tool-based architecture where:
1. LLM receives user question with tool definitions
2. LLM decides which tools to call based on question type
3. Agent executes tools and feeds results back
4. Loop continues until LLM provides final answer or max iterations reached

**Key design decisions:**
- Tools are defined as OpenAI-compatible function schemas
- `query_api` tool authenticates with `LMS_API_KEY` from environment
- Max 10 iterations to prevent infinite loops
- Stalling detection: if LLM says "let me continue" without tool calls, force final answer

### Lessons Learned

1. **Environment variable handling**: Subprocess doesn't inherit parent environment by default. Had to explicitly pass `env=os.environ` in `subprocess.run()`.

2. **Tool descriptions matter**: Vague tool descriptions led to LLM choosing wrong tools. Added explicit examples and "do NOT use for..." guidance.

3. **Iteration limits**: Some questions require many tool calls. Increased from 6 to 10 iterations, but complex "list all" questions still struggle.

4. **System prompt engineering**: Added explicit workflow instructions ("For wiki questions: list_files → read_file → answer") improved tool selection accuracy.

5. **Authentication complexity**: The `query_api` tool needs to support both authenticated and unauthenticated requests. Empty `LMS_API_KEY` allows testing auth error responses (401).

6. **LLM limitations**: The model sometimes continues generating "Let me check more files" even after reaching useful information. Added stalling detection to force final answers.

### Future Improvements

1. **Parallel tool execution**: Currently tools execute sequentially. Could parallelize independent `read_file` calls.

2. **Response caching**: Cache file contents to avoid re-reading same file multiple times.

3. **Better error handling**: More specific error messages for different failure modes (network, auth, not found).

4. **Extended context**: For large files, implement chunked reading to avoid truncation.

5. **Multi-turn conversation**: Support conversation history for follow-up questions.


### Agent doesn't find the answer

- The documentation may not contain the answer
- Try using different keywords in your question
- Check that the wiki files exist using `list_files("wiki")`
