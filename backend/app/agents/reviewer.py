"""Agent 5: Code Review & Testing Agent (Senior QA Engineer).

The orchestrator runs the REAL checks (static analysis + sandboxed pytest)
and hands the results to this agent. The agent reviews code and results but
can never change pass/fail counts: those are computed from actual execution.
"""

import re
from typing import Any

from app.agents import mock_knowledge as mk
from app.agents.base import BaseAgent
from app.agents.codegen import route_for, snake
from app.agents.schemas import ReviewAgentOutput
from app.prompts import templates
from app.prompts.templates import untrusted

DANGEROUS_PATTERNS = [
    (r"\beval\(", "Use of eval() allows arbitrary code execution."),
    (r"\bexec\(", "Use of exec() allows arbitrary code execution."),
    (r"\bsubprocess\b|\bos\.system\(", "Spawning shell processes from application code."),
    (r"(?i)(api[_-]?key|secret|password)\s*=\s*['\"][^'\"]{6,}['\"]", "Hard-coded secret."),
]


def test_category(name: str) -> str:
    if "not_found" in name or "validation" in name:
        return "edge_case"
    if "health" in name:
        return "api"
    if "report" in name:
        return "functional"
    return "api"


class ReviewTestingAgent(BaseAgent):
    name = "review_testing"
    display_name = "Code Review & Testing Agent"
    description = (
        "Reviews generated code, runs approved static checks and tests in a sandbox, maps "
        "results to requirements and decides whether correction is needed."
    )
    role_prompt = templates.REVIEWER
    output_model = ReviewAgentOutput

    def summarize_input(self, ctx):
        outcomes = ctx.get("outcomes", [])
        return {
            "files": len(ctx.get("artifacts", [])),
            "executed_checks": len(outcomes),
            "failed_checks": sum(1 for o in outcomes if o["status"] in ("failed", "error")),
            "correction_attempt": ctx.get("correction_attempts", 0),
        }

    def build_user_prompt(self, ctx):
        return "\n\n".join([
            "Review this generated code against the requirements.",
            untrusted("functional_requirements",
                      ctx.get("requirements_analysis", {}).get("functional_requirements", [])),
            untrusted("generated_code", [
                {"file_path": a["file_path"], "content": a["content"][:10000]}
                for a in ctx.get("artifacts", [])
            ]),
            "These are the REAL results of the checks that were executed:",
            untrusted("execution_results", [
                {k: o.get(k) for k in ("name", "status", "error")}
                for o in ctx.get("outcomes", [])
            ]),
        ])

    def mock_output(self, ctx: dict[str, Any]) -> dict[str, Any]:
        artifacts = ctx.get("artifacts", [])
        outcomes = ctx.get("outcomes", [])
        analysis = ctx.get("requirements_analysis", {})
        code = {a["file_path"]: a["content"] for a in artifacts}
        all_code = "\n".join(code.values())
        tests_code = "\n".join(c for p, c in code.items() if "test" in p)

        issues = []
        for outcome in outcomes:
            if outcome["status"] in ("failed", "error"):
                first_line = (outcome.get("error") or "check failed").splitlines()[0][:300]
                issues.append({
                    "id": f"ISS-{len(issues) + 1:02d}", "severity": "high", "category": "defect",
                    "file_path": outcome.get("file_path"),
                    "description": f"{outcome['name']} failed: {first_line}",
                    "recommendation": "Fix the defect and re-run the test suite.",
                })
            elif outcome["status"] == "skipped" and outcome["name"].startswith("pytest"):
                issues.append({
                    "id": f"ISS-{len(issues) + 1:02d}", "severity": "medium",
                    "category": "test-execution", "file_path": None,
                    "description": "Automated tests were NOT executed: "
                                   + (outcome.get("error") or "sandbox unavailable"),
                    "recommendation": "Install Docker and build the sandbox image so tests can "
                                      "run in isolation.",
                })
        for path, content in code.items():
            for pattern, message in DANGEROUS_PATTERNS:
                if re.search(pattern, content):
                    issues.append({
                        "id": f"ISS-{len(issues) + 1:02d}", "severity": "critical",
                        "category": "security", "file_path": path, "description": message,
                        "recommendation": "Remove the construct or justify it explicitly.",
                    })
        if mk.mentions(mk.AUTH_PATTERN, ctx.get("requirement", "")) and "jwt" not in \
                all_code.lower():
            issues.append({
                "id": f"ISS-{len(issues) + 1:02d}", "severity": "medium", "category": "scope",
                "file_path": "app/main.py",
                "description": "Authentication/authorisation required by the requirements is "
                               "not implemented in the generated prototype.",
                "recommendation": "Add login, password hashing and role checks before release.",
            })

        test_names = re.findall(r"^def (test_\w+)", tests_code, re.M)
        entities = ctx.get("architecture", {}).get("database_entities", [])
        coverage, test_cases = [], []
        entity_requirement: dict[str, str] = {}  # snake_case entity -> first FR id
        for fr in analysis.get("functional_requirements", []):
            desc = fr["description"].lower()
            match = None
            for entity in entities:
                words = re.findall(r"[A-Z][a-z]+", entity["name"])
                if any(w.lower() in desc for w in words if len(w) > 3):
                    match = entity
                    break
            if "report" in desc and "/api/reports/summary" in all_code:
                coverage.append({"requirement_id": fr["id"], "status": "partial",
                                 "evidence": "Summary report endpoint implemented; detailed "
                                             "reports not specified."})
            elif match and route_for(match["name"]) in all_code:
                entity_key = snake(match["name"])
                entity_requirement.setdefault(entity_key, fr["id"])
                tested = any(entity_key in t for t in test_names)
                coverage.append({
                    "requirement_id": fr["id"], "status": "covered" if tested else "partial",
                    "evidence": f"{route_for(match['name'])} endpoints implemented"
                                + (" and exercised by API tests." if tested else "; untested."),
                })
            else:
                coverage.append({"requirement_id": fr["id"], "status": "not_covered",
                                 "evidence": "No implementing code found by keyword analysis."})

        for i, name in enumerate(test_names, 1):
            related = next((req for key, req in entity_requirement.items() if key in name), None)
            test_cases.append({
                "id": f"TC-{i:02d}", "name": name, "category": test_category(name),
                "description": name.replace("test_", "").replace("_", " ").capitalize() + ".",
                "requirement_id": related,
            })

        failed = any(o["status"] in ("failed", "error") for o in outcomes)
        critical = any(i["severity"] == "critical" for i in issues)
        return {
            "review_status": "changes_requested" if failed or critical else "approved",
            "summary": (
                f"[MOCK MODE] Rule-based review of {len(artifacts)} files and "
                f"{len(outcomes)} executed checks. "
                + ("Failures were found and must be corrected." if failed
                   else "All executed checks passed.")
            ),
            "issues": issues,
            "test_cases": test_cases,
            "requirement_coverage": coverage,
            "recommendations": [
                "Replace in-memory storage with a database before production.",
                "Add authentication and role-based access tests.",
            ],
        }
