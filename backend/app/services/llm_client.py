"""Minimal client for any OpenAI-compatible Chat Completions API.

Responsibilities: send the request with a timeout, request JSON output,
parse it, and report token usage + latency. Validation and retries live in
the agent layer (app/agents/base.py) so they can use schema feedback.
"""

import json
import logging
import time
from dataclasses import dataclass
from typing import Any

import httpx

from app.config import Settings, get_settings

logger = logging.getLogger("agentforge.llm")


# Provider overload / rate-limit statuses worth retrying after a short pause.
TRANSIENT_STATUSES = {429, 500, 502, 503, 504}
BACKOFF_SECONDS = (2.0, 5.0, 10.0)


class LLMError(Exception):
    """Raised for transport/provider errors. Messages never contain the API key."""


@dataclass
class LLMResponse:
    data: dict[str, Any]
    prompt_tokens: int
    completion_tokens: int
    latency_seconds: float


class LLMClient:
    def __init__(self, settings: Settings, transport: httpx.BaseTransport | None = None,
                 sleep=time.sleep):
        if settings.llm_api_key is None:
            raise ValueError("LLMClient requires LLM_API_KEY; use mock mode otherwise.")
        self._settings = settings
        self._sleep = sleep
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
        if settings.llm_reasoning_effort is not None:
            body["reasoning_effort"] = settings.llm_reasoning_effort

        started = time.perf_counter()
        response = self._post_with_backoff(body)
        latency = time.perf_counter() - started

        if response.status_code >= 400:
            # Provider error bodies can be long; keep a short, key-free excerpt.
            raise LLMError(f"LLM provider returned HTTP {response.status_code}: "
                           f"{response.text[:300]}")
        try:
            payload = response.json()
            choice = payload["choices"][0]
            content = choice["message"]["content"]
            usage = payload.get("usage") or {}
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LLMError("LLM response had an unexpected format") from exc

        prompt_tokens = int(usage.get("prompt_tokens") or 0)
        completion_tokens = int(usage.get("completion_tokens") or 0)
        if choice.get("finish_reason") == "length":
            # Reasoning models spend part of the budget on hidden "thinking" tokens,
            # so a truncated answer is a configuration problem, not bad JSON.
            error = LLMError(
                f"LLM output was truncated at the token limit ({settings.llm_max_tokens}); "
                "increase LLM_MAX_TOKENS")
            error.prompt_tokens, error.completion_tokens = prompt_tokens, completion_tokens
            raise error
        try:
            data = json.loads(content)
        except (TypeError, json.JSONDecodeError) as exc:
            error = LLMError("LLM did not return valid JSON")
            error.prompt_tokens, error.completion_tokens = prompt_tokens, completion_tokens
            raise error from exc
        if not isinstance(data, dict):
            raise LLMError("LLM JSON output must be an object")
        return LLMResponse(data, prompt_tokens, completion_tokens, latency)

    def _post_with_backoff(self, body: dict[str, Any]) -> httpx.Response:
        """POST, retrying transient provider errors (overload, rate limit) with backoff.

        Schema/validation retries are separate and live in the agent layer.
        """
        timeout = self._settings.llm_timeout_seconds
        for attempt, pause in enumerate((*BACKOFF_SECONDS, None)):
            try:
                response = self._client.post("/chat/completions", json=body)
            except httpx.TimeoutException as exc:
                raise LLMError(f"LLM request timed out after {timeout}s") from exc
            except httpx.HTTPError as exc:
                raise LLMError(f"LLM request failed: {type(exc).__name__}") from exc
            if response.status_code not in TRANSIENT_STATUSES or pause is None:
                return response
            logger.warning("LLM provider returned HTTP %d; retry %d/%d in %.0fs",
                            response.status_code, attempt + 1, len(BACKOFF_SECONDS), pause)
            self._sleep(pause)
        raise AssertionError("unreachable")


def get_llm_client() -> LLMClient | None:
    """Return a live client, or None to signal clearly-labelled mock mode."""
    settings = get_settings()
    return LLMClient(settings) if settings.llm_mode == "live" else None
