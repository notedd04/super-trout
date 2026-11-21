#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

VERSION="${GODOT_VERSION:-4.7.2}"
ARCH="$(uname -m)"
case "$ARCH" in
  x86_64) ASSET="Godot_v${VERSION}-stable_linux.x86_64.zip"; BINARY="Godot_v${VERSION}-stable_linux.x86_64" ;;
  *) echo "Unsupported architecture: $ARCH" >&2; exit 1 ;;
esac

STATE_DIR="${CLOUDDECK_STATE_DIR:-$HOME/.clouddeck}"
BIN_DIR="$STATE_DIR/bin"
mkdir -p "$BIN_DIR"
URL="https://github.com/godotengine/godot/releases/download/${VERSION}-stable/${ASSET}"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

curl --fail --location --silent --show-error "$URL" --output "$TMP/$ASSET"
unzip -q "$TMP/$ASSET" -d "$TMP"
install -m 755 "$TMP/$BINARY" "$BIN_DIR/godot"
"$BIN_DIR/godot" --version
ln -sf "$BIN_DIR/godot" "$STATE_DIR/bin/godot"
