#!/usr/bin/env bash
set -Eeuo pipefail
STATE_DIR="${CLOUDDECK_STATE_DIR:-$HOME/.clouddeck}"
if [[ -f "$STATE_DIR/runtime.env" ]]; then
  set -a
  # The installer writes this file with restrictive permissions and fixed values.
  source "$STATE_DIR/runtime.env"
  set +a
fi
APP_DIR="$STATE_DIR/app"
APP_PORT="${CLOUDDECK_APP_PORT:-8080}"
PID_DIR="$STATE_DIR/pids"
LOG_DIR="$STATE_DIR/logs"
mkdir -p "$PID_DIR" "$LOG_DIR"
export CLOUDDECK_STATE_DIR="$STATE_DIR"

is_alive() {
  local name="$1" file="$PID_DIR/$1.pid" pid command_line
  [[ -s "$file" ]] || return 1
  pid="$(cat "$file")"
  [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null || { rm -f "$file"; return 1; }
  command_line="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
  if [[ "$name" == "api" && "$command_line" == *"uvicorn"* && "$command_line" == *"clouddeck.backend.main:app"* ]]; then
    return 0
  fi
  if [[ "$name" == "nginx" && "$command_line" == *"nginx"* && "$command_line" == *"$STATE_DIR/nginx.conf"* ]]; then
    return 0
  fi
  rm -f "$file"
  return 1
}

start_bg() {
  local name="$1"; shift
  if is_alive "$name"; then return 0; fi
  rm -f "$PID_DIR/$name.pid"
  setsid nohup "$@" >>"$LOG_DIR/$name.log" 2>&1 </dev/null &
  echo "$!" > "$PID_DIR/$name.pid"
}

if [[ ! -x "$STATE_DIR/.venv/bin/uvicorn" ]]; then
  echo "CloudDeck Python environment is missing. Run setup.sh again." >&2
  exit 1
fi

start_bg api bash -lc "cd '$APP_DIR' && exec '$STATE_DIR/.venv/bin/uvicorn' clouddeck.backend.main:app --host 127.0.0.1 --port 8081 --proxy-headers --forwarded-allow-ips=127.0.0.1"
sleep 1

if ! curl --silent --fail http://127.0.0.1:8081/api/v1/health >/dev/null; then
  echo "CloudDeck API failed to start. See $LOG_DIR/api.log" >&2
  exit 1
fi

if ! is_alive nginx; then
  rm -f "$PID_DIR/nginx.pid"
  nohup nginx -p "$STATE_DIR/nginx/" -c "$STATE_DIR/nginx.conf" -g 'daemon off;' >>"$LOG_DIR/nginx.log" 2>&1 </dev/null &
  echo "$!" > "$PID_DIR/nginx.pid"
fi
sleep 1
if ! curl --silent --fail "http://127.0.0.1:${APP_PORT}/api/v1/health" >/dev/null; then
  echo "CloudDeck gateway failed to start. See $LOG_DIR/nginx-error.log and $LOG_DIR/nginx.log" >&2
  exit 1
fi

if [[ "${1:-}" != "--quiet" ]]; then
  if [[ -z "${CLOUDDECK_PUBLIC_URL:-}" ]]; then
    if [[ -n "${CODESPACE_NAME:-}" ]]; then
      CLOUDDECK_PUBLIC_URL="https://${CODESPACE_NAME}-${APP_PORT}.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}/"
    else
      CLOUDDECK_PUBLIC_URL="http://127.0.0.1:${APP_PORT}/"
    fi
  fi
  echo "CloudDeck control plane is online."
  echo "Open: $CLOUDDECK_PUBLIC_URL"
fi
