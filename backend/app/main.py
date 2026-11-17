"""FastAPI application entry point.

This file only *assembles* the app (settings, middleware, error handlers,
routers). Business logic lives in services/, agents/, and orchestration/.

Run locally (from the backend/ folder):
    uvicorn app.main:app --reload
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    return app


app = create_app()
