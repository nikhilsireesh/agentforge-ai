"""Tests for ORM models: relationships, defaults, cascades and DB constraints."""

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, StatementError

from app.models import (
    AgentRun,
    Approval,
    Artifact,
    Execution,
    ExecutionLog,
    Project,
    Requirement,
    TestResult,
    User,
)
from app.models.enums import (
    ApprovalCheckpoint,
    ApprovalDecision,
    ApprovalStatus,
    ArtifactType,
    ExecutionStatus,
    ProjectStatus,
    TestStatus,
    UserRole,
)

LEAVE_REQUIREMENT = (
    "Build an employee leave management application with employee registration, login, "
    "leave applications, manager approvals, HR administration, leave balance tracking, "
    "and attendance reports."
)


def make_project(db, **overrides) -> Project:
    project = Project(name="Employee Leave Management", business_domain="HR", **overrides)
    db.add(project)
    db.commit()
    return project


def test_project_defaults(db_session):
    project = make_project(db_session)
    assert project.id is not None
    assert project.status == ProjectStatus.DRAFT
    assert project.created_at is not None
    assert project.updated_at is not None


def test_full_execution_graph_persists(db_session):
    user = User(name="Reviewer", email="reviewer@example.com", password_hash="x", role="reviewer")
    project = make_project(db_session, owner=user)
    project.requirements.append(Requirement(raw_requirement=LEAVE_REQUIREMENT))

    execution = Execution(project=project, status=ExecutionStatus.RUNNING)
    execution.agent_runs.append(AgentRun(agent_name="requirement_analyst", is_mock=True))
    execution.approvals.append(
        Approval(checkpoint=ApprovalCheckpoint.ARCHITECTURE, reviewer=user)
    )
    execution.artifacts.append(
        Artifact(
            artifact_type=ArtifactType.SOURCE_CODE,
            file_path="backend/app/main.py",
            metadata_json={"language": "python"},
        )
    )
    execution.test_results.append(TestResult(test_name="test_login", test_status="failed"))
    execution.logs.append(ExecutionLog(agent_name="developer", message="Generated 1 file"))
    db_session.add(execution)
    db_session.commit()
    db_session.expire_all()

    loaded = db_session.get(Execution, execution.id)
    assert loaded.project.owner.role == UserRole.REVIEWER
    assert loaded.project.requirements[0].approval_status == ApprovalStatus.PENDING
    assert loaded.approvals[0].decision == ApprovalDecision.PENDING
    assert loaded.artifacts[0].metadata_json == {"language": "python"}
    assert loaded.test_results[0].test_status == TestStatus.FAILED
    assert loaded.correction_attempts == 0
    assert loaded.agent_runs[0].token_usage == 0


def test_artifact_metadata_column_is_named_metadata(db_session):
    columns = db_session.execute(text("PRAGMA table_info(artifacts)")).fetchall()
    assert "metadata" in {column[1] for column in columns}


def test_deleting_project_cascades_to_children(db_session):
    project = make_project(db_session)
    execution = Execution(project=project)
    execution.logs.append(ExecutionLog(message="started"))
    project.requirements.append(Requirement(raw_requirement="Inventory app"))
    db_session.add(execution)
    db_session.commit()

    db_session.delete(project)
    db_session.commit()

    assert db_session.scalars(select(Execution)).all() == []
    assert db_session.scalars(select(ExecutionLog)).all() == []
    assert db_session.scalars(select(Requirement)).all() == []


def test_foreign_keys_are_enforced(db_session):
    db_session.add(Requirement(project_id=9999, raw_requirement="orphan"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_email_must_be_unique(db_session):
    db_session.add(User(name="A", email="dup@example.com", password_hash="x"))
    db_session.commit()
    db_session.add(User(name="B", email="dup@example.com", password_hash="y"))
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_invalid_enum_value_rejected_by_orm(db_session):
    db_session.add(Project(name="Bad", status="banana"))
    with pytest.raises(StatementError):
        db_session.commit()


def test_invalid_enum_value_rejected_by_database(db_session):
    """Even raw SQL that bypasses Python is blocked by the CHECK constraint."""
    with pytest.raises(IntegrityError):
        db_session.execute(
            text(
                "INSERT INTO projects (name, status, created_at, updated_at) "
                "VALUES ('Bad', 'banana', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)"
            )
        )


def test_correction_attempts_capped_at_two(db_session):
    project = make_project(db_session)
    db_session.add(Execution(project=project, correction_attempts=3))
    with pytest.raises(IntegrityError):
        db_session.commit()
