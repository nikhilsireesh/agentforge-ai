"""Agent 4: Developer Agent (Senior Full-Stack Software Developer).

Returns structured code artifacts only. It never executes anything; files are
written to an isolated folder and must be reviewed and approved.
"""

from app.agents import codegen
from app.agents import mock_knowledge as mk
from app.agents.base import BaseAgent
from app.agents.schemas import DeveloperOutput
from app.config import get_settings
from app.prompts import templates
from app.prompts.templates import untrusted


class DeveloperAgent(BaseAgent):
    name = "developer"
    display_name = "Developer Agent"
    description = (
        "Generates the application code, configuration and unit tests from the approved "
        "architecture, and applies corrections reported by the review agent."
    )
    role_prompt = templates.DEVELOPER
    output_model = DeveloperOutput
    max_tokens = 16000

    def summarize_input(self, ctx):
        return {
            "code_version": ctx.get("code_version"),
            "correction_attempt": ctx.get("correction_attempts", 0),
            "entities": [e["name"] for e in ctx.get("architecture", {}).get("database_entities",
                                                                             [])],
            "feedback": (ctx.get("revision_feedback") or "")[:500] or None,
        }

    def build_user_prompt(self, ctx):
        architecture = ctx.get("architecture", {})
        parts = [
            "Implement this approved architecture.",
            untrusted("approved_architecture", {
                k: architecture.get(k) for k in (
                    "architecture_overview", "database_entities", "api_specifications",
                    "authentication_strategy", "implementation_plan")
            }),
            untrusted("functional_requirements",
                      ctx.get("requirements_analysis", {}).get("functional_requirements", [])),
        ]
        if ctx.get("revision_feedback"):
            parts.append("Correction / reviewer feedback to address:")
            parts.append(untrusted("feedback", ctx["revision_feedback"]))
        if ctx.get("previous_artifacts"):
            parts.append("Your previous version of the code:")
            parts.append(untrusted("previous_code", [
                {"file_path": a["file_path"], "content": a["content"][:12000]}
                for a in ctx["previous_artifacts"]
            ]))
        return "\n\n".join(parts)

    def mock_output(self, ctx):
        architecture = ctx.get("architecture", {})
        text = ctx.get("requirement", "")
        is_first_version = ctx.get("code_version", 1) == 1
        inject = get_settings().mock_inject_defect and is_first_version
        title = ctx.get("project", {}).get("name") or "Generated Service"
        artifacts = codegen.generate_project(
            title=title.replace('"', "'"),
            entities=architecture.get("database_entities") or mk.detect_entities(text),
            include_reports=mk.mentions(mk.REPORT_PATTERN, text),
            inject_defect=inject,
        )
        previous = {a["file_path"]: a["content"] for a in ctx.get("previous_artifacts", [])}
        for artifact in artifacts:
            if artifact["file_path"] in previous:
                artifact["proposed_action"] = "update"
        notes = ["[MOCK MODE] Code produced by AgentForge's template generator, not an LLM."]
        if inject:
            notes.append("[MOCK DEMO] One defect was intentionally injected into app/main.py "
                         "to demonstrate review and controlled correction.")
        if ctx.get("revision_feedback"):
            notes.append("Feedback addressed in this version: "
                         + ctx["revision_feedback"][:300])
        return {
            "summary": f"Generated a FastAPI service with {len(artifacts)} files covering "
                       f"{len(architecture.get('database_entities', []))} entities.",
            "artifacts": artifacts,
            "notes": notes,
        }
