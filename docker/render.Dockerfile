# Single-container image for platforms that run one web service (e.g. Render):
# FastAPI serves both the API and the built React app on one origin.
#   docker build -f docker/render.Dockerfile -t agentforge-web .
#   docker run -p 8000:8000 agentforge-web        →  http://localhost:8000
FROM node:22-alpine AS frontend
WORKDIR /app
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ .
RUN npm run build

FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    DATABASE_URL=sqlite:////data/agentforge.db \
    CHECKPOINT_DB_PATH=/data/checkpoints.db \
    GENERATED_PROJECTS_DIR=/data/generated_projects \
    FRONTEND_DIST_DIR=/app/frontend_dist \
    SANDBOX_MODE=disabled

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
COPY --from=frontend /app/dist /app/frontend_dist
RUN useradd --uid 10001 --create-home app \
    && mkdir -p /data/generated_projects \
    && chown -R app:app /data /app
USER app

EXPOSE 8000
# Render (and similar hosts) pass the port in $PORT.
CMD ["sh", "-c", "alembic upgrade head && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
