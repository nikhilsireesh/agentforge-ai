# Deployment Guide

## Docker Compose (single host)

```bash
cp backend/.env.example backend/.env    # set LLM_API_KEY, AUTH_ENABLED=true, JWT_SECRET=...
docker compose up --build -d
open http://localhost:8080
```

- `frontend`: nginx serves the React build and proxies `/api` and `/health` to `backend:8000`.
- `backend`: runs `alembic upgrade head`, then uvicorn as a non-root user. Data lives in the `agentforge-data` volume (`/data`: database, checkpoints, generated files).
- The sandbox is **disabled in Compose**. Executing generated tests from inside a container would need the Docker socket, which is effectively root on the host. For sandboxed test execution, run the backend on a host with Docker (see README) or move test execution to a dedicated, isolated runner service (see the roadmap).

## Images

| Image | Dockerfile | Build context |
|---|---|---|
| Backend | `docker/backend.Dockerfile` | repository root |
| Frontend | `docker/frontend.Dockerfile` | repository root |
| Test sandbox | `docker/sandbox.Dockerfile` | `docker/` |

## CI (`.github/workflows/ci.yml`)

On every push to `main` and every pull request: backend lint, migrations and tests; frontend build; Playwright E2E; and Docker builds of all three images.

## Production checklist

- [ ] `APP_ENV=production`, `AUTH_ENABLED=true`, a long random `JWT_SECRET`
- [ ] Real `CORS_ORIGINS`; serve over HTTPS (TLS at a load balancer or reverse proxy)
- [ ] Switch `DATABASE_URL` to PostgreSQL (the SQLAlchemy models and Alembic migrations are portable; driver needed: `psycopg`)
- [ ] Back up the data volume (database, checkpoints, generated files)
- [ ] Set LLM pricing variables if cost reporting matters
- [ ] Centralise logs (the `agentforge.audit` logger) and monitor `/health`
- [ ] Keep human approval mandatory. AgentForge never deploys generated software itself.
