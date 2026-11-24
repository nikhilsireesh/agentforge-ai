"""Response schemas for system/health endpoints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: Literal["ok"]
    app_name: str
    version: str
    environment: str
    timestamp: datetime


class ComponentStatus(BaseModel):
    status: Literal["ok", "error", "unavailable"]
    detail: str | None = None


class SystemStatusResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    environment: str
    database: ComponentStatus
    sandbox: ComponentStatus
    llm_mode: Literal["live", "mock"]
    llm_model: str
    auth_enabled: bool
    demo_login_enabled: bool = False
    mock_inject_defect: bool
    cost_per_1m_input: float
    cost_per_1m_output: float
    timestamp: datetime
