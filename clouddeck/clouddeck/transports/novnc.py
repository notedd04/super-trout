"""Authenticated noVNC browser stream transport."""

from __future__ import annotations


class NoVNCTransport:
    transport_id = "novnc"

    def viewer_path(self) -> str:
        return "/vnc.html?autoconnect=true&resize=scale&path=websockify&reconnect=true"

    def capabilities(self) -> dict[str, bool]:
        return {
            "browser_stream": True,
            "websocket": True,
            "webrtc": False,
            "touch_gestures": True,
            "clipboard": True,
            "native_gamepad": False,
        }
