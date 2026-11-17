from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.enums import (
    AgentRunStatus,
    ApprovalCheckpoint,
    ApprovalDecision,
    ExecutionStatus,
    LogLevel,
    TestStatus,
)
from app.schemas.common import ORMModel


class ExecuteRequest(BaseModel):
    requirement_id: int | None = Field(
        default=None, description="Requirement to analyse. Defaults to the latest one."
    )


class ApprovalRead(ORMModel):
    id: int
    execution_id: int
    checkpoint: ApprovalCheckpoint
    decision: ApprovalDecision
    feedback: str | None
    reviewer_id: int | None
    reviewer_name: str | None = None
    created_at: datetime
    decided_at: datetime | None
    project_id: int | None = None
    project_name: str | None = None
    summary: dict[str, Any] | None = None


class ExecutionRead(ORMModel):
    id: int
    project_id: int
    project_name: str | None = None
    requirement_id: int | None
    status: ExecutionStatus
    current_agent: str | None
    llm_mode: str
    correction_attempts: int
    error_message: str | None
    started_at: datetime
    completed_at: datetime | None
    total_duration: float | None


class ExecutionDetail(ExecutionRead):
    pending_approval: ApprovalRead | None = None
    # Latest successful output of each agent, keyed by agent name.
    outputs: dict[str, Any] = {}


class AgentRunRead(ORMModel):
    id: int
    execution_id: int
    agent_name: str
    attempt: int
    status: AgentRunStatus
    input_data: dict[str, Any] | None
    output_data: dict[str, Any] | None
    started_at: datetime | None
    completed_at: datetime | None
    duration_seconds: float | None
    prompt_tokens: int
    completion_tokens: int
    token_usage: int
    is_mock: bool
    error_message: str | None


class ExecutionLogRead(ORMModel):
    id: int
    execution_id: int
    agent_name: str | None
    log_level: LogLevel
    message: str
    timestamp: datetime


class TestResultRead(ORMModel):
    __test__ = False

    id: int
    execution_id: int
    iteration: int
    test_name: str
    test_status: TestStatus
    execution_output: str | None
    error_message: str | None
    duration_seconds: float | None
    created_at: datetime


class DecisionRequest(BaseModel):
    feedback: str | None = Field(default=None, max_length=5000)


class RejectRequest(BaseModel):
    feedback: str = Field(min_length=3, max_length=5000)
    request_revision: bool = Field(
        default=False,
        description="true = send back to the agent with this feedback; false = stop the workflow",
    )


WorkflowNodeStatus = Literal[
    "pending", "running", "completed", "failed", "waiting_approval", "skipped"
]


class WorkflowNode(BaseModel):
    id: str
    label: str
    kind: Literal["agent", "approval", "control"]
    status: WorkflowNodeStatus
    detail: str | None = None


class WorkflowEdge(BaseModel):
    source: str
    target: str
    label: str | None = None
    traversed: bool = False


class WorkflowView(BaseModel):
    execution_id: int
    status: ExecutionStatus
    nodes: list[WorkflowNode]
    edges: list[WorkflowEdge]
    transitions: list[ExecutionLogRead]
