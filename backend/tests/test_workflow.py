"""End-to-end workflow tests through the public API (mock LLM mode, sandbox disabled).

These prove the orchestration really pauses at every approval checkpoint,
resumes on decision, routes failed checks into controlled correction, and
produces documentation and a downloadable delivery package.
"""

import io
import zipfile

from tests.conftest import INVENTORY_REQUIREMENT

CHECKPOINT_ORDER = ["requirements", "architecture", "code", "test_execution", "deployment"]


def execute(client, project_id):
    response = client.post(f"/api/projects/{project_id}/execute")
    assert response.status_code == 202, response.text
    return response.json()["id"]


def state(client, execution_id):
    return client.get(f"/api/executions/{execution_id}").json()


def approve(client, execution_id, feedback=None):
    response = client.post(f"/api/executions/{execution_id}/approve",
                           json={"feedback": feedback})
    assert response.status_code == 200, response.text
    return response.json()


def run_to_completion(client, execution_id):
    seen = []
    for _ in range(10):
        current = state(client, execution_id)
        if current["status"] != "waiting_approval":
            break
        seen.append(current["pending_approval"]["checkpoint"])
        approve(client, execution_id)
    return seen, state(client, execution_id)


def test_full_workflow_with_correction_and_delivery(client, leave_project):
    execution_id = execute(client, leave_project["id"])

    first = state(client, execution_id)
    assert first["status"] == "waiting_approval"
    assert first["llm_mode"] == "mock"
    assert first["pending_approval"]["checkpoint"] == "requirements"
    analysis = first["outputs"]["requirement_analyst"]
    assert len(analysis["functional_requirements"]) >= 7
    assert analysis["missing_information"] and analysis["clarification_questions"]
    assert "Manager" in analysis["user_roles"]

    seen, final = run_to_completion(client, execution_id)
    assert ["requirements", *seen][:1] == ["requirements"]
    assert seen == CHECKPOINT_ORDER
    assert final["status"] == "completed", final["error_message"]
    # The injected mock defect was caught by real static checks and corrected once.
    assert final["correction_attempts"] == 1

    tests = client.get(f"/api/executions/{execution_id}/tests").json()
    first_iteration = [t for t in tests if t["iteration"] == 0]
    second_iteration = [t for t in tests if t["iteration"] == 1]
    assert any(t["test_status"] == "failed" and "ruff::app/main.py" in t["test_name"]
               for t in first_iteration)
    assert not any(t["test_status"] == "failed" for t in second_iteration)
    # Sandbox disabled → pytest is honestly reported as skipped, never passed.
    pytest_rows = [t for t in tests if t["test_name"].startswith("pytest")]
    assert pytest_rows and all(t["test_status"] == "skipped" for t in pytest_rows)

    review = final["outputs"]["review_testing"]
    assert review["failed_tests"] == 0 and review["passed_tests"] > 0
    assert review["skipped_tests"] == 1

    agents = client.get(f"/api/executions/{execution_id}/agents").json()
    names = [a["agent_name"] for a in agents]
    for agent in ["requirement_analyst", "research", "solution_architect", "developer",
                  "review_testing", "documentation"]:
        assert agent in names
    assert names.count("developer") == 2  # original + one correction
    assert all(a["status"] == "completed" and a["is_mock"] for a in agents)

    artifacts = client.get(f"/api/projects/{leave_project['id']}/artifacts").json()
    docs = [a for a in artifacts if a["metadata_json"].get("category") == "delivery_document"]
    code = [a for a in artifacts if a["metadata_json"].get("category") == "code"]
    assert len(docs) == 11
    assert code and all(a["metadata_json"]["code_version"] == 2 for a in code)
    assert all(a["approval_status"] == "approved" for a in code)

    main_py = next(a for a in code if a["metadata_json"]["relative_path"] == "app/main.py")
    content = client.get(f"/api/artifacts/{main_py['id']}").json()["content"]
    assert "HTTPExeption" not in content and "/api/leave-requests" in content

    report = next(a for a in docs if "test_report" in a["file_path"])
    report_text = client.get(f"/api/artifacts/{report['id']}").json()["content"]
    assert "Mock mode" in report_text and "Skipped" in report_text

    package = client.get(f"/api/executions/{execution_id}/package")
    assert package.status_code == 200
    names_in_zip = zipfile.ZipFile(io.BytesIO(package.content)).namelist()
    assert "manifest.json" in names_in_zip
    assert "source/app/main.py" in names_in_zip
    assert "docs/11_final_delivery_report.md" in names_in_zip

    project = client.get(f"/api/projects/{leave_project['id']}").json()
    assert project["status"] == "completed"

    workflow = client.get(f"/api/executions/{execution_id}/workflow").json()
    statuses = {n["id"]: n["status"] for n in workflow["nodes"]}
    assert statuses["correction"] == "completed"
    assert statuses["documentation"] == "completed"
    assert any(e["source"] == "correction" and e["traversed"] for e in workflow["edges"])

    logs = client.get(f"/api/executions/{execution_id}/logs").json()
    assert any("Controlled correction 1/2" in log["message"] for log in logs)


