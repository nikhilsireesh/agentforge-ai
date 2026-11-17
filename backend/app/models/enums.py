"""Allowed values for every status/category column.

Using `StrEnum` means each member behaves like a normal string, so it
serializes cleanly to JSON and compares equal to its text value.
"""

from enum import StrEnum


class UserRole(StrEnum):
    ADMIN = "admin"
    REVIEWER = "reviewer"  # can approve/reject checkpoints
    MEMBER = "member"  # can create projects and run workflows


class ProjectStatus(StrEnum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    AWAITING_APPROVAL = "awaiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"


class ProjectComplexity(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class ApprovalStatus(StrEnum):
    """Approval state of a requirement or artifact."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class ExecutionStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AgentRunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class ApprovalCheckpoint(StrEnum):
    REQUIREMENTS = "requirements"
    ARCHITECTURE = "architecture"
    CODE = "code"
    TEST_EXECUTION = "test_execution"
    DEPLOYMENT = "deployment"


class ApprovalDecision(StrEnum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    REVISION_REQUESTED = "revision_requested"


class ArtifactType(StrEnum):
    SOURCE_CODE = "source_code"
    TEST = "test"
    CONFIGURATION = "configuration"
    DOCUMENTATION = "documentation"
    REPORT = "report"


class TestStatus(StrEnum):
    __test__ = False  # stop pytest from trying to collect this class as a test

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


class LogLevel(StrEnum):
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
