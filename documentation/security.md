# Security Design & Responsible AI

| Threat | Control | Where |
|---|---|---|
| Generated code harming the host | Never executed on the host. Static checks only parse (`ast`) or lint (Ruff). pytest runs only in Docker with `--network none`, `--user 10001`, `--read-only`, `--cap-drop ALL`, `no-new-privileges`, CPU/memory/pids limits, a `noexec` tmpfs and a hard timeout plus `docker kill`. The command is a fixed allowlist; nothing from an LLM becomes a command. | `services/sandbox.py` |
| Host credentials leaking into the sandbox | Only the generated code (read-only) and an output folder are mounted. No Docker socket, no home directory, no environment secrets. Compose disables the sandbox rather than mounting the socket. | `sandbox.py`, `docker-compose.yml` |
| Prompt injection | User and agent content is wrapped in `<untrusted_data>`, with closing tags neutralised. System prompts give security rules priority. Outputs must match strict schemas, and test counts never come from the model. | `prompts/templates.py`, `agents/` |
| Fabricated research or tests | Sources are forced to `unverified`. Skipped tests are shown as skipped. Mock outputs are labelled everywhere. | `research.py`, `graph.py` |
| Path traversal / arbitrary file write | Artifact paths validated twice: by schema (relative, safe characters, allowed extensions, no `..` or dotfiles) and by `safe_join` (resolved path must stay inside the storage root). Symlinks are skipped when zipping and serving. | `agents/schemas.py`, `services/artifact_store.py` |
| Stored XSS through generated files | Artifact downloads use `application/octet-stream` plus `nosniff` and are never rendered as HTML. Markdown is rendered by react-markdown without raw HTML. | `routes/artifacts.py` |
| Weak credentials storage | PBKDF2-HMAC-SHA256, 600k iterations, random salt, constant-time compare. | `services/auth_service.py` |
| Unauthorised actions | Optional JWT (HS256, expiring). Roles: admin, reviewer, member. Only reviewers and admins decide approvals; members modify only their own projects. Production refuses to start auth without `JWT_SECRET`. Optional `DEMO_LOGIN_ENABLED` adds a one-click shared *Guest Reviewer* (reviewer role, random unusable password, password login refused) for public demos. | `dependencies.py` |
| Abuse / DoS | Per-IP rate limit on workflow starts and auth; 1 MB request-body limit; input length limits; LLM timeouts, token caps and retry limits; recursion limit on the graph. | `dependencies.py`, `middleware/metrics.py`, `config.py` |
| SSRF via research URLs | URL probing is off by default. When enabled, only `https` URLs resolving to public IPs, with no redirects. | `agents/research.py` |
| Secret exposure | Secrets only from env (`SecretStr`). LLM errors never include the key. Generic 500 responses. `.env` is git-ignored. | `config.py`, `llm_client.py`, `error_handlers.py` |
| Cross-origin abuse | CORS restricted to configured origins; nginx security headers. | `main.py`, `docker/nginx.conf` |
| Untraceable decisions | Approvals store reviewer, timestamp and feedback. The `agentforge.audit` logger records create/update/delete/execute/approve/reject. Execution logs persist every step. | `routes/*`, `recorder.py` |
| Unsupervised changes | Five mandatory human checkpoints. AgentForge never deploys; it produces a package that a human approved. | `orchestration/graph.py` |

**Agents have no administrative permissions.** They are pure functions from context to validated output. They cannot read or write the database, the filesystem, or the network (apart from the optional research URL check).
