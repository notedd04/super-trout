#!/usr/bin/env bash
set -Eeuo pipefail

VERSION="1"
STATE_DIR="${ECHOCLOUD_STATE:-$HOME/.echocloud}"
MANIFEST="$STATE_DIR/manifest.json"
LOG="$STATE_DIR/provision.log"
mkdir -p "$STATE_DIR"
exec > >(tee -a "$LOG") 2>&1

stage() { printf '{"stage":"%s","status":"running"}\n' "$1"; }
done_stage() { printf '{"stage":"%s","status":"done"}\n' "$1"; }

stage "Preparing environment"
export DEBIAN_FRONTEND=noninteractive
mkdir -p "$STATE_DIR"
done_stage "Preparing environment"

stage "Installing desktop"
if ! command -v xfce4-session >/dev/null; then sudo apt-get update && sudo apt-get install -y xfce4 xfce4-terminal dbus-x11; fi
done_stage "Installing desktop"

stage "Configuring remote access"
cat > "$STATE_DIR/start-desktop.sh" <<'EOF'
#!/usr/bin/env bash
set -e
export DISPLAY=:1
mkdir -p "$HOME/.vnc"
if ! pgrep -x Xvfb >/dev/null; then Xvfb :1 -screen 0 1920x1080x24 -nolisten tcp >/tmp/xvfb.log 2>&1 & fi
sleep 1
if ! pgrep -f 'x11vnc.*5901' >/dev/null; then x11vnc -display :1 -rfbport 5901 -localhost -forever -shared -nopw >/tmp/x11vnc.log 2>&1 & fi
if ! pgrep -f 'xfce4-session' >/dev/null; then dbus-launch --exit-with-session xfce4-session >/tmp/xfce.log 2>&1 & fi
exec websockify --web=/usr/share/novnc/ 6080 localhost:5901
EOF
chmod 0755 "$STATE_DIR/start-desktop.sh"
done_stage "Configuring remote access"

stage "Installing development tools"
command -v python3 >/dev/null
command -v git >/dev/null
command -v node >/dev/null
python3 -m pip install --user -r /workspaces/codespaces-blank/backend/requirements.txt >/dev/null 2>&1 || true
done_stage "Installing development tools"

stage "Preparing storage"
mkdir -p "$HOME/workspace-persist" /workspaces/codespaces-blank/data
ln -sfn "$HOME/workspace-persist" /workspaces/codespaces-blank/data/persistent
done_stage "Preparing storage"

stage "Testing connection"
nohup "$STATE_DIR/start-desktop.sh" >/tmp/echocloud-desktop.log 2>&1 &
sleep 3
python3 - <<'PY'
import socket
for port in (5901, 6080):
    with socket.socket() as sock:
        sock.settimeout(2)
        if sock.connect_ex(("127.0.0.1", port)) != 0:
            raise SystemExit(f"port {port} failed")
PY
done_stage "Testing connection"

python3 - <<PY
import json, os, platform
with open("$MANIFEST", "w") as handle:
    json.dump({"version": "$VERSION", "os": platform.platform(), "desktop": "XFCE", "vnc": "x11vnc", "web": "noVNC", "persistent_dir": os.path.expanduser("~/workspace-persist")}, handle, indent=2)
PY

printf '{"status":"complete","manifest":"%s"}\n' "$MANIFEST"
