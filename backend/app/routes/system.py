"""Health and system status endpoints.

- GET /health            -> liveness: "is the process running?" (no DB access, very cheap)
- GET /api/system/status -> readiness: database, sandbox, LLM mode, auth mode
"""

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.config import APP_VERSION, Settings, get_settings
from app.database import get_db
from app.schemas.system import ComponentStatus, HealthResponse, SystemStatusResponse
from app.services.sandbox import sandbox_status

logger = logging.getLogger(__name__)
router = APIRouter(tags=["System"])


@router.get("/health", response_model=HealthResponse, summary="Liveness check")
def health(settings: Settings = Depends(get_settings)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        app_name=settings.app_name,
        version=APP_VERSION,
        environment=settings.app_env,
        timestamp=datetime.now(UTC),
    )


@router.get(
    "/api/system/status",
    response_model=SystemStatusResponse,
    summary="Readiness check (database, sandbox, LLM mode)",
)
def system_status(
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> SystemStatusResponse:
    try:
        db.execute(text("SELECT 1"))
        database = ComponentStatus(status="ok")
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        database = ComponentStatus(status="error", detail="Database is unreachable.")

    available, reason = sandbox_status(settings)
    return SystemStatusResponse(
        status="ok" if database.status == "ok" else "degraded",
        version=APP_VERSION,
        environment=settings.app_env,
        database=database,
        sandbox=ComponentStatus(status="ok" if available else "unavailable", detail=reason),
        llm_mode=settings.llm_mode,
        llm_model=settings.llm_model,
        auth_enabled=settings.auth_enabled,
        demo_login_enabled=settings.auth_enabled and settings.demo_login_enabled,
        mock_inject_defect=settings.mock_inject_defect,
        cost_per_1m_input=settings.llm_input_cost_per_1m,
        cost_per_1m_output=settings.llm_output_cost_per_1m,
        timestamp=datetime.now(UTC),
    )
