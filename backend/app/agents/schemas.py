"""Structured output contracts for every agent.

Every LLM response is parsed into one of these Pydantic models. If the
response does not match, the agent retries with the validation error as
feedback. Nothing unvalidated is passed to the next agent.
"""

import keyword
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

ShortText = Field(max_length=2000)


# ---------------------------------------------------------------- Requirement Analyst
class RequirementItem(BaseModel):
    id: str = Field(max_length=20)
    description: str = Field(max_length=1000)
    priority: Literal["must", "should", "could"] = "must"
    # stated = in the client text; inferred = logically implied; assumed = not confirmed
    source: Literal["stated", "inferred", "assumed"] = "stated"


class UserStory(BaseModel):
    id: str = Field(max_length=20)
    role: str = Field(max_length=100)
    story: str = Field(max_length=1000)
    related_requirements: list[str] = Field(default_factory=list)


class AcceptanceCriterion(BaseModel):
    id: str = Field(max_length=20)
    requirement_id: str = Field(max_length=20)
    criterion: str = Field(max_length=1000)


class RequirementsAnalysis(BaseModel):
    project_name: str = Field(max_length=200)
    business_problem: str = Field(max_length=3000)
    objectives: list[str] = Field(default_factory=list, max_length=30)
    functional_requirements: list[RequirementItem] = Field(min_length=1, max_length=60)
    non_functional_requirements: list[RequirementItem] = Field(default_factory=list, max_length=40)
    user_roles: list[str] = Field(default_factory=list, max_length=20)
    user_stories: list[UserStory] = Field(default_factory=list, max_length=60)
    acceptance_criteria: list[AcceptanceCriterion] = Field(default_factory=list, max_length=120)
    dependencies: list[str] = Field(default_factory=list, max_length=30)
    constraints: list[str] = Field(default_factory=list, max_length=30)
    assumptions: list[str] = Field(default_factory=list, max_length=30)
    missing_information: list[str] = Field(default_factory=list, max_length=30)
    ambiguities: list[str] = Field(default_factory=list, max_length=30)
    contradictions: list[str] = Field(default_factory=list, max_length=30)
    clarification_questions: list[str] = Field(default_factory=list, max_length=30)


# ---------------------------------------------------------------- Research
class FrameworkComparison(BaseModel):
    category: str = Field(max_length=100)
    options: list[str] = Field(max_length=6)
    recommended: str = Field(max_length=100)
    rationale: str = Field(max_length=1500)


class LibraryRecommendation(BaseModel):
    name: str = Field(max_length=100)
    purpose: str = Field(max_length=500)
    notes: str = Field(default="", max_length=500)


class ImplementationOption(BaseModel):
    name: str = Field(max_length=150)
    description: str = Field(max_length=1500)
    pros: list[str] = Field(default_factory=list, max_length=10)
    cons: list[str] = Field(default_factory=list, max_length=10)


class TechnicalRisk(BaseModel):
    risk: str = Field(max_length=500)
    impact: Literal["low", "medium", "high"]
    mitigation: str = Field(max_length=1000)


class Source(BaseModel):
    title: str = Field(max_length=300)
    url: str | None = Field(default=None, max_length=500)
    # The model cannot browse. Sources are always "unverified" unless a URL check ran;
    # even "reachable" only means the URL responded, not that its content was checked.
    verification: Literal["unverified", "reachable", "unreachable"] = "unverified"


class ResearchReport(BaseModel):
    recommended_stack: dict[str, str]
    framework_comparison: list[FrameworkComparison] = Field(default_factory=list, max_length=10)
    library_recommendations: list[LibraryRecommendation] = Field(
        default_factory=list, max_length=25
    )
    api_integrations: list[str] = Field(default_factory=list, max_length=20)
    implementation_options: list[ImplementationOption] = Field(default_factory=list, max_length=6)
    technical_risks: list[TechnicalRisk] = Field(default_factory=list, max_length=20)
    complexity_estimate: Literal["low", "medium", "high"] = "medium"
    recommendations: list[str] = Field(default_factory=list, max_length=25)
    sources: list[Source] = Field(default_factory=list, max_length=20)
    verification_note: str = Field(default="", max_length=1000)


# ---------------------------------------------------------------- Solution Architect
FIELD_TYPES = Literal["str", "int", "float", "bool", "date"]


class FieldSpec(BaseModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]{0,40}$")
    type: FIELD_TYPES = "str"
    required: bool = True
    description: str = Field(default="", max_length=300)

    @field_validator("name")
    @classmethod
    def not_reserved(cls, value: str) -> str:
        if keyword.iskeyword(value) or value == "id":
            raise ValueError(f"'{value}' is reserved (ids are added automatically)")
        return value


class EntitySpec(BaseModel):
    name: str = Field(pattern=r"^[A-Z][A-Za-z0-9]{0,40}$")
    description: str = Field(default="", max_length=500)
    fields: list[FieldSpec] = Field(min_length=1, max_length=25)
    relationships: list[str] = Field(default_factory=list, max_length=10)


class ComponentSpec(BaseModel):
    name: str = Field(max_length=100)
    responsibility: str = Field(max_length=500)


class ApiSpec(BaseModel):
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
    path: str = Field(max_length=200)
    description: str = Field(max_length=500)
    auth_required: bool = True
    roles: list[str] = Field(default_factory=list, max_length=10)


class ImplementationStep(BaseModel):
    step: int
    title: str = Field(max_length=200)
    description: str = Field(max_length=1000)
    deliverables: list[str] = Field(default_factory=list, max_length=10)


