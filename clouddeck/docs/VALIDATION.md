# CloudDeck 0.2.0 validation record

**Scope:** source-level, backend, API-contract, static gateway, and mocked-browser UI validation. This record does not claim that the archive has been installed in the user's Codespace or OPPO handset.

## Automated checks

| Check | Result | Scope |
|---|---|---|
| `pytest -q` | **21 passed** | Authentication and CSRF, bootstrap contract, profiles, SQLite persistence with capped event history, adapter registry, process/session manager, input allowlist, renewable input lease, stale-PID identity check |
| `python -m compileall -q clouddeck tests` | **Pass** | Python syntax/bytecode compilation |
| `node --check web/assets/app.js` | **Pass** | Browser client JavaScript syntax |
| `bash -n scripts/*.sh` | **Pass** | Installer and lifecycle shell syntax |
| `nginx -t` | **Pass** | Rendered reverse-proxy configuration with a clean state directory and non-default forwarded port |

## Browser layout and interaction check

The production HTML, CSS, and JavaScript were loaded in Chromium with a mocked API response so the UI could be exercised without requiring a live Codespace. The following were checked:

- 390 × 844 mobile viewport: all five navigation destinations respond; dark/light theme changes; CloudMoon link destination is correct; no horizontal overflow.
- 1365 × 900 desktop viewport: side navigation rail remains outside the main content; no horizontal overflow.
- No browser JavaScript runtime errors during the reviewed flows.

The captures in `docs/review/` are layout evidence from this mocked API test. They are not screenshots of the user's OPPO, a running Codespace desktop, or a live video stream.

## Security and process boundaries in the tested source

- API mutation tests require both same-origin validation and the CSRF token.
- The noVNC viewer and WebSocket endpoint are gated by Nginx `auth_request`.
- The API, websockify, and VNC services bind to loopback; only the Nginx app port is forwarded.
- PID records are checked against expected process command names before they are trusted or stopped.
- The input API accepts only named keyboard controls; a renewable 900 ms lease releases held keys when the client disappears.
- Access-key reset rotates the password hash and cookie signing secret, stops the desktop, and reloads the API process.

## Not yet validated

1. Installing the archive into the user's actual Codespace and confirming that the selected machine has enough RAM/CPU for XFCE.
2. Starting XFCE, x11vnc, and websockify together on the live host and establishing a real authenticated noVNC WebSocket/VNC stream.
3. Physical OPPO Android 8.1 Chrome/WebView behaviour, PWA installation, screen orientation, touch latency, audio, and memory use.
4. Real controller support beyond the keyboard-emulated Browser Gamepad API mapping.
5. Playability of any specific game. Codespaces in this deployment has no provisioned gaming GPU; a dedicated GPU host and a tested video transport are later milestones.
6. Selkies/WebRTC or Moonlight/Sunshine integration. The transport interface is present, but those adapters are not shipped in this version.

The next acceptance milestone is a live Codespaces install followed by an authenticated stream test on the phone. A game-playability claim requires a GPU-backed host and a real game test from Malawi, including measured latency and bandwidth.
