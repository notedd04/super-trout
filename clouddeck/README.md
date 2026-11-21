# CloudDeck 0.2.0 — Personal Cloud Console

CloudDeck is a mobile-first control console for a remote Linux desktop and external cloud-gaming services. The first deployment target is the user's existing GitHub Codespace. The codebase separates the mobile client, control API, session lifecycle, and stream gateway so that a dedicated GPU host and a higher-performance streaming transport can be added without replacing the phone app.

> **Honest capability boundary:** the Codespaces edition is a CPU-oriented Linux desktop. It is useful for coding, browser-based tools, lightweight Linux applications, and experiments. It is not a GPU gaming PC and is not expected to run demanding 3D games at playable frame rates. For games like those offered by CloudMoon, CloudDeck links to the external game-streaming service that owns the GPU servers. For arbitrary PC games, a separate GPU host is required.

## What is implemented in this milestone

- Installable PWA with a dark/light theme, mobile navigation, responsive dashboard, home-screen manifest, and offline-cached application shell.
- Python/FastAPI control plane with password authentication, signed 12-hour session cookies, CSRF validation, login throttling, and safe API errors.
- Typed `SessionProvider` / `StreamTransport` contracts and a fail-closed adapter registry, with the current Codespaces and noVNC adapters.
- SQLite persistence with WAL for preferences, session records, and an auditable activity log.
- On-demand XFCE desktop using Xvfb, x11vnc, and websockify.
- Single private forwarded port: Nginx serves the PWA and noVNC client, reverse-proxies the API, and gates both the viewer page and WebSocket stream using the authenticated app session.
- Loopback-only backend, VNC, and WebSocket gateway. Only the Nginx app port is forwarded.
- Three display profiles: Data saver (800×450), Balanced (1024×576), and Desktop (1280×720).
- Touch gamepad-to-keyboard bridge and physical Gamepad API mapping for basic keyboard-driven games. This is not native XInput/SDL gamepad passthrough.
- Fixed, allowlisted desktop launch actions (terminal, file manager, text editor). No arbitrary shell endpoint.
- CloudMoon external launch entry. CloudMoon owns its catalogue, accounts, sessions, queues, geographic availability, and play limits.
- Start/stop controls, basic host metrics, session history, and reconnect-friendly UI state.

## Install in your existing Codespace

1. Open your Codespace in the browser: `https://super-trout-jrgv6gxg56gxcpg67.github.dev/`.
2. Download `clouddeck-0.2.0-codespaces.zip` from this handoff and upload it into the Codespace workspace using the Explorer's **Upload Files** action.
3. In the Codespace terminal, run:

   ```bash
   unzip -o clouddeck-0.2.0-codespaces.zip -d clouddeck
   bash clouddeck/scripts/setup.sh
   ```

4. The installer installs desktop packages and Python dependencies, creates the app access key, attempts to set the configured app port (default `8080`) to **Private**, and starts the control plane. The Linux desktop itself remains stopped until you press **Start session** in the app.
5. Open the printed phone URL in Chrome, sign in using the generated access key, then use Chrome's menu → **Install app** / **Add to Home screen**.
6. Open CloudDeck from the home screen. Select **Balanced** to start, then press **Start session** and **Open desktop**.

The address for the supplied Codespace is expected to be:

`https://super-trout-jrgv6gxg56gxcpg67-8080.app.github.dev/`

GitHub generates forwarded-port addresses from the Codespace name and port. The installer prints the authoritative URL from the environment; use that value if it differs.

## Security model

- Keep the configured forwarded app port (default `8080`) **Private**. The installer attempts to enforce this through `gh codespace ports visibility`; verify the Ports tab after setup. Never make the port Public.
- Only Nginx on the configured app port (default `8080`) binds to the Codespace network interface.
- FastAPI (`8081`), websockify (`6080`), and raw VNC (`5900`) bind to loopback only.
- Nginx requires a valid CloudDeck session cookie before serving `/vnc.html` or forwarding `/websockify`.
- The app password is scrypt-hashed at rest. The session cookie is HMAC-signed, `HttpOnly`, `Secure`, and `SameSite=Strict`; mutating requests require a double-submit CSRF token and same-origin validation.
- Login attempts are throttled. API schemas constrain profile IDs, application IDs, and injected key names.
- There is no arbitrary command-execution API and no public VNC endpoint.
- The access key is printed once at setup and stored locally with restrictive permissions at `~/.clouddeck/access-key.txt`. Keep it private.

## Recovery and lifecycle

