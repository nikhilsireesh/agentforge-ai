"""Starts, resumes and finalises workflow executions.

The graph runs in a background thread so HTTP requests return immediately;
the frontend polls for progress. Checkpoints are stored in SQLite
(CHECKPOINT_DB_PATH), so a workflow paused for approval survives restarts.
"""

import logging
import sqlite3
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from typing import Any

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command
from sqlalchemy.orm import Session

from app.config import get_settings
from app.models import Execution, Project, Requirement
from app.models.enums import ExecutionStatus, ProjectStatus
from app.orchestration import recorder
from app.orchestration.graph import ExecutionCancelled, build_graph

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4, thread_name_prefix="agentforge-workflow")
_graph = None
_connection: sqlite3.Connection | None = None
_graph_lock = threading.Lock()


def get_graph():
    global _graph, _connection
    with _graph_lock:
        if _graph is None:
            _connection = sqlite3.connect(get_settings().checkpoint_db_path,
                                          check_same_thread=False)
            _graph = build_graph(SqliteSaver(_connection))
        return _graph


def reset_graph() -> None:
    """Drop the cached graph (used by tests)."""
    global _graph, _connection
    with _graph_lock:
        if _connection is not None:
            _connection.close()
        _graph, _connection = None, None


def _config(thread_id: str) -> dict[str, Any]:
    return {"configurable": {"thread_id": thread_id}, "recursion_limit": 100}


def start_execution(db: Session, project: Project, requirement: Requirement) -> Execution:
    settings = get_settings()
    execution = Execution(
        project_id=project.id, requirement_id=requirement.id, thread_id=uuid.uuid4().hex,
        status=ExecutionStatus.PENDING, llm_mode=settings.llm_mode,
    )
    project.status = ProjectStatus.IN_PROGRESS
    db.add(execution)
    db.commit()
    recorder.log(execution.id, f"Execution created (LLM mode: {settings.llm_mode}).",
                 agent="orchestrator")
    initial_state = {
        "project_id": project.id,
        "execution_id": execution.id,
        "requirement_id": requirement.id,
        "requirement": requirement.raw_requirement,
        "project": recorder.project_snapshot(project.id),
        "llm_mode": settings.llm_mode,
        "correction_attempts": 0,
        "code_version": 0,
        "code_approved": False,
        "approval_status": "",
        "execution_logs": [],
        "errors": [],
    }
    _submit(execution.id, execution.thread_id, initial_state)
    return execution


def resume_execution(execution: Execution, decision: str, feedback: str | None) -> None:
    _submit(execution.id, execution.thread_id,
            Command(resume={"decision": decision, "feedback": feedback}))


def _submit(execution_id: int, thread_id: str, graph_input: Any) -> None:
    if get_settings().execution_mode == "inline":
        _drive(execution_id, thread_id, graph_input)
    else:
        _executor.submit(_drive, execution_id, thread_id, graph_input)


def _drive(execution_id: int, thread_id: str, graph_input: Any) -> None:
    """Run the graph until it finishes or pauses at an approval checkpoint."""
    config = _config(thread_id)
    try:
        recorder.mark_running(execution_id)
        graph = get_graph()
        graph.invoke(graph_input, config)
        snapshot = graph.get_state(config)
        if snapshot.next:
            interrupts = [i.value for task in snapshot.tasks for i in task.interrupts]
            if not interrupts:
                raise RuntimeError(f"Workflow stopped unexpectedly before {snapshot.next}")
            recorder.pause_for_approval(execution_id, interrupts[0])
        elif snapshot.values.get("approval_status") == "rejected":
            recorder.finish(execution_id, ExecutionStatus.CANCELLED,
                            "Rejected by reviewer at checkpoint "
                            f"'{snapshot.values.get('last_checkpoint')}'. Workflow stopped.")
        else:
            recorder.finish(execution_id, ExecutionStatus.COMPLETED,
                            "Workflow completed: documentation and delivery package ready.")
    except ExecutionCancelled:
        recorder.finish(execution_id, ExecutionStatus.CANCELLED, "Execution cancelled by user.")
    except Exception as exc:  # noqa: BLE001 - every failure must be recorded, never lost
        logger.exception("Execution %s failed", execution_id)
        recorder.finish(execution_id, ExecutionStatus.FAILED,
                        f"Execution failed: {type(exc).__name__}: {str(exc)[:1500]}")
