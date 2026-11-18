# Interview Demonstration Guide (≈10 minutes)

**Before the interview:** start the backend and frontend (README Quick start). For a clean slate, stop the backend and delete `backend/agentforge.db*`, `backend/checkpoints.db*` and `generated_projects/execution_*`, then run `alembic upgrade head`. Decide whether to demo in **mock mode** (offline and deterministic, shows the correction loop reliably) or **live mode** (set `LLM_API_KEY`).

| # | Step | Where | What to say |
|---|---|---|---|
| 1 | Show the empty Overview, then **New Project → Employee Leave Management** | Overview, wizard | "A client gives a one-sentence requirement. Everything from here is produced by agents under my supervision." |
| 2 | Continue through the wizard, tick *Start immediately*, **Create & start agents** | Wizard | The API returns `202` immediately; the LangGraph workflow runs in a background thread. |
| 3 | Watch the Requirement Analyst complete, then the graph pause (amber) | Workflow Monitor | "Each node is a LangGraph node. Approval nodes call `interrupt()`: state is checkpointed to SQLite and the run stops until a human decides." |
| 4 | Open **Requirements**: FR/NFR with *stated / inferred / assumed*, missing info, questions. Click **Edit analysis**, change something, save, then **Approve** | Requirements | "The agent must not invent requirements; assumptions are labelled. My edits are re-validated against the same schema and flow to the next agents." |
| 5 | Research + Architect run. Open **Architecture**: diagram, entities, endpoints, *Technology research* tab with **unverified** sources | Architecture | "Research can't browse, so sources are forced to *unverified*, which is honest by construction." |
| 6 | **Approve** architecture → Developer runs → open **Code Artifacts** | Code Artifacts | File tree, syntax highlighting, SHA-256, approval status. In mock mode, point out the labelled injected defect. |
| 7 | **Approve** code, then **Approve** test execution | Testing Center | "Static checks parse and lint without executing. pytest runs only in a locked-down Docker container: no network, non-root, read-only." |
| 8 | Switch iteration to **Initial run**: `static::ruff::app/main.py` failed (F821 undefined name). Switch to latest: all passing. Show *Correction attempts 1/2* | Testing Center | "Failures trigger controlled correction, capped at two. Pass/fail counts come from real execution; the reviewing LLM can't change them." |
| 9 | Show the dashed correction loop lit up in the graph | Workflow Monitor | Conditional routing in LangGraph. |
| 10 | **Approve** final delivery → open **Documentation** → *Final Delivery Report* (approval log) → **Download delivery package** | Documentation | "Documents are rendered from validated state, so they can't claim anything that didn't happen." |
| 11 | Open **Analytics** and **Agent Workspace** | Analytics | Completion rate, test pass rate, correction frequency, tokens and cost (live mode), API p50/p95, all from the database. |
| 12 | (Optional) Inventory demo, using **Request revision** with feedback | Wizard, approvals | Proves the workflow handles other domains, and shows the revision path. |
| 13 | (Optional) Restart the backend while a run is waiting for approval, then approve | Terminal | Checkpoint persistence: the workflow resumes exactly where it stopped. |

## Likely questions

- **Why LangGraph?** Explicit state machine, conditional edges, built-in checkpointing, and `interrupt()` for human-in-the-loop. That's better than ad-hoc chained prompts.
- **How do you stop hallucinated success?** Schemas, untrusted-data separation, counts computed from executed checks, *skipped ≠ passed*, mock labelling, documents rendered from state.
- **What would you do next?** A dedicated sandbox runner service, PostgreSQL + Redis/Celery, RAG over company standards, GitHub PR export, SSE instead of polling (see the roadmap).

## Resume bullets

- Built **AgentForge AI**, a multi-agent software delivery platform (FastAPI, LangGraph, React). Six specialised LLM agents turn natural-language business requirements into validated specs, architecture, code, tests and documentation.
- Designed a **LangGraph state machine** with typed shared state, SQLite checkpointing, conditional routing, a bounded self-correction loop and **five human-in-the-loop approval gates** that survive server restarts.
- Implemented **safe execution of AI-generated code**: static analysis plus pytest inside a network-less, non-root, read-only, resource-limited Docker sandbox, with results parsed from JUnit and never fabricated.
- Hardened the platform against **prompt injection, path traversal and SSRF**, added JWT/RBAC, rate limiting and audit logging, and backed it with 65 pytest tests, Playwright E2E tests and GitHub Actions CI.
