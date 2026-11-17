"""Agent 3: Solution Architect (Senior Enterprise Software Architect)."""

from app.agents import mock_knowledge as mk
from app.agents.base import BaseAgent
from app.agents.codegen import route_for
from app.agents.schemas import ArchitectureSpec
from app.prompts import templates
from app.prompts.templates import untrusted


class SolutionArchitectAgent(BaseAgent):
    name = "solution_architect"
    display_name = "Solution Architect"
    description = (
        "Designs the system architecture: components, database entities, API endpoints, "
        "security approach, implementation roadmap and architecture decisions."
    )
    role_prompt = templates.SOLUTION_ARCHITECT
    output_model = ArchitectureSpec

    def summarize_input(self, ctx):
        return {
            "functional_requirements": len(
                ctx.get("requirements_analysis", {}).get("functional_requirements", [])
            ),
            "recommended_stack": ctx.get("research_report", {}).get("recommended_stack"),
            "revision_feedback": ctx.get("revision_feedback"),
        }

    def build_user_prompt(self, ctx):
        parts = [
            "Design the solution architecture.",
            untrusted("approved_requirements", ctx.get("requirements_analysis", {})),
            untrusted("research_report", ctx.get("research_report", {})),
        ]
        if ctx.get("revision_feedback"):
            parts.append("A human reviewer requested changes to your previous architecture:")
            parts.append(untrusted("reviewer_feedback", ctx["revision_feedback"]))
            parts.append(untrusted("previous_architecture", ctx.get("architecture", {})))
        return "\n\n".join(parts)

    def mock_output(self, ctx):
        text = ctx.get("requirement", "")
        analysis = ctx.get("requirements_analysis", {})
        fr_text = " ".join(fr["description"] for fr in analysis.get("functional_requirements", []))
        entities = mk.detect_entities(text + " " + fr_text)
        has_auth = mk.mentions(mk.AUTH_PATTERN, text)
        has_reports = mk.mentions(mk.REPORT_PATTERN, text)
        roles = analysis.get("user_roles", [])

        apis = []
        if has_auth:
            apis += [
                {"method": "POST", "path": "/api/auth/register",
                 "description": "Register a user account", "auth_required": False},
                {"method": "POST", "path": "/api/auth/login",
                 "description": "Exchange credentials for a JWT", "auth_required": False},
            ]
        for entity in entities:
            route, name = route_for(entity["name"]), entity["name"]
            apis += [
                {"method": "POST", "path": route, "description": f"Create {name}"},
                {"method": "GET", "path": route, "description": f"List {name} records"},
                {"method": "GET", "path": f"{route}/{{id}}", "description": f"Get one {name}"},
                {"method": "PUT", "path": f"{route}/{{id}}", "description": f"Update {name}"},
                {"method": "DELETE", "path": f"{route}/{{id}}", "description": f"Delete {name}"},
            ]
        if has_reports:
            apis.append({"method": "GET", "path": "/api/reports/summary",
                         "description": "Aggregated report data", "roles": roles[1:3]})

        frontend = [{"name": "App shell & navigation",
                     "responsibility": "Layout, routing and role-aware menus"}]
        if has_auth:
            frontend.append({"name": "Login & registration pages",
                             "responsibility": "Authenticate users and store the session token"})
        frontend += [{"name": f"{e['name']} pages",
                      "responsibility": f"List, create, edit and delete {e['name']} records"}
                     for e in entities]
        if has_reports:
            frontend.append({"name": "Reports dashboard",
                             "responsibility": "Charts and tables built from report endpoints"})

        backend = [
            {"name": "API layer", "responsibility": "FastAPI routers, HTTP status codes"},
            {"name": "Validation", "responsibility": "Pydantic request/response models"},
            {"name": "Service layer", "responsibility": "Business rules and workflows"},
            {"name": "Persistence", "responsibility": "SQLAlchemy repositories and migrations"},
        ]
        if has_auth:
            backend.append({"name": "Auth module",
                            "responsibility": "Password hashing, JWT issuing, RBAC checks"})
        if has_reports:
            backend.append({"name": "Reporting service",
                            "responsibility": "Aggregations for management reports"})

        steps = [
            ("Project setup", "Repository, environments, CI skeleton", ["Repo", "CI pipeline"]),
            ("Data model", "Entities, migrations and seed data", ["Migrations"]),
            ("Core APIs", "CRUD endpoints with validation", ["REST API", "OpenAPI docs"]),
        ]
        if has_auth:
            steps.append(("Authentication & RBAC", "Login, tokens, role checks", ["Auth API"]))
        if has_reports:
            steps.append(("Reports", "Report endpoints and dashboard", ["Reports"]))
        steps += [
            ("Frontend", "Pages for each module", ["React UI"]),
            ("Testing", "Unit, API and E2E tests", ["Test report"]),
            ("Deployment", "Containerise and deploy after approval", ["Docker images"]),
        ]

        return {
            "architecture_overview": (
                "A three-tier web application: a React single-page frontend calls a FastAPI REST "
                "backend organised as a modular monolith, which persists data in a relational "
                f"database. Core entities: {', '.join(e['name'] for e in entities)}. "
                + ("Access is protected with JWT authentication and role-based authorisation. "
                   if has_auth else "")
                + "[MOCK MODE] Designed by AgentForge's rule set, not an LLM."
            ),
            "frontend_components": frontend,
            "backend_components": backend,
            "database_entities": entities,
            "api_specifications": apis,
            "authentication_strategy": (
                "Email/password login issuing short-lived JWT access tokens; passwords hashed "
                "with a slow salted algorithm; every endpoint checks the caller's role."
                if has_auth else
                "Not requested by the client; recommend at least JWT-based admin authentication."
            ),
            "security_considerations": [
                "Validate and size-limit every input; return generic error messages.",
                "Enforce role-based authorisation on every endpoint, not just in the UI.",
                "Store secrets in environment variables; never in code.",
                "Use HTTPS and restrictive CORS in production.",
                "Record approval and admin actions in an audit log.",
            ],
            "scalability_considerations": [
                "Stateless API instances behind a load balancer.",
                "Database indexes on foreign keys and frequently filtered columns.",
                "Pagination on all list endpoints.",
            ],
            "implementation_plan": [
                {"step": i, "title": t, "description": d, "deliverables": deliv}
                for i, (t, d, deliv) in enumerate(steps, 1)
            ],
            "architecture_decisions": [
                {"decision": "Modular monolith instead of microservices",
                 "rationale": "Lower complexity for an MVP with one team.",
                 "alternatives": ["Microservices"],
                 "trade_offs": "Modules scale together; can be split later."},
                {"decision": "REST + OpenAPI",
                 "rationale": "Simple, well-tooled, self-documenting.",
                 "alternatives": ["GraphQL"],
                 "trade_offs": "Clients may make more requests for nested data."},
                {"decision": "Generated prototype uses in-memory storage",
                 "rationale": "Lets generated code be tested in an offline sandbox.",
                 "alternatives": ["PostgreSQL from day one"],
                 "trade_offs": "Persistence layer must be added before production."},
            ],
        }