- **Restart control plane:** open a new Codespace terminal; the `.bashrc` hook starts the API and Nginx idempotently. Or run `~/.clouddeck/start-services.sh`.
- **Stop only the desktop:** use the app's Stop desktop action or run `~/.clouddeck/stop-desktop.sh`.
- **Stop all CloudDeck processes:** run `~/.clouddeck/stop-all.sh`.
- **Reset access key:** run `~/.clouddeck/reset-access.sh` in the Codespace terminal. This stops the desktop, reloads the API with a newly generated key, invalidates existing browser sessions, and prints the new key.
- **Rebuild the Codespace container:** rerun the package's `bash clouddeck/scripts/setup.sh`; the project files and container packages may not survive a rebuild.
- A Codespace stop/start ends the running desktop and server processes. Opening a new terminal triggers the idempotent service startup hook. The control plane is not an always-on service outside the Codespace lifecycle.

## Performance profiles

| Profile | Virtual display | Use |
|---|---:|---|
| Data saver | 800×450, 16-bit | Limited mobile data or slower connections |
| Balanced | 1024×576, 24-bit | Recommended first test |
| Desktop | 1280×720, 24-bit | Coding and desktop work where bandwidth permits |

These profiles change display resolution and colour depth. They do not change the Codespace's CPU count or add GPU acceleration. The app's resource panel reports host memory usage and one-minute load average; load average is not a CPU percentage.

## Controls

- The noVNC viewer supports touch gestures, its on-screen keyboard, scaling, and clipboard actions.
- CloudDeck's additional touch controls map directional inputs to WASD and the A/B/X/Y-style buttons to Space, Shift, E, and Q.
- A connected controller is sampled through the browser Gamepad API and mapped to the same keyboard keys.
- This input bridge is intentionally limited to keyboard-emulated controls. Games that require analog triggers, native XInput, SDL, raw joystick events, or mouse-aim fidelity need the later native gamepad adapter and a compatible GPU streaming host.
- **Release all** sends key-up events. A server-side 900 ms input lease is renewed while controls are held; if the browser closes or the connection disappears, the watchdog releases held keys automatically.

## Troubleshooting

- **The app URL does not open:** confirm the Codespace is running, open a new terminal, run `~/.clouddeck/start-services.sh`, and verify port `8080` is Private and forwarded.
- **The app loads but desktop start fails:** inspect `~/.clouddeck/logs/xvfb.log`, `desktop.log`, `x11vnc.log`, and `websockify.log`.
- **The viewer asks to connect but stays blank:** make sure the desktop session is running, then refresh the viewer. Check the Codespace Ports tab; only port 8080 should be exposed.
- **The browser cannot install the app:** open the URL directly in Chrome and use its menu → Add to Home screen. Browser install support depends on its version and policy.
- **Touch controls do not work:** tap the controls in CloudDeck's viewer and verify that the desktop is focused. Some games do not support keyboard input.
- **A game runs slowly:** this is a host capability limit, not a phone setting. Lower the resolution or use a dedicated game-streaming provider. The Codespaces desktop has no provisioned gaming GPU in this configuration.
- **Access key lost:** use `~/.clouddeck/reset-access.sh` from a Codespace terminal.

## Project structure

```text
CloudDeck/
├── clouddeck/
│   ├── backend/          # FastAPI control-plane routes and API contracts
│   ├── services/         # Desktop lifecycle and constrained input bridge
│   ├── providers/        # Codespaces session provider adapter
│   ├── transports/       # noVNC browser transport adapter
│   ├── contracts.py      # Provider and transport protocols
│   ├── registry.py       # Explicit adapter registration
│   ├── database.py       # SQLite WAL persistence and event history
│   ├── security.py       # Password hash, signed sessions and CSRF checks
│   └── settings.py       # Environment-derived runtime configuration
├── web/
│   ├── assets/           # Mobile UI and client logic
│   ├── icons/            # PWA icons
│   ├── index.html
│   ├── manifest.webmanifest
│   └── sw.js             # App-shell-only cache; never caches API/stream data
├── deploy/               # Nginx reverse-proxy/auth-gate template
├── scripts/              # Codespaces installation and lifecycle scripts
├── docs/                 # Architecture, decisions, security and roadmap
└── tests/                # Unit and API integration checks
```

## Current release boundary

CloudDeck 0.2.0 is a Codespaces-oriented control panel and remote Linux desktop. The archive is not pre-installed in the user's Codespace, a real session has not been started, and the physical OPPO has not been tested in this environment. Those are deployment/device acceptance steps, not completed claims. A real GPU PC provider, native gamepad streaming, and the Godot desktop client remain later milestones.
