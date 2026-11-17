"""Shared state passed between LangGraph nodes.

Each node reads the validated fields it needs and returns only the fields it
changes. LangGraph merges the updates and checkpoints the result after every
step, which is what makes pausing for human approval and resuming possible.
"""

import operator
from typing import Annotated, Any, TypedDict


class AgentForgeState(TypedDict, total=False):
    project_id: int
    execution_id: int
    requirement_id: int | None
    requirement: str
    project: dict[str, Any]
    llm_mode: str

    requirements_analysis: dict[str, Any]
    research_report: dict[str, Any]
    architecture: dict[str, Any]
    implementation_plan: list[dict[str, Any]]
    generated_artifacts: list[dict[str, Any]]
    code_version: int
    code_approved: bool
    developer_notes: list[str]
    review_report: dict[str, Any]
    test_results: dict[str, Any]
    correction_attempts: int
    documentation: dict[str, Any]

    approval_status: str
    last_checkpoint: str
    revision_feedback: str | None

    current_agent: str
    execution_status: str
    # Annotated with operator.add: updates are appended instead of replaced.
    execution_logs: Annotated[list[str], operator.add]
    errors: Annotated[list[str], operator.add]


MAX_CORRECTION_ATTEMPTS = 2
