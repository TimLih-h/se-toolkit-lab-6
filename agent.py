#!/usr/bin/env python3
"""Agent CLI — answers questions using an LLM.

Usage:
    uv run agent.py "What does REST stand for?"

Output:
    JSON line to stdout: {"answer": "...", "tool_calls": []}
"""

import argparse
import json
import sys
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


def call_llm(question: str, settings: AgentSettings) -> str:
    """Call the LLM API and return the answer."""
    url = f"{settings.llm_api_base}/chat/completions"

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.llm_api_key}",
    }

    payload = {
        "model": settings.llm_model,
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful assistant. Answer questions concisely and accurately.",
            },
            {"role": "user", "content": question},
        ],
        "temperature": 0.7,
        "max_tokens": 1024,
    }

    try:
        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json()

            # Extract answer from response
            if (
                "choices" in data
                and len(data["choices"]) > 0
                and "message" in data["choices"][0]
                and "content" in data["choices"][0]["message"]
            ):
                return data["choices"][0]["message"]["content"]
            else:
                print(f"Unexpected API response format: {data}", file=sys.stderr)
                sys.exit(1)

    except httpx.HTTPStatusError as e:
        print(f"HTTP error: {e.response.status_code} - {e.response.text}", file=sys.stderr)
        sys.exit(1)
    except httpx.RequestError as e:
        print(f"Request error: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Agent CLI — answers questions using an LLM")
    parser.add_argument("question", help="The question to answer")
    args = parser.parse_args()

    # Load settings
    settings = load_settings()

    # Call LLM
    answer = call_llm(args.question, settings)

    # Output result as JSON
    result: dict[str, Any] = {
        "answer": answer,
        "tool_calls": [],
    }

    print(json.dumps(result))


if __name__ == "__main__":
    main()
