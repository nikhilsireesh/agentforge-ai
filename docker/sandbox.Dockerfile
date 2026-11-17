# Locked-down image for running GENERATED tests. It contains only the packages
# generated code is allowed to use; containers run with --network none, so
# nothing can be installed or downloaded at test time.
#   docker build -t agentforge-sandbox:latest -f docker/sandbox.Dockerfile docker
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN pip install fastapi==0.115.6 pydantic==2.10.4 uvicorn==0.32.1 pytest==8.3.4 httpx==0.28.1 \
    && useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin sandbox

USER 10001:10001
WORKDIR /workspace
