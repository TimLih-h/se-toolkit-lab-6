# Agent Documentation

## Overview

This project includes a CLI agent (`agent.py`) that answers questions using an LLM (Large Language Model). The agent is the foundation for more advanced agentic capabilities that will be added in subsequent tasks.

## Architecture

```
User question → agent.py → LLM API → JSON answer
```

### Components

1. **`agent.py`** — Main CLI entry point
   - Parses command-line arguments
   - Loads LLM configuration from `.env.agent.secret`
   - Calls the LLM API via HTTP
   - Outputs structured JSON response

2. **`.env.agent.secret`** — LLM configuration
   - API key for authentication
   - API base URL (OpenAI-compatible endpoint)
   - Model name

3. **LLM Provider** — Qwen Code API
   - Deployed on VM at `http://10.93.25.233:42005/v1`
   - Model: `qwen3-coder-plus`
   - 1000 free requests per day

## Usage

### Basic Usage

```bash
# Run with a question
uv run agent.py "What does REST stand for?"
```

### Output Format

The agent outputs a single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

Fields:
- `answer` (string): The LLM's answer to the question
- `tool_calls` (array): Empty for Task 1 (will be populated in Task 2)

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

## Testing

Run the regression test:

```bash
uv run pytest backend/tests/unit/test_agent.py -v
```

The test verifies:
- Agent outputs valid JSON
- `answer` field is present and non-empty
- `tool_calls` field is present and is an array

## Implementation Details

### Request Flow

1. User provides a question as command-line argument
2. Agent loads settings from `.env.agent.secret`
3. Agent builds a chat completion request:
   - System prompt: "You are a helpful assistant..."
   - User message: the question
4. Agent sends HTTP POST to `{LLM_API_BASE}/chat/completions`
5. Agent extracts the answer from the response
6. Agent outputs JSON with answer and empty tool_calls

### Error Handling

- Missing or invalid configuration → exit code 1
- HTTP errors (4xx, 5xx) → exit code 1 with error message to stderr
- Network errors → exit code 1 with error message to stderr
- Unexpected API response format → exit code 1

### Dependencies

- `httpx` — HTTP client for API requests
- `pydantic-settings` — Configuration loading from environment
- Standard library: `argparse`, `json`, `sys`

## Future Extensions (Tasks 2-3)

- **Task 2:** Add tools (`read_file`, `list_files`, `query_api`) and agentic loop
- **Task 3:** Expand system prompt with domain knowledge about the lab

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

### "Unexpected API response format"

The LLM API may have returned an error. Check stderr for details.
