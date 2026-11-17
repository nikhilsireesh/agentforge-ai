from datetime import datetime
from typing import Any

from app.models.enums import ApprovalStatus, ArtifactType
from app.schemas.common import ORMModel


class ArtifactRead(ORMModel):
    id: int
    execution_id: int
    artifact_type: ArtifactType
    file_path: str
    metadata_json: dict[str, Any] | None
    approval_status: ApprovalStatus
    created_at: datetime


class ArtifactContent(ArtifactRead):
    content: str | None
    truncated: bool = False
