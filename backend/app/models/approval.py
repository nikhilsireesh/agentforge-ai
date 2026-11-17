from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, str_enum
from app.models.enums import ApprovalCheckpoint, ApprovalDecision

if TYPE_CHECKING:
    from app.models.execution import Execution
    from app.models.user import User


class Approval(CreatedAtMixin, Base):
    """A human-in-the-loop checkpoint. Created as 'pending'; the workflow waits on it."""

    __tablename__ = "approvals"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), index=True
    )
    checkpoint: Mapped[ApprovalCheckpoint] = mapped_column(
        str_enum(ApprovalCheckpoint, "approval_checkpoint")
    )
    decision: Mapped[ApprovalDecision] = mapped_column(
        str_enum(ApprovalDecision, "approval_decision"),
        default=ApprovalDecision.PENDING,
        index=True,
    )
    # What the reviewer is asked to approve (counts, names) captured when the workflow paused.
    request_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    feedback: Mapped[str | None] = mapped_column(Text)
    reviewer_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"))
    # created_at = when approval was requested; decided_at = when a human decided.
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    execution: Mapped[Execution] = relationship(back_populates="approvals")
    reviewer: Mapped[User | None] = relationship()
