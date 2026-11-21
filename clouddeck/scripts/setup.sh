#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd -- "$SCRIPT_DIR/.." && pwd)"
STATE_DIR="${CLOUDDECK_STATE_DIR:-$HOME/.clouddeck}"
export CLOUDDECK_STATE_DIR="$STATE_DIR"
APP_DIR="$STATE_DIR/app"
APP_PORT="${CLOUDDECK_APP_PORT:-8080}"
WEB_ROOT="$STATE_DIR/webroot"
LOG_DIR="$STATE_DIR/logs"

if [[ "${CODESPACES:-}" != "true" ]]; then
  echo "This installer is intended to run inside your GitHub Codespace." >&2
  exit 1
fi
if ! command -v sudo >/dev/null 2>&1 || ! sudo -n true 2>/dev/null; then
  echo "Passwordless sudo is required to install the desktop and gateway packages." >&2
  exit 1
fi

printf '\n[1/6] Installing the desktop and network gateway...\n'
if command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    nginx xfce4 xfce4-terminal xfce4-session xfce4-panel xfdesktop4 xfwm4 xfce4-settings \
    thunar mousepad dbus-x11 xvfb x11vnc novnc websockify xdotool fonts-dejavu-core \
    curl ca-certificates python3-venv python3-pip
elif command -v apk >/dev/null 2>&1; then
  sudo apk update
  sudo apk add \
    nginx xfce4 xfce4-terminal xfce4-session xfce4-panel xfdesktop xfwm4 xfce4-settings \
    thunar mousepad dbus-x11 xvfb x11vnc novnc websockify xdotool font-dejavu \
    curl ca-certificates py3-pip py3-virtualenv python3
else
  echo "Unsupported package manager; apt-get or apk is required." >&2
  exit 1
fi

printf '\n[2/6] Installing CloudDeck application files...\n'
mkdir -p "$STATE_DIR" "$APP_DIR" "$WEB_ROOT" "$LOG_DIR" "$STATE_DIR/pids" "$STATE_DIR/nginx"
chmod 700 "$STATE_DIR" "$LOG_DIR" "$STATE_DIR/pids"
rm -rf "$APP_DIR/clouddeck" "$APP_DIR/requirements.txt"
cp -a "$PROJECT_DIR/clouddeck" "$APP_DIR/"
cp "$PROJECT_DIR/requirements.txt" "$APP_DIR/requirements.txt"

printf '\n[3/6] Creating an isolated Python environment...\n'
if command -v apk >/dev/null 2>&1; then
  python3 -m venv --system-site-packages "$STATE_DIR/.venv"
  ln -sf "$(command -v uvicorn)" "$STATE_DIR/.venv/bin/uvicorn"
else
  python3 -m venv "$STATE_DIR/.venv"
  "$STATE_DIR/.venv/bin/pip" install --disable-pip-version-check --no-warn-script-location -r "$APP_DIR/requirements.txt"
fi

printf '\n[4/6] Preparing the browser client and secure gateway...\n'
NOVNC_SOURCE=""
for candidate in /usr/share/novnc /usr/share/noVNC; do
  if [[ -f "$candidate/vnc.html" ]]; then NOVNC_SOURCE="$candidate"; break; fi
done
if [[ -z "$NOVNC_SOURCE" ]]; then
  echo "The noVNC web client was not found after package installation." >&2
  exit 1
fi
find "$WEB_ROOT" -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
cp -a "$NOVNC_SOURCE"/. "$WEB_ROOT"/
cp -a "$PROJECT_DIR/web"/. "$WEB_ROOT"/

sed \
  -e "s|__STATE_DIR__|$STATE_DIR|g" \
  -e "s|__WEB_ROOT__|$WEB_ROOT|g" \
  -e "s|__APP_PORT__|$APP_PORT|g" \
  "$PROJECT_DIR/deploy/nginx.conf.template" > "$STATE_DIR/nginx.conf"
chmod 600 "$STATE_DIR/nginx.conf"

printf '\n[5/6] Creating the CloudDeck access key...\n'
if [[ ! -s "$STATE_DIR/auth.json" ]]; then
  AUTH_TMP="$(mktemp "$STATE_DIR/.auth.XXXXXX")"
  trap 'rm -f "${AUTH_TMP:-}"' EXIT
  ACCESS_KEY="$(CLOUDDECK_AUTH_TMP="$AUTH_TMP" PYTHONPATH="$APP_DIR" python3 - <<'PY'
