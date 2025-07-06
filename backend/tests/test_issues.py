import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.fixture
def admin_token():
    admin = {"email": "admin2@example.com", "password": "adminpass", "role": "ADMIN"}
    client.post("/api/auth/register", json=admin)
    r = client.post("/api/auth/login", data={"email": admin["email"], "password": admin["password"]})
    return r.json()["access_token"]

@pytest.fixture
def reporter_token():
    user = {"email": "rep@example.com", "password": "reppass", "role": "REPORTER"}
    client.post("/api/auth/register", json=user)
    r = client.post("/api/auth/login", data={"email": user["email"], "password": user["password"]})
    return r.json()["access_token"]

def test_create_and_list_issue(reporter_token):
    r = client.post("/api/issues", headers={"Authorization": f"Bearer {reporter_token}"}, data={"title": "Bug", "description": "desc", "severity": "LOW"})
    assert r.status_code == 200
    r = client.get("/api/issues", headers={"Authorization": f"Bearer {reporter_token}"})
    assert r.status_code == 200
    assert len(r.json()) >= 1

def test_delete_issue(admin_token, reporter_token):
    # Reporter creates issue
    r = client.post("/api/issues", headers={"Authorization": f"Bearer {reporter_token}"}, data={"title": "Bug2", "description": "desc", "severity": "LOW"})
    issue_id = r.json()["id"]
    # Admin deletes
    r = client.delete(f"/api/issues/{issue_id}", headers={"Authorization": f"Bearer {admin_token}"})
    assert r.status_code == 200
    # Reporter cannot delete
    r = client.post("/api/issues", headers={"Authorization": f"Bearer {reporter_token}"}, data={"title": "Bug3", "description": "desc", "severity": "LOW"})
    issue_id = r.json()["id"]
    r = client.delete(f"/api/issues/{issue_id}", headers={"Authorization": f"Bearer {reporter_token}"})
    assert r.status_code == 403 