"""Render delivery documents (Markdown) from validated workflow state.

Facts (requirements, entities, endpoints, test counts) come straight from
state, so the documents always match what was actually built and tested.
The Documentation agent contributes only the narrative sections.
"""

from datetime import UTC, datetime
from typing import Any

DOC_TITLES = {
    "01_project_overview.md": "Project Overview",
    "02_business_requirements_BRD.md": "Business Requirements (BRD)",
    "03_software_requirements_SRS.md": "Software Requirements (SRS)",
    "04_system_architecture.md": "System Architecture",
    "05_database_design.md": "Database Design",
    "06_api_documentation.md": "API Documentation",
    "07_test_report.md": "Test Report",
    "08_installation_guide.md": "Installation Guide",
    "09_deployment_guide.md": "Deployment Guide",
    "10_known_limitations.md": "Known Limitations",
    "11_final_delivery_report.md": "Final Delivery Report",
}


def _bullets(items: list[str], empty: str = "_None recorded._") -> str:
    return "\n".join(f"- {item}" for item in items) if items else empty


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    if not rows:
        return "_None._"
    def esc(value: Any) -> str:
        return str(value if value is not None else "").replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines += ["| " + " | ".join(esc(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)


def _header(title: str, state: dict[str, Any]) -> str:
    project = state.get("project", {})
    mode = state.get("llm_mode", "mock")
    banner = (
        "\n> **Mock mode:** agent outputs were produced by AgentForge's rule-based mock mode, "
        "not by a large language model.\n" if mode == "mock" else ""
    )
    return (
        f"# {title}\n\n"
        f"**Project:** {project.get('name', '')}  \n"
        f"**Execution:** #{state.get('execution_id')}  \n"
        f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')} by AgentForge AI\n"
        f"{banner}\n"
    )


def _requirements_rows(items: list[dict]) -> list[list[Any]]:
    return [[i["id"], i["description"], i.get("priority", ""), i.get("source", "")]
            for i in items]


def render_documents(state: dict[str, Any], narrative: dict[str, Any]) -> dict[str, str]:
    analysis = state.get("requirements_analysis", {})
    research = state.get("research_report", {})
    arch = state.get("architecture", {})
    review = state.get("review_report", {})
    artifacts = state.get("generated_artifacts", [])
    approvals = state.get("approval_history", [])
    entities = arch.get("database_entities", [])

    docs: dict[str, str] = {}

    docs["01_project_overview.md"] = _header("Project Overview", state) + f"""## Overview

{narrative.get('project_overview', '')}

## Executive summary

{narrative.get('executive_summary', '')}

## Original client requirement

> {state.get('requirement', '').replace(chr(10), chr(10) + '> ')}
"""

    docs["02_business_requirements_BRD.md"] = _header("Business Requirements Document", state) + f"""## Business problem

{analysis.get('business_problem', '')}

## Objectives

{_bullets(analysis.get('objectives', []))}

## Stakeholders / user roles

{_bullets(analysis.get('user_roles', []))}

## Dependencies

{_bullets(analysis.get('dependencies', []))}

## Constraints

{_bullets(analysis.get('constraints', []))}

## Assumptions (to be confirmed)

{_bullets(analysis.get('assumptions', []))}

## Missing information

{_bullets(analysis.get('missing_information', []))}

## Clarification questions

{_bullets(analysis.get('clarification_questions', []))}
"""

    stories = [[s["id"], s["role"], s["story"], ", ".join(s.get("related_requirements", []))]
               for s in analysis.get("user_stories", [])]
    criteria = [[c["id"], c["requirement_id"], c["criterion"]]
                for c in analysis.get("acceptance_criteria", [])]
    docs["03_software_requirements_SRS.md"] = _header("Software Requirements Specification", state) + f"""## Functional requirements

{_table(['ID', 'Requirement', 'Priority', 'Source'], _requirements_rows(analysis.get('functional_requirements', [])))}

## Non-functional requirements

{_table(['ID', 'Requirement', 'Priority', 'Source'], _requirements_rows(analysis.get('non_functional_requirements', [])))}

_Source legend: **stated** = in client text; **inferred** = logically required; **assumed** = must be confirmed._

## User stories

{_table(['ID', 'Role', 'Story', 'Requirements'], stories)}

## Acceptance criteria

{_table(['ID', 'Requirement', 'Criterion'], criteria)}

## Ambiguities

{_bullets(analysis.get('ambiguities', []))}
"""

    stack = [[k, v] for k, v in research.get("recommended_stack", {}).items()]
    decisions = [[d["decision"], d["rationale"], ", ".join(d.get("alternatives", [])),
                  d.get("trade_offs", "")] for d in arch.get("architecture_decisions", [])]
    docs["04_system_architecture.md"] = _header("System Architecture", state) + f"""## Overview

{arch.get('architecture_overview', '')}

## Technology stack (Research Agent recommendation, requires verification)

{_table(['Layer', 'Technology'], stack)}

> {research.get('verification_note', '')}

## Frontend components

{_table(['Component', 'Responsibility'], [[c['name'], c['responsibility']] for c in arch.get('frontend_components', [])])}

## Backend components

{_table(['Component', 'Responsibility'], [[c['name'], c['responsibility']] for c in arch.get('backend_components', [])])}

## Authentication & authorisation

{arch.get('authentication_strategy', '')}

## Security considerations

{_bullets(arch.get('security_considerations', []))}

## Scalability considerations

{_bullets(arch.get('scalability_considerations', []))}

## Architecture decisions

{_table(['Decision', 'Rationale', 'Alternatives', 'Trade-offs'], decisions)}

## Technical risks

{_table(['Risk', 'Impact', 'Mitigation'], [[r['risk'], r['impact'], r['mitigation']] for r in research.get('technical_risks', [])])}
"""

    entity_sections = []
    for entity in entities:
        rows = [["id", "int", "yes", "Primary key (auto-generated)"]] + [
            [f["name"], f["type"], "yes" if f.get("required", True) else "no",
             f.get("description", "")] for f in entity["fields"]
        ]
        entity_sections.append(
            f"### {entity['name']}\n\n{entity.get('description', '')}\n\n"
            + _table(["Field", "Type", "Required", "Description"], rows)
            + ("\n\n**Relationships:** " + "; ".join(entity["relationships"])
               if entity.get("relationships") else "")
        )
    docs["05_database_design.md"] = _header("Database Design", state) + "## Entities\n\n" + (
        "\n\n".join(entity_sections) or "_No entities._") + "\n"

    apis = [[a["method"], f"`{a['path']}`", a["description"],
             "yes" if a.get("auth_required", True) else "no", ", ".join(a.get("roles", []))]
            for a in arch.get("api_specifications", [])]
    docs["06_api_documentation.md"] = _header("API Documentation", state) + f"""## Designed endpoints

{_table(['Method', 'Path', 'Description', 'Auth', 'Roles'], apis)}

## Generated prototype

The generated FastAPI service publishes interactive OpenAPI documentation at `/docs` when it is
running. Endpoints marked as requiring authentication are enforced only once authentication is
implemented (see Known Limitations).
"""

    executed = review.get("executed_tests", [])
    issue_rows = [[i["id"], i["severity"], i["category"], i.get("file_path") or "",
                   i["description"]] for i in review.get("issues", [])]
    coverage_rows = [[c["requirement_id"], c["status"], c["evidence"]]
                     for c in review.get("requirement_coverage", [])]
    test_rows = [[t["name"], t["status"], (t.get("error") or "").splitlines()[0][:120]
                  if t.get("error") else ""] for t in executed]
    docs["07_test_report.md"] = _header("Test Report", state) + f"""## Summary (actual execution results)

| Passed | Failed | Skipped | Correction attempts | Review status |
|---|---|---|---|---|
| {review.get('passed_tests', 0)} | {review.get('failed_tests', 0)} | {review.get('skipped_tests', 0)} | {state.get('correction_attempts', 0)} | {review.get('review_status', 'n/a')} |

Counts come from checks that actually ran (static analysis on the host, pytest only inside the
Docker sandbox). Skipped checks were **not** executed.

## Executed checks (final iteration)

{_table(['Check', 'Status', 'Detail'], test_rows)}

## Review findings

{_table(['ID', 'Severity', 'Category', 'File', 'Description'], issue_rows)}

## Requirement coverage

{_table(['Requirement', 'Status', 'Evidence'], coverage_rows)}

## Designed test cases

{_table(['ID', 'Name', 'Category', 'Requirement'], [[t['id'], t['name'], t['category'], t.get('requirement_id') or ''] for t in review.get('test_cases', [])])}
"""

    docs["08_installation_guide.md"] = _header("Installation Guide", state) + f"""## Prerequisites

{_bullets(narrative.get('installation_notes', []))}

## Steps

```bash
cd source
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
uvicorn app.main:app --reload    # http://localhost:8000/docs
python -m pytest                 # run the test suite
```

## Files delivered

{_table(['File', 'Description'], [[a['file_path'], a.get('description', '')] for a in artifacts])}
"""

    docs["09_deployment_guide.md"] = _header("Deployment Guide", state) + f"""> Deployment must be explicitly approved by a human. AgentForge AI never deploys automatically.

## Notes

{_bullets(narrative.get('deployment_notes', []))}

## Example container build

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY source/ .
RUN pip install --no-cache-dir -r requirements.txt
RUN useradd --uid 10001 app && chown -R app /app
USER app
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```
"""

    docs["10_known_limitations.md"] = _header("Known Limitations", state) + f"""## Known limitations

{_bullets(narrative.get('known_limitations', []))}

## Future enhancements

{_bullets(narrative.get('future_enhancements', []))}
"""

    approval_rows = [[a["checkpoint"], a["decision"], a.get("reviewer") or "",
                      a.get("decided_at") or "", a.get("feedback") or ""] for a in approvals]
    docs["11_final_delivery_report.md"] = _header("Final Delivery Report", state) + f"""## Executive summary

{narrative.get('executive_summary', '')}

## Delivery contents

- {len(artifacts)} source files (folder `source/`)
- {len(analysis.get('functional_requirements', []))} functional requirements,
  {len(entities)} database entities, {len(arch.get('api_specifications', []))} designed endpoints
- Executed checks: **{review.get('passed_tests', 0)} passed, {review.get('failed_tests', 0)} failed,
  {review.get('skipped_tests', 0)} skipped**
- Correction iterations used: {state.get('correction_attempts', 0)} of 2

## Human approvals

{_table(['Checkpoint', 'Decision', 'Reviewer', 'Decided at', 'Feedback'], approval_rows)}

## Open items

{_bullets(analysis.get('clarification_questions', [])[:8])}

## Known limitations

{_bullets(narrative.get('known_limitations', []))}
"""
    return docs
