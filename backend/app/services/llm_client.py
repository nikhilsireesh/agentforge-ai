"""Minimal client for any OpenAI-compatible Chat Completions API.

Responsibilities: send the request with a timeout, request JSON output,
parse it, and report token usage + latency. Validation and retries live in
the agent layer (app/agents/base.py) so they can use schema feedback.
"""

import json
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings, get_settings


class LLMError(Exception):
    """Raised for transport/provider errors. Messages never contain the API key."""


@dataclass
class LLMResponse:
    data: dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    latency_seconds: float


class LLMClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None):
        if settings.llm_api_key is None:
            raise ValueError("LLMClient requires LLM_API_KEY; use mock mode otherwise.")
        self._settings = settings
        self._client = httpx.Client(
            base_url=settings.llm_base_url.rstrip("/"),
            timeout=settings.llm_timeout_seconds,
            transport=transport,
            headers={"Authorization": f"Bearer {settings.llm_api_key.get_secret_value()}"},
        )

    def chat_json(self, system_prompt: str, user_prompt: str, max_tokens: int | None = None):
        settings = self._settings
        body: dict[str, Any] = {
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            settings.llm_max_tokens_param: max_tokens or settings.llm_max_tokens,
        }
        if settings.llm_temperature is not None:
            body["temperature"] = settings.llm_temperature

        started = time.perf_counter()
        try:
            response = self._client.post("/chat/completions", json=body)
        except httpx.TimeoutException as exc:
            raise LLMError(f"LLM request timed out after {settings.llm_timeout_seconds}s") from exc
        except httpx.HTTPError as exc:
            raise LLMError(f"LLM request failed: {type(exc).__name__}") from exc
        latency = time.perf_counter() - started

        if response.status_code >= 400:
            # Provider error bodies can be long; keep a short, key-free excerpt.
            raise LLMError(f"LLM provider returned HTTP {response.status_code}: "
                           f"{response.text[:300]}")
        try:
            payload = response.json()
            content = payload["choices"][0]["message"]["content"]
            usage = payload.get("usage") or {}
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM response had an unexpected format") from exc

        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        try:
            data = json.loads(content)
        except (TypeError, json.JSONDecodeError) as exc:
            error = LLMError("LLM did not return valid JSON")
            error.prompt_tokens, error.completion_tokens = prompt_tokens, completion_tokens
            raise error from exc
        if not isinstance(data, dict):
            raise LLMError("LLM JSON output must be an object")
        return LLMResponse(data, prompt_tokens, completion_tokens, latency)


def get_llm_client() -> LLMClient | None:
    """Return a live client, or None to signal clearly-labelled mock mode."""
    settings = get_settings()
    return LLMClient(settings) if settings.llm_mode == "live" else None
