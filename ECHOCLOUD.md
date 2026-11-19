ECHOCLOUD

Principal Engineering Mission — Build a Real Personal Cloud Computer

Project owner: Echo
Lead engineer: Luna
Project type: Personal cloud computing platform + native Android client
Priority: High
Delivery expectation: Fully implemented, tested, documented, and published source code with an installable Android APK.

---

1. THE MISSION

I want you to engineer something genuinely ambitious.

Build EchoCloud, a personal cloud computer that I can access and control from my Android phone.

This is NOT primarily a cloud gaming platform. It is NOT just a remote terminal, a website with a few buttons, or a basic Codespaces dashboard.

I want an actual remote computer.

The experience should be similar in concept to CloudMoon, a remote desktop service, or a personal virtual computer, but with its own identity, capabilities, and carefully designed interface.

I want to be able to:

- Start my cloud computer.
- Connect to its desktop from my phone.
- Use a real Linux desktop environment.
- Open applications.
- Browse files.
- Download and upload files.
- Use a terminal.
- Develop games and software.
- Run Python scripts.
- Work with Git and GitHub.
- Install compatible applications.
- Run lightweight games where technically possible.
- Host development servers.
- Monitor CPU, RAM, disk and network usage.
- Save projects and return to them later.
- Disconnect and reconnect without losing my work.

I already have access to GitHub Codespaces, including configurations around 16 GB RAM and potentially 32 GB or 64 GB RAM.

Investigate the actual available machine configurations and account allowances rather than assuming all configurations are available.

The most important requirement: make setup extremely easy.

I do not want to manually install 20 packages, configure a dozen services, copy credentials into multiple files, or repeat lengthy setup procedures every time I want to use my computer.

The intended experience:

1. Install EchoCloud APK.
2. Connect GitHub once.
3. Authorize the necessary permissions.
4. Select an available Codespaces configuration.
5. Press CREATE CLOUD PC.
6. Wait for automatic provisioning.
7. Connect to the desktop.
8. Use the computer.

After the first provisioning, subsequent sessions should be dramatically simpler:

OPEN APP → CONNECT → RESUME COMPUTER.

No unnecessary reinstallations.

---

2. ENGINEERING FREEDOM

You have permission to choose a completely different architecture from what I initially imagined.

Do NOT force the project into Godot.

I want a native Android application, and I expect you to evaluate:

- Kotlin
- Jetpack Compose
- Rust
- Go
- Python
- TypeScript
- C/C++
- WebRTC
- WebSocket
- QUIC
- Apache Guacamole
- noVNC
- TigerVNC
- X11/VNC
- Wayland-compatible solutions
- RDP
- Remote desktop streaming technologies

Research the best current implementations and compare their strengths.

Choose technologies based on reliability, performance, Android compatibility, security, maintenance and actual feasibility.

My initial preference is:

Android: Kotlin + Jetpack Compose.

Backend: Python or Go, depending on which provides the better architecture.

Cloud infrastructure: GitHub Codespaces initially, with an abstraction that could support other cloud providers in the future.

Desktop: A real Linux desktop environment such as XFCE.

However, these are starting preferences, not restrictions.

Do not select technologies simply because they are familiar.

---

3. THE CLOUD COMPUTER

This is the heart of the product.

I want a genuine remote computer with a desktop environment.

Investigate whether GitHub Codespaces can reliably support:

- XFCE
- Fluxbox
- Xfce4-terminal
- Firefox or Chromium
- File managers
- Remote desktop streaming
- noVNC
- VNC
- Linux GUI applications
- Audio where possible
- Clipboard synchronization
- File transfer
- Keyboard input
- Touch input
- Resolution changes

Do not assume that because something works in a normal Linux container it will work inside GitHub Codespaces.

Test the actual hosted environment.

If Codespaces prevents a particular feature, investigate alternatives rather than shipping something that does not work.

The desktop must be usable from a mobile device.

Implement:

- Touch-friendly interaction.
- Virtual mouse.
- Tap-to-click.
- Long-press.
- Dragging.
- Scrolling.
- Mobile keyboard integration.
- Keyboard shortcuts.
- Zoom and pan.
- Fullscreen.
- Desktop resolution adjustment.
- Connection quality indicator.
- Reconnection after temporary network interruptions.

The desktop must not be a static image or a simulated interface.

It must provide actual interaction with the remote machine.

---

4. ONE-TIME SETUP AND PROVISIONING

This is one of the highest-priority requirements.

Create a reliable provisioning system.

I want a single initial setup operation that handles everything automatically.

It should:

1. Detect the environment.
2. Check available resources.
3. Verify the operating system.
4. Install required packages.
5. Install and configure the desktop.
6. Install remote access services.
7. Install development tools.
8. Configure the API.
9. Configure authentication.
10. Configure storage directories.
11. Create startup services.
12. Verify installations.
13. Run connection tests.
14. Record installation state.
15. Report success or specific failures.

