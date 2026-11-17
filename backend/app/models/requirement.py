from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, DateTime, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, str_enum, utc_now
from app.models.enums import ApprovalStatus

if TYPE_CHECKING:
    from app.models.project import Project


class Requirement(CreatedAtMixin, Base):
    __tablename__ = "requirements"

    id: Mapped[int] = mapped_column(primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), index=True
    )
    # The client's natural-language text, exactly as submitted.
    raw_requirement: Mapped[str] = mapped_column(Text)
    # The Requirement Analyst agent's validated JSON output (null until analysed).
    structured_output: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        str_enum(ApprovalStatus, "requirement_approval_status"),
        default=ApprovalStatus.PENDING,
    )
    # Added because PUT /api/requirements/{id} lets users edit requirements.
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    project: Mapped[Project] = relationship(back_populates="requirements")
