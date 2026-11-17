"""Agent 1: Requirement Analyst (Senior Business Analyst)."""

from typing import Any

from app.agents import mock_knowledge as mk
from app.agents.base import AgentValidationError, BaseAgent
from app.agents.schemas import RequirementsAnalysis
from app.prompts import templates
from app.prompts.templates import untrusted


def project_context(ctx: dict[str, Any]) -> dict[str, Any]:
    project = ctx.get("project", {})
    return {k: v for k, v in project.items() if v}


class RequirementAnalystAgent(BaseAgent):
    name = "requirement_analyst"
    display_name = "Requirement Analyst"
    description = (
        "Turns the client's natural-language request into structured requirements, user stories "
        "and acceptance criteria, and flags missing or ambiguous information."
    )
    role_prompt = templates.REQUIREMENT_ANALYST
    output_model = RequirementsAnalysis

    def summarize_input(self, ctx):
        return {
            "requirement_chars": len(ctx["requirement"]),
            "requirement_preview": ctx["requirement"][:300],
            "revision_feedback": ctx.get("revision_feedback"),
        }

    def build_user_prompt(self, ctx):
        parts = [
            "Analyse this client requirement.",
            untrusted("project_details", project_context(ctx)),
            untrusted("client_requirement", ctx["requirement"]),
        ]
        if ctx.get("revision_feedback"):
            parts.append("A human reviewer requested a revision of your previous analysis:")
            parts.append(untrusted("reviewer_feedback", ctx["revision_feedback"]))
            parts.append(untrusted("previous_analysis", ctx.get("requirements_analysis", {})))
        return "\n\n".join(parts)

    def validate_output(self, output, ctx):
        ids = [item.id for item in output.functional_requirements]
        if len(ids) != len(set(ids)):
            raise AgentValidationError("functional requirement ids must be unique")

    def mock_output(self, ctx):
        text = ctx["requirement"]
        project = ctx.get("project", {})
        features = mk.extract_features(text)
        roles = mk.detect_roles(text)
        assumptions = [
            "Web application used through modern desktop and mobile browsers.",
            "Single organisation (no multi-tenancy).",
            "Non-functional requirements marked 'assumed' were not stated by the client.",
        ]
        if not roles:
            roles = ["End User", "Administrator"]
            assumptions.append("User roles were not stated; 'End User' and 'Administrator' "
                               "are assumed.")

        frs = [
            {"id": f"FR-{i:02d}", "description": f"The system shall support {feature}.",
             "priority": "must", "source": "stated"}
            for i, feature in enumerate(features, 1)
        ]
        has_auth = mk.mentions(mk.AUTH_PATTERN, text)
        if len(roles) > 1:
            frs.append({
                "id": f"FR-{len(frs) + 1:02d}",
                "description": "The system shall restrict each function to the user roles "
                               "permitted to use it.",
                "priority": "must", "source": "inferred",
            })

        def nfr(i, text_, source):
            return {"id": f"NFR-{i:02d}", "description": text_, "priority": "should",
                    "source": source}

        nfrs = [
            nfr(1, "Passwords are stored only as salted hashes; all traffic uses HTTPS.",
                "inferred" if has_auth else "assumed"),
            nfr(2, "Typical API responses complete in under 500 ms at expected load.", "assumed"),
            nfr(3, "The system is available during business hours with daily backups.",
                "assumed"),
            nfr(4, "The user interface is responsive and accessible (WCAG 2.1 AA).", "assumed"),
            nfr(5, "Approval and administrative actions are audit-logged with user and time.",
                "inferred" if mk.mentions(r"approv|admin", text) else "assumed"),
        ]

        stories, criteria = [], []
        for i, item in enumerate(frs, 1):
            feature = features[i - 1] if i <= len(features) else "role-based access"
            role = mk.pick_role(feature, roles)
            stories.append({
                "id": f"US-{i:02d}", "role": role,
                "story": f"As a {role}, I want {feature} so that this part of the business "
                         "process is handled in the system.",
                "related_requirements": [item["id"]],
            })
            criteria.append({
                "id": f"AC-{i:02d}", "requirement_id": item["id"],
                "criterion": f"Given an authorised {role}, when they use {feature}, then the "
                             "action is saved and confirmed; invalid input is rejected with a "
                             "clear error message.",
            })

        missing = [
            "Expected number of users and data volume.",
            "Hosting/deployment environment and any compliance requirements.",
            "Data retention and backup requirements.",
        ]
        if has_auth:
            missing.append("Authentication method (email/password, SSO, MFA) is not specified.")
        if mk.mentions(r"\bleave\b", text):
            missing.append("Leave policy rules (leave types, accrual, carry-over, approval "
                           "chain) are not specified.")
        if mk.mentions(r"inventory|stock", text):
            missing.append("Stock valuation method and reorder rules are not specified.")
        if mk.mentions(mk.REPORT_PATTERN, text):
            missing.append("Report contents, filters and export formats are not specified.")
        if mk.mentions(r"notif|alert|email", text):
            missing.append("Notification channels (email, in-app, SMS) are not specified.")

        vague = ("administration", "management", "tracking", "reports", "alerts", "catalogue")
        ambiguities = [
            f"'{feature}' is broad; the exact operations and rules are not defined."
            for feature in features if any(word in feature.lower() for word in vague)
        ]
        questions = [
            f"Please clarify: {item[0].lower() + item[1:].rstrip('.')}?"
            if not item.endswith("?") else item
            for item in missing
        ]
        constraints = [line.strip() for line in (project.get("constraints") or "").splitlines()
                       if line.strip()]
        if project.get("preferred_tech_stack"):
            constraints.append(f"Preferred technology stack: {project['preferred_tech_stack']}")
        if ctx.get("revision_feedback"):
            assumptions.append(
                "[MOCK MODE] Reviewer feedback was recorded but cannot be semantically applied "
                f"without an LLM: \"{ctx['revision_feedback'][:300]}\""
            )

        dependencies = []
        if has_auth:
            dependencies.append("Decision on identity provider / authentication approach.")
        if mk.mentions(r"notif|alert|email", text):
            dependencies.append("Email or messaging service for notifications.")
        if mk.mentions(r"payroll|erp|integrat", text):
            dependencies.append("Access to existing systems mentioned in the requirement.")

        return {
            "project_name": project.get("name") or "Untitled Project",
            "business_problem": (
                "The client needs a software system that supports "
                + ", ".join(features)
                + ". The current process, pain points and scale were not described and should "
                  "be confirmed with the client."
            ),
            "objectives": [f"Provide {feature}" for feature in features[:8]]
            + (["Give each role access only to the functions it needs"] if len(roles) > 1
               else []),
            "functional_requirements": frs,
            "non_functional_requirements": nfrs,
            "user_roles": roles,
            "user_stories": stories,
            "acceptance_criteria": criteria,
            "dependencies": dependencies,
            "constraints": constraints,
            "assumptions": assumptions,
            "missing_information": missing,
            "ambiguities": ambiguities,
            "contradictions": [],
            "clarification_questions": questions,
        }