The provisioning process must be:

- Idempotent.
- Recoverable.
- Safe to rerun.
- Version-aware.
- Logged.
- Resumable after interruption.

Do not reinstall everything on every launch.

Maintain a provisioning manifest that records installed components and their versions.

Separate persistent data from disposable runtime files.

Create a clear setup screen showing actual progress, not an endlessly spinning animation.

If provisioning fails, explain what failed and offer a safe retry.

---

5. GITHUB CODESPACES INTEGRATION

Implement proper Codespaces integration.

Research the GitHub API and OAuth/device authorization options.

I want the app to be able to:

- Authenticate with GitHub.
- Display available repositories.
- Create or select a repository.
- Create a Codespace.
- Select an available machine configuration.
- Start an existing Codespace.
- Stop a Codespace.
- Inspect its state.
- Retrieve connection information.
- Handle provisioning.
- Detect stopped or deleted environments.
- Reconnect to existing environments.

Investigate Codespaces machine availability and pricing.

Do not assume 32 GB or 64 GB machines are guaranteed.

Show the user the actual options returned by GitHub.

Display relevant resource information and estimated usage costs before starting an expensive machine.

Do not expose GitHub tokens to the cloud desktop, logs, browser JavaScript, or public endpoints.

Use secure Android credential storage and an appropriately designed authentication flow.

Do not request excessively broad GitHub permissions.

---

6. THE ANDROID APPLICATION

Build a native Android application.

Kotlin + Jetpack Compose is the preferred starting point.

The app should feel like a professionally designed product, not a developer demo.

It should have its own design identity.

Suggested identity:

Name: EchoCloud

Visual direction:

- Dark graphite surfaces.
- Deep midnight backgrounds.
- Carefully controlled cyan or electric-blue accents.
- Warm neutral secondary text.
- Subtle gradients.
- Precise typography.
- Elegant spacing.
- Smooth animations.
- Functional loading states.
- Refined icons.
- Deliberate information hierarchy.

Avoid:

- Generic AI-looking dashboards.
- Excessive glassmorphism.
- Random gradients.
- Oversized empty cards.
- Excessive rounded rectangles.
- Emoji-based icons.
- Unnecessary decoration.
- Fake statistics.
- Buttons that do nothing.

I want a distinctive product with visual personality.

Create a consistent design system with:

- Color tokens.
- Typography scale.
- Spacing system.
- Component specifications.
- Iconography.
- Motion principles.
- Responsive layouts.

The UI must work on smaller Android screens.

---

7. APPLICATION SCREENS

Implement the following screens.

A. Welcome

A carefully designed introduction to EchoCloud.

Explain that it provides a personal remote computer.

Allow the user to connect their GitHub account.

B. Cloud PC dashboard

Show:

- Current machine state.
- Running/stopped status.
- CPU configuration.
- RAM.
- Storage.
- Last session.
- Current usage.
- Connection status.

Primary actions:

- START
- CONNECT
- STOP
- RESTART

Only display actions that can actually be performed.

C. Machine creation

Allow selection of available machine configurations.

Show resource specifications.

Show pricing and included usage where available.

Clearly communicate limitations before creation.

D. Provisioning

Show meaningful installation stages.

For example:

- Preparing environment.
- Installing desktop.
- Configuring remote access.
- Installing development tools.
- Preparing storage.
- Testing connection.

Show actual progress from the backend.

E. Remote desktop

This is the primary experience.

Provide a proper remote desktop viewer.

Include:

- Fullscreen.
- Keyboard.
- Mouse controls.
- Touch mode.
- Clipboard.
- Connection status.
- Reconnect.
- Resolution controls.

F. Files

Create a usable remote file manager.

Support:

- Browse directories.
- Upload.
- Download.
- Rename.
- Create folders.
- Delete with confirmation.
- File information.

Enforce workspace permissions.

G. Applications

Show installed applications.

Allow launching and managing supported applications.

Include:

- Godot.
- Python.
- Git.
- Terminal.
- Browser.
- File manager.

Detect actual availability rather than showing every application as installed.

H. System monitor

Display:

- CPU usage.
- Memory usage.
- Disk usage.
- Network throughput.
- Process information.
- Uptime.
- Temperature only if genuinely available.

Use real telemetry.

I. Settings

Include:

- GitHub account.
- Machine configuration.
- Connection settings.
- Storage settings.
- Theme.
- Privacy.
- Diagnostics.
- About.

---

8. DEVELOPMENT WORKSTATION

The cloud computer should be useful for actual software development.

Prepare a configurable development environment.

Prioritize:

