from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import httpx

from clouddeck.database import Database
from clouddeck.security import SessionSecurity, verify_password
from clouddeck.registry import AdapterRegistry
from clouddeck.settings import Settings
from clouddeck.services.developer_workspace import DeveloperWorkspace
from clouddeck.services.ai_provider import AIProvider
from clouddeck.services.tool_runner import ToolRunner

settings = Settings.load()
settings.state_dir.mkdir(parents=True, exist_ok=True)
auth_config = settings.load_auth()
security = SessionSecurity(auth_config["cookie_secret"])
database = Database(settings.state_dir / "clouddeck.sqlite3")
registry = AdapterRegistry(settings.state_dir, display=settings.display)
provider = registry.provider("codespaces")
transport = registry.transport("novnc")
developer_workspace = DeveloperWorkspace(settings.state_dir)
ai_provider = AIProvider(settings.state_dir)
tool_runner = ToolRunner(settings.state_dir)
provider.session_id = database.active_session_id()


def reconcile_session_record() -> bool:
    """Close a persisted session whose desktop process stack no longer exists."""
    if provider.session_id is None or provider.status()["running"]:
        return False
    stale_session_id = provider.session_id
    database.session_stopped(stale_session_id)
    provider.session_id = None
    database.event(
        "session.interrupted",
        {"session_id": stale_session_id, "reason": "desktop process stack was not running"},
    )
    return True


reconcile_session_record()

app = FastAPI(
    title="CloudDeck Control Plane",
    version="0.2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

login_attempts: dict[str, deque[float]] = defaultdict(deque)


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class ProfileRequest(BaseModel):
    profile_id: str = Field(min_length=1, max_length=32)


class InputRequest(BaseModel):
    keys: list[str] = Field(default_factory=list, max_length=12)


class LaunchRequest(BaseModel):
    app_id: str = Field(min_length=1, max_length=32)


class DeveloperSaveRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    code: str = Field(default="", max_length=100_000)


class DeveloperRunRequest(BaseModel):
    name: str = Field(min_length=3, max_length=100)
    timeout_seconds: float = Field(default=10.0, ge=1.0, le=30.0)


class PointerRequest(BaseModel):
    dx: int = Field(default=0, ge=-500, le=500)
    dy: int = Field(default=0, ge=-500, le=500)
    scroll_y: int = Field(default=0, ge=-20, le=20)
    button: str | None = Field(default=None, max_length=6)


class AIConfigureRequest(BaseModel):
    base_url: str = Field(min_length=8, max_length=300)
    model: str = Field(min_length=1, max_length=200)


class AIKeyRequest(BaseModel):
    api_key: str = Field(min_length=1, max_length=4096)


class AIChatRequest(BaseModel):
    messages: list[dict[str, str]] = Field(min_length=1, max_length=12)
    max_tokens: int = Field(default=1024, ge=64, le=4096)


class AIScreenshotReviewRequest(BaseModel):
    prompt: str = Field(default="Review this desktop screenshot and explain what is visible.", min_length=1, max_length=32000)


class AutomationRequest(BaseModel):
    recipe: str = Field(min_length=3, max_length=32)


class ToolRunRequest(BaseModel):
    tool: str = Field(min_length=2, max_length=32)
    args: list[str] = Field(default_factory=list, max_length=64)
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)


class ProviderPresetRequest(BaseModel):
    provider: str = Field(min_length=2, max_length=32)
    model: str = Field(min_length=1, max_length=200)


def require_auth(request: Request, mutation: bool = False) -> None:
    security.require(request, mutation=mutation)


def require_same_origin(request: Request) -> None:
    security.ensure_same_origin(request)


