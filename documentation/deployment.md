# Deployment Guide

## Render (public demo, one click)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/nikhilsireesh/agentforge-ai)

The `render.yaml` Blueprint creates one free Docker web service from `docker/render.Dockerfile`. FastAPI serves both the API and the built React app (`FRONTEND_DIST_DIR`), so there is a single URL and no CORS setup.

1. Sign in at render.com with GitHub, open the button link above and click **Apply**.
2. The first build takes about 5 minutes. Open the `https://agentforge-ai-….onrender.com` URL Render shows.

Public-demo defaults:

- **Mock LLM mode.** No API key is set, so visitors can't spend your LLM quota.
- **Sandbox disabled.** Render can't run Docker inside a service, so generated pytest runs are reported as *skipped*; static checks still run.
- **Free-plan limits.** The service sleeps after about 15 minutes idle (the first request then takes about a minute), and there is no persistent disk, so projects reset on restart. For persistence, switch to a paid plan, add a disk mounted at `/data`, and keep the defaults.

To use a real LLM on a public URL, set `AUTH_ENABLED=true` first (a `JWT_SECRET` is already generated), then add `LLM_API_KEY`, `LLM_BASE_URL` and `LLM_MODEL` in the service's **Environment** tab. Without auth, anyone with the link could use up your quota.


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
| Single service (Render) | `docker/render.Dockerfile` | repository root |

## CI (`.github/workflows/ci.yml`)

On every push to `main` and every pull request: backend lint, migrations and tests; frontend build; Playwright E2E; and Docker builds of all four images.

## Production checklist

- [ ] `APP_ENV=production`, `AUTH_ENABLED=true`, a long random `JWT_SECRET`
- [ ] Real `CORS_ORIGINS`; serve over HTTPS (TLS at a load balancer or reverse proxy)
- [ ] Switch `DATABASE_URL` to PostgreSQL (the SQLAlchemy models and Alembic migrations are portable; driver needed: `psycopg`)
- [ ] Back up the data volume (database, checkpoints, generated files)
- [ ] Set LLM pricing variables if cost reporting matters
- [ ] Centralise logs (the `agentforge.audit` logger) and monitor `/health`
- [ ] Keep human approval mandatory. AgentForge never deploys generated software itself.
