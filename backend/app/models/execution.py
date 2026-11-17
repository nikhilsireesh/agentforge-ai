from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, str_enum, utc_now
from app.models.enums import ExecutionStatus

if TYPE_CHECKING:
    from app.models.agent_run import AgentRun
    from app.models.approval import Approval
    from app.models.artifact import Artifact
    from app.models.execution_log import ExecutionLog
    from app.models.project import Project
    from app.models.requirement import Requirement
    from app.models.test_result import TestResult

CHILD_RELATIONSHIP = {"cascade": "all, delete-orphan", "passive_deletes": True}


class Execution(Base):
    """One run of the multi-agent workflow for a project."""

    __tablename__ = "executions"
    __table_args__ = (
        CheckConstraint(
            "correction_attempts >= 0 AND correction_attempts <= 2",
            name="correction_attempts_range",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    # The requirement version this run analysed.
    requirement_id: Mapped[int | None] = mapped_column(
        ForeignKey("requirements.id", ondelete="SET NULL")
    )
    # LangGraph thread id: identifies this run's saved checkpoints so it can be resumed.
    thread_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    status: Mapped[ExecutionStatus] = mapped_column(
        str_enum(ExecutionStatus, "execution_status"),
        default=ExecutionStatus.PENDING,
        index=True,
    )
    current_agent: Mapped[str | None] = mapped_column(String(50))
    # "live" or "mock": recorded so results are never confused with real LLM output.
    llm_mode: Mapped[str] = mapped_column(String(10), default="mock")
    # Max two correction loops (spec rule); enforced in code and by the DB constraint.
    correction_attempts: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utc_now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    total_duration: Mapped[float | None] = mapped_column(Float)  # seconds, incl. human waits

    project: Mapped[Project] = relationship(back_populates="executions")
    requirement: Mapped[Requirement | None] = relationship()

    agent_runs: Mapped[list[AgentRun]] = relationship(
        back_populates="execution", **CHILD_RELATIONSHIP
    )
    approvals: Mapped[list[Approval]] = relationship(
        back_populates="execution", **CHILD_RELATIONSHIP
    )
    artifacts: Mapped[list[Artifact]] = relationship(
        back_populates="execution", **CHILD_RELATIONSHIP
    )
    test_results: Mapped[list[TestResult]] = relationship(
        back_populates="execution", **CHILD_RELATIONSHIP
    )
    logs: Mapped[list[ExecutionLog]] = relationship(
        back_populates="execution", **CHILD_RELATIONSHIP
    )
