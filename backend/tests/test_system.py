"""Tests for health/status endpoints and the global error format."""

from app.config import APP_VERSION


def test_health_returns_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["app_name"] == "AgentForge AI"
    assert body["version"] == APP_VERSION
    assert "X-Response-Time-ms" in response.headers


def test_system_status_reports_components(client):
    body = client.get("/api/system/status").json()
    assert body["status"] == "ok"
    assert body["database"]["status"] == "ok"
    assert body["llm_mode"] == "mock"
    assert body["sandbox"]["status"] == "unavailable"
    assert "SANDBOX_MODE=disabled" in body["sandbox"]["detail"]
    assert body["auth_enabled"] is False


def test_unknown_route_uses_consistent_error_format(client):
    response = client.get("/does-not-exist")
    assert response.status_code == 404
    assert response.json() == {
        "success": False,
        "error": {"code": "HTTP_404", "message": "Not Found"},
    }


def test_validation_error_format(client):
    response = client.post("/api/projects", json={"name": ""})
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["error"]["code"] == "VALIDATION_ERROR"
    assert body["error"]["details"]


def test_openapi_documents_all_required_endpoints(client):
    paths = client.get("/openapi.json").json()["paths"]
    required = [
        "/api/projects", "/api/projects/{project_id}", "/api/projects/{project_id}/requirements",
        "/api/requirements/{requirement_id}", "/api/projects/{project_id}/execute",
        "/api/executions/{execution_id}", "/api/executions/{execution_id}/agents",
        "/api/executions/{execution_id}/logs", "/api/executions/{execution_id}/cancel",
        "/api/approvals", "/api/executions/{execution_id}/approve",
        "/api/executions/{execution_id}/reject", "/api/projects/{project_id}/artifacts",
        "/api/artifacts/{artifact_id}", "/api/artifacts/{artifact_id}/download",
        "/api/analytics/overview", "/api/analytics/agents", "/api/analytics/executions",
        "/health", "/api/system/status",
    ]
    missing = [path for path in required if path not in paths]
    assert missing == []


def test_cors_allows_configured_frontend_only(client):
    allowed = client.options(
        "/health",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers.get("access-control-allow-origin") == "http://localhost:5173"

    blocked = client.options(
        "/health",
        headers={"Origin": "http://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in blocked.headers


def test_oversized_body_rejected(client):
    response = client.post("/api/projects", content=b"x" * 1_100_000,
                           headers={"Content-Type": "application/json"})
    assert response.status_code == 413
