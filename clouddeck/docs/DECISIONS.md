# Architecture decision records

## ADR-001 — PWA first, Godot client later

**Decision:** Ship the first mobile client as a small installable PWA.

**Reasoning:** It can be opened through a Codespaces HTTPS port without APK export/signing, runs on older Android versions with a compatible browser, and integrates directly with HTML5 streaming clients. A later Godot client can reuse the Python API contracts rather than reimplement session management.

**Trade-off:** PWA browser APIs and embedded streaming clients vary by browser. Native controller capture, low-level video surfaces, and OS lifecycle integration are limited.

## ADR-002 — FastAPI control plane, SQLite persistence

**Decision:** Use FastAPI and SQLite WAL for the initial control plane.

**Reasoning:** Typed request schemas, simple testability, explicit API boundaries, no external database service, and low deployment overhead. SQLite is adequate for a single-user, one-host session manager and can be migrated behind a repository interface later.

**Trade-off:** This is not a multi-tenant production control plane. Provider orchestration and concurrency need a different persistence/queue strategy if multiple users or hosts are introduced.

## ADR-003 — One private forwarded port

**Decision:** Serve the PWA, API proxy, noVNC page, and authenticated WebSocket through one Nginx port.

**Reasoning:** It avoids cross-origin cookie/iframe issues and reduces manual port handling. Nginx protects the viewer and stream handshake through the FastAPI auth check.

**Trade-off:** Nginx must be running correctly for the whole interface; its loopback upstreams need health checks and diagnostics.

## ADR-004 — Codespaces is a development/desktop provider, not the gaming provider

**Decision:** Keep Codespaces for development and light desktop workloads. Treat CloudMoon as an external mobile cloud-gaming provider. Require a dedicated GPU host for arbitrary demanding PC games.

**Reasoning:** Cloud streaming needs the game to render on a remote GPU/accelerator and the stream to be encoded efficiently. A virtual display plus CPU-only VNC does not create that hardware capability.

**Trade-off:** The initial app cannot honestly offer an integrated Steam/Windows gaming session. It provides a modular route to add one later.

## ADR-005 — noVNC as the first reliable transport; Selkies next

**Decision:** Implement noVNC in 0.2.0 and select Selkies as the next performance-oriented browser streaming integration.

**Reasoning:** noVNC is easy to install from distro packages, has mobile browser touch gestures and clipboard support, and works through a single WebSocket proxy. Selkies offers video-codec-based streaming, gamepad input, WebSockets/WebRTC and a browser-native client, making it a better fit for future GPU-enabled hosts.

**Trade-off:** noVNC is not a low-latency gaming transport. The 0.2.0 gamepad feature maps to keyboard input and will not work for every game.

## ADR-006 — no arbitrary command endpoint

**Decision:** No API accepts raw shell commands from the browser.

**Reasoning:** This app manages a remote host. A web-exposed terminal endpoint would significantly widen the attack surface. The current implementation provides only fixed application launch identifiers and a constrained key-state API.

**Trade-off:** More advanced remote administration requires a separate, explicit, permission-controlled tool layer and audit policy.
