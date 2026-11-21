#!/usr/bin/env bash
set -Eeuo pipefail
STATE_DIR="${CLOUDDECK_STATE_DIR:-$HOME/.clouddeck}"
PID_DIR="$STATE_DIR/pids"

expected_process() {
  local name="$1" pid="$2" command_line
  [[ -r "/proc/$pid/cmdline" ]] || return 1
  command_line="$(tr '\0' ' ' < "/proc/$pid/cmdline" 2>/dev/null || true)"
  case "$name" in
    xvfb) [[ "$command_line" == *"Xvfb"* ]] ;;
    desktop) [[ "$command_line" == *"dbus-run-session"* || "$command_line" == *"startxfce4"* || "$command_line" == *"xfce4-session"* ]] ;;
    vnc) [[ "$command_line" == *"x11vnc"* ]] ;;
    websockify) [[ "$command_line" == *"websockify"* ]] ;;
    *) return 1 ;;
  esac
}

stop_one() {
  local name="$1" file="$PID_DIR/$1.pid" pid
  [[ -s "$file" ]] || return 0
  pid="$(cat "$file")"
  if [[ "$pid" =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
    if expected_process "$name" "$pid"; then
      kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
      for _ in $(seq 1 30); do
        kill -0 "$pid" 2>/dev/null || break
        sleep 0.1
      done
      if kill -0 "$pid" 2>/dev/null && expected_process "$name" "$pid"; then
        kill -KILL -- "-$pid" 2>/dev/null || kill -KILL "$pid" 2>/dev/null || true
      fi
    else
      echo "Ignoring stale $name PID file; process identity does not match."
    fi
  fi
  rm -f "$file"
}

for name in websockify vnc desktop xvfb; do stop_one "$name"; done
echo "CloudDeck desktop stopped. The control panel remains online."
