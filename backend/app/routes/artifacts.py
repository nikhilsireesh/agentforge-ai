from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.models.enums import ArtifactType
from app.schemas.artifact import ArtifactContent, ArtifactRead
from app.services import artifact_service

router = APIRouter(tags=["Artifacts"])


@router.get("/api/projects/{project_id}/artifacts", response_model=list[ArtifactRead])
def list_artifacts(project_id: int, execution_id: int | None = None,
                   artifact_type: ArtifactType | None = None, latest_only: bool = True,
                   db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    return artifact_service.list_for_project(db, project_id, execution_id, artifact_type,
                                             latest_only)


@router.get("/api/artifacts/{artifact_id}", response_model=ArtifactContent)
def get_artifact(artifact_id: int, db: Session = Depends(get_db),
                 _user: User = Depends(get_current_user)):
    return artifact_service.get_with_content(db, artifact_id)


@router.get("/api/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: int, db: Session = Depends(get_db),
                      _user: User = Depends(get_current_user)) -> FileResponse:
    artifact, path = artifact_service.file_path_for(db, artifact_id)
    # Served as a download (never rendered) so generated HTML/JS cannot run in the app origin.
    return FileResponse(path, filename=path.name, media_type="application/octet-stream",
                        headers={"X-Content-Type-Options": "nosniff"})
