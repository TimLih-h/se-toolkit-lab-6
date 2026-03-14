# Task 3: The System Agent — Implementation Plan

## Overview

Extend the agent from Task 2 with:
1. New tool: `query_api` for backend API calls
2. Authentication via `LMS_API_KEY` from environment
3. Updated system prompt to distinguish wiki vs system questions
4. Pass the `run_eval.py` benchmark (10/10 questions)

## Tool Definition: `query_api`

### Schema

```json
{
  "name": "query_api",
  "description": "Call the deployed backend API to get current system state or data. Use this for questions about database contents, API responses, status codes, or system behavior.",
  "parameters": {
    "type": "object",
    "properties": {
      "method": {
        "type": "string",
        "description": "HTTP method (GET, POST, etc.)",
        "enum": ["GET", "POST", "PUT", "DELETE", "PATCH"]
      },
      "path": {
        "type": "string",
        "description": "API endpoint path (e.g., '/items/', '/analytics/completion-rate')"
      },
      "body": {
        "type": "string",
        "description": "Optional JSON request body for POST/PUT requests"
      }
    },
    "required": ["method", "path"]
  }
}
```

### Implementation

```python
def query_api(method: str, path: str, body: str | None = None) -> str:
    """Call the backend API and return response."""
    base_url = os.environ.get("AGENT_API_BASE_URL", "http://localhost:42002")
    api_key = os.environ.get("LMS_API_KEY")
    
    url = f"{base_url}{path}"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    
    # Make request based on method
    # Return JSON string with status_code and body
```

## Environment Variables

### Required (from `.env.agent.secret`)
- `LLM_API_KEY` — LLM provider API key
- `LLM_API_BASE` — LLM API endpoint
- `LLM_MODEL` — Model name

### Required (from `.env.docker.secret`)
- `LMS_API_KEY` — Backend API authentication

### Optional
- `AGENT_API_BASE_URL` — Backend URL (default: `http://localhost:42002`)

**Important:** All values must be read from environment variables, not hardcoded. The autochecker injects its own values.

## System Prompt Update

The system prompt needs to guide the LLM on when to use each tool:

```
You are a system documentation assistant. You have access to:

1. list_files(path) — Discover files in directories
2. read_file(path) — Read file contents from the repository
3. query_api(method, path, body) — Call the deployed backend API

Use these tools strategically:

**Use read_file/list_files when:**
- Asked about documentation ("How do I...?", "What are the steps...")
- Asked about source code ("What framework...", "Show me the code...")
- Asked to explain architecture or configuration

**Use query_api when:**
- Asked about current data ("How many items...", "What is the score...")
- Asked about API behavior ("What status code...", "Test this endpoint...")
- Asked to diagnose errors or bugs in the running system

**Workflow:**
1. For wiki questions: list_files → read_file → answer with source
2. For code questions: list_files → read_file → answer with source
3. For data questions: query_api → answer with data
4. For bug diagnosis: query_api (to see error) → read_file (to find bug) → explain

Always cite your sources when using read_file.
```

## Benchmark Strategy

### Run Initial Evaluation

```bash
uv run run_eval.py
```

Expected output shows which questions pass/fail with feedback.

### Iteration Plan

1. **First run:** Identify failing questions
2. **Analyze failures:**
   - Wrong tool chosen? → Improve system prompt
   - Tool called incorrectly? → Improve tool description
   - Tool implementation bug? → Fix code
   - Answer format wrong? → Adjust prompt
3. **Fix and re-run** until 10/10 pass

### Expected Tool Usage by Question

| # | Question Type | Expected Tool |
|---|---------------|---------------|
| 0 | Wiki: protect branch | `read_file` |
| 1 | Wiki: SSH connection | `read_file` |
| 2 | Code: web framework | `read_file` |
| 3 | Code: API routers | `list_files` |
| 4 | Data: item count | `query_api` |
| 5 | API: status code | `query_api` |
| 6 | Bug: division error | `query_api` + `read_file` |
| 7 | Bug: NoneType error | `query_api` + `read_file` |
| 8 | Architecture: request flow | `read_file` |
| 9 | ETL: idempotency | `read_file` |

## Files to Create/Modify

1. `plans/task-3.md` — this plan
2. `agent.py` — add `query_api` tool, update settings, update system prompt
3. `AGENT.md` — document `query_api` and lessons learned
4. `backend/tests/unit/test_agent.py` — add 2 new tests
5. `.env.docker.secret` — ensure `LMS_API_KEY` is set (already exists)

## Testing Strategy

### Test 1: Framework Question

**Question:** `"What framework does the backend use?"`

**Expected:**
- `read_file` in tool_calls
- Answer contains "FastAPI"

### Test 2: Database Count Question

**Question:** `"How many items are in the database?"`

**Expected:**
- `query_api` in tool_calls
- Answer contains a number > 0

## Acceptance Criteria Checklist

- [ ] `plans/task-3.md` exists with implementation plan
- [ ] `agent.py` defines `query_api` as function-calling schema
- [ ] `query_api` authenticates with `LMS_API_KEY` from env
- [ ] Agent reads all LLM config from environment variables
- [ ] Agent reads `AGENT_API_BASE_URL` (defaults to localhost)
- [ ] Agent answers static system questions correctly
- [ ] Agent answers data-dependent questions correctly
- [ ] `run_eval.py` passes all 10 questions
- [ ] `AGENT.md` documents final architecture (200+ words)
- [ ] 2 tool-calling regression tests exist and pass
- [ ] Autochecker bot benchmark passes
- [ ] Git workflow followed (issue, branch, PR, review, merge)

## Initial Benchmark Score

*To be filled after first run of `run_eval.py`*

Expected format:
```
X/10 passed

Failing questions:
- [4/10] ...feedback...
- [7/10] ...feedback...
```

## Iteration Log

*To be filled as we fix issues*

### Iteration 1
- Issue: ...
- Fix: ...
- Result: X/10

### Iteration 2
- ...
