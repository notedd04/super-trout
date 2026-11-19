# EchoCloud setup

## Open in Codespaces

1. Push this repository to GitHub and open it in a Codespace.
2. Wait for `.devcontainer/devcontainer.json` and `scripts/provision.sh` to finish.
3. Verify private ports 6080 and 8000 are available.
4. Open port 6080 to start noVNC in a private browser session.

## Provisioning recovery

The provisioning script is rerunnable and logs to `~/.echocloud/provision.log`. It writes component state to `~/.echocloud/manifest.json`.

## Persistence

Keep repository projects inside `/workspaces` or the normal Codespaces workspace. Keep untracked persistent files in `~/workspace-persist`.

## Stopping or deleting

Stopping is reversible. Container rebuilds or full Codespace deletion can remove disposable state outside the persistent workspace. Git commit and push project data before destructive operations.

## Android

Open `android/` in Android Studio. Set API and noVNC URLs to the private forwarded URLs for the running Codespace, then install the debug APK.