def test_revision_request_reruns_agent_with_feedback(client, leave_project):
    execution_id = execute(client, leave_project["id"])
    response = client.post(f"/api/executions/{execution_id}/reject", json={
        "feedback": "Please add a requirement for public holidays.", "request_revision": True})
    assert response.status_code == 200
    assert response.json()["decision"] == "revision_requested"

    current = state(client, execution_id)
    assert current["pending_approval"]["checkpoint"] == "requirements"
    runs = client.get(f"/api/executions/{execution_id}/agents").json()
    assert [r["agent_name"] for r in runs] == ["requirement_analyst", "requirement_analyst"]
    assert runs[1]["input_data"]["revision_feedback"].startswith("Please add")


def test_rejection_stops_workflow(client, leave_project):
    execution_id = execute(client, leave_project["id"])
    approve(client, execution_id)  # requirements
    client.post(f"/api/executions/{execution_id}/reject",
                json={"feedback": "Wrong architecture direction."})
    final = state(client, execution_id)
    assert final["status"] == "cancelled"
    assert "architecture" in final["error_message"]
    names = [r["agent_name"] for r in client.get(f"/api/executions/{execution_id}/agents").json()]
    assert "developer" not in names


def test_edited_requirements_flow_into_next_agents(client, leave_project):
    execution_id = execute(client, leave_project["id"])
    requirement = client.get(f"/api/projects/{leave_project['id']}/requirements").json()[0]
    edited = requirement["structured_output"]
    edited["functional_requirements"].append({
        "id": "FR-99", "description": "The system shall support public holiday calendars.",
        "priority": "should", "source": "stated"})
    assert client.put(f"/api/requirements/{requirement['id']}",
                      json={"structured_output": edited}).status_code == 200
    approve(client, execution_id)
    research_run = [r for r in client.get(f"/api/executions/{execution_id}/agents").json()
                    if r["agent_name"] == "research"][0]
    assert research_run["input_data"]["functional_requirements"] == \
        len(edited["functional_requirements"])
    requirement = client.get(f"/api/projects/{leave_project['id']}/requirements").json()[0]
    assert requirement["approval_status"] == "approved"


def test_cancel_waiting_execution_and_conflicts(client, leave_project):
    execution_id = execute(client, leave_project["id"])
    # Only one active execution per project.
    assert client.post(f"/api/projects/{leave_project['id']}/execute").status_code == 409
    # Deleting a project with an active execution is blocked.
    assert client.delete(f"/api/projects/{leave_project['id']}").status_code == 409

    cancelled = client.post(f"/api/executions/{execution_id}/cancel").json()
    assert cancelled["status"] == "cancelled"
    assert client.post(f"/api/executions/{execution_id}/approve").status_code == 409
    approvals = client.get("/api/approvals", params={"execution_id": execution_id}).json()
    assert approvals["items"][0]["decision"] == "rejected"


