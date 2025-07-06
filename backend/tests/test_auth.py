import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

@pytest.fixture
def user_data():
    return {"email": "test@example.com", "password": "testpass", "role": "REPORTER"}

def test_register_and_login(user_data):
    r = client.post("/api/auth/register", json=user_data)
    assert r.status_code == 200
    r = client.post("/api/auth/login", data={"email": user_data["email"], "password": user_data["password"]})
    assert r.status_code == 200
    token = r.json()["access_token"]
    assert token

def test_rbac_user_list(user_data):
    # Register admin
    admin = {"email": "admin@example.com", "password": "adminpass", "role": "ADMIN"}
    client.post("/api/auth/register", json=admin)
    r = client.post("/api/auth/login", data={"email": admin["email"], "password": admin["password"]})
    token = r.json()["access_token"]
    # Admin can list users
    r = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    # Reporter cannot list users
    client.post("/api/auth/register", json=user_data)
    r = client.post("/api/auth/login", data={"email": user_data["email"], "password": user_data["password"]})
    token = r.json()["access_token"]
    r = client.get("/api/users", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403 