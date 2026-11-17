# AgentForge AI: Requirements

## Problem statement

Turning a client's business request into working, tested, documented software involves analysts, architects, developers, QA and writers, and a lot of hand-offs where context gets lost. Generic chatbots can draft pieces of this, but they don't keep shared context, enforce structure, run real tests, or let a human supervise each step.

**AgentForge AI** coordinates specialised AI agents through an explicit, auditable workflow with shared state, validated hand-offs, real test execution and human approval gates.

## Business requirements

| ID | Requirement |
|---|---|
| BR-1 | Reduce the time from client requirement to a reviewed prototype and delivery documentation. |
| BR-2 | Keep humans accountable: no work progresses past key stages without recorded approval. |
| BR-3 | Make AI output trustworthy: structured, validated, traceable, and never overstated. |
| BR-4 | Work across business domains (shown with HR leave management and inventory management). |
| BR-5 | Give managers visibility into progress, quality and cost. |

## Functional requirements

| ID | Requirement | Implemented in |
|---|---|---|
| FR-1 | Create, edit, delete, search, filter, sort and paginate projects | Projects API & page |
| FR-2 | Submit natural-language requirements; keep requirement versions | Requirements API, wizard |
| FR-3 | Analyse requirements into FR/NFR, roles, stories, acceptance criteria, gaps and questions | Requirement Analyst |
| FR-4 | Produce a research report with labelled, unverified sources | Research Agent |
| FR-5 | Produce an architecture: components, entities, APIs, security, plan, decisions | Solution Architect |
| FR-6 | Generate code artifacts with tests; store them safely and version them | Developer Agent, artifact store |
| FR-7 | Review code, run static checks and sandboxed tests, map coverage | Review & Testing Agent, sandbox |
| FR-8 | Automatically correct failures, at most twice | Correction loop |
| FR-9 | Pause at 5 checkpoints; approve, request revision or reject with feedback | Approval Center, LangGraph interrupts |
| FR-10 | Generate 11 delivery documents and a downloadable package | Documentation Agent, `/package` |
| FR-11 | Show live workflow status, agent details and logs | Workflow Monitor, Agent Workspace |
| FR-12 | Report analytics from real data (completion, duration, tests, retries, tokens, cost, latency) | Analytics |
| FR-13 | Optional authentication with roles | Auth, RBAC |

## Non-functional requirements

| ID | Requirement | How it is met |
|---|---|---|
| NFR-1 Security | Generated code isolated; secrets protected; input validated | See [security.md](security.md) |
| NFR-2 Reliability | Workflows survive restarts while waiting for approval; failures recorded, never lost | SQLite checkpoints; runner exception handling |
| NFR-3 Data integrity | Invalid states impossible at the DB level | FKs, CHECK constraints, migrations |
| NFR-4 Honesty | No fabricated tests, metrics or sources | Counts from execution; mock labels; skipped ≠ passed |
| NFR-5 Performance | API responsive while agents run | Background threads; WAL; p50/p95 latency tracked |
| NFR-6 Usability | Clear, responsive, accessible UI | Tailwind layout, keyboard-focusable controls, labelled inputs, colour + text status |
| NFR-7 Maintainability | Modular layers, typed code, tests, CI | See [architecture.md](architecture.md), [testing.md](testing.md) |
| NFR-8 Portability | Run locally or in containers | venv/npm or Docker Compose |