import base64, json, os, secrets
from clouddeck.security import hash_password
password = secrets.token_urlsafe(18)
secret = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
with open(os.environ["CLOUDDECK_AUTH_TMP"], "w", encoding="utf-8") as target:
    json.dump({"password_hash": hash_password(password), "cookie_secret": secret}, target)
print(password)
PY
)"
  install -m 600 "$AUTH_TMP" "$STATE_DIR/auth.json"
  rm -f "$AUTH_TMP"
  trap - EXIT
  printf '%s\n' "$ACCESS_KEY" > "$STATE_DIR/access-key.txt"
  chmod 600 "$STATE_DIR/access-key.txt"
else
  ACCESS_KEY="(existing access key retained; see ~/.clouddeck/access-key.txt)"
fi

cp "$PROJECT_DIR/scripts/start-services.sh" "$STATE_DIR/start-services.sh"
cp "$PROJECT_DIR/scripts/stop-desktop.sh" "$STATE_DIR/stop-desktop.sh"
cp "$PROJECT_DIR/scripts/stop-all.sh" "$STATE_DIR/stop-all.sh"
cp "$PROJECT_DIR/scripts/reset-access.sh" "$STATE_DIR/reset-access.sh"
cp "$PROJECT_DIR/scripts/boot-clouddeck.sh" "$STATE_DIR/boot-clouddeck.sh"
cp "$PROJECT_DIR/scripts/workstation-preset.sh" "$STATE_DIR/workstation-preset.sh"
chmod 700 "$STATE_DIR"/*.sh

BASHRC="$HOME/.bashrc"
MARKER="# CloudDeck control-plane autostart"
if [[ -d "$(dirname "$BASHRC")" ]] && ! grep -Fq "$MARKER" "$BASHRC" 2>/dev/null; then
  cat >> "$BASHRC" <<BASHRC_BLOCK

# CloudDeck control-plane autostart (idempotent; does not start the remote desktop)
if [ "\${CODESPACES:-}" = "true" ] && [ -x "$STATE_DIR/start-services.sh" ]; then
  ( CLOUDDECK_STATE_DIR="$STATE_DIR" "$STATE_DIR/start-services.sh" --quiet >/dev/null 2>&1 & )
fi
BASHRC_BLOCK
fi

printf '\n[6/6] Starting the control plane and securing the forwarded port...\n'
if [[ -x "$STATE_DIR/stop-all.sh" ]]; then
  CLOUDDECK_STATE_DIR="$STATE_DIR" "$STATE_DIR/stop-all.sh" >/dev/null 2>&1 || true
fi
cat > "$STATE_DIR/runtime.env" <<RUNTIME_ENV
CLOUDDECK_APP_PORT=$APP_PORT
CLOUDDECK_DISPLAY=${CLOUDDECK_DISPLAY:-:1}
CLOUDDECK_DEFAULT_PROFILE=${CLOUDDECK_DEFAULT_PROFILE:-balanced}
RUNTIME_ENV
chmod 600 "$STATE_DIR/runtime.env"
export CLOUDDECK_APP_PORT="$APP_PORT"
export CLOUDDECK_PUBLIC_URL="https://${CODESPACE_NAME}-${APP_PORT}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}/"
"$STATE_DIR/start-services.sh"
if command -v gh >/dev/null 2>&1 && [[ -n "${CODESPACE_NAME:-}" ]]; then
  gh codespace ports visibility "${APP_PORT}:private" -c "$CODESPACE_NAME" >/dev/null 2>&1 || true
fi

cat <<EOF

============================================================
CLOUDDECK 0.2.0 IS INSTALLED

Open on your phone:
$CLOUDDECK_PUBLIC_URL

CloudDeck access key:
$ACCESS_KEY

Save the access key privately. It is only shown here during first setup.
The desktop starts only when you press Start session in CloudDeck.

SECURITY
- App port $APP_PORT is set to PRIVATE when GitHub CLI permissions allow it.
- Only the private app port is exposed.
- API, VNC, and WebSocket gateway bind to loopback.
- The viewer and its WebSocket require your CloudDeck login.
- Never make the app port public.

PHONE
1. Open the URL in Chrome while signed into the same GitHub account.
2. Enter the access key above.
3. Install CloudDeck from Chrome's menu -> Install app / Add to Home screen.
4. Open it from the home screen, choose a performance profile, then Start session.
============================================================
EOF