def test_inventory_domain_second_demo(client, settings, monkeypatch):
    monkeypatch.setattr(settings, "mock_inject_defect", False)
    project = client.post("/api/projects", json={
        "name": "Inventory Management", "business_domain": "Retail",
        "requirement": INVENTORY_REQUIREMENT}).json()
    execution_id = execute(client, project["id"])
    _, final = run_to_completion(client, execution_id)
    assert final["status"] == "completed"
    assert final["correction_attempts"] == 0
    entities = [e["name"] for e in final["outputs"]["solution_architect"]["database_entities"]]
    assert {"Product", "Supplier", "Warehouse", "PurchaseOrder"} <= set(entities)


def test_analytics_reflect_real_data(client, leave_project):
    empty = client.get("/api/analytics/overview").json()
    assert empty["total_executions"] == 0 and empty["agent_completion_rate"] is None

    execution_id = execute(client, leave_project["id"])
    run_to_completion(client, execution_id)

    overview = client.get("/api/analytics/overview").json()
    assert overview["total_projects"] == 1
    assert overview["successful_executions"] == 1
    assert overview["agent_completion_rate"] == 1.0
    assert overview["recent_activity"]

    agents = {a["agent"]: a for a in client.get("/api/analytics/agents").json()}
    assert agents["developer"]["total_runs"] == 2
    assert agents["developer"]["mock_runs"] == 2

    executions = client.get("/api/analytics/executions").json()
    assert executions["workflow_completion_rate"] == 1.0
    assert executions["executions_with_corrections"] == 1
    assert executions["llm"]["total_tokens"] == 0  # mock mode uses no tokens
    assert executions["llm"]["estimated_cost_usd"] == 0
    assert executions["test_totals"]["failed"] >= 1  # the injected defect, really detected


def test_critical_review_opinion_alone_does_not_trigger_correction(client, leave_project,
                                                                  settings, monkeypatch):
    from app.agents import AGENTS

    monkeypatch.setattr(settings, "mock_inject_defect", False)
    reviewer = AGENTS["review_testing"]
    original = reviewer.mock_output

    def with_critical(ctx):
        output = original(ctx)
        output["issues"].append({"id": "ISS-99", "severity": "critical", "category": "scope",
                                 "file_path": None, "description": "No authentication.",
                                 "recommendation": "Add auth."})
        return output

    monkeypatch.setattr(reviewer, "mock_output", with_critical)
    execution_id = execute(client, leave_project["id"])
    for _ in range(4):
        approve(client, execution_id)
    current = state(client, execution_id)
    assert current["correction_attempts"] == 0
    assert current["pending_approval"]["checkpoint"] == "deployment"
    assert current["pending_approval"]["summary"]["critical_review_issues"] == 1


def test_regression_guard_delivers_best_version(client, leave_project, settings, monkeypatch):
    from app.agents import AGENTS

    monkeypatch.setattr(settings, "mock_inject_defect", False)
    developer = AGENTS["developer"]
    original = developer.mock_output

    def regressing(ctx):
        output = original(ctx)
        broken = ["app/main.py"] if ctx["code_version"] == 1 else ["app/main.py", "app/models.py"]
        for artifact in output["artifacts"]:
            if artifact["file_path"] in broken:
                artifact["content"] += "\nBROKEN = undefined_name\n"
        return output

    monkeypatch.setattr(developer, "mock_output", regressing)
    execution_id = execute(client, leave_project["id"])
    seen, final = run_to_completion(client, execution_id)
    assert final["status"] == "completed"
    assert final["correction_attempts"] == 2
    review = final["outputs"]["review_testing"]
    assert review["code_version"] == 1 and review["reverted_from_version"] == 3
    assert review["failed_tests"] == 1

    logs = client.get(f"/api/executions/{execution_id}/logs").json()
    assert any("Regression guard" in log["message"] for log in logs)

    package = client.get(f"/api/executions/{execution_id}/package")
    archive = zipfile.ZipFile(io.BytesIO(package.content))
    assert '"code_version": 1' in archive.read("manifest.json").decode()

    artifacts = client.get(f"/api/projects/{leave_project['id']}/artifacts",
                           params={"latest_only": False}).json()
    approved = {a["metadata_json"]["code_version"] for a in artifacts
                if a["metadata_json"].get("category") == "code"
                and a["approval_status"] == "approved"}
    assert approved == {1}
