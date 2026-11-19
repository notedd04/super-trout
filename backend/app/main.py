import os
import shutil
import secrets
import time
from pathlib import Path
from typing import Any

import httpx
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

GITHUB_API = "https://api.github.com"
STARTED = time.time()
app = FastAPI(title="EchoCloud API", version="0.1.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:*", "https://*.github.dev", "https://*.app.github.dev"], allow_methods=["*"], allow_headers=["*"])


def github_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}", "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28"}


def require_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Bearer GitHub token required")
    token = authorization.removeprefix("Bearer ").strip()
    if not token:
        raise HTTPException(401, "Bearer GitHub token required")
    return token


@app.get("/health")
async def health() -> dict[str, Any]:
    return {"status": "ok", "service": "echocloud", "uptime_seconds": int(time.time() - STARTED)}


@app.get("/api/v1/repos")
async def repos(token: str = Depends(require_token)):
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{GITHUB_API}/user/repos", headers=github_headers(token), params={"sort": "updated", "per_page": 50})
        response.raise_for_status()
        return [{"id": x["id"], "name": x["name"], "full_name": x["full_name"], "private": x["private"]} for x in response.json()]


@app.get("/api/v1/codespaces")
async def codespaces(token: str = Depends(require_token)):
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{GITHUB_API}/user/codespaces", headers=github_headers(token))
        response.raise_for_status()
        return response.json()


@app.post("/api/v1/codespaces")
async def create_codespace(payload: dict[str, Any], token: str = Depends(require_token)):
    body = {k: payload[k] for k in ("repository_id", "ref", "location", "machine") if k in payload and payload[k]}
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{GITHUB_API}/user/codespaces", headers=github_headers(token), json=body)
        if response.status_code >= 400:
            raise HTTPException(response.status_code, response.text)
        return response.json()


@app.post("/api/v1/codespaces/{codespace_name}/{action}")
async def codespace_action(codespace_name: str, action: str, token: str = Depends(require_token)):
    if action not in {"start", "stop"}:
        raise HTTPException(404, "Unknown action")
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(f"{GITHUB_API}/user/codespaces/{codespace_name}/{action}", headers=github_headers(token))
        if response.status_code >= 400:
            raise HTTPException(response.status_code, response.text)
        return response.json()


@app.get("/api/v1/telemetry")
async def telemetry():
    import psutil
    return {
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory": {"total": psutil.virtual_memory().total, "used": psutil.virtual_memory().used, "percent": psutil.virtual_memory().percent},
        "disk": {"total": psutil.disk_usage("/").total, "used": psutil.disk_usage("/").used, "percent": psutil.disk_usage("/").percent},
        "uptime_seconds": int(time.time() - psutil.boot_time()),
    }


@app.get("/api/v1/files")
async def list_files(path: str = "/workspaces"):
    root = Path("/workspaces").resolve()
    target = (root / path.lstrip("/" )).resolve()
    if root not in target.parents and target != root:
        raise HTTPException(403, "Outside workspace")
    if not target.exists() or not target.is_dir():
        raise HTTPException(404, "Directory not found")
    entries = []
    for item in sorted(target.iterdir(), key=lambda p: p.name.lower())[:500]:
        entries.append({"name": item.name, "path": str(item), "directory": item.is_dir(), "size": item.stat().st_size if item.is_file() else 0})
    return {"path": str(target), "entries": entries}
