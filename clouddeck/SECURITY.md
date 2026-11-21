# Security notes

CloudDeck is currently a single-user Codespaces deployment. It is not a hardened multi-tenant service.

## Before opening the app

- Keep the Codespaces forwarded port private.
- Use the app's generated access key; do not paste it into chat, source files, repository commits, or issue reports.
- Keep `~/.clouddeck/auth.json`, `access-key.txt`, and the `~/.clouddeck` directory private.
- Never publish raw VNC (5900), websockify (6080), or the control API (8081).

## Implemented controls

- Salted scrypt password hashes and expiring HMAC-signed sessions.
- Secure, HttpOnly, SameSite=Strict session cookies and a separate CSRF cookie.
- Same-origin enforcement for authentication and state-changing requests.
- Login throttling and strict Pydantic request contracts.
- Nginx authentication subrequests for the noVNC viewer and WebSocket handshake.
- Loopback-only API, websockify, and VNC listeners.
- Allowlisted desktop launch identifiers and keyboard input names; no arbitrary command API.
- Serialized session mutations and a renewable input lease that releases stuck keys when client heartbeats stop.

## Scope limitations

- This first release is intended for one trusted user inside one Codespace.
- The stream uses VNC and is not suitable for sensitive multi-user environments.
- The API does not implement account recovery, multi-user roles, a remote GPU-host pairing flow, or a managed secret vault.
- The forwarded-port private setting is attempted by the installer but must be verified in the GitHub Ports panel.

Report security issues privately to the project owner. Do not publish credentials, live port URLs with access details, session cookies, or screenshots containing secrets.
