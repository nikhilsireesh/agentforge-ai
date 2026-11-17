"""Project and requirement API tests."""

from tests.conftest import INVENTORY_REQUIREMENT, LEAVE_REQUIREMENT


def test_create_project_with_requirement(client, leave_project):
    assert leave_project["name"] == "Employee Leave Management System"
    assert leave_project["status"] == "draft"
    assert leave_project["requirement_count"] == 1
    requirements = client.get(f"/api/projects/{leave_project['id']}/requirements").json()
    assert requirements[0]["raw_requirement"] == LEAVE_REQUIREMENT
    assert requirements[0]["approval_status"] == "pending"


def test_list_search_filter_sort_and_paginate(client):
    for name, domain in [("Alpha HR", "HR"), ("Beta Stock", "Retail"), ("Gamma HR", "HR")]:
        client.post("/api/projects", json={"name": name, "business_domain": domain})

    page = client.get("/api/projects", params={"page_size": 2}).json()
    assert page["total"] == 3 and len(page["items"]) == 2 and page["page"] == 1

    found = client.get("/api/projects", params={"search": "stock"}).json()
    assert [p["name"] for p in found["items"]] == ["Beta Stock"]

    hr = client.get("/api/projects", params={"business_domain": "hr", "sort": "name",
                                             "order": "asc"}).json()
    assert [p["name"] for p in hr["items"]] == ["Alpha HR", "Gamma HR"]


def test_update_and_delete_project(client, leave_project):
    pid = leave_project["id"]
    updated = client.put(f"/api/projects/{pid}", json={"description": "Updated"}).json()
    assert updated["description"] == "Updated"
    assert updated["name"] == leave_project["name"]  # untouched fields are kept

    assert client.delete(f"/api/projects/{pid}").status_code == 204
    assert client.get(f"/api/projects/{pid}").status_code == 404


def test_requirement_crud_and_validation(client, leave_project):
    pid = leave_project["id"]
    created = client.post(f"/api/projects/{pid}/requirements",
                          json={"raw_requirement": INVENTORY_REQUIREMENT})
    assert created.status_code == 201
    rid = created.json()["id"]

    too_short = client.post(f"/api/projects/{pid}/requirements", json={"raw_requirement": "x"})
    assert too_short.status_code == 422

    invalid = client.put(f"/api/requirements/{rid}",
                         json={"structured_output": {"project_name": "no requirements"}})
    assert invalid.status_code == 422

    edited = client.put(f"/api/requirements/{rid}", json={"raw_requirement":
                                                          INVENTORY_REQUIREMENT + " Extra."})
    assert edited.json()["raw_requirement"].endswith("Extra.")


def test_execute_requires_requirement(client):
    project = client.post("/api/projects", json={"name": "Empty"}).json()
    response = client.post(f"/api/projects/{project['id']}/execute")
    assert response.status_code == 400


def test_missing_resources_return_404(client):
    assert client.get("/api/projects/9999").status_code == 404
    assert client.get("/api/executions/9999").status_code == 404
    assert client.get("/api/artifacts/9999").status_code == 404
