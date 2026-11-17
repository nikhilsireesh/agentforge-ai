from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.enums import ApprovalStatus
from app.schemas.common import ORMModel


class RequirementCreate(BaseModel):
    raw_requirement: str = Field(min_length=10, max_length=10_000)


class RequirementUpdate(BaseModel):
    raw_requirement: str | None = Field(default=None, min_length=10, max_length=10_000)
    # Edited Requirement Analyst output; validated against the agent's schema in the service.
    structured_output: dict[str, Any] | None = None


class RequirementRead(ORMModel):
    id: int
    project_id: int
    raw_requirement: str
    structured_output: dict[str, Any] | None
    approval_status: ApprovalStatus
    created_at: datetime
    updated_at: datetime