class ArchitectureDecision(BaseModel):
    decision: str = Field(max_length=300)
    rationale: str = Field(max_length=1000)
    alternatives: list[str] = Field(default_factory=list, max_length=6)
    trade_offs: str = Field(default="", max_length=1000)


class ArchitectureSpec(BaseModel):
    architecture_overview: str = Field(max_length=4000)
    frontend_components: list[ComponentSpec] = Field(default_factory=list, max_length=30)
    backend_components: list[ComponentSpec] = Field(default_factory=list, max_length=30)
    database_entities: list[EntitySpec] = Field(min_length=1, max_length=15)
    api_specifications: list[ApiSpec] = Field(default_factory=list, max_length=80)
    authentication_strategy: str = Field(max_length=2000)
    security_considerations: list[str] = Field(default_factory=list, max_length=25)
    scalability_considerations: list[str] = Field(default_factory=list, max_length=25)
    implementation_plan: list[ImplementationStep] = Field(default_factory=list, max_length=20)
    architecture_decisions: list[ArchitectureDecision] = Field(default_factory=list, max_length=15)

    @model_validator(mode="after")
    def unique_entities(self) -> "ArchitectureSpec":
        names = [entity.name for entity in self.database_entities]
        if len(names) != len(set(names)):
            raise ValueError("database_entities must have unique names")
        return self


# ---------------------------------------------------------------- Developer
ALLOWED_EXTENSIONS = {
    ".py", ".md", ".txt", ".toml", ".json", ".cfg", ".ini", ".yml", ".yaml",
    ".js", ".jsx", ".ts", ".tsx", ".html", ".css",
}
SAFE_PATH = re.compile(r"^[A-Za-z0-9_\-]+(/[A-Za-z0-9_\-.]+)*$|^[A-Za-z0-9_\-.]+$")


class CodeArtifact(BaseModel):
    file_path: str = Field(max_length=200)
    file_type: str = Field(max_length=30)
    description: str = Field(max_length=500)
    content: str = Field(max_length=60_000)
    dependencies: list[str] = Field(default_factory=list, max_length=20)
    proposed_action: Literal["create", "update"] = "create"

    @field_validator("file_path")
    @classmethod
    def safe_relative_path(cls, value: str) -> str:
        value = value.strip().replace("\\", "/")
        parts = value.split("/")
        if (
            value.startswith("/")
            or ".." in parts
            or not SAFE_PATH.match(value)
            or any(part.startswith(".") for part in parts)
        ):
            raise ValueError(f"unsafe file path: {value!r}")
        suffix = "." + value.rsplit(".", 1)[-1] if "." in parts[-1] else ""
        if suffix not in ALLOWED_EXTENSIONS:
            raise ValueError(f"file type not allowed: {value!r}")
        return value


class DeveloperOutput(BaseModel):
    summary: str = Field(max_length=3000)
    artifacts: list[CodeArtifact] = Field(min_length=1, max_length=25)
    notes: list[str] = Field(default_factory=list, max_length=20)

    @model_validator(mode="after")
    def check_bundle(self) -> "DeveloperOutput":
        paths = [artifact.file_path for artifact in self.artifacts]
        if len(paths) != len(set(paths)):
            raise ValueError("artifact file paths must be unique")
        if not any(p.split("/")[-1].startswith("test_") and p.endswith(".py") for p in paths):
            raise ValueError("at least one pytest file named test_*.py is required")
        if sum(len(artifact.content) for artifact in self.artifacts) > 300_000:
            raise ValueError("total generated code exceeds 300 KB")
        return self


# ---------------------------------------------------------------- Review & Testing
class ReviewIssue(BaseModel):
    id: str = Field(max_length=20)
    severity: Literal["critical", "high", "medium", "low"]
    category: str = Field(max_length=50)
    file_path: str | None = Field(default=None, max_length=200)
    description: str = Field(max_length=1500)
    recommendation: str = Field(max_length=1500)


class TestCaseSpec(BaseModel):
    __test__ = False

    id: str = Field(max_length=20)
    name: str = Field(max_length=200)
    category: Literal[
        "unit", "integration", "api", "functional", "edge_case", "regression", "security"
    ]
    description: str = Field(max_length=1000)
    requirement_id: str | None = Field(default=None, max_length=20)


class CoverageItem(BaseModel):
    requirement_id: str = Field(max_length=20)
    status: Literal["covered", "partial", "not_covered"]
    evidence: str = Field(max_length=1000)


class ReviewAgentOutput(BaseModel):
    """What the LLM produces. Pass/fail counts are NOT here: they come from real execution."""

    review_status: Literal["approved", "changes_requested"]
    summary: str = Field(max_length=3000)
    issues: list[ReviewIssue] = Field(default_factory=list, max_length=50)
    test_cases: list[TestCaseSpec] = Field(default_factory=list, max_length=60)
    requirement_coverage: list[CoverageItem] = Field(default_factory=list, max_length=60)
    recommendations: list[str] = Field(default_factory=list, max_length=25)


# ---------------------------------------------------------------- Documentation
class DocumentationNarrative(BaseModel):
    """Narrative sections. Factual sections (tables, schema, APIs, test counts) are rendered
    directly from validated state so documentation cannot drift from what was built."""

    project_overview: str = Field(max_length=4000)
    executive_summary: str = Field(max_length=3000)
    known_limitations: list[str] = Field(default_factory=list, max_length=25)
    future_enhancements: list[str] = Field(default_factory=list, max_length=25)
    deployment_notes: list[str] = Field(default_factory=list, max_length=25)
    installation_notes: list[str] = Field(default_factory=list, max_length=25)
