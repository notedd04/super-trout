#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

STATE_DIR="${CLOUDDECK_STATE_DIR:-$HOME/.clouddeck}"
LOG_FILE="$STATE_DIR/logs/workstation-preset.log"
mkdir -p "$STATE_DIR/logs"
exec > >(tee -a "$LOG_FILE") 2>&1

printf '[CloudDeck workstation preset]\n'
printf 'Host: %s %s\n' "$(uname -s)" "$(uname -m)"
printf 'Desktop: XFCE 4\n'

if command -v lspci >/dev/null 2>&1; then
  printf '\nGraphics hardware:\n'
  lspci | grep -Ei 'vga|3d|display' || printf 'No PCI graphics adapter detected.\n'
else
  printf '\nGPU inventory: lspci is unavailable.\n'
fi

if command -v apk >/dev/null 2>&1; then
  sudo apk add \
    firefox xfce4-terminal thunar mousepad dbus-x11 xvfb x11vnc novnc websockify xdotool \
    xrdb ffmpeg mesa vulkan-loader git curl ca-certificates python3 py3-pip
elif command -v apt-get >/dev/null 2>&1; then
  sudo apt-get update
  sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends \
    firefox xfce4 xfce4-terminal thunar mousepad dbus-x11 xvfb x11vnc novnc websockify xdotool \
    x11-xserver-utils ffmpeg mesa-utils vulkan-tools git curl ca-certificates python3 python3-pip python3-venv
else
  echo 'Unsupported package manager.' >&2
  exit 1
fi

printf '\nCapability report:\n'
for command in firefox xfce4-session xfce4-terminal thunar mousepad xvfb x11vnc websockify xdotool; do
  if command -v "$command" >/dev/null 2>&1; then printf '%-18s installed\n' "$command"; else printf '%-18s missing\n' "$command"; fi
done

if command -v glxinfo >/dev/null 2>&1; then glxinfo -B 2>/dev/null | sed -n '1,12p' || true; fi
printf '\nPreset complete. Proprietary GPU drivers are not installed automatically.\n'
