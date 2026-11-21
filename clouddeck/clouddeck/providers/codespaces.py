"""GitHub Codespaces Linux desktop provider.

This adapter intentionally owns no GitHub provisioning credentials. The user
already has a running Codespace; this provider manages the Linux desktop inside it.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from clouddeck.services.session_manager import PROFILES, SessionManager


class CodespacesProvider:
    provider_id = "codespaces"
    profiles = PROFILES

    def __init__(self, state_dir: Path, display: str = ":1") -> None:
        self.manager = SessionManager(state_dir, display=display)
        self.manager.session_id = None

    @property
    def session_id(self) -> int | None:
        return self.manager.session_id

    @session_id.setter
    def session_id(self, value: int | None) -> None:
        self.manager.session_id = value

    def status(self) -> dict[str, Any]:
        return self.manager.status()

    def start(self, profile_id: str) -> dict[str, Any]:
        return self.manager.start(profile_id)

    def stop(self) -> dict[str, Any]:
        return self.manager.stop()

    def restart(self, profile_id: str) -> dict[str, Any]:
        return self.manager.restart(profile_id)

    def launch_app(self, app_id: str) -> dict[str, Any]:
        return self.manager.launch_app(app_id)

    def set_keys(self, requested: list[str]) -> dict[str, Any]:
        return self.manager.set_keys(requested)

    def heartbeat(self) -> dict[str, Any]:
        return self.manager.heartbeat()

    def screenshot(self) -> dict[str, Any]:
        return self.manager.screenshot()

    def pointer(self, dx: int, dy: int, button: str | None = None, scroll_y: int = 0) -> dict[str, Any]:
        return self.manager.pointer(dx, dy, button=button, scroll_y=scroll_y)

    def release_all(self) -> None:
        self.manager.release_all()

    def metrics(self) -> dict[str, Any]:
        return self.manager.metrics()

    def capabilities(self) -> dict[str, bool]:
        return {
            "desktop_stream": True,
            "touch_keyboard": True,
            "virtual_gamepad_keyboard_bridge": True,
            "physical_gamepad_keyboard_bridge": True,
            "native_gamepad_passthrough": False,
            "gpu_acceleration": False,
        }
