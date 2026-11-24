"""FastAPI application entry point.

This file only *assembles* the app (settings, middleware, error handlers,
routers). Business logic lives in services/, agents/, and orchestration/.

Run locally (from the backend/ folder):
    uvicorn app.main:app --reload
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from app.config import APP_VERSION, get_settings
from app.middleware.error_handlers import register_exception_handlers
from app.middleware.metrics import MetricsMiddleware
from app.orchestration import recorder
from app.routes import analytics, artifacts, auth, executions, projects, system
from app.utils.logging import configure_logging

logger = logging.getLogger("agentforge")


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "Starting %s v%s (env=%s, llm_mode=%s, auth=%s)",
            settings.app_name, APP_VERSION, settings.app_env, settings.llm_mode,
            "on" if settings.auth_enabled else "off",
        )
        if settings.app_env != "test":
            recovered = recorder.recover_interrupted()
            if recovered:
                logger.warning("Marked %d interrupted execution(s) as failed.", recovered)
        settings.generated_root.mkdir(parents=True, exist_ok=True)
        yield
        logger.info("Shutting down %s", settings.app_name)

    app = FastAPI(
        title=settings.app_name,
        version=APP_VERSION,
        description=(
            "Multi-agent AI platform: from business requirements to working software. "
            "Errors use the shape {success: false, error: {code, message, details?}}; "
            "lists use {items, total, page, page_size}."
        ),
        lifespan=lifespan,
    )

    # Only the configured frontend origins may call the API from a browser.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type"],
        expose_headers=["Content-Disposition", "X-Response-Time-ms"],
    )
    app.add_middleware(MetricsMiddleware, max_body_bytes=settings.max_request_body_bytes)

    register_exception_handlers(app)
    for module in (system, auth, projects, executions, artifacts, analytics):
        app.include_router(module.router)
    if settings.frontend_dist_dir is not None:
        mount_frontend(app, settings.frontend_dist_dir)
    return app


# Paths owned by the API; never answered with the single-page app.
_API_PREFIXES = ("api/", "docs", "redoc", "openapi.json", "health")


def mount_frontend(app: FastAPI, dist_dir: Path) -> None:
    """Serve the built React app; unknown paths get index.html (React Router handles them)."""
    root = dist_dir.resolve()
    index = root / "index.html"
    if not index.is_file():
        logger.warning("FRONTEND_DIST_DIR=%s has no index.html; frontend not served.", root)
        return

    @app.get("/{full_path:path}", include_in_schema=False)
    def frontend(full_path: str) -> FileResponse:
        if full_path.startswith(_API_PREFIXES):
            raise HTTPException(status_code=404, detail="Not Found")
        candidate = (root / full_path).resolve()
        # Only files inside the build folder; anything else falls back to the app shell.
        if full_path and candidate.is_relative_to(root) and candidate.is_file():
            cache = "public, max-age=31536000, immutable" if full_path.startswith("assets/") \
                else "no-cache"
            return FileResponse(candidate, headers={"Cache-Control": cache})
        return FileResponse(index, headers={"Cache-Control": "no-cache"})


app = create_app()
