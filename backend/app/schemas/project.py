from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.models.enums import ExecutionStatus, ProjectComplexity, ProjectStatus
from app.schemas.common import ORMModel


class ProjectBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    business_domain: str | None = Field(default=None, max_length=100)
    preferred_tech_stack: str | None = Field(default=None, max_length=500)
    complexity: ProjectComplexity | None = None
    constraints: str | None = Field(default=None, max_length=5000)


class ProjectCreate(ProjectBase):
    # Optional: the wizard can submit the first requirement together with the project.
    requirement: str | None = Field(default=None, max_length=10_000)


class ProjectUpdate(BaseModel):
    """All fields optional: only the provided ones are changed."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=5000)
    business_domain: str | None = Field(default=None, max_length=100)
    preferred_tech_stack: str | None = Field(default=None, max_length=500)
    complexity: ProjectComplexity | None = None
    constraints: str | None = Field(default=None, max_length=5000)
    status: Literal["draft", "archived"] | None = None


class ExecutionBrief(ORMModel):
    id: int
    status: ExecutionStatus
    current_agent: str | None
    started_at: datetime
    completed_at: datetime | None
    total_duration: float | None
    correction_attempts: int
    llm_mode: str


class ProjectRead(ProjectBase, ORMModel):
    id: int
    owner_id: int | None
    status: ProjectStatus
    created_at: datetime
    updated_at: datetime
    requirement_count: int = 0
    execution_count: int = 0
    latest_execution: ExecutionBrief | None = None


class ProjectDetail(ProjectRead):
    executions: list[ExecutionBrief] = []
