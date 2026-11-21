# CloudDeck roadmap

The current archive implements the M0 foundation and the initial provider/transport contracts for a single Codespace. Physical-device acceptance and actual stream testing remain open; later milestones are proposals, not shipped functionality.

## M0 — Architecture and delivery foundation (0.2.0)

- [x] PWA-first mobile client and theme system
- [x] FastAPI control plane with typed endpoints
- [x] SQLite WAL state and event history
- [x] Authenticated one-port Nginx edge
- [x] Codespaces XFCE/Xvfb/noVNC lifecycle
- [x] Data saver / balanced / desktop profiles
- [x] Keyboard-emulated touch and physical gamepad bridge
- [x] Health, host metrics, event history, and installer
- [x] Typed `SessionProvider` and `StreamTransport` contracts with fail-closed adapter registry
- [ ] Physical OPPO Android 8.1 compatibility test
- [ ] Live Codespace install and process/port acceptance test

## M1 — Reliable desktop experience

- [x] Serialize desktop lifecycle and input mutations; verify PID identity and reconcile interrupted sessions.
- [x] Add stale-key release watchdog and renewable input lease.
- Add touch-mouse mode and structured log rotation.
- Add noVNC stream diagnostics and measured latency/bandwidth indicators.
- Validate browser storage/session cookie behaviour on Chrome for Android 8.1.
- Capture and review actual phone screenshots and memory usage.

## M2 — Selkies transport

- [x] Define and test the provider-independent transport interface.
- [ ] Implement a Selkies adapter with a pinned stable release.
- Detect browser codecs using the Selkies client instead of assuming H.264/WebCodecs support.
- Select WebSocket when WebRTC/TURN is unavailable; use WebRTC when a tested TURN path is configured.
- Integrate native/virtual gamepad support from the stream client.
- Add data saver / balanced / latency presets based on observed stream statistics.
- Do not enable by default on Codespaces until CPU and memory tests pass.

## M3 — Real cloud gaming provider integration

- [x] Add the initial provider registry and provider capability manifest; future adapters still require conformance tests.
- Add a clear separation between external services (launch-only) and providers with documented APIs.
- Evaluate regional availability, latency from Malawi, input support, free-tier constraints, and pricing before adding any provider.
- Store provider credentials only in a server-side secret store; never put them in frontend JS or logs.
- Never scrape undocumented services or bypass queues, ads, session limits, or geographical restrictions.

## M4 — GPU cloud PC host

- Add an Ubuntu/Windows GPU host adapter.
- Deploy a hardened host agent with mutual authentication, heartbeat, lease, session lifecycle, and explicit host pairing.
- Use Selkies for a browser-hosted Linux desktop or Moonlight/Sunshine for a native low-latency path where supported.
- Provision GPU drivers and encoder support; verify H.264/H.265/AV1 encode capability before allowing a performance profile.
- Add ephemeral host lifecycle, persistent disk snapshots, storage quotas, spend caps, and idle shutdown.
- Benchmark from Malawi before claiming a game is playable.

## M5 — Godot client

- Build a native Godot UI client for desktop and Android.
- Reuse the documented HTTP API/schema and provider registry.
- Integrate the selected native video/gamepad stream library through a well-defined GDExtension or platform bridge.
- Keep networking/session orchestration in Python so the client can be replaced.
- Export and test on the actual Android 8.1 OPPO before calling it supported.

## M6 — Desktop Python companion

- Add a desktop companion with system tray, host diagnostics, host pairing, and stream-server service management.
- Support LAN PCs first, followed by remote relay/hosted GPU providers.
- Use an explicit host identity and rotating credentials; no permanent public VNC ports.

## Release gates

A milestone is not complete until its acceptance tests pass. A GitHub API response or process start alone is not considered a usable session. For streaming, acceptance requires actual browser connection, measured frame delivery, controller input, audio where applicable, reconnect, and a real game/application test on the target phone.