def session_payload() -> dict[str, Any]:
    profile_id = database.get_setting("profile", "balanced")
    profile = provider.profiles.get(profile_id, provider.profiles["balanced"])
    desktop = provider.status()
    return {
        "app": {"name": "CloudDeck", "version": "0.2.0", "channel": "codespaces"},
        "workspace": {
            "name": settings.codespace_name,
            "repository": os.environ.get("GITHUB_REPOSITORY", ""),
            "url": settings.public_url(),
        },
        "session": {
            **desktop,
            "provider": provider.provider_id,
            "transport": transport.transport_id,
            "profile": profile,
            "stream_path": transport.viewer_path(),
        },
        "profiles": list(provider.profiles.values()),
        "capabilities": {
            **provider.capabilities(),
            "cloud_games_catalog": "external_provider",
            "stream_transport": transport.capabilities(),
        },
        "external_services": [
            {"id": "cloudmoon", "name": "CloudMoon", "kind": "mobile-cloud-gaming", "url": "https://www.cloudmoonapp.com/", "available": True},
        ],
    }


@app.get("/api/v1/health")
def health() -> dict[str, Any]:
    return {"ok": True, "service": "clouddeck-control-plane", "version": "0.2.0"}


@app.get("/api/v1/auth/status")
def auth_status(request: Request) -> dict[str, bool]:
    decoded = security.decode(request.cookies.get("clouddeck_session"))
    return {"authenticated": decoded is not None}


@app.post("/api/v1/auth/login")
def login(payload: LoginRequest, request: Request, response: Response) -> dict[str, Any]:
    require_same_origin(request)
    client_ip = request.client.host if request.client else "unknown"
    now = time.monotonic()
    attempts = login_attempts[client_ip]
    while attempts and now - attempts[0] > 300:
        attempts.popleft()
    if len(attempts) >= 8:
        raise HTTPException(status_code=429, detail="Too many attempts. Wait a few minutes and try again.")
    if not verify_password(payload.password, auth_config["password_hash"]):
        attempts.append(now)
        raise HTTPException(status_code=401, detail="That access key is not correct.")
    attempts.clear()
    token, csrf, expires = security.issue()
    security.set_cookies(response, token, csrf, expires)
    return {"authenticated": True, "expires_at": expires}


