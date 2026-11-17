"""Database recording for the orchestrator.

Workflow nodes run in background threads, so each helper opens its own short
session (`database.SessionLocal` is looked up at call time so tests can
rebind it). Agents never write to the database themselves.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, update

from app import database
from app.agents.base import AgentResult
from app.models import (
    AgentRun,
    Approval,
    Artifact,
    Execution,
    ExecutionLog,
    Project,
    Requirement,
    TestResult,
)
from app.models.enums import (
    AgentRunStatus,
    ApprovalCheckpoint,
    ApprovalDecision,
    ApprovalStatus,
    ArtifactType,
    ExecutionStatus,
    LogLevel,
    ProjectStatus,
)
from app.services import artifact_store
from app.services.docs_renderer import DOC_TITLES


@contextmanager
def session_scope() -> Iterator:
    db = database.SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _now() -> datetime:
    return datetime.now(UTC)


def _aware(value: datetime) -> datetime:
    """SQLite returns naive datetimes; treat them as UTC."""
    return value if value.tzinfo else value.replace(tzinfo=UTC)


def log(execution_id: int, message: str, level: LogLevel = LogLevel.INFO,
        agent: str | None = None) -> None:
    with session_scope() as db:
        db.add(ExecutionLog(execution_id=execution_id, agent_name=agent, log_level=level,
                            message=message[:5000]))


def is_cancelled(execution_id: int) -> bool:
    with session_scope() as db:
        status = db.scalar(select(Execution.status).where(Execution.id == execution_id))
        return status == ExecutionStatus.CANCELLED


def set_current(execution_id: int, node: str) -> None:
    with session_scope() as db:
        db.execute(update(Execution).where(Execution.id == execution_id)
                   .values(current_agent=node))


def mark_running(execution_id: int) -> None:
    with session_scope() as db:
        execution = db.get(Execution, execution_id)
        if execution and execution.status != ExecutionStatus.CANCELLED:
            execution.status = ExecutionStatus.RUNNING
            execution.project.status = ProjectStatus.IN_PROGRESS


def start_agent_run(execution_id: int, agent_name: str, input_summary: dict[str, Any],
                    is_mock: bool) -> int:
    with session_scope() as db:
        run = AgentRun(execution_id=execution_id, agent_name=agent_name,
                       input_data=input_summary, status=AgentRunStatus.RUNNING,
                       started_at=_now(), is_mock=is_mock)
        db.add(run)
        db.flush()
        return run.id


def complete_agent_run(run_id: int, result: AgentResult, duration: float) -> None:
    with session_scope() as db:
        run = db.get(AgentRun, run_id)
        run.status = AgentRunStatus.COMPLETED
        run.output_data = result.output
        run.completed_at = _now()
        run.duration_seconds = round(duration, 4)
        run.attempt = result.attempts
        run.prompt_tokens = result.prompt_tokens
        run.completion_tokens = result.completion_tokens
        run.token_usage = result.prompt_tokens + result.completion_tokens
        run.is_mock = result.is_mock


def update_agent_output(run_id: int, output: dict[str, Any]) -> None:
    with session_scope() as db:
        db.get(AgentRun, run_id).output_data = output


def fail_agent_run(run_id: int, error: str, duration: float, attempts: int = 1,
                   prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
    with session_scope() as db:
        run = db.get(AgentRun, run_id)
        run.status = AgentRunStatus.FAILED
        run.error_message = error[:5000]
        run.completed_at = _now()
        run.duration_seconds = round(duration, 4)
        run.attempt = attempts
        run.prompt_tokens = prompt_tokens
        run.completion_tokens = completion_tokens
        run.token_usage = prompt_tokens + completion_tokens


def save_requirement_output(requirement_id: int | None, output: dict[str, Any]) -> None:
    if requirement_id is None:
        return
    with session_scope() as db:
        requirement = db.get(Requirement, requirement_id)
        if requirement:
            requirement.structured_output = output
            requirement.approval_status = ApprovalStatus.PENDING


def load_requirement_output(requirement_id: int | None) -> dict[str, Any] | None:
    if requirement_id is None:
        return None
    with session_scope() as db:
        requirement = db.get(Requirement, requirement_id)
        return requirement.structured_output if requirement else None


def save_code_artifacts(execution_id: int, code_version: int, artifacts: list[dict[str, Any]],
                        is_mock: bool) -> list[dict[str, Any]]:
    """Write files to the sandbox folder and register Artifact rows (pending approval)."""
    base = artifact_store.code_dir(execution_id, code_version)
    saved = []
    with session_scope() as db:
        for item in artifacts:
            _, stored = artifact_store.write_text_file(base, item["file_path"], item["content"])
            is_test = item["file_path"].split("/")[-1].startswith("test_")
            row = Artifact(
                execution_id=execution_id,
                artifact_type=ArtifactType.TEST if is_test else (
                    ArtifactType.DOCUMENTATION if item["file_path"].endswith(".md")
                    else ArtifactType.CONFIGURATION if item["file_type"] in ("text", "toml",
                                                                             "json", "yaml")
                    else ArtifactType.SOURCE_CODE),
                file_path=stored,
                metadata_json={
                    "relative_path": item["file_path"],
                    "file_type": item["file_type"],
                    "description": item["description"],
                    "dependencies": item.get("dependencies", []),
                    "proposed_action": item.get("proposed_action", "create"),
                    "code_version": code_version,
                    "size_bytes": len(item["content"].encode()),
                    "sha256": artifact_store.sha256(item["content"]),
                    "is_mock": is_mock,
                    "category": "code",
                },
                approval_status=ApprovalStatus.PENDING,
            )
            db.add(row)
            db.flush()
            saved.append({**item, "artifact_id": row.id, "stored_path": stored})
    return saved


def set_code_artifacts_status(execution_id: int, code_version: int,
                              status: ApprovalStatus) -> None:
    with session_scope() as db:
        rows = db.scalars(select(Artifact).where(Artifact.execution_id == execution_id)).all()
        for row in rows:
            meta = row.metadata_json or {}
            if meta.get("category") == "code" and meta.get("code_version") == code_version:
                row.approval_status = status


def save_documents(execution_id: int, documents: dict[str, str]) -> dict[str, int]:
    base = artifact_store.docs_dir(execution_id)
    ids = {}
    with session_scope() as db:
        for name, content in documents.items():
            _, stored = artifact_store.write_text_file(base, name, content)
            row = Artifact(
                execution_id=execution_id, artifact_type=ArtifactType.DOCUMENTATION,
                file_path=stored,
                metadata_json={"relative_path": name, "category": "delivery_document",
                               "title": DOC_TITLES.get(name, name),
                               "size_bytes": len(content.encode()),
                               "sha256": artifact_store.sha256(content)},
                approval_status=ApprovalStatus.APPROVED,
            )
            db.add(row)
            db.flush()
            ids[name] = row.id
    return ids


def save_test_results(execution_id: int, iteration: int, outcomes: list[dict[str, Any]]) -> None:
    with session_scope() as db:
        for outcome in outcomes:
            db.add(TestResult(
                execution_id=execution_id, iteration=iteration, test_name=outcome["name"][:300],
                test_status=outcome["status"],
                execution_output=(outcome.get("output") or "")[:8000],
                error_message=outcome.get("error"),
                duration_seconds=outcome.get("duration_seconds"),
            ))


def set_correction_attempts(execution_id: int, attempts: int) -> None:
    with session_scope() as db:
        db.execute(update(Execution).where(Execution.id == execution_id)
                   .values(correction_attempts=attempts))


def approval_history(execution_id: int) -> list[dict[str, Any]]:
    with session_scope() as db:
        rows = db.scalars(select(Approval).where(Approval.execution_id == execution_id)
                          .order_by(Approval.id)).all()
        return [{
            "checkpoint": str(a.checkpoint), "decision": str(a.decision),
            "reviewer": a.reviewer.name if a.reviewer else None,
            "decided_at": a.decided_at.strftime("%Y-%m-%d %H:%M") if a.decided_at else None,
            "feedback": a.feedback,
        } for a in rows]


def pause_for_approval(execution_id: int, payload: dict[str, Any]) -> None:
    checkpoint = ApprovalCheckpoint(payload["checkpoint"])
    with session_scope() as db:
        execution = db.get(Execution, execution_id)
        if execution.status == ExecutionStatus.CANCELLED:
            return
        existing = db.scalar(select(Approval).where(
            Approval.execution_id == execution_id,
            Approval.decision == ApprovalDecision.PENDING))
        if existing is None:
            db.add(Approval(execution_id=execution_id, checkpoint=checkpoint,
                            request_summary=payload.get("summary")))
        execution.status = ExecutionStatus.WAITING_APPROVAL
        execution.current_agent = f"approval_{checkpoint.value}"
        execution.project.status = ProjectStatus.AWAITING_APPROVAL
        db.add(ExecutionLog(execution_id=execution_id, agent_name="orchestrator",
                            message=f"Paused: waiting for human approval at checkpoint "
                                    f"'{checkpoint.value}'."))


def finish(execution_id: int, status: ExecutionStatus, message: str | None = None) -> None:
    with session_scope() as db:
        execution = db.get(Execution, execution_id)
        if execution.status == ExecutionStatus.CANCELLED:
            status = ExecutionStatus.CANCELLED  # a cancel request always wins
        execution.status = status
        execution.current_agent = None
        execution.completed_at = _now()
        execution.total_duration = round(
            (execution.completed_at - _aware(execution.started_at)).total_seconds(), 3)
        if message and status != ExecutionStatus.COMPLETED:
            execution.error_message = message[:5000]
        execution.project.status = {
            ExecutionStatus.COMPLETED: ProjectStatus.COMPLETED,
            ExecutionStatus.FAILED: ProjectStatus.FAILED,
        }.get(status, ProjectStatus.DRAFT)
        level = LogLevel.ERROR if status == ExecutionStatus.FAILED else LogLevel.INFO
        db.add(ExecutionLog(execution_id=execution_id, agent_name="orchestrator",
                            log_level=level,
                            message=message or f"Execution finished with status '{status}'."))


def recover_interrupted() -> int:
    """At startup, executions left 'running' by a crash cannot continue; mark them failed.
    Executions waiting for approval are untouched: their checkpoints are on disk."""
    with session_scope() as db:
        rows = db.scalars(select(Execution).where(Execution.status.in_(
            [ExecutionStatus.RUNNING, ExecutionStatus.PENDING]))).all()
        for execution in rows:
            execution.status = ExecutionStatus.FAILED
            execution.error_message = "Server restarted while this execution was running."
            execution.completed_at = _now()
            execution.project.status = ProjectStatus.FAILED
        return len(rows)


def project_snapshot(project_id: int) -> dict[str, Any]:
    with session_scope() as db:
        p = db.get(Project, project_id)
        return {
            "name": p.name, "description": p.description, "business_domain": p.business_domain,
            "preferred_tech_stack": p.preferred_tech_stack,
            "complexity": str(p.complexity) if p.complexity else None,
            "constraints": p.constraints,
        }
