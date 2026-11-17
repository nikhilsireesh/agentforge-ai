"""Agent 2: Research Agent (Senior Technical Research Engineer).

The model cannot browse, so every source is marked "unverified". When
RESEARCH_CHECK_URLS=true, public https URLs are probed and marked
"reachable"/"unreachable" (which still does not verify their content).
"""

import ipaddress
import socket
from typing import Any
from urllib.parse import urlparse

import httpx

from app.agents import mock_knowledge as mk
from app.agents.base import BaseAgent
from app.agents.schemas import ResearchReport
from app.config import get_settings
from app.prompts import templates
from app.prompts.templates import untrusted

MOCK_NOTE = (
    "MOCK MODE: produced by AgentForge's built-in rule set, not by an LLM and not from live web "
    "research. Source URLs are well-known documentation home pages and were not accessed during "
    "this run. A human must verify all recommendations."
)


def _is_public_https(url: str) -> bool:
    """Block SSRF: only https URLs that resolve to public IP addresses."""
    parsed = urlparse(url)
    if parsed.scheme != "https" or not parsed.hostname:
        return False
    try:
        infos = socket.getaddrinfo(parsed.hostname, 443)
    except OSError:
        return False
    for info in infos:
        address = ipaddress.ip_address(info[4][0])
        if not address.is_global:
            return False
    return True


def check_url(url: str) -> str:
    if not _is_public_https(url):
        return "unreachable"
    try:
        response = httpx.get(url, timeout=5, follow_redirects=False)
        return "reachable" if response.status_code < 400 else "unreachable"
    except httpx.HTTPError:
        return "unreachable"


class ResearchAgent(BaseAgent):
    name = "research"
    display_name = "Research Agent"
    description = (
        "Recommends a technology stack, compares frameworks and libraries, and identifies "
        "technical risks. Recommendations are labelled as requiring verification."
    )
    role_prompt = templates.RESEARCH
    output_model = ResearchReport

    def summarize_input(self, ctx):
        analysis = ctx.get("requirements_analysis", {})
        return {
            "functional_requirements": len(analysis.get("functional_requirements", [])),
            "preferred_tech_stack": ctx.get("project", {}).get("preferred_tech_stack"),
        }

    def build_user_prompt(self, ctx):
        return "\n\n".join([
            "Research the technical approach for these approved requirements.",
            untrusted("project_details", ctx.get("project", {})),
            untrusted("approved_requirements", ctx.get("requirements_analysis", {})),
        ])

    def post_process(self, output: ResearchReport, ctx: dict[str, Any]) -> ResearchReport:
        check = get_settings().research_check_urls
        for source in output.sources:
            source.verification = "unverified"
            if check and source.url:
                source.verification = check_url(source.url)
        if "verif" not in output.verification_note.lower():
            output.verification_note = (
                "Model-generated recommendations based on training knowledge; not verified "
                "against live documentation. " + output.verification_note
            ).strip()
        return output

    def mock_output(self, ctx):
        project = ctx.get("project", {})
        text = ctx.get("requirement", "")
        has_auth = mk.mentions(mk.AUTH_PATTERN, text)
        has_reports = mk.mentions(mk.REPORT_PATTERN, text)
        stack = {
            "backend": "Python 3.11 + FastAPI",
            "frontend": "React + Vite",
            "database": "PostgreSQL (SQLite for local development)",
            "orm_migrations": "SQLAlchemy 2 + Alembic",
            "authentication": "JWT access tokens with role-based access control",
            "testing": "pytest + HTTPX; Playwright for UI flows",
            "deployment": "Docker + Docker Compose",
        }
        recommendations = [
            "Start with a modular monolith; split services only when scale requires it.",
            "Validate all input at the API boundary with Pydantic models.",
            "Automate tests in CI before every deployment.",
        ]
        if project.get("preferred_tech_stack"):
            stack["client_preference"] = project["preferred_tech_stack"]
            recommendations.insert(0, "The client's preferred stack should take precedence; "
                                      "confirm whether the defaults above are acceptable.")
        integrations = []
        if mk.mentions(r"notif|alert|email", text):
            integrations.append("Email delivery service (SMTP or transactional email API).")
        if mk.mentions(r"payroll|erp|sso|ldap|active directory", text):
            integrations.append("Integration with existing enterprise systems mentioned by the "
                                "client.")
        risks = [
            {"risk": "Requirements contain unconfirmed assumptions and missing business rules.",
             "impact": "high",
             "mitigation": "Resolve clarification questions before final sign-off."},
            {"risk": "Scope growth from broad features (administration, reporting).",
             "impact": "medium", "mitigation": "Agree an MVP scope and change process."},
        ]
        if has_auth:
            risks.append({"risk": "Authentication and authorisation mistakes expose data.",
                          "impact": "high",
                          "mitigation": "Use proven libraries, hash passwords, test RBAC rules."})
        if has_reports:
            risks.append({"risk": "Report queries may become slow as data grows.",
                          "impact": "medium",
                          "mitigation": "Add indexes and pre-aggregate heavy reports."})
        complexity = project.get("complexity") or ("high" if len(
            mk.extract_features(text)) > 8 else "medium")
        return {
            "recommended_stack": stack,
            "framework_comparison": [
                {"category": "Backend framework", "options": ["FastAPI", "Django", "Flask"],
                 "recommended": "FastAPI",
                 "rationale": "Type-driven validation, automatic OpenAPI docs, high performance."},
                {"category": "Frontend framework", "options": ["React", "Vue", "Angular"],
                 "recommended": "React",
                 "rationale": "Large ecosystem and component libraries for dashboards."},
                {"category": "Database", "options": ["PostgreSQL", "MySQL", "SQLite"],
                 "recommended": "PostgreSQL",
                 "rationale": "Reliable relational database with strong constraint support."},
            ],
            "library_recommendations": [
                {"name": "Pydantic", "purpose": "Request/response validation"},
                {"name": "SQLAlchemy", "purpose": "ORM and query building"},
                {"name": "Alembic", "purpose": "Database schema migrations"},
                {"name": "PyJWT", "purpose": "Signed access tokens"},
                {"name": "React Router", "purpose": "Client-side routing"},
            ] + ([{"name": "Recharts", "purpose": "Report charts"}] if has_reports else []),
            "api_integrations": integrations
            or ["No external API integrations were identified in the requirement."],
            "implementation_options": [
                {"name": "Modular monolith (recommended)",
                 "description": "One deployable backend with clear internal modules.",
                 "pros": ["Simple to build, test and deploy"],
                 "cons": ["Scales as one unit"]},
                {"name": "Microservices",
                 "description": "Separate services per domain area.",
                 "pros": ["Independent scaling"],
                 "cons": ["Much higher operational complexity for an MVP"]},
            ],
            "technical_risks": risks,
            "complexity_estimate": complexity,
            "recommendations": recommendations,
            "sources": [
                {"title": "FastAPI documentation", "url": "https://fastapi.tiangolo.com/"},
                {"title": "SQLAlchemy documentation", "url": "https://docs.sqlalchemy.org/"},
                {"title": "React documentation", "url": "https://react.dev/"},
                {"title": "PostgreSQL documentation", "url": "https://www.postgresql.org/docs/"},
            ],
            "verification_note": MOCK_NOTE,
        }