- Godot Engine stable.
- Python.
- Git.
- GitHub CLI.
- Node.js.
- npm/pnpm.
- Java.
- Kotlin tooling where practical.
- Build tools.
- VS Code Server or a browser-based editor.
- Common Linux development utilities.

Do not install everything indiscriminately.

Make optional tool packs available.

For Godot, investigate:

- Editor availability.
- Headless mode.
- Project imports.
- Export templates.
- Automated testing.
- Linux builds.
- Android export requirements.

The user develops games, so the environment should make it practical to work on real Godot projects from the phone.

---

9. LIGHTWEIGHT GAMING

This is a secondary capability.

I understand Codespaces is not a dedicated gaming GPU machine.

Do not promise performance that does not exist.

However, investigate whether compatible lightweight games can run.

Test:

- 2D games.
- Simple Linux games.
- Browser games.
- Retro games.
- Lightweight 3D applications where feasible.

Measure actual performance.

Report limitations honestly.

The cloud computer must remain a general-purpose workstation rather than being redesigned around game streaming.

---

10. STORAGE AND PERSISTENCE

This is critical.

I do not want to lose my projects because a Codespace stops.

Design storage carefully.

Separate:

1. Persistent user files.
2. Project repositories.
3. Application configurations.
4. Runtime caches.
5. Temporary files.
6. Logs.

Use the persistent Codespaces workspace for user data.

Implement Git integration and automated backup options.

Provide:

- Backup.
- Restore.
- Export.
- Project synchronization.
- Storage usage monitoring.
- Recovery after container restart.

Never silently delete user data.

Do not treat a running container's filesystem as permanent storage.

Explain which data survives stopping, rebuilding, deleting or recreating a Codespace.

Implement clear warnings before destructive operations.

---

11. NETWORKING AND REMOTE ACCESS

This is a major technical risk.

Do not assume a forwarded Codespaces port can be accessed indefinitely from an Android APK.

Investigate:

- GitHub private forwarded ports.
- GitHub authentication requirements.
- Forwarded URL stability.
- Token expiry.
- HTTPS.
- WebSocket connectivity.
- WebRTC compatibility.
- NAT traversal.
- TURN.
- Connection recovery.
- Network changes on mobile.

The Android app must have a secure and reliable way to authenticate.

Do not hard-code a temporary forwarded URL.

Do not expose the remote desktop publicly without authentication.

If GitHub's private-port authentication cannot be used reliably from a native application, design an appropriate authenticated gateway or another supported solution.

Do not claim the connection works until tested from an actual Android device or emulator against an actual running Codespace.

---

12. SECURITY

Treat this as a real product.

Implement:

- Secure token storage.
- Least-privilege permissions.
- HTTPS.
- Authenticated APIs.
- Secure WebSocket connections.
- Session expiration.
- Token rotation.
- Request validation.
- Rate limiting.
- Path traversal protection.
- Process isolation where practical.
- Safe file operations.
- Audit logs.
- Secret redaction.

Never expose:

- GitHub personal access tokens.
- OAuth secrets.
- Private SSH keys.
- API credentials.
- Authentication headers.

Do not build a publicly accessible unauthenticated terminal.

Do not create arbitrary command execution endpoints.

Any remote shell must have a deliberately designed security model.

---

13. PERFORMANCE AND STABILITY

Optimize the complete experience.

Prioritize:

- Fast startup.
- Low memory consumption on Android.
- Efficient remote streaming.
- Adaptive image quality.
- Adaptive frame rates.
- Reconnection.
- Background/foreground lifecycle handling.
- Efficient network requests.
- Minimal battery consumption.
- Graceful failure handling.

Test on slower networks.

The user may access this from Malawi using mobile internet.

Design for unstable connections and variable bandwidth.

The application must not crash simply because the network temporarily disappears.

---

14. TESTING REQUIREMENTS

Do not deliver based on appearance alone.

Create automated tests.

Test:

- Authentication.
- Provisioning.
- Provisioning recovery.
- Machine creation.
- Machine startup.
- Machine shutdown.
- API responses.
- File operations.
- Storage persistence.
- Remote desktop connection.
- Reconnection.
- Token expiration.
- Error handling.
- Android navigation.
- APK installation.
- App lifecycle.
- Network interruption.

Run the application against a real Codespace.

Verify the actual remote desktop.

Verify that files survive a stop/start cycle.

Verify that the APK can connect.

Capture screenshots and logs.

Maintain a known-issues document.

Do not mark a feature complete merely because its screen exists.

A feature is complete only when its underlying functionality works.

---

15. ANDROID APK AND GITHUB RELEASE

I want a real installable APK.

Use a suitable Android build system.

Generate:

- Debug APK for testing.
- Release APK.
- Source code.
- Build instructions.
- Version information.
- Checksums.
- Release notes.

Configure a reproducible Gradle build.

Use GitHub Actions where appropriate.

