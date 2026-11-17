# AgentForge AI backend (FastAPI + LangGraph). Build from the repository root:
#   docker build -f docker/backend.Dockerfile -t agentforge-backend .
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    DATABASE_URL=sqlite:////data/agentforge.db \
    CHECKPOINT_DB_PATH=/data/checkpoints.db \
    GENERATED_PROJECTS_DIR=/data/generated_projects

WORKDIR /app
COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
# Run as an unprivileged user; /data holds the database, checkpoints and generated files.
RUN useradd --uid 10001 --create-home app \
    && mkdir -p /data/generated_projects \
    && chown -R app:app /data /app
USER app

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000"]
