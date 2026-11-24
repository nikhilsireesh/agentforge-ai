"""Shared test fixtures.

Each test gets its own temporary SQLite database file and generated-files
folder, so tests never touch real data and never affect each other.
Workflows run inline (same thread) in mock mode with the sandbox disabled.
"""

import os
import tempfile
from collections.abc import Generator

# Must be set before the app is imported (settings are read once).
_TMP = tempfile.mkdtemp(prefix="agentforge-tests-")
os.environ.update({
    "APP_ENV": "test",
    "EXECUTION_MODE": "inline",
    "LLM_API_KEY": "",
    "SANDBOX_MODE": "disabled",
    "AUTH_ENABLED": "false",
    "CHECKPOINT_DB_PATH": ":memory:",
    "GENERATED_PROJECTS_DIR": os.path.join(_TMP, "generated"),
    "RATE_LIMIT_PER_MINUTE": "1000",
    "MOCK_INJECT_DEFECT": "true",
    "RESEARCH_CHECK_URLS": "false",
})

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from app import database  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.database import build_engine  # noqa: E402
from app.dependencies import rate_limiter  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Base  # noqa: E402
from app.orchestration import runner  # noqa: E402

get_settings.cache_clear()

LEAVE_REQUIREMENT = (
    "Build an employee leave management application with employee registration, login, leave "
    "applications, manager approvals, HR administration, leave balance tracking, and "
    "attendance reports."
)
INVENTORY_REQUIREMENT = (
    "Build an inventory management application with product catalogue, supplier management, "
    "warehouse stock levels, purchase orders, low-stock alerts, and inventory reports."
)


@pytest.fixture()
def engine(tmp_path):
    test_engine = build_engine(f"sqlite:///{tmp_path / 'test.db'}")
    Base.metadata.create_all(test_engine)
    original_bind = database.SessionLocal.kw["bind"]
    database.SessionLocal.configure(bind=test_engine)
    runner.reset_graph()
    rate_limiter.reset()
    yield test_engine
    database.SessionLocal.configure(bind=original_bind)
    runner.reset_graph()
    test_engine.dispose()


@pytest.fixture()
def db_session(engine) -> Generator[Session, None, None]:
    session = database.SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def client(engine) -> Generator[TestClient, None, None]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture()
def settings():
    return get_settings()


@pytest.fixture()
def leave_project(client) -> dict:
    response = client.post("/api/projects", json={
        "name": "Employee Leave Management System",
        "description": "Leave and attendance management for a mid-sized company.",
        "business_domain": "Human Resources",
        "complexity": "medium",
        "requirement": LEAVE_REQUIREMENT,
    })
    assert response.status_code == 201, response.text
    return response.json()
