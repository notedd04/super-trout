from fastapi.testclient import TestClient

from clouddeck.backend.main import app
from tests.conftest import TEST_PASSWORD


client = TestClient(app, base_url="https://testserver")


def login():
    response = client.post(
        "/api/v1/auth/login",
        json={"password": TEST_PASSWORD},
        headers={"Origin": "https://testserver"},
    )
    assert response.status_code == 200
    return client.cookies.get("clouddeck_csrf")


def test_auth_flow_and_private_bootstrap_contract():
    client.cookies.clear()
    assert client.get("/api/v1/auth/status").json()["authenticated"] is False
    csrf = login()
    assert csrf
    bootstrap = client.get("/api/v1/bootstrap")
    assert bootstrap.status_code == 200
    data = bootstrap.json()
    assert data["app"]["version"] == "0.2.0"
    assert data["workspace"]["name"] == "clouddeck-test"
    assert data["session"]["provider"] == "codespaces"
    assert data["session"]["transport"] == "novnc"
    assert data["capabilities"]["stream_transport"]["webrtc"] is False
    assert data["capabilities"]["gpu_acceleration"] is False
    assert data["session"]["running"] is False


def test_mutation_requires_csrf_and_same_origin():
    client.cookies.clear()
    login()
    profile = client.post(
        "/api/v1/profile",
        json={"profile_id": "data_saver"},
        headers={"Origin": "https://testserver"},
    )
    assert profile.status_code == 403

    csrf = client.cookies.get("clouddeck_csrf")
    profile = client.post(
        "/api/v1/profile",
        json={"profile_id": "data_saver"},
        headers={"Origin": "https://attacker.example", "X-CSRF-Token": csrf},
    )
    assert profile.status_code == 403


def test_profile_mutation_uses_known_profile():
    client.cookies.clear()
    csrf = login()
    response = client.post(
        "/api/v1/profile",
        json={"profile_id": "data_saver"},
        headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.json()["profile"]["resolution"] == "800x450"


def test_tool_contract_is_allowlisted():
    client.cookies.clear()
    login()
    tools = client.get("/api/v1/tools")
    assert tools.status_code == 200
    ids = {item["id"] for item in tools.json()["tools"]}
    assert {"python", "git", "ffmpeg"}.issubset(ids)

    csrf = client.cookies.get("clouddeck_csrf")
    rejected = client.post(
        "/api/v1/tools/run",
        json={"tool": "bash", "args": ["-c", "echo unsafe"]},
        headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
    )
    assert rejected.status_code == 422


def test_gemini_and_openrouter_provider_presets():
    client.cookies.clear()
    csrf = login()
    gemini = client.post(
        "/api/v1/providers/preset",
        json={"provider": "gemini", "model": "gemini-2.5-flash"},
        headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
    )
    assert gemini.status_code == 200
    assert gemini.json()["base_url"] == "https://generativelanguage.googleapis.com/v1beta/openai"


def test_unknown_application_is_rejected_without_shell_endpoint():
    client.cookies.clear()
    csrf = login()
    response = client.post(
        "/api/v1/apps/launch",
        json={"app_id": "arbitrary-shell"},
        headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
    )
    assert response.status_code == 409


def test_developer_workspace_save_and_run_are_authenticated(tmp_path):
    client.cookies.clear()
    unauthorized = client.post(
        "/api/v1/developer/files",
        json={"name": "hello.py", "code": "print('hello')"},
        headers={"Origin": "https://testserver"},
    )
    assert unauthorized.status_code == 401

    csrf = login()
    saved = client.post(
        "/api/v1/developer/files",
        json={"name": "hello.py", "code": "print('hello')"},
        headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
    )
    assert saved.status_code == 200
    run = client.post(
        "/api/v1/developer/run",
        json={"name": "hello.py", "timeout_seconds": 5},
        headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
    )
    assert run.status_code == 200
    assert run.json()["stdout"].strip() == "hello"


def test_automation_rejects_unknown_recipe():
    client.cookies.clear()
    csrf = login()
    response = client.post(
        "/api/v1/automation/run",
        json={"recipe": "rm -rf /"},
        headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
    )
    assert response.status_code == 422


def test_ai_status_does_not_expose_credentials():
    client.cookies.clear()
    csrf = login()
    response = client.get("/api/v1/ai/status")
    assert response.status_code == 200
    assert response.json()["configured"] is False
    assert "api_key" not in response.json()


def test_input_heartbeat_requires_auth_and_reports_lease_state():
    client.cookies.clear()
    unauthorized = client.post(
        "/api/v1/input/heartbeat",
        headers={"Origin": "https://testserver"},
    )
    assert unauthorized.status_code == 401

    csrf = login()
    response = client.post(
        "/api/v1/input/heartbeat",
        headers={"Origin": "https://testserver", "X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True, "active": False, "lease_ms": 900}
