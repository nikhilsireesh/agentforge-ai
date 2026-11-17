from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, str_enum
from app.models.enums import TestStatus

if TYPE_CHECKING:
    from app.models.execution import Execution


class TestResult(CreatedAtMixin, Base):
    """The outcome of one actually-executed test. Rows exist only for tests that really ran."""

    __tablename__ = "test_results"
    __test__ = False  # stop pytest from trying to collect this class as a test

    id: Mapped[int] = mapped_column(primary_key=True)
    execution_id: Mapped[int] = mapped_column(
        ForeignKey("executions.id", ondelete="CASCADE"), index=True
    )
    # 0 = first run, 1-2 = re-runs after controlled correction. Shows fail -> fix -> pass.
    iteration: Mapped[int] = mapped_column(Integer, default=0)
    test_name: Mapped[str] = mapped_column(String(300))
    test_status: Mapped[TestStatus] = mapped_column(str_enum(TestStatus, "test_status"), index=True)
    execution_output: Mapped[str | None] = mapped_column(Text)
    error_message: Mapped[str | None] = mapped_column(Text)
    duration_seconds: Mapped[float | None] = mapped_column(Float)

    execution: Mapped[Execution] = relationship(back_populates="test_results")
