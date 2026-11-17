"""Agent 6: Documentation Agent (Senior Technical Writer).

Writes narrative sections; the factual documents are assembled by
app/services/docs_renderer.py from validated workflow state.
"""

from app.agents.base import BaseAgent
from app.agents.schemas import DocumentationNarrative
from app.prompts import templates
from app.prompts.templates import untrusted


class DocumentationAgent(BaseAgent):
    name = "documentation"
    display_name = "Documentation Agent"
    description = (
        "Produces the BRD, SRS, architecture, API, testing, installation and deployment "
        "documents and the final delivery report."
    )
    role_prompt = templates.DOCUMENTATION
    output_model = DocumentationNarrative

    def summarize_input(self, ctx):
        review = ctx.get("review_report", {})
        return {
            "artifacts": len(ctx.get("artifacts", [])),
            "passed_tests": review.get("passed_tests"),
            "failed_tests": review.get("failed_tests"),
            "skipped_tests": review.get("skipped_tests"),
        }

    def build_user_prompt(self, ctx):
        analysis = ctx.get("requirements_analysis", {})
        review = ctx.get("review_report", {})
        return "\n\n".join([
            "Write the narrative documentation sections for this delivery.",
            untrusted("project", ctx.get("project", {})),
            untrusted("requirements_summary", {
                "business_problem": analysis.get("business_problem"),
                "objectives": analysis.get("objectives"),
                "missing_information": analysis.get("missing_information"),
            }),
            untrusted("architecture_overview",
                      ctx.get("architecture", {}).get("architecture_overview")),
            untrusted("delivered_files", [a["file_path"] for a in ctx.get("artifacts", [])]),
            untrusted("actual_test_results", {
                k: review.get(k) for k in ("passed_tests", "failed_tests", "skipped_tests",
                                           "review_status", "issues")
            }),
        ])

    def mock_output(self, ctx):
        project = ctx.get("project", {})
        analysis = ctx.get("requirements_analysis", {})
        review = ctx.get("review_report", {})
        architecture = ctx.get("architecture", {})
        entities = ", ".join(e["name"] for e in architecture.get("database_entities", []))
        passed = review.get("passed_tests", 0)
        failed = review.get("failed_tests", 0)
        skipped = review.get("skipped_tests", 0)
        limitations = [
            "[MOCK MODE] All agent outputs in this delivery were produced by AgentForge's "
            "rule-based mock mode, not by a large language model.",
            "Generated service uses in-memory storage; data is lost on restart.",
            "Authentication and role-based access are designed but not implemented in the "
            "generated prototype.",
        ]
        if skipped:
            limitations.append(f"{skipped} check(s) were skipped (e.g. sandbox unavailable); "
                               "their results are unknown.")
        if failed:
            limitations.append(f"{failed} check(s) were still failing at delivery time.")
        limitations += [f"Open question: {q}" for q in analysis.get("missing_information", [])[:4]]
        return {
            "project_overview": (
                f"{project.get('name', 'This project')} — "
                f"{project.get('description') or analysis.get('business_problem', '')} "
                f"The delivered prototype implements the entities {entities}."
            ),
            "executive_summary": (
                f"AgentForge AI analysed the requirement, designed the architecture and generated "
                f"a runnable service. Executed checks: {passed} passed, {failed} failed, "
                f"{skipped} skipped. Human approval was recorded at each checkpoint."
            ),
            "known_limitations": limitations,
            "future_enhancements": [
                "Persist data in PostgreSQL with migrations.",
                "Implement authentication, RBAC and audit logging in the generated service.",
                "Add a frontend for each module.",
                "Resolve the open clarification questions with the client.",
            ],
            "deployment_notes": [
                "Build a container image from the generated service.",
                "Configure secrets via environment variables.",
                "Deploy only after explicit human approval.",
            ],
            "installation_notes": [
                "Requires Python 3.11+.",
                "Install dependencies with `pip install -r requirements.txt`.",
            ],
        }
