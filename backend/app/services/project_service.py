"""Project and requirement business logic."""

from typing import Literal

from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.agents.schemas import RequirementsAnalysis
from app.models import Execution, Project, Requirement, User
from app.models.enums import ExecutionStatus, ProjectStatus, UserRole
from app.schemas.project import (
    ExecutionBrief,
    ProjectCreate,
    ProjectDetail,
    ProjectRead,
    ProjectUpdate,
)
from app.schemas.requirement import RequirementUpdate

ACTIVE_STATUSES = (ExecutionStatus.PENDING, ExecutionStatus.RUNNING,
                   ExecutionStatus.WAITING_APPROVAL)
SortField = Literal["created_at", "updated_at", "name", "status"]


def _get_project(db: Session, project_id: int) -> Project:
    project = db.get(Project, project_id)
    if project is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found.")
    return project


def _check_owner(project: Project, user: User) -> None:
    """Members may only modify their own projects; admins may modify any."""
    if user.role != UserRole.ADMIN and project.owner_id not in (None, user.id):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "You can only modify your own projects.")


def to_read(db: Session, project: Project, detail: bool = False) -> ProjectRead | ProjectDetail:
    executions = db.scalars(select(Execution).where(Execution.project_id == project.id)
                            .order_by(Execution.id.desc())).all()
    requirement_count = db.scalar(select(func.count(Requirement.id))
                                  .where(Requirement.project_id == project.id)) or 0
    data = ProjectRead.model_validate(project).model_dump()
    data.update(
        requirement_count=requirement_count,
        execution_count=len(executions),
        latest_execution=ExecutionBrief.model_validate(executions[0]) if executions else None,
    )
    if detail:
        return ProjectDetail(**data, executions=[ExecutionBrief.model_validate(e)
                                                 for e in executions])
    return ProjectRead(**data)


def list_projects(db: Session, *, search: str | None, status_filter: ProjectStatus | None,
                  domain: str | None, sort: SortField, order: Literal["asc", "desc"],
                  page: int, page_size: int) -> tuple[list[ProjectRead], int]:
    query = select(Project)
    if search:
        pattern = f"%{search.strip()}%"
        query = query.where(or_(Project.name.ilike(pattern), Project.description.ilike(pattern),
                                Project.business_domain.ilike(pattern)))
    if status_filter:
        query = query.where(Project.status == status_filter)
    if domain:
        query = query.where(Project.business_domain.ilike(domain))
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    column = getattr(Project, sort)
    query = query.order_by(column.asc() if order == "asc" else column.desc(), Project.id.desc())
    rows = db.scalars(query.offset((page - 1) * page_size).limit(page_size)).all()
    return [to_read(db, p) for p in rows], total


def create_project(db: Session, payload: ProjectCreate, user: User) -> Project:
    data = payload.model_dump(exclude={"requirement"})
    project = Project(**data, owner_id=user.id)
    db.add(project)
    db.flush()
    if payload.requirement and payload.requirement.strip():
        db.add(Requirement(project_id=project.id, raw_requirement=payload.requirement.strip()))
    db.commit()
    return project


def get_project(db: Session, project_id: int) -> Project:
    return _get_project(db, project_id)


def update_project(db: Session, project_id: int, payload: ProjectUpdate, user: User) -> Project:
    project = _get_project(db, project_id)
    _check_owner(project, user)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, field, value)
    db.commit()
    return project


def delete_project(db: Session, project_id: int, user: User) -> None:
    project = _get_project(db, project_id)
    _check_owner(project, user)
    active = db.scalar(select(func.count(Execution.id)).where(
        Execution.project_id == project_id, Execution.status.in_(ACTIVE_STATUSES)))
    if active:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "Cancel the project's active execution before deleting it.")
    db.delete(project)
    db.commit()


# ------------------------------------------------------------------ requirements
def add_requirement(db: Session, project_id: int, text: str, user: User) -> Requirement:
    project = _get_project(db, project_id)
    _check_owner(project, user)
    requirement = Requirement(project_id=project_id, raw_requirement=text.strip())
    db.add(requirement)
    db.commit()
    return requirement


def list_requirements(db: Session, project_id: int) -> list[Requirement]:
    _get_project(db, project_id)
    return list(db.scalars(select(Requirement).where(Requirement.project_id == project_id)
                           .order_by(Requirement.id.desc())).all())


def update_requirement(db: Session, requirement_id: int, payload: RequirementUpdate,
                       user: User) -> Requirement:
    requirement = db.get(Requirement, requirement_id)
    if requirement is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Requirement not found.")
    _check_owner(requirement.project, user)
    if payload.raw_requirement is not None:
        requirement.raw_requirement = payload.raw_requirement.strip()
    if payload.structured_output is not None:
        try:
            # Edits must still match the Requirement Analyst's schema.
            validated = RequirementsAnalysis.model_validate(payload.structured_output)
        except ValidationError as exc:
            raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY,
                                f"structured_output is invalid: {exc.errors()[:3]}") from exc
        requirement.structured_output = validated.model_dump(mode="json")
    db.commit()
    return requirement
