"""Base class shared by all six agents.

An agent = role prompt + structured output schema + validation + retry policy.
Agents are pure: they receive a context dict and return a validated result.
They never touch the database; the orchestrator records everything.
"""

import logging
import time
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ValidationError

from app.prompts.templates import build_system_prompt
from app.services.llm_client import LLMClient, LLMError

logger = logging.getLogger(__name__)


class AgentValidationError(ValueError):
    """Output parsed but broke an agent-specific rule."""


class AgentExecutionError(RuntimeError):
    """The agent could not produce valid output within its retry budget."""

    def __init__(self, message: str, attempts: int, prompt_tokens: int, completion_tokens: int):
        super().__init__(message)
        self.attempts = attempts
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


@dataclass
class AgentResult:
    output: dict[str, Any]
    is_mock: bool
    attempts: int = 1
    prompt_tokens: int = 0
    completion_tokens: int = 0
    llm_latency_seconds: float = 0.0


class BaseAgent:
    name: str = ""
    display_name: str = ""
    description: str = ""
    role_prompt: str = ""
    output_model: type[BaseModel]
    max_tokens: int | None = None

    # ---- hooks implemented by each agent ---------------------------------
    def build_user_prompt(self, ctx: dict[str, Any]) -> str:
        raise NotImplementedError

    def mock_output(self, ctx: dict[str, Any]) -> dict[str, Any]:
        """Deterministic output for MOCK mode (no LLM). Always labelled as mock."""
        raise NotImplementedError

    def validate_output(self, output: BaseModel, ctx: dict[str, Any]) -> None:
        """Extra business rules beyond the schema. Raise AgentValidationError to retry."""

    def post_process(self, output: BaseModel, ctx: dict[str, Any]) -> BaseModel:
        return output

    def summarize_input(self, ctx: dict[str, Any]) -> dict[str, Any]:
        return {}

    # ---- shared machinery -------------------------------------------------
    @property
    def system_prompt(self) -> str:
        return build_system_prompt(self.role_prompt, self.output_model.model_json_schema())

    def run(self, ctx: dict[str, Any], llm: LLMClient | None, max_retries: int) -> AgentResult:
        if llm is None:
            output = self.output_model.model_validate(self.mock_output(ctx))
            self.validate_output(output, ctx)
            output = self.post_process(output, ctx)
            return AgentResult(output=output.model_dump(mode="json"), is_mock=True)

        user_prompt = self.build_user_prompt(ctx)
        prompt_tokens = completion_tokens = 0
        latency = 0.0
        last_error = "unknown error"
        total_attempts = max_retries + 1

        for attempt in range(1, total_attempts + 1):
            prompt = user_prompt
            if attempt > 1:
                prompt += (
                    "\n\nYour previous response was rejected for this reason:\n"
                    f"{last_error[:1500]}\nReturn a corrected, complete JSON object."
                )
            started = time.perf_counter()
            try:
                response = llm.chat_json(self.system_prompt, prompt, self.max_tokens)
                prompt_tokens += response.prompt_tokens
                completion_tokens += response.completion_tokens
                latency += response.latency_seconds
                output = self.output_model.model_validate(response.data)
                self.validate_output(output, ctx)
                output = self.post_process(output, ctx)
                return AgentResult(
                    output=output.model_dump(mode="json"),
                    is_mock=False,
                    attempts=attempt,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    llm_latency_seconds=latency,
                )
            except (LLMError, ValidationError, AgentValidationError) as exc:
                latency += time.perf_counter() - started if isinstance(exc, LLMError) else 0
                prompt_tokens += getattr(exc, "prompt_tokens", 0)
                completion_tokens += getattr(exc, "completion_tokens", 0)
                last_error = str(exc)
                logger.warning("%s attempt %d/%d failed: %s", self.name, attempt,
                               total_attempts, last_error[:300])

        raise AgentExecutionError(
            f"{self.display_name} failed after {total_attempts} attempt(s): {last_error[:500]}",
            attempts=total_attempts,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
