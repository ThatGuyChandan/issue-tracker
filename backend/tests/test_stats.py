from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

def test_dashboard_stats():
    # Register and login as admin
    admin = {"email": "admin3@example.com", "password": "adminpass", "role": "ADMIN"}
    client.post("/api/auth/register", json=admin)
    r = client.post("/api/auth/login", data={"email": admin["email"], "password": admin["password"]})
    token = r.json()["access_token"]
    r = client.get("/api/stats/dashboard", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert isinstance(r.json(), list) 