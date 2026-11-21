#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
STATE_DIR="${CLOUDDECK_STATE_DIR:-$HOME/.clouddeck}"
APP_DIR="$STATE_DIR/app"
if [[ ! -x "$STATE_DIR/.venv/bin/python" ]]; then
  echo "CloudDeck Python environment is missing." >&2
  exit 1
fi
AUTH_TMP="$(mktemp "$STATE_DIR/.auth-reset.XXXXXX")"
trap 'rm -f "${AUTH_TMP:-}"' EXIT
NEW_KEY="$(CLOUDDECK_AUTH_TMP="$AUTH_TMP" PYTHONPATH="$APP_DIR" "$STATE_DIR/.venv/bin/python" - <<'PY'
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
rm -f "$AUTH_TMP" "$STATE_DIR/access-key.txt"
trap - EXIT
printf '%s\n' "$NEW_KEY" > "$STATE_DIR/access-key.txt"
chmod 600 "$STATE_DIR/access-key.txt"

# The API loads its signing secret at process startup. Restart its process so
# the new key is immediately authoritative, and stop any active desktop input.
"$STATE_DIR/stop-desktop.sh" >/dev/null 2>&1 || true
API_PID_FILE="$STATE_DIR/pids/api.pid"
if [[ -s "$API_PID_FILE" ]]; then
  API_PID="$(cat "$API_PID_FILE")"
  if [[ "$API_PID" =~ ^[0-9]+$ ]] && kill -0 "$API_PID" 2>/dev/null; then
    API_COMMAND="$(tr '\0' ' ' < "/proc/$API_PID/cmdline" 2>/dev/null || true)"
    if [[ "$API_COMMAND" == *"uvicorn"* && "$API_COMMAND" == *"clouddeck.backend.main:app"* ]]; then
      kill -TERM "$API_PID" 2>/dev/null || true
      for _ in $(seq 1 30); do
        kill -0 "$API_PID" 2>/dev/null || break
        sleep 0.1
      done
      if kill -0 "$API_PID" 2>/dev/null; then kill -KILL "$API_PID" 2>/dev/null || true; fi
    else
      echo "Ignoring stale API PID file; process identity does not match." >&2
    fi
  fi
  rm -f "$API_PID_FILE"
fi
"$STATE_DIR/start-services.sh" --quiet

echo "New CloudDeck access key: $NEW_KEY"
echo "Existing browser sessions have been invalidated. The desktop was stopped and the API reloaded."
