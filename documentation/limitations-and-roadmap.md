# Known Limitations & Roadmap

## Known limitations

| Area | Limitation |
|---|---|
| LLM quality | Verified live with Gemini `gemini-3.1-flash-lite` (a small, fast model): it produces valid structured output but writes thin test suites (≈3 tests). Larger models should produce better code and tests. Free-tier Gemini models are sometimes overloaded (HTTP 503); the agent retry policy absorbs short outages. |
| Mock mode | Rule-based keyword heuristics. Useful for demos and development, but not intelligent: reviewer feedback is recorded but not semantically applied. Everything is labelled *mock*. |
| Generated software | The mock generator, and the live Developer prompt, target a FastAPI service with in-memory storage and no auth, so it can be tested offline. It is a prototype, not production code. Live-LLM code quality varies by model. |
| Sandbox packages | Generated code can only use fastapi, pydantic, pytest and httpx (pre-installed; no network at test time). |
| Compose | Sandbox disabled inside Compose to avoid mounting the Docker socket. |
| Scale | Single process with background threads and SQLite. Not designed for many concurrent workflows or multiple API instances. The rate limiter and latency metrics are in-memory. |
| Restarts | A workflow that was *running* (not waiting for approval) when the server stopped is marked failed and must be restarted. |
| Real-time | The UI polls every 1.5–3 s instead of streaming. |
| Auth | Single-tenant: all authenticated users see all projects. No password reset or MFA. |
| Research | No web browsing; sources are model knowledge and labelled unverified. |
| Cost | Cost is estimated from configured prices × real token counts. Accurate only if prices are set correctly. |

## Roadmap

1. Dedicated **sandbox runner service** (gVisor or Firecracker) so tests run safely in containerised deployments.
2. **PostgreSQL + Redis/Celery** workers; LangGraph Postgres checkpointer; horizontal scaling.
3. **Server-Sent Events** for live logs and status.
4. **GitHub integration**: push the approved package as a branch and pull request (still behind human approval).
5. **RAG** over company coding standards and past projects for the Architect and Developer agents.
6. Live **web research** with real citation fetching and verification.
7. Multi-tenant organisations, SSO, per-project permissions.
8. Frontend code generation and visual previews of generated UIs.
