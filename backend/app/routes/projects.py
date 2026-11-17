"""Project and requirement endpoints."""

import logging
from typing import Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import User
from app.models.enums import ProjectStatus
from app.schemas.common import Page
from app.schemas.project import ProjectCreate, ProjectDetail, ProjectRead, ProjectUpdate
from app.schemas.requirement import RequirementCreate, RequirementRead, RequirementUpdate
from app.services import project_service

router = APIRouter(tags=["Projects & Requirements"])
audit = logging.getLogger("agentforge.audit")


@router.post("/api/projects", response_model=ProjectDetail, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    project = project_service.create_project(db, payload, user)
    audit.info("user=%s action=create_project project=%s", user.id, project.id)
    return project_service.to_read(db, project, detail=True)


@router.get("/api/projects", response_model=Page[ProjectRead])
def list_projects(
    search: str | None = Query(default=None, max_length=200),
    status: ProjectStatus | None = None,
    business_domain: str | None = Query(default=None, max_length=100),
    sort: Literal["created_at", "updated_at", "name", "status"] = "updated_at",
    order: Literal["asc", "desc"] = "desc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    _user: User = Depends(get_current_user),
):
    items, total = project_service.list_projects(
        db, search=search, status_filter=status, domain=business_domain, sort=sort,
        order=order, page=page, page_size=page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/api/projects/{project_id}", response_model=ProjectDetail)
def get_project(project_id: int, db: Session = Depends(get_db),
                _user: User = Depends(get_current_user)):
    return project_service.to_read(db, project_service.get_project(db, project_id), detail=True)


@router.put("/api/projects/{project_id}", response_model=ProjectDetail)
def update_project(project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)):
    project = project_service.update_project(db, project_id, payload, user)
    audit.info("user=%s action=update_project project=%s", user.id, project_id)
    return project_service.to_read(db, project, detail=True)


@router.delete("/api/projects/{project_id}", status_code=204)
def delete_project(project_id: int, db: Session = Depends(get_db),
                   user: User = Depends(get_current_user)) -> Response:
    project_service.delete_project(db, project_id, user)
    audit.info("user=%s action=delete_project project=%s", user.id, project_id)
    return Response(status_code=204)


@router.post("/api/projects/{project_id}/requirements", response_model=RequirementRead,
             status_code=201)
def add_requirement(project_id: int, payload: RequirementCreate, db: Session = Depends(get_db),
                    user: User = Depends(get_current_user)):
    return project_service.add_requirement(db, project_id, payload.raw_requirement, user)


@router.get("/api/projects/{project_id}/requirements", response_model=list[RequirementRead])
def list_requirements(project_id: int, db: Session = Depends(get_db),
                      _user: User = Depends(get_current_user)):
    return project_service.list_requirements(db, project_id)


@router.put("/api/requirements/{requirement_id}", response_model=RequirementRead)
def update_requirement(requirement_id: int, payload: RequirementUpdate,
                       db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    requirement = project_service.update_requirement(db, requirement_id, payload, user)
    audit.info("user=%s action=update_requirement requirement=%s", user.id, requirement_id)
    return requirement
