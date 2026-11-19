# EchoCloud Architecture

## Decision

GitHub Codespaces is the initial compute provider. It supplies a Linux container, persistent repositories, machine selection, private ports, and lifecycle management. EchoCloud uses a private noVNC WebSocket endpoint for the desktop rather than a public or fake desktop renderer.

XFCE runs over X11 with Xvfb and x11vnc. noVNC/websockify forwards the VNC stream to the browser. This is not GPU acceleration and should not be marketed as a gaming GPU service.

## Components

1. Android Compose client stores GitHub credentials in EncryptedSharedPreferences.
2. FastAPI backend proxies GitHub APIs and reads real host telemetry.
3. Codespaces dev container installs XFCE, noVNC, x11vnc and development tools.
4. noVNC runs in an Android WebView as the remote desktop transport.

## Security boundaries

- GitHub bearer tokens stay out of noVNC JavaScript and desktop endpoints.
- Codespaces private ports require GitHub authentication according to repository/organization policy.
- The backend is restricted to workspace paths for file operations.
- No arbitrary shell command endpoint is implemented.
- Android settings and OAuth values must be supplied as secrets/build properties.

## Persistence

Repository files survive a stopped Codespace according to GitHub Codespaces workspace storage. `~/workspace-persist` is for explicitly persistent untracked data. Container rebuilds, image changes, and destructive deletion can remove local state outside those areas.

## Known constraints

Codespaces availability and 32/64 GB configurations vary by account and organization. Machine options must be taken from the live GitHub API. Forwarded private-port authentication has mobile WebView and cookie implications that require live device testing.
