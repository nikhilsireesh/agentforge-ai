"""Execution, approval and test-result endpoints."""

import logging

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, rate_limit, require_reviewer
from app.models import AgentRun, ExecutionLog, TestResult, User
from app.models.enums import ApprovalDecision, ExecutionStatus
from app.schemas.common import Page
from app.schemas.execution import (
    AgentRunRead,
    ApprovalRead,
    DecisionRequest,
    ExecuteRequest,
    ExecutionDetail,
    ExecutionLogRead,
    ExecutionRead,
    RejectRequest,
    TestResultRead,
    WorkflowView,
)
from app.services import artifact_service, execution_service

router = APIRouter(tags=["Executions & Approvals"])
audit = logging.getLogger("agentforge.audit")


@router.post("/api/projects/{project_id}/execute", response_model=ExecutionRead,
             status_code=202, dependencies=[Depends(rate_limit("execute"))])
def execute(project_id: int, payload: ExecuteRequest | None = None,
            db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    execution = execution_service.start(db, project_id, payload.requirement_id if payload
                                        else None, user)
    audit.info("user=%s action=execute project=%s execution=%s", user.id, project_id,
               execution.id)
    db.refresh(execution)
    return execution_service.to_read(execution)


@router.get("/api/executions", response_model=Page[ExecutionRead])
def list_executions(project_id: int | None = None, status: ExecutionStatus | None = None,
                    page: int = Query(default=1, ge=1),
                    page_size: int = Query(default=20, ge=1, le=100),
                    db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    items, total = execution_service.list_executions(db, project_id, status, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.get("/api/executions/{execution_id}", response_model=ExecutionDetail)
def get_execution(execution_id: int, db: Session = Depends(get_db),
                  _user: User = Depends(get_current_user)):
    return execution_service.detail(db, execution_id)


@router.get("/api/executions/{execution_id}/agents", response_model=list[AgentRunRead])
def agent_runs(execution_id: int, db: Session = Depends(get_db),
               _user: User = Depends(get_current_user)):
    execution_service.get_execution(db, execution_id)
    return db.scalars(select(AgentRun).where(AgentRun.execution_id == execution_id)
                      .order_by(AgentRun.id)).all()


@router.get("/api/executions/{execution_id}/logs", response_model=list[ExecutionLogRead])
def logs(execution_id: int, after_id: int = Query(default=0, ge=0),
         limit: int = Query(default=500, ge=1, le=2000), db: Session = Depends(get_db),
         _user: User = Depends(get_current_user)):
    execution_service.get_execution(db, execution_id)
    return db.scalars(select(ExecutionLog).where(ExecutionLog.execution_id == execution_id,
                                                 ExecutionLog.id > after_id)
                      .order_by(ExecutionLog.id).limit(limit)).all()


@router.get("/api/executions/{execution_id}/tests", response_model=list[TestResultRead])
def test_results(execution_id: int, db: Session = Depends(get_db),
                 _user: User = Depends(get_current_user)):
    execution_service.get_execution(db, execution_id)
    return db.scalars(select(TestResult).where(TestResult.execution_id == execution_id)
                      .order_by(TestResult.iteration, TestResult.id)).all()


@router.get("/api/executions/{execution_id}/workflow", response_model=WorkflowView)
def workflow(execution_id: int, db: Session = Depends(get_db),
             _user: User = Depends(get_current_user)):
    return execution_service.workflow_view(db, execution_id)


@router.get("/api/executions/{execution_id}/package")
def download_package(execution_id: int, db: Session = Depends(get_db),
                     _user: User = Depends(get_current_user)) -> Response:
    filename, content = artifact_service.delivery_package(db, execution_id)
    return Response(content, media_type="application/zip",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})


@router.post("/api/executions/{execution_id}/cancel", response_model=ExecutionRead)
def cancel(execution_id: int, db: Session = Depends(get_db),
           user: User = Depends(get_current_user)):
    execution = execution_service.cancel(db, execution_id, user)
    audit.info("user=%s action=cancel execution=%s", user.id, execution_id)
    return execution_service.to_read(execution)


@router.get("/api/approvals", response_model=Page[ApprovalRead])
def list_approvals(decision: ApprovalDecision | None = None, execution_id: int | None = None,
                   page: int = Query(default=1, ge=1),
                   page_size: int = Query(default=50, ge=1, le=100),
                   db: Session = Depends(get_db), _user: User = Depends(get_current_user)):
    items, total = execution_service.list_approvals(db, decision, execution_id, page, page_size)
    return Page(items=items, total=total, page=page, page_size=page_size)


@router.post("/api/executions/{execution_id}/approve", response_model=ApprovalRead)
def approve(execution_id: int, payload: DecisionRequest | None = None,
            db: Session = Depends(get_db), reviewer: User = Depends(require_reviewer)):
    approval = execution_service.decide(db, execution_id, ApprovalDecision.APPROVED,
                                        payload.feedback if payload else None, reviewer)
    audit.info("user=%s action=approve execution=%s checkpoint=%s", reviewer.id,
               execution_id, approval.checkpoint)
    return execution_service.approval_to_read(approval)


@router.post("/api/executions/{execution_id}/reject", response_model=ApprovalRead)
def reject(execution_id: int, payload: RejectRequest, db: Session = Depends(get_db),
           reviewer: User = Depends(require_reviewer)):
    decision = (ApprovalDecision.REVISION_REQUESTED if payload.request_revision
                else ApprovalDecision.REJECTED)
    approval = execution_service.decide(db, execution_id, decision, payload.feedback, reviewer)
    audit.info("user=%s action=%s execution=%s checkpoint=%s", reviewer.id, decision,
               execution_id, approval.checkpoint)
    return execution_service.approval_to_read(approval)