@app.post("/api/v1/auth/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    require_auth(request, mutation=True)
    security.clear_cookies(response)
    return {"authenticated": False}


@app.get("/api/v1/auth/check")
def auth_check(request: Request) -> Response:
    try:
        security.require(request, mutation=False)
    except HTTPException:
        return Response(status_code=401)
    return Response(status_code=204)


@app.get("/api/v1/bootstrap")
def bootstrap(request: Request) -> dict[str, Any]:
    require_auth(request)
    result = session_payload()
    result["metrics"] = provider.metrics()
    result["events"] = database.recent_events(12)
    return result


@app.post("/api/v1/session/start")
def start_session(request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    profile_id = database.get_setting("profile", "balanced")
    reconcile_session_record()
    try:
        result = provider.start(profile_id)
    except (RuntimeError, ValueError) as error:
        database.event("session.start.failed", {"reason": str(error)})
        raise HTTPException(status_code=503, detail=str(error)) from error
    if provider.session_id is None:
        provider.session_id = database.session_started(profile_id)
    database.event("session.started", {"profile": profile_id, "already_running": result["already_running"]})
    return {"session": result, "bootstrap": session_payload()}


@app.post("/api/v1/session/stop")
def stop_session(request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    provider.stop()
    database.session_stopped(provider.session_id)
    provider.session_id = None
    database.event("session.stopped", {})
    return {"session": provider.status()}


@app.post("/api/v1/profile")
def update_profile(payload: ProfileRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    if payload.profile_id not in provider.profiles:
        raise HTTPException(status_code=422, detail="Unknown performance profile.")
    was_running = provider.status()["running"]
    if not was_running:
        reconcile_session_record()
    old_session = provider.session_id
    database.set_setting("profile", payload.profile_id)
    if was_running:
        try:
            provider.restart(payload.profile_id)
        except (RuntimeError, ValueError) as error:
            database.event("profile.apply.failed", {"profile": payload.profile_id, "reason": str(error)})
            raise HTTPException(status_code=503, detail=str(error)) from error
        database.session_stopped(old_session)
        provider.session_id = database.session_started(payload.profile_id)
    database.event("profile.changed", {"profile": payload.profile_id, "restarted": was_running})
    return {"profile": provider.profiles[payload.profile_id], "session": provider.status()}


@app.post("/api/v1/input/pointer")
def input_pointer(payload: PointerRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    if payload.button not in {None, "left", "middle", "right"}:
        raise HTTPException(status_code=422, detail="Unknown pointer button.")
    try:
        return provider.pointer(payload.dx, payload.dy, payload.button, payload.scroll_y)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/v1/input/heartbeat")
def input_heartbeat(request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    return provider.heartbeat()


@app.post("/api/v1/input/state")
def input_state(payload: InputRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    try:
        return provider.set_keys(payload.keys)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error


@app.post("/api/v1/apps/launch")
def launch_app(payload: LaunchRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    try:
        result = provider.launch_app(payload.app_id)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
    database.event("app.launched", {"app": payload.app_id})
    return result


@app.get("/api/v1/metrics")
def metrics(request: Request) -> dict[str, Any]:
    require_auth(request)
    return provider.metrics()


@app.get("/api/v1/tools")
def tools(request: Request) -> dict[str, Any]:
    require_auth(request)
    return {"tools": tool_runner.tools()}


@app.post("/api/v1/tools/run")
def tools_run(payload: ToolRunRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    try:
        return tool_runner.run(payload.tool, payload.args, payload.timeout_seconds)
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=422 if isinstance(error, ValueError) else 503, detail=str(error)) from error


@app.get("/api/v1/tools/jobs/{job_id}")
def tools_job(job_id: str, request: Request) -> dict[str, Any]:
    require_auth(request)
    try:
        return tool_runner.status(job_id)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=404 if isinstance(error, FileNotFoundError) else 422, detail=str(error)) from error


@app.get("/api/v1/providers")
def providers(request: Request) -> dict[str, Any]:
    require_auth(request)
    return {"providers": [
        {"id": "openrouter", "kind": "openai-compatible", "auth": "api-key", "status": "verified-contract"},
        {"id": "gemini", "kind": "openai-compatible", "auth": "api-key", "status": "api-key-required", "browser_setup": "https://aistudio.google.com/apikey", "cookie_session": "not-used", "vision": "model-dependent", "image_generation": "endpoint-model-dependent"},
        {"id": "local-model", "kind": "openai-compatible", "auth": "optional", "status": "self-hosted"},
        {"id": "puter", "kind": "external-browser-ai", "auth": "browser-session", "status": "not-integrated", "note": "No stable server API or cookie extraction; integrate only through an explicit provider SDK/API."},
    ]}


@app.post("/api/v1/providers/preset")
def provider_preset(payload: ProviderPresetRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    presets = {
        "openrouter": "https://openrouter.ai/api/v1",
        "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
        "local-model": "http://127.0.0.1:11434/v1",
    }
    if payload.provider not in presets:
        raise HTTPException(status_code=422, detail="Unknown provider preset.")
    try:
        return ai_provider.configure(presets[payload.provider], payload.model)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error


@app.get("/api/v1/automation/recipes")
def automation_recipes(request: Request) -> dict[str, Any]:
    require_auth(request)
    return {"recipes": [
        {"id": "desktop-start", "name": "Start Linux desktop", "safe": True},
        {"id": "desktop-stop", "name": "Stop Linux desktop", "safe": True},
        {"id": "health-check", "name": "Check CloudDeck health", "safe": True},
    ]}


@app.post("/api/v1/automation/run")
def automation_run(payload: AutomationRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    if payload.recipe == "desktop-start":
        profile_id = database.get_setting("profile", "balanced")
        result = provider.start(profile_id)
        database.event("automation.recipe.run", {"recipe": payload.recipe})
        return {"recipe": payload.recipe, "result": result}
    if payload.recipe == "desktop-stop":
        result = provider.stop()
        database.event("automation.recipe.run", {"recipe": payload.recipe})
        return {"recipe": payload.recipe, "result": result}
    if payload.recipe == "health-check":
        database.event("automation.recipe.run", {"recipe": payload.recipe})
        return {"recipe": payload.recipe, "result": {"health": "ok", "desktop": provider.status()}}
    raise HTTPException(status_code=422, detail="Unknown automation recipe.")


@app.get("/api/v1/ai/status")
def ai_status(request: Request) -> dict[str, Any]:
    require_auth(request)
    return ai_provider.status()


@app.post("/api/v1/ai/configure")
def ai_configure(payload: AIConfigureRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    try:
        result = ai_provider.configure(payload.base_url, payload.model)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    database.event("ai.provider.configured", {"configured": result["configured"], "model": payload.model})
    return result


@app.post("/api/v1/ai/key")
def ai_key(payload: AIKeyRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    try:
        result = ai_provider.set_key(payload.api_key)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    database.event("ai.provider.key.updated", {})
    return result


@app.post("/api/v1/ai/review-screenshot")
def ai_review_screenshot(payload: AIScreenshotReviewRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    screenshot_dir = settings.state_dir / "screenshots"
    files = sorted(screenshot_dir.glob("desktop-*.png"), key=lambda path: path.stat().st_mtime, reverse=True) if screenshot_dir.is_dir() else []
    if not files:
        raise HTTPException(status_code=404, detail="Capture a desktop screenshot first.")
    try:
        result = ai_provider.review_screenshot(files[0], payload.prompt)
    except (RuntimeError, ValueError, httpx.HTTPError) as error:
        raise HTTPException(status_code=502 if isinstance(error, RuntimeError) else 422, detail=str(error)) from error
    database.event("ai.screenshot.reviewed", {"prompt_chars": len(payload.prompt)})
    return result


@app.post("/api/v1/ai/chat")
def ai_chat(payload: AIChatRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    try:
        result = ai_provider.chat(payload.messages, payload.max_tokens)
    except (RuntimeError, ValueError, httpx.HTTPError) as error:
        raise HTTPException(status_code=502 if isinstance(error, RuntimeError) else 422, detail=str(error)) from error
    database.event("ai.chat.completed", {"message_count": len(payload.messages)})
    return result


@app.post("/api/v1/desktop/screenshot")
def desktop_screenshot(request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    try:
        result = provider.screenshot()
    except RuntimeError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error
    database.event("desktop.screenshot.captured", {"bytes": result["bytes"]})
    return result


@app.get("/api/v1/desktop/screenshot/latest")
def desktop_screenshot_latest(request: Request) -> FileResponse:
    require_auth(request)
    screenshot_dir = settings.state_dir / "screenshots"
    files = sorted(screenshot_dir.glob("desktop-*.png"), key=lambda path: path.stat().st_mtime, reverse=True) if screenshot_dir.is_dir() else []
    if not files:
        raise HTTPException(status_code=404, detail="No desktop screenshot has been captured.")
    return FileResponse(files[0], media_type="image/png", filename=files[0].name)


@app.get("/api/v1/events")
def events(request: Request) -> list[dict[str, Any]]:
    require_auth(request)
    return database.recent_events(30)


@app.get("/api/v1/developer/files")
def developer_files(request: Request) -> dict[str, Any]:
    require_auth(request)
    return {"files": developer_workspace.list_files()}


@app.get("/api/v1/developer/files/{name}")
def developer_read(name: str, request: Request) -> dict[str, Any]:
    require_auth(request)
    try:
        return developer_workspace.read(name)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=404 if isinstance(error, FileNotFoundError) else 422, detail=str(error)) from error


@app.post("/api/v1/developer/files")
def developer_save(payload: DeveloperSaveRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    try:
        result = developer_workspace.save(payload.name, payload.code)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    database.event("developer.file.saved", {"name": payload.name, "bytes": result["bytes"]})
    return result


@app.post("/api/v1/developer/run")
def developer_run(payload: DeveloperRunRequest, request: Request) -> dict[str, Any]:
    require_auth(request, mutation=True)
    try:
        result = developer_workspace.run(payload.name, payload.timeout_seconds)
    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(status_code=404 if isinstance(error, FileNotFoundError) else 422, detail=str(error)) from error
    database.event("developer.file.run", {"name": payload.name, "exit_code": result["exit_code"]})
    return result


@app.exception_handler(Exception)
async def unhandled_error(_request: Request, _error: Exception) -> JSONResponse:
    # Never send traceback details or server paths to the client.
    return JSONResponse(status_code=500, content={"detail": "CloudDeck encountered an internal error. Check its local logs."})
