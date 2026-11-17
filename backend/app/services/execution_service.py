"""Execution lifecycle, approvals and the workflow view."""

from datetime import UTC, datetime
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models import AgentRun, Approval, Execution, ExecutionLog, Requirement, User
from app.models.enums import (
    AgentRunStatus,
    ApprovalDecision,
    ApprovalStatus,
    ExecutionStatus,
    ProjectStatus,
)
from app.orchestration import runner
from app.schemas.execution import (
    ApprovalRead,
    ExecutionDetail,
    ExecutionLogRead,
    ExecutionRead,
    WorkflowEdge,
    WorkflowNode,
    WorkflowView,
)
from app.services.project_service import ACTIVE_STATUSES, _check_owner, get_project


def get_execution(db: Session, execution_id: int) -> Execution:
    execution = db.get(Execution, execution_id)
    if execution is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Execution not found.")
    return execution


def start(db: Session, project_id: int, requirement_id: int | None, user: User) -> Execution:
    project = get_project(db, project_id)
    _check_owner(project, user)
    active = db.scalar(select(func.count(Execution.id)).where(
        Execution.project_id == project_id, Execution.status.in_(ACTIVE_STATUSES)))
    if active:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "This project already has an active execution.")
    query = select(Requirement).where(Requirement.project_id == project_id)
    if requirement_id:
        query = query.where(Requirement.id == requirement_id)
    requirement = db.scalar(query.order_by(Requirement.id.desc()))
    if requirement is None:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Submit a requirement for this project before executing.")
    return runner.start_execution(db, project, requirement)


def to_read(execution: Execution) -> ExecutionRead:
    read = ExecutionRead.model_validate(execution)
    read.project_name = execution.project.name if execution.project else None
    return read


def approval_to_read(approval: Approval) -> ApprovalRead:
    read = ApprovalRead.model_validate(approval)
    read.reviewer_name = approval.reviewer.name if approval.reviewer else None
    read.project_id = approval.execution.project_id
    read.project_name = approval.execution.project.name
    read.summary = approval.request_summary
    return read


def detail(db: Session, execution_id: int) -> ExecutionDetail:
    execution = get_execution(db, execution_id)
    data = to_read(execution).model_dump()
    pending = db.scalar(select(Approval).where(Approval.execution_id == execution_id,
                                               Approval.decision == ApprovalDecision.PENDING))
    outputs: dict[str, Any] = {}
    runs = db.scalars(select(AgentRun).where(AgentRun.execution_id == execution_id,
                                             AgentRun.status == AgentRunStatus.COMPLETED)
                      .order_by(AgentRun.id)).all()
    for run in runs:
        outputs[run.agent_name] = run.output_data  # later runs overwrite earlier ones
    return ExecutionDetail(**data, outputs=outputs,
                           pending_approval=approval_to_read(pending) if pending else None)


def list_executions(db: Session, project_id: int | None, status_filter: ExecutionStatus | None,
                    page: int, page_size: int) -> tuple[list[ExecutionRead], int]:
    query = select(Execution)
    if project_id:
        query = query.where(Execution.project_id == project_id)
    if status_filter:
        query = query.where(Execution.status == status_filter)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(Execution.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return [to_read(e) for e in rows], total


def cancel(db: Session, execution_id: int, user: User) -> Execution:
    execution = get_execution(db, execution_id)
    _check_owner(execution.project, user)
    if execution.status not in ACTIVE_STATUSES:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            f"Execution is already {execution.status}.")
    was_waiting = execution.status == ExecutionStatus.WAITING_APPROVAL
    execution.status = ExecutionStatus.CANCELLED
    db.execute(update(Approval).where(Approval.execution_id == execution_id,
                                      Approval.decision == ApprovalDecision.PENDING)
               .values(decision=ApprovalDecision.REJECTED, feedback="Execution cancelled.",
                       reviewer_id=user.id, decided_at=datetime.now(UTC)))
    if was_waiting:
        # Nothing is running, so finalise immediately.
        execution.completed_at = datetime.now(UTC)
        execution.current_agent = None
        execution.project.status = ProjectStatus.DRAFT
    db.add(ExecutionLog(execution_id=execution_id, agent_name="orchestrator",
                        message=f"Cancellation requested by {user.name}."))
    db.commit()
    return execution


def decide(db: Session, execution_id: int, decision: ApprovalDecision, feedback: str | None,
           reviewer: User) -> Approval:
    """Record a human decision on the pending checkpoint and resume the workflow."""
    execution = get_execution(db, execution_id)
    if execution.status != ExecutionStatus.WAITING_APPROVAL:
        raise HTTPException(status.HTTP_409_CONFLICT,
                            "This execution is not waiting for an approval.")
    approval = db.scalar(select(Approval).where(Approval.execution_id == execution_id,
                                                Approval.decision == ApprovalDecision.PENDING))
    if approval is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "No pending approval found.")
    # Conditional update: if two reviewers click at once, only one decision wins.
    result = db.execute(
        update(Approval)
        .where(Approval.id == approval.id, Approval.decision == ApprovalDecision.PENDING)
        .values(decision=decision, feedback=feedback, reviewer_id=reviewer.id,
                decided_at=datetime.now(UTC))
    )
    if result.rowcount != 1:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, "This approval was already decided.")
    if approval.checkpoint == "requirements" and execution.requirement:
        execution.requirement.approval_status = {
            ApprovalDecision.APPROVED: ApprovalStatus.APPROVED,
            ApprovalDecision.REJECTED: ApprovalStatus.REJECTED,
        }.get(decision, ApprovalStatus.PENDING)
    execution.status = ExecutionStatus.RUNNING
    execution.project.status = ProjectStatus.IN_PROGRESS
    db.commit()
    db.refresh(approval)
    runner.resume_execution(execution, decision.value, feedback)
    return approval


