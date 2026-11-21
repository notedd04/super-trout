#!/usr/bin/env bash
set -Eeuo pipefail
STATE_DIR="${CLOUDDECK_STATE_DIR:-$HOME/.clouddeck}"
"$STATE_DIR/stop-desktop.sh" || true
PID_DIR="$STATE_DIR/pids"

for name in nginx api; do
  file="$PID_DIR/$name.pid"
  [[ -s "$file" ]] || continue
  pid="$(cat "$file")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    command_line="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
    matches=false
    if [[ "$name" == "api" && "$command_line" == *"uvicorn"* && "$command_line" == *"clouddeck.backend.main:app"* ]]; then
      matches=true
    elif [[ "$name" == "nginx" && "$command_line" == *"nginx"* && "$command_line" == *"$STATE_DIR/nginx.conf"* ]]; then
      matches=true
    fi
    if [[ "$matches" == true ]]; then
      kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
      for _ in $(seq 1 30); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
      done
      if kill -0 "$pid" 2>/dev/null; then
        kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
      fi
    else
      echo "Ignoring stale $name PID file; process identity does not match."
    fi
  fi
  rm -f "$file"
done
echo "CloudDeck services stopped."
