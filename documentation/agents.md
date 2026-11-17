# Agent Responsibilities

All agents share `agents/base.py`:

- **Structured output:** the LLM must return JSON matching the agent's Pydantic schema (`agents/schemas.py`). The schema is embedded in the system prompt.
- **Validation:** schema validation plus agent-specific rules (`validate_output`) and post-processing (`post_process`).
- **Retry policy:** up to `LLM_MAX_RETRIES` extra attempts. Each retry includes the previous validation error as feedback.
- **Bookkeeping (by the orchestrator):** an `agent_runs` row with status, input summary, output, start/end time, duration, prompt/completion tokens, attempts, `is_mock` and error message, plus log lines.
- **Safety:** user text and other agents' output are wrapped in `<untrusted_data>` tags, and every system prompt says to treat them as data.
- **Mock mode:** each agent has a deterministic `mock_output` used when no API key is configured. It is labelled in the UI, the logs and the documents.

| # | Agent (`name`) | Input | Output schema | Notable rules |
|---|---|---|---|---|
| 1 | Requirement Analyst (`requirement_analyst`) | Client requirement, project details, reviewer feedback | `RequirementsAnalysis`: problem, objectives, FR/NFR (each with `source`: stated / inferred / assumed), roles, user stories, acceptance criteria, dependencies, constraints, assumptions, missing information, ambiguities, contradictions, clarification questions | Must not silently invent requirements; ids must be unique. Human edits are validated against the same schema. |
| 2 | Research Agent (`research`) | Approved requirements, project details | `ResearchReport`: stack, framework comparison, libraries, integrations, implementation options, risks, complexity, recommendations, sources, verification note | Every source is forced to `unverified`. With `RESEARCH_CHECK_URLS=true`, only public `https` URLs are probed (SSRF guard), and a hit means *reachable*, not *verified*. |
| 3 | Solution Architect (`solution_architect`) | Requirements, research, feedback | `ArchitectureSpec`: overview, frontend/backend components, entities (typed fields), API specs, auth strategy, security, scalability, plan, decisions | Entity names PascalCase, unique; field names snake_case, not Python keywords, no `id`. |
| 4 | Developer Agent (`developer`) | Architecture, functional requirements, previous code, correction feedback | `DeveloperOutput`: summary, artifacts `[file_path, file_type, description, content, dependencies, proposed_action]`, notes | Paths must be relative, without `..` or hidden files, with allowed extensions only. Needs ≥1 `test_*.py`, ≤25 files, ≤300 KB. It never executes anything; files go to `code_v<n>/` and need approval. |
| 5 | Code Review & Testing (`review_testing`) | Code, requirements, **real** check results | `ReviewAgentOutput`: status, summary, issues (severity), test cases (category, linked requirement), requirement coverage, recommendations | Pass/fail/skip counts are computed by the orchestrator from executed checks; the model cannot change them. `correction_required` = any failed check or critical issue. |
| 6 | Documentation Agent (`documentation`) | Project, requirements summary, architecture, delivered files, actual test results | `DocumentationNarrative`: overview, executive summary, limitations, enhancements, deployment and installation notes | Narrative only; the 11 documents are rendered from validated state (`services/docs_renderer.py`). |

## Delivery documents produced

`01_project_overview`, `02_business_requirements_BRD`, `03_software_requirements_SRS`, `04_system_architecture`, `05_database_design`, `06_api_documentation`, `07_test_report`, `08_installation_guide`, `09_deployment_guide`, `10_known_limitations`, `11_final_delivery_report` (including the human-approval log). All are available in the Documentation Center and in the delivery zip.