def list_approvals(db: Session, decision: ApprovalDecision | None, execution_id: int | None,
                   page: int, page_size: int) -> tuple[list[ApprovalRead], int]:
    query = select(Approval)
    if decision:
        query = query.where(Approval.decision == decision)
    if execution_id:
        query = query.where(Approval.execution_id == execution_id)
    total = db.scalar(select(func.count()).select_from(query.subquery())) or 0
    rows = db.scalars(query.order_by(Approval.id.desc())
                      .offset((page - 1) * page_size).limit(page_size)).all()
    return [approval_to_read(a) for a in rows], total


# ------------------------------------------------------------------ workflow view
WORKFLOW_NODES = [
    ("requirement_analyst", "Requirement Analyst", "agent", None),
    ("approval_requirements", "Requirements Approval", "approval", "requirements"),
    ("research", "Research Agent", "agent", None),
    ("solution_architect", "Solution Architect", "agent", None),
    ("approval_architecture", "Architecture Approval", "approval", "architecture"),
    ("developer", "Developer Agent", "agent", None),
    ("approval_code", "Code Approval", "approval", "code"),
    ("approval_test_execution", "Test Execution Approval", "approval", "test_execution"),
    ("review_testing", "Review & Testing", "agent", None),
    ("correction", "Controlled Correction", "control", None),
    ("approval_deployment", "Final Delivery Approval", "approval", "deployment"),
    ("documentation", "Documentation Agent", "agent", None),
]
WORKFLOW_EDGES = [
    ("requirement_analyst", "approval_requirements", None),
    ("approval_requirements", "research", "approved"),
    ("research", "solution_architect", None),
    ("solution_architect", "approval_architecture", None),
    ("approval_architecture", "developer", "approved"),
    ("developer", "approval_code", None),
    ("approval_code", "approval_test_execution", "approved"),
    ("approval_test_execution", "review_testing", "approved"),
    ("review_testing", "correction", "failed"),
    ("correction", "developer", "fix"),
    ("review_testing", "approval_deployment", "passed"),
    ("approval_deployment", "documentation", "approved"),
]
RUN_STATUS = {AgentRunStatus.RUNNING: "running", AgentRunStatus.COMPLETED: "completed",
              AgentRunStatus.FAILED: "failed", AgentRunStatus.SKIPPED: "skipped",
              AgentRunStatus.PENDING: "pending"}
DECISION_STATUS = {ApprovalDecision.PENDING: "waiting_approval",
                   ApprovalDecision.APPROVED: "completed",
                   ApprovalDecision.REJECTED: "failed",
                   ApprovalDecision.REVISION_REQUESTED: "completed"}


def workflow_view(db: Session, execution_id: int) -> WorkflowView:
    execution = get_execution(db, execution_id)
    runs = db.scalars(select(AgentRun).where(AgentRun.execution_id == execution_id)
                      .order_by(AgentRun.id)).all()
    approvals = db.scalars(select(Approval).where(Approval.execution_id == execution_id)
                           .order_by(Approval.id)).all()
    latest_run = {run.agent_name: run for run in runs}
    run_counts: dict[str, int] = {}
    for run in runs:
        run_counts[run.agent_name] = run_counts.get(run.agent_name, 0) + 1
    latest_approval = {str(a.checkpoint): a for a in approvals}
    finished = execution.status in (ExecutionStatus.COMPLETED, ExecutionStatus.FAILED,
                                    ExecutionStatus.CANCELLED)

    nodes = []
    for node_id, label, kind, checkpoint in WORKFLOW_NODES:
        detail_text = None
        if kind == "agent":
            run = latest_run.get(node_id)
            node_status = RUN_STATUS[run.status] if run else "pending"
            if run and run_counts[node_id] > 1:
                detail_text = f"{run_counts[node_id]} runs"
            if run and run.duration_seconds is not None:
                detail_text = (detail_text + " · " if detail_text else "") + \
                    f"{run.duration_seconds:.1f}s"
        elif kind == "approval":
            approval = latest_approval.get(checkpoint)
            node_status = DECISION_STATUS[approval.decision] if approval else "pending"
            if approval and approval.decision != ApprovalDecision.PENDING:
                detail_text = str(approval.decision).replace("_", " ")
        else:
            node_status = "completed" if execution.correction_attempts else (
                "skipped" if finished and node_id == "correction" else "pending")
            if execution.correction_attempts:
                detail_text = f"{execution.correction_attempts}/2 attempts"
        if finished and node_status == "pending":
            node_status = "skipped"
        nodes.append(WorkflowNode(id=node_id, label=label, kind=kind, status=node_status,
                                  detail=detail_text))

    status_by_id = {n.id: n.status for n in nodes}
    done = {"completed", "running", "waiting_approval", "failed"}
    edges = [WorkflowEdge(source=s, target=t, label=label,
                          traversed=status_by_id[s] in done and status_by_id[t] in done)
             for s, t, label in WORKFLOW_EDGES]
    transitions = db.scalars(select(ExecutionLog).where(
        ExecutionLog.execution_id == execution_id,
        ExecutionLog.agent_name.in_(["orchestrator"])).order_by(ExecutionLog.id)).all()
    return WorkflowView(execution_id=execution_id, status=execution.status, nodes=nodes,
                        edges=edges,
                        transitions=[ExecutionLogRead.model_validate(t) for t in transitions])
