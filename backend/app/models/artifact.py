from __future__ import annotations

from typing import TYPE_CHECKING, Any

from sqlalchemy import JSON, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, str_enum
from app.models.enums import ApprovalStatus, ArtifactType

if TYPE_CHECKING:
    from app.models.execution import Execution


class Artifact(CreatedAtMixin, Base):
    """A generated file (code, test, doc...). Contents live on disk under generated_projects/."""

    __tablename__ = "artifacts"

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), index=True
    )
    artifact_type: Mapped[ArtifactType] = mapped_column(str_enum(ArtifactType, "artifact_type"))
    # Relative path inside the execution's sandbox folder; validated before any disk access.
    file_path: Mapped[str] = mapped_column(String(500))
    # `metadata` is reserved by SQLAlchemy, so the Python attribute is `metadata_json`
    # while the database column is still named "metadata".
    metadata_json: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        str_enum(ApprovalStatus, "artifact_approval_status"), default=ApprovalStatus.PENDING
    )

    execution: Mapped[Execution] = relationship(back_populates="artifacts")
