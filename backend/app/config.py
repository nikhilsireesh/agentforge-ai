"""Application configuration.

All settings are read from environment variables (or a local `.env` file) so
that secrets such as API keys never live in source code.
"""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

APP_VERSION = "1.0.0"
BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Typed settings. Pydantic validates every value at startup."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Application ---
    app_name: str = "AgentForge AI"
    app_env: Literal["development", "test", "production"] = "development"
    debug: bool = False
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"

    # --- Database / storage ---
    database_url: str = "sqlite:///./agentforge.db"
    # LangGraph checkpoints (paused workflows) are persisted here so approvals survive restarts.
    checkpoint_db_path: str = "./checkpoints.db"
    generated_projects_dir: Path = BACKEND_DIR.parent / "generated_projects"

    # --- HTTP ---
    cors_origins: str = "http://localhost:5173"
    max_request_body_bytes: int = 1_000_000
    rate_limit_per_minute: int = Field(default=20, ge=1)

    # --- Authentication ---
    # Disabled by default for local demos: every request acts as a built-in demo admin.
    auth_enabled: bool = False
    jwt_secret: SecretStr | None = None
    jwt_expire_minutes: int = Field(default=480, ge=5)

    # --- Workflow execution ---
    # "thread": run workflows in background threads. "inline": run inside the request (tests).
    execution_mode: Literal["thread", "inline"] = "thread"
    max_requirement_chars: int = Field(default=10_000, ge=100)

    # --- LLM ---
    llm_api_key: SecretStr | None = None
    llm_base_url: str = "https://api.openai.com/v1"
    llm_model: str = "gpt-4o-mini"
    llm_timeout_seconds: int = Field(default=120, ge=5, le=600)
    llm_max_retries: int = Field(default=2, ge=0, le=5)
    llm_max_tokens: int = Field(default=8000, ge=256)
    # Some newer models require "max_completion_tokens" instead of "max_tokens".
    llm_max_tokens_param: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    llm_temperature: float | None = 0.2
    # Prices used ONLY to estimate cost from real token counts. Verify with your provider.
    llm_input_cost_per_1m: float = Field(default=0.0, ge=0)
    llm_output_cost_per_1m: float = Field(default=0.0, ge=0)
    # Mock mode only: first code version contains a labelled defect to demo the correction loop.
    mock_inject_defect: bool = True
    # Research agent: if true, check that suggested URLs respond (does not verify content).
    research_check_urls: bool = False

    # --- Test sandbox (generated code is NEVER executed on the host) ---
    sandbox_mode: Literal["auto", "docker", "disabled"] = "auto"
    sandbox_image: str = "agentforge-sandbox:latest"
    sandbox_timeout_seconds: int = Field(default=120, ge=10, le=900)
    sandbox_memory: str = "512m"
    sandbox_cpus: str = "1.0"

    @field_validator("llm_api_key", "jwt_secret", mode="before")
    @classmethod
    def empty_secret_is_none(cls, value: object) -> object:
        """Treat `LLM_API_KEY=` (empty) as 'not configured'."""
        return None if value in ("", None) else value

    @field_validator("llm_temperature", mode="before")
    @classmethod
    def empty_temperature_is_none(cls, value: object) -> object:
        return None if value in ("", "none", "None") else value

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def llm_mode(self) -> Literal["live", "mock"]:
        """'mock' when no API key is configured. Mock output is always labelled as such."""
        return "live" if self.llm_api_key else "mock"

    @property
    def generated_root(self) -> Path:
        path = self.generated_projects_dir
        if not path.is_absolute():
            path = (BACKEND_DIR / path).resolve()
        return path


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance (read once per process)."""
    return Settings()
