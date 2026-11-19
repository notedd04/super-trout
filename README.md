# EchoCloud

EchoCloud is a personal Linux cloud workstation with native Android access. It uses GitHub Codespaces, XFCE, X11 VNC, noVNC, and a FastAPI control plane.

## Repository layout

- `.devcontainer/` - Codespaces desktop environment
- `scripts/provision.sh` - resumable, idempotent desktop provisioning
- `backend/` - authenticated GitHub and telemetry API
- `android/` - native Kotlin/Compose client
- `docs/` - architecture and limitations

## Codespaces

Open this repository in a Codespace. The dev container provisions XFCE and noVNC on private forwarded ports `6080` and `5901`.

Provision state is stored in `~/.echocloud/`; project and persistent data should be kept in `~/workspace-persist/` or a normal repository-backed workspace path.

## Run the API

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn app.main:app --app-dir backend --reload --port 8000
```

Open `http://localhost:8000/docs` for API documentation.

## Android

Open `android/` in Android Studio, set `echocloud.api.base_url` and `echocloud.desktop.base_url` via Gradle properties or the in-app settings, then build the debug APK.
