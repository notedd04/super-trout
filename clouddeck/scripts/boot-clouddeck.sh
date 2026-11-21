#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

STATE_DIR="${CLOUDDECK_STATE_DIR:-$HOME/.clouddeck}"
if [[ -f "$STATE_DIR/runtime.env" ]]; then
  set -a
  source "$STATE_DIR/runtime.env"
  set +a
fi
export CLOUDDECK_STATE_DIR="$STATE_DIR"

"$STATE_DIR/start-services.sh" --quiet

KEY_FILE="$STATE_DIR/access-key.txt"
COOKIE_JAR="$STATE_DIR/boot-cookies.txt"
APP_PORT="${CLOUDDECK_APP_PORT:-8080}"
if [[ ! -s "$KEY_FILE" ]]; then
  echo "CloudDeck access key is missing." >&2
  exit 1
fi

HOST="127.0.0.1:${APP_PORT}"
KEY="$(cat "$KEY_FILE")"
LOGIN_JSON="$(curl --fail --silent --show-error \
  -H 'Origin: http://127.0.0.1:8080' \
  -H 'Content-Type: application/json' \
  --cookie-jar "$COOKIE_JAR" \
  -d "{\"password\":\"$KEY\"}" \
  "http://$HOST/api/v1/auth/login")"
CSRF="$(awk '$6=="clouddeck_csrf"{print $7}' "$COOKIE_JAR")"

PROFILE="$(grep -E '^CLOUDDECK_DEFAULT_PROFILE=' "$STATE_DIR/runtime.env" 2>/dev/null | cut -d= -f2 || true)"
PROFILE="${PROFILE:-balanced}"
curl --fail --silent --show-error \
  -H 'Origin: http://127.0.0.1:8080' \
  -H 'Content-Type: application/json' \
  -H "X-CSRF-Token: $CSRF" \
  --cookie "$COOKIE_JAR" \
  -d "{\"profile_id\":\"$PROFILE\"}" \
  "http://$HOST/api/v1/profile" >/dev/null

curl --fail --silent --show-error \
  -H 'Origin: http://127.0.0.1:8080' \
  -H "X-CSRF-Token: $CSRF" \
  --cookie "$COOKIE_JAR" \
  -X POST \
  "http://$HOST/api/v1/session/start" >/dev/null
