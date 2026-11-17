"""Import every model here so `Base.metadata` knows about all tables
(Alembic and the test suite rely on this)."""

from app.models.agent_run import AgentRun
from app.models.approval import Approval
from app.models.artifact import Artifact
from app.models.base import Base
from app.models.execution import Execution
from app.models.execution_log import ExecutionLog
from app.models.project import Project
from app.models.requirement import Requirement
from app.models.test_result import TestResult
from app.models.user import User

__all__ = [
    "AgentRun",
    "Approval",
    "Artifact",
    "Base",
    "Execution",
    "ExecutionLog",
    "Project",
    "Requirement",
    "TestResult",
    "User",
]
