from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, str_enum
from app.models.enums import AgentRunStatus

if TYPE_CHECKING:
    from app.models.execution import Execution


class AgentRun(Base):
    """One invocation of one agent inside an execution. `attempt` = LLM attempts used."""

    __tablename__ = "agent_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), index=True
    )
    agent_name: Mapped[str] = mapped_column(String(50), index=True)
    attempt: Mapped[int] = mapped_column(Integer, default=1)
    input_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    output_data: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    status: Mapped[AgentRunStatus] = mapped_column(
        str_enum(AgentRunStatus, "agent_run_status"), default=AgentRunStatus.PENDING, index=True
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    # Token counts as reported by the LLM API (0 in mock mode). Split so cost can be estimated.
    prompt_tokens: Mapped[int] = mapped_column(Integer, default=0)
    completion_tokens: Mapped[int] = mapped_column(Integer, default=0)
    token_usage: Mapped[int] = mapped_column(Integer, default=0)  # total
    # True when output came from mock mode, so analytics never mixes it with real LLM data.
    is_mock: Mapped[bool] = mapped_column(default=False)

    error_message: Mapped[str | None] = mapped_column(Text)

    execution: Mapped[Execution] = relationship(back_populates="agent_runs")