Publish the source code to GitHub.

Create a proper GitHub Release containing the installable APK.

Do not commit signing passwords or private keys.

If a production signing key is needed, document secure generation and storage.

Do not claim an APK has been published until the GitHub Release actually exists and the asset can be downloaded.

---

16. DESIGN QUALITY

I want you to treat design as an engineering discipline.

Before implementation, research modern remote desktop applications, workstation interfaces and native Android products.

Study interaction patterns from professional software.

Develop a distinctive EchoCloud design language.

Create visual references and a design system.

Pay attention to:

- Information hierarchy.
- Typography.
- Spacing.
- Contrast.
- Motion.
- Touch targets.
- Navigation.
- Feedback.
- Error states.
- Loading states.
- Empty states.

The remote desktop itself should receive the most attention.

I want it to feel like controlling a real computer from a phone.

Do not spend all your time polishing a dashboard while the desktop connection is broken.

Functionality first, then visual refinement, then another full review.

---

17. IMPLEMENTATION MILESTONES

Work in this order.

MILESTONE 1 — Research and architecture

Research the latest official documentation.

Evaluate Codespaces capabilities.

Investigate desktop streaming.

Choose the most reliable architecture.

Identify platform restrictions.

Produce an architecture document and risk register.

MILESTONE 2 — Cloud infrastructure

Create the GitHub repository.

Build the Codespaces configuration.

Implement provisioning.

Install and configure the desktop.

Implement secure service startup.

Verify persistence.

MILESTONE 3 — Remote desktop

Implement the real remote desktop transport.

Test interaction from mobile.

Verify keyboard, mouse and touch.

Measure latency and stability.

MILESTONE 4 — Android application

Build the native Kotlin application.

Implement GitHub authentication.

Implement cloud machine management.

Implement desktop access.

Implement file management and monitoring.

MILESTONE 5 — Development workstation

Install and verify development tools.

Test Godot.

Test Python.

Test Git.

Test lightweight compatible applications.

MILESTONE 6 — Hardening and quality assurance

Run automated tests.

Fix defects.

Test recovery.

Test security.

Test poor network conditions.

Review the complete design.

MILESTONE 7 — Release

Publish source code.

Publish APK.

Create documentation.

Create release notes.

Provide installation instructions.

Provide a final test report.

---

18. NON-NEGOTIABLE RULES

1. Do not stop at research.
2. Do not deliver only a prototype.
3. Do not create fake desktop functionality.
4. Do not create nonfunctional buttons.
5. Do not fake telemetry.
6. Do not claim unsupported GPU capabilities.
7. Do not assume Codespaces configurations are available without checking.
8. Do not silently destroy persistent files.
9. Do not expose credentials.
10. Do not skip actual testing.
11. Do not leave placeholder screens.
12. Do not publish an APK that has not been tested.
13. Do not sacrifice stability for unnecessary features.
14. Do not ask the user to manually perform tasks that can safely be automated.
15. Do not repeatedly reinstall dependencies on every launch.
16. Do not hide limitations.
17. Do not claim completion without evidence.

If a capability is impossible within Codespaces, explain why and evaluate an alternative.

If an alternative requires additional spending, explain the costs before using it.

You have permission to use available internet research, coding environments, build systems, GitHub integrations, command-line tools, package managers and testing tools.

Use your available capabilities fully.

---

19. FINAL DELIVERABLES

The final GitHub repository must contain:

- Android application source.
- Backend source.
- Provisioning scripts.
- Codespaces configuration.
- Desktop configuration.
- API documentation.
- Security documentation.
- Architecture documentation.
- Automated tests.
- CI/CD workflows.
- Build instructions.
- Troubleshooting guide.
- Known limitations.
- Release documentation.

The GitHub Release must contain:

- Installable Android APK.
- Version number.
- Release notes.
- Checksums.

Also provide:

1. Repository URL.
2. Release URL.
3. APK download link.
4. Installation instructions.
5. One-time setup instructions.
6. Reconnection instructions.
7. Actual machine specifications tested.
8. Actual performance observations.
9. Completed test results.
10. Remaining limitations.

---

20. FINAL PRODUCT VISION

I want EchoCloud to become my personal computer in the cloud.

Something I can open on my Android phone and genuinely use.

I want to develop games, work on applications, run tools, manage files, use a desktop, and experiment with software without needing to own a powerful physical computer.

It should have the convenience of a mobile app, the capabilities of a remote Linux workstation, and the reliability of a properly engineered service.

I am not asking for a mockup.

I am asking you to build the real thing.

Think like a principal engineer. Design like a serious product team. Test like a release engineer.

Make thoughtful technical decisions, document them, and execute the entire project.

Start by researching and validating the architecture, then immediately move into implementation.

Do not return with only a plan. Deliver working software.