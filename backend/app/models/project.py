from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, str_enum, utc_now
from app.models.enums import ProjectComplexity, ProjectStatus

if TYPE_CHECKING:
    from app.models.execution import Execution
    from app.models.requirement import Requirement
    from app.models.user import User


class Project(CreatedAtMixin, Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Nullable until authentication is added; deleting a user keeps their projects.
    owner_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(200), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    business_domain: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[ProjectStatus] = mapped_column(
        str_enum(ProjectStatus, "project_status"), default=ProjectStatus.DRAFT, index=True
    )

    # Extra fields required by the "New Project" wizard (not in the original table spec).
    preferred_tech_stack: Mapped[str | None] = mapped_column(String(500))
    complexity: Mapped[ProjectComplexity | None] = mapped_column(
        str_enum(ProjectComplexity, "project_complexity")
    )
    constraints: Mapped[str | None] = mapped_column(Text)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now
    )

    owner: Mapped[User | None] = relationship(back_populates="projects")
    # Deleting a project deletes its requirements and executions (and their children).
    requirements: Mapped[list[Requirement]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )
    executions: Mapped[list[Execution]] = relationship(
        back_populates="project", cascade="all, delete-orphan", passive_deletes=True
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r} status={self.status}>"
