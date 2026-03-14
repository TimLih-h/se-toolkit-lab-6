# Task 1: Call an LLM from Code — Implementation Plan

## LLM Provider Choice

**Provider:** Qwen Code API (deployed on VM)

**Why Qwen Code:**
- 1000 free requests per day — sufficient for development and autochecker evaluation
- Works from Russia without VPN
- No credit card required
- Already deployed on our VM at `http://10.93.25.233:42005/v1`
- Supports OpenAI-compatible chat completions API with tool calling

**Model:** `qwen3-coder-plus`

**Configuration** (in `.env.agent.secret`):
```
LLM_API_KEY=my-secret-qwen-key
LLM_API_BASE=http://10.93.25.233:42005/v1
LLM_MODEL=qwen3-coder-plus
```

## Agent Architecture

### Input/Output

**Input:** Single command-line argument (question string)
```bash
uv run agent.py "What does REST stand for?"
```

**Output:** Single JSON line to stdout
```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

### Flow

1. Parse command-line argument (question)
2. Load LLM configuration from `.env.agent.secret`
3. Build system prompt (minimal for Task 1)
4. Call LLM API via HTTP POST to `/v1/chat/completions`
5. Extract answer from response
6. Output JSON with `answer` and empty `tool_calls` array

### Error Handling

- Exit code 0 on success
- Exit code 1 on failure (API error, missing config, etc.)
- All debug/progress output to stderr
- Only valid JSON to stdout

### Dependencies

- `httpx` — already in `pyproject.toml` for HTTP requests
- `pydantic-settings` — already in `pyproject.toml` for config loading
- Standard library: `sys`, `json`, `argparse`

## Testing Strategy

**Framework:** `pytest` (already configured in project)

**Test:** Single regression test that:
1. Runs `agent.py` as subprocess with a test question
2. Parses stdout as JSON
3. Verifies `answer` field exists and is non-empty
4. Verifies `tool_calls` field exists and is an array

## Files to Create

1. `plans/task-1.md` — this plan
2. `agent.py` — main agent CLI
3. `AGENT.md` — documentation
4. `backend/tests/unit/test_agent.py` — regression test

## Acceptance Criteria Checklist

- [ ] `plans/task-1.md` exists with implementation plan
- [ ] `agent.py` exists in project root
- [ ] `uv run agent.py "..."` outputs valid JSON with `answer` and `tool_calls`
- [ ] API key stored in `.env.agent.secret` (not hardcoded)
- [ ] `AGENT.md` documents the solution
- [ ] 1 regression test exists and passes
- [ ] Git workflow followed (issue, branch, PR, review, merge)
