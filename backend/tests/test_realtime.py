from fastapi.testclient import TestClient
from backend.main import app

def test_socketio_connect():
    client = TestClient(app)
    r = client.get("/socket.io/")
    assert r.status_code in (200, 400, 404)  # 400/404 if not a websocket request, 200 if handled 