from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_telemetry():
    response = client.get("/api/v1/telemetry")
    assert response.status_code == 200
    payload = response.json()
    assert payload["cpu_percent"] >= 0
    assert payload["memory"]["total"] > 0


def test_requires_github_token():
    response = client.get("/api/v1/repos")
    assert response.status_code == 401
