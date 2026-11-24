# System Architecture

## 1. Big picture

```
┌────────────────────────┐   REST/JSON    ┌──────────────────────────────────────────────┐
│ React SPA (Vite)       │ ─────────────► │ FastAPI                                      │
│ Tailwind · React Flow  │ ◄───────────── │  routes/ → services/ → orchestration/runner  │
│ Recharts · polling 2s  │   (via proxy)  │                         │                    │
└────────────────────────┘                │                 LangGraph StateGraph         │
                                          │      ┌──────────────────┴─────────────┐      │
                                          │   agents/ (6)                 approval nodes  │
                                          │      │                        (interrupt)     │
                                          │   LLM client ──► OpenAI-compatible API        │
                                          │   or mock mode (rule-based, labelled)         │
                                          └───┬───────────────┬───────────────┬──────────┘
                                              │               │               │
                                     SQLite (SQLAlchemy)  checkpoints.db   generated_projects/
                                     9 tables, Alembic    (paused graphs)  execution_<id>/
                                                                           code_v<n>/, docs/
                                                                                │
                                                                     static checks (ast, Ruff)
                                                                     pytest → Docker sandbox only
```

## 2. Layers

| Layer | Responsibility | Rule |
|---|---|---|
| `routes/` | Parse HTTP, check auth, call a service, return a schema | No business logic |
| `schemas/` | Pydantic request/response models | All input validated at the edge |
| `services/` | Business rules: projects, executions, approvals, artifacts, analytics, sandbox | Testable without HTTP |
| `orchestration/` | LangGraph graph, shared state, runner (threads), recorder (DB writes) | The only place that decides "what runs next" |
| `agents/` | Prompt + output schema + validation + retry; mock-mode logic | Agents never touch the DB or run commands |
| `models/` | SQLAlchemy tables with FKs, indexes, CHECK constraints | Invariants also enforced in the database |

## 3. Workflow graph

Nodes: `requirement_analyst`, `approval_requirements`, `research`, `solution_architect`, `approval_architecture`, `developer`, `approval_code`, `approval_test_execution`, `review_testing`, `correction`, `approval_deployment`, `documentation`.

| From | Condition | To |
|---|---|---|
| any approval node | approved | next step |
| any approval node | revision requested (feedback) | the agent that produced the work |
| any approval node | rejected | END (execution *cancelled*, reason recorded) |
| `developer` | code not yet approved | `approval_code` |
| `developer` | code approved (correction loop) | `review_testing` |
| `review_testing` | checks failed, and attempts < 2 | `correction` → `developer` |
| `review_testing` | passed, or 2 attempts used | `approval_deployment` (failures visible to the reviewer) |

**How approvals work.** An approval node calls `interrupt(payload)`. LangGraph saves a checkpoint to `checkpoints.db` and returns. The runner sees `snapshot.next`, creates a pending `approvals` row and marks the execution `waiting_approval`. When a reviewer decides, the API atomically updates the row with a conditional UPDATE, so double-clicks can't both win. It then resumes the same thread with `Command(resume={decision, feedback})`. Nothing with side effects runs before `interrupt()`, because LangGraph re-runs the node from the top on resume.

**Execution model.** Graphs run in a `ThreadPoolExecutor`, so requests return immediately (`202`) and the UI polls. An execution that was *running* during a crash is marked failed at startup. Executions *waiting for approval* survive a restart.

## 4. Shared state (`orchestration/state.py`)

`AgentForgeState` (TypedDict) holds the project snapshot, the requirement text, every agent's validated output (`requirements_analysis`, `research_report`, `architecture`, `generated_artifacts`, `review_report`, `documentation`), the counters `code_version` and `correction_attempts`, approval fields (`approval_status`, `last_checkpoint`, `revision_feedback`) and append-only `execution_logs`/`errors`. Each node returns only the keys it changes.

## 5. Data model

```
users 1──* projects 1──* requirements
                    1──* executions ──? requirements (analysed version)
                              1──* agent_runs      (status, I/O summary, tokens, duration, attempts, is_mock)
                              1──* approvals       (checkpoint, decision, feedback, reviewer, request_summary)
                              1──* artifacts       (type, safe relative path, metadata incl. sha256, approval)
                              1──* test_results    (iteration, name, status, output, error, duration)
                              1──* execution_logs  (agent, level, message, timestamp)
```

- Deleting a project cascades to everything below it.
- Every status column is a VARCHAR with a **CHECK constraint**; `correction_attempts` is constrained to 0–2.
- SQLite foreign keys are enabled explicitly (`PRAGMA foreign_keys=ON`), and WAL mode allows reads during background writes.
- Additions beyond the original table spec: wizard fields on projects; `updated_at` on requirements; `requirement_id`, `thread_id`, `llm_mode`, `correction_attempts` and `error_message` on executions; token split, `attempt` and `is_mock` on agent runs; `decided_at` and `request_summary` on approvals; `iteration` on test results. The `metadata` column is mapped as `metadata_json` because `metadata` is reserved in SQLAlchemy.

## 6. Key decisions

| Decision | Why | Trade-off |
|---|---|---|
| Background threads, not Celery/Redis | Zero extra infrastructure for an MVP | Single process; no horizontal scaling of workers |
| SQLite + Alembic | Simple setup; migrations keep a path to PostgreSQL | Limited write concurrency |
| Raw `httpx` LLM client (not an SDK) | Works with any OpenAI-compatible endpoint; transparent; easy to mock | Implements only chat completions + JSON mode |
| Documents rendered from state + LLM narrative | Facts in the docs cannot drift from what was built | Less free-form prose |
| Mock mode instead of failing without a key | Whole platform demonstrable offline; clearly labelled | Mock outputs are heuristic, not intelligent |
| Generated prototype uses in-memory storage | Lets generated tests run in an offline sandbox | Persistence must be added for production |
