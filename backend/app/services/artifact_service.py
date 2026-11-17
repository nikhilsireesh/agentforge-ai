"""Artifact listing, preview and secure download."""

import json
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Artifact, Execution
from app.models.enums import ArtifactType
from app.schemas.artifact import ArtifactContent, ArtifactRead
from app.services import artifact_store
from app.services.execution_service import detail as execution_detail
from app.services.execution_service import get_execution
from app.services.project_service import get_project

MAX_PREVIEW_BYTES = 1_000_000


def list_for_project(db: Session, project_id: int, execution_id: int | None,
                     artifact_type: ArtifactType | None, latest_only: bool) -> list[ArtifactRead]:
    get_project(db, project_id)
    query = select(Artifact).join(Execution).where(Execution.project_id == project_id)
    if execution_id:
        query = query.where(Artifact.execution_id == execution_id)
    if artifact_type:
        query = query.where(Artifact.artifact_type == artifact_type)
    rows = list(db.scalars(query.order_by(Artifact.id)).all())
    if latest_only:
        # Keep only the newest code version per execution (documents are always kept).
        latest: dict[int, int] = {}
        for row in rows:
            version = (row.metadata_json or {}).get("code_version")
            if version is not None:
                latest[row.execution_id] = max(latest.get(row.execution_id, 0), version)
        rows = [r for r in rows if (r.metadata_json or {}).get("code_version") in
                (None, latest.get(r.execution_id))]
    return [ArtifactRead.model_validate(r) for r in rows]


def _get(db: Session, artifact_id: int) -> Artifact:
    artifact = db.get(Artifact, artifact_id)
    if artifact is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact not found.")
    return artifact


def file_path_for(db: Session, artifact_id: int) -> tuple[Artifact, Path]:
    artifact = _get(db, artifact_id)
    try:
        path = artifact_store.resolve_stored_path(artifact.file_path)
    except artifact_store.UnsafePathError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid artifact path.") from exc
    if not path.is_file() or path.is_symlink():
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Artifact file is missing on disk.")
    return artifact, path


def get_with_content(db: Session, artifact_id: int) -> ArtifactContent:
    artifact, path = file_path_for(db, artifact_id)
    raw = path.read_bytes()[:MAX_PREVIEW_BYTES]
    data = ArtifactRead.model_validate(artifact).model_dump()
    return ArtifactContent(**data, content=raw.decode("utf-8", errors="replace"),
                           truncated=path.stat().st_size > MAX_PREVIEW_BYTES)


def delivery_package(db: Session, execution_id: int) -> tuple[str, bytes]:
    execution = get_execution(db, execution_id)
    info = execution_detail(db, execution_id)
    review = info.outputs.get("review_testing") or {}
    code_version = (info.outputs.get("developer") or {}).get("code_version")
    manifest = {
        "project": execution.project.name,
        "execution_id": execution.id,
        "status": str(execution.status),
        "llm_mode": execution.llm_mode,
        "code_version": code_version,
        "test_summary": {k: review.get(k) for k in ("passed_tests", "failed_tests",
                                                     "skipped_tests", "review_status")},
        "correction_attempts": execution.correction_attempts,
    }
    content = artifact_store.build_package(
        execution_id, code_version, {"manifest.json": json.dumps(manifest, indent=2)})
    safe_name = "".join(c if c.isalnum() else "-" for c in execution.project.name).strip("-")
    return f"{safe_name or 'project'}-execution-{execution.id}.zip", content
