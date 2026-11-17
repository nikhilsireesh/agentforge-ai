from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, str_enum, utc_now
from app.models.enums import LogLevel

if TYPE_CHECKING:
    from app.models.execution import Execution


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), index=True
    )
    agent_name: Mapped[str | None] = mapped_column(String(50))  # null = orchestrator/system
    log_level: Mapped[LogLevel] = mapped_column(
        str_enum(LogLevel, "log_level"), default=LogLevel.INFO
    )
    message: Mapped[str] = mapped_column(Text)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True
    )

    execution: Mapped[Execution] = relationship(back_populates="logs")
