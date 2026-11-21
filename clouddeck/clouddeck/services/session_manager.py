from __future__ import annotations

import os
import signal
import shutil
import subprocess
from datetime import datetime, timezone
import threading
import time
import fcntl
from contextlib import contextmanager
from pathlib import Path
from typing import Any


PROFILES: dict[str, dict[str, Any]] = {
    "data_saver": {
        "id": "data_saver", "name": "Data saver", "resolution": "800x450", "depth": 16,
        "description": "Smallest stream footprint for limited mobile data.", "stream_hint": "low",
    },
    "balanced": {
        "id": "balanced", "name": "Balanced", "resolution": "1024x576", "depth": 24,
        "description": "Recommended starting point for this phone and Codespaces.", "stream_hint": "medium",
    },
    "portrait": {
        "id": "portrait", "name": "Portrait", "resolution": "576x1024", "depth": 24,
        "description": "Tall portrait display optimized for upright phone use.", "stream_hint": "medium",
    },
    "desktop": {
        "id": "desktop", "name": "Desktop", "resolution": "1280x720", "depth": 24,
        "description": "More workspace area for development and browser use.", "stream_hint": "high",
    },
}

ALLOWED_KEYS = {
    "w": "w", "a": "a", "s": "s", "d": "d",
    "up": "Up", "down": "Down", "left": "Left", "right": "Right",
    "space": "space", "shift": "Shift_L", "ctrl": "Control_L", "alt": "Alt_L",
    "enter": "Return", "escape": "Escape", "tab": "Tab",
    "e": "e", "q": "q", "r": "r", "f": "f", "c": "c",
    "1": "1", "2": "2", "3": "3", "4": "4",
}

APP_COMMANDS: dict[str, list[str]] = {
    "terminal": ["xfce4-terminal"],
    "files": ["thunar"],
    "editor": ["mousepad"],
    "browser": ["firefox"],
    "settings": ["xfce4-settings-manager"],
}


class SessionManager:
    INPUT_LEASE_SECONDS = 0.9
    WATCHDOG_INTERVAL_SECONDS = 0.2
    def __init__(self, state_dir: Path, display: str = ":1") -> None:
        self.state_dir = state_dir
        self.log_dir = state_dir / "logs"
        self.pid_dir = state_dir / "pids"
        self.display = display
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.pid_dir.mkdir(parents=True, exist_ok=True)
        self.pressed_keys: set[str] = set()
        self._last_input_at = 0.0
        self.session_id: int | None = None
        self._thread_lock = threading.RLock()
        self._watchdog_stop = threading.Event()
        self._watchdog_thread = threading.Thread(
            target=self._watchdog_loop,
            name="clouddeck-input-watchdog",
            daemon=True,
        )
        self._watchdog_thread.start()

    @contextmanager
    def _exclusive(self):
        """Serialize lifecycle/input mutations within and across API processes."""
        with self._thread_lock:
            lock_path = self.state_dir / "session.lock"
            with lock_path.open("a+") as lock_file:
                fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)

    def _watchdog_loop(self) -> None:
        while not self._watchdog_stop.wait(self.WATCHDOG_INTERVAL_SECONDS):
            self._expire_stale_keys()

    def _expire_stale_keys(self, now: float | None = None) -> bool:
        """Release emulated keys when the phone stops renewing its input lease."""
        with self._thread_lock:
            current = time.monotonic() if now is None else now
            if self.pressed_keys and current - self._last_input_at >= self.INPUT_LEASE_SECONDS:
                self._release_all_locked()
                return True
        return False

    def heartbeat(self) -> dict[str, Any]:
        with self._thread_lock:
            active = bool(self.pressed_keys)
            if active:
                self._last_input_at = time.monotonic()
            return {"ok": True, "active": active, "lease_ms": int(self.INPUT_LEASE_SECONDS * 1000)}

    def close(self) -> None:
        """Stop the watchdog for orderly tests/shutdown."""
        self._watchdog_stop.set()
        if self._watchdog_thread.is_alive():
            self._watchdog_thread.join(timeout=1.0)

    @staticmethod
    def _pid_alive(pid: int) -> bool:
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    @staticmethod
    def _process_matches(name: str, pid: int) -> bool:
        """Confirm a PID still belongs to the expected CloudDeck child process."""
        signatures = {
            "xvfb": {"Xvfb"},
            "desktop": {"dbus-run-session", "startxfce4", "xfce4-session"},
            "vnc": {"x11vnc"},
            "websockify": {"websockify"},
        }
        expected = signatures.get(name)
        if not expected:
            return False
        try:
            raw = Path(f"/proc/{pid}/cmdline").read_bytes()
            arguments = [part.decode("utf-8", errors="replace") for part in raw.split(b"\0") if part]
        except OSError:
            return False
        command_names = {Path(argument).name for argument in arguments}
        return bool(command_names & expected)

    def _read_pid(self, name: str) -> int | None:
        path = self.pid_dir / f"{name}.pid"
        try:
            pid = int(path.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            path.unlink(missing_ok=True)
            return None
        if not self._pid_alive(pid) or not self._process_matches(name, pid):
            path.unlink(missing_ok=True)
            return None
        return pid

    def _spawn(self, name: str, command: list[str], env: dict[str, str] | None = None) -> int:
        existing = self._read_pid(name)
        if existing:
            return existing
        logfile = (self.log_dir / f"{name}.log").open("ab", buffering=0)
        process = subprocess.Popen(
            command,
            stdin=subprocess.DEVNULL,
            stdout=logfile,
            stderr=subprocess.STDOUT,
            env=env or os.environ.copy(),
            start_new_session=True,
            close_fds=True,
        )
        logfile.close()
        (self.pid_dir / f"{name}.pid").write_text(str(process.pid), encoding="utf-8")
        return process.pid

    def _stop(self, name: str, timeout: float = 2.0) -> None:
        path = self.pid_dir / f"{name}.pid"
        pid = self._read_pid(name)
        if pid:
            try:
                os.killpg(pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            deadline = time.monotonic() + timeout
            while time.monotonic() < deadline and self._pid_alive(pid):
                time.sleep(0.05)
            if self._pid_alive(pid):
                try:
                    os.killpg(pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
        path.unlink(missing_ok=True)

    def status(self) -> dict[str, Any]:
        names = ["xvfb", "desktop", "vnc", "websockify"]
        processes = {name: self._read_pid(name) is not None for name in names}
        running = all(processes.values())
        return {"running": running, "processes": processes, "display": self.display if running else None}

    def start(self, profile_id: str) -> dict[str, Any]:
        with self._exclusive():
            return self._start_locked(profile_id)

    def _start_locked(self, profile_id: str) -> dict[str, Any]:
        if profile_id not in PROFILES:
            raise ValueError("Unknown performance profile.")
        current = self.status()
        if current["running"]:
            return {"running": True, "already_running": True, "profile": PROFILES[profile_id]}

        profile = PROFILES[profile_id]
        width, height = profile["resolution"].split("x", 1)
        desktop_home = self.state_dir / "desktop-home"
        xdg_config = desktop_home / ".config"
        xdg_cache = desktop_home / ".cache"
        xdg_runtime = desktop_home / ".runtime"
        for directory in (desktop_home, xdg_config, xdg_cache, xdg_runtime):
            directory.mkdir(parents=True, exist_ok=True)
        xdg_runtime.chmod(0o700)
        display_env = os.environ.copy()
        display_env.update({
            "HOME": str(desktop_home),
            "XDG_CONFIG_HOME": str(xdg_config),
            "XDG_CACHE_HOME": str(xdg_cache),
            "XDG_RUNTIME_DIR": str(xdg_runtime),
            "DISPLAY": self.display,
        })
        self._spawn("xvfb", ["Xvfb", self.display, "-screen", "0", f"{width}x{height}x{profile['depth']}", "-dpi", "96", "-ac", "+extension", "RANDR", "-nolisten", "tcp"])
        time.sleep(1.0)
        if not self._read_pid("xvfb"):
            raise RuntimeError("Virtual display failed to start. Inspect ~/.clouddeck/logs/xvfb.log.")

        if shutil.which("dbus-run-session"):
            desktop_command = ["dbus-run-session", "--", "startxfce4"]
        else:
            desktop_command = ["startxfce4"]
        self._spawn("desktop", desktop_command, display_env)
        time.sleep(1.0)
        self._spawn(
            "vnc",
            ["x11vnc", "-display", self.display, "-rfbport", "5900", "-localhost", "-forever", "-shared", "-repeat", "-noxdamage", "-wait", "35", "-defer", "35", "-nopw", "-o", str(self.log_dir / "x11vnc.log")],
            display_env,
        )
        time.sleep(0.5)
        self._spawn("websockify", ["websockify", "--heartbeat", "30", "127.0.0.1:6080", "127.0.0.1:5900"])
        time.sleep(0.5)
        if not self.status()["running"]:
            self._stop_locked()
            raise RuntimeError("One or more desktop services failed to start. Inspect ~/.clouddeck/logs/.")
        return {"running": True, "already_running": False, "profile": profile}

    def stop(self) -> dict[str, Any]:
        with self._exclusive():
            return self._stop_locked()

    def _stop_locked(self) -> dict[str, Any]:
        self._release_all_locked()
        for name in ["websockify", "vnc", "desktop", "xvfb"]:
            self._stop(name)
        return {"running": False}

    def restart(self, profile_id: str) -> dict[str, Any]:
        with self._exclusive():
            self._stop_locked()
            time.sleep(0.3)
            return self._start_locked(profile_id)

    def launch_app(self, app_id: str) -> dict[str, Any]:
        with self._exclusive():
            if app_id not in APP_COMMANDS:
                raise ValueError("That application is not in the approved launcher list.")
            if not self.status()["running"]:
                raise RuntimeError("Start the desktop before launching applications.")
            command = APP_COMMANDS[app_id]
            if not shutil.which(command[0]):
                raise RuntimeError(f"{command[0]} is not installed in this desktop image.")
            env = os.environ.copy()
            env["DISPLAY"] = self.display
            subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
            return {"launched": app_id}

    def set_keys(self, requested: list[str]) -> dict[str, Any]:
        with self._exclusive():
            normalized = {key.lower() for key in requested}
            if len(normalized) > 12 or any(key not in ALLOWED_KEYS for key in normalized):
                raise ValueError("Input contains an unsupported key.")
            if not self.status()["running"]:
                raise RuntimeError("The desktop is not running.")
            if not shutil.which("xdotool"):
                raise RuntimeError("xdotool is not installed.")
            now = time.monotonic()
            if now - self._last_input_at < 0.008:
                return {"accepted": False, "reason": "rate_limited"}
            self._last_input_at = now
            env = os.environ.copy()
            env["DISPLAY"] = self.display
            to_release = self.pressed_keys - normalized
            to_press = normalized - self.pressed_keys
            for key in sorted(to_release):
                subprocess.run(["xdotool", "keyup", ALLOWED_KEYS[key]], env=env, check=False, capture_output=True, timeout=1)
            for key in sorted(to_press):
                subprocess.run(["xdotool", "keydown", ALLOWED_KEYS[key]], env=env, check=False, capture_output=True, timeout=1)
            self.pressed_keys = normalized
            return {"accepted": True, "pressed": sorted(self.pressed_keys)}

    def _release_all_locked(self) -> None:
        if self.pressed_keys and shutil.which("xdotool"):
            env = os.environ.copy()
            env["DISPLAY"] = self.display
            for key in sorted(self.pressed_keys):
                subprocess.run(["xdotool", "keyup", ALLOWED_KEYS[key]], env=env, check=False, capture_output=True, timeout=1)
        self.pressed_keys.clear()

    def release_all(self) -> None:
        with self._exclusive():
            self._release_all_locked()

    def screenshot(self) -> dict[str, Any]:
        with self._exclusive():
            if not self.status()["running"]:
                raise RuntimeError("The desktop is not running.")
            ffmpeg = shutil.which("ffmpeg")
            if not ffmpeg:
                raise RuntimeError("ffmpeg is not installed.")
            screenshot_dir = self.state_dir / "screenshots"
            screenshot_dir.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            target = screenshot_dir / f"desktop-{timestamp}.png"
            env = os.environ.copy()
            env["DISPLAY"] = self.display
            result = subprocess.run(
                [ffmpeg, "-y", "-f", "x11grab", "-i", self.display, "-frames:v", "1", str(target)],
                env=env,
                capture_output=True,
                timeout=15,
                check=False,
            )
            if result.returncode != 0 or not target.is_file():
                raise RuntimeError("The desktop screenshot could not be captured.")
            return {"path": str(target), "bytes": target.stat().st_size, "captured_at": timestamp}

    def pointer(self, dx: int, dy: int, button: str | None = None, scroll_y: int = 0) -> dict[str, Any]:
        with self._exclusive():
            if not self.status()["running"]:
                raise RuntimeError("The desktop is not running.")
            if not shutil.which("xdotool"):
                raise RuntimeError("xdotool is not installed.")
            dx = max(-500, min(500, dx))
            dy = max(-500, min(500, dy))
            scroll_y = max(-20, min(20, scroll_y))
            env = os.environ.copy()
            env["DISPLAY"] = self.display
            if dx or dy:
                subprocess.run(["xdotool", "mousemove_relative", "--", str(dx), str(dy)], env=env, check=False, capture_output=True, timeout=1)
            if scroll_y:
                direction = "4" if scroll_y > 0 else "5"
                for _ in range(min(abs(scroll_y), 20)):
                    subprocess.run(["xdotool", "click", direction], env=env, check=False, capture_output=True, timeout=1)
            if button in {"left", "middle", "right"}:
                button_number = {"left": "1", "middle": "2", "right": "3"}[button]
                subprocess.run(["xdotool", "click", button_number], env=env, check=False, capture_output=True, timeout=1)
            return {"accepted": True}

    def metrics(self) -> dict[str, Any]:
        load = None
        memory = {"total_mb": None, "used_mb": None, "used_percent": None}
        try:
            load = float(Path("/proc/loadavg").read_text().split()[0])
        except (OSError, ValueError):
            pass
        try:
            values: dict[str, int] = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                parts = line.split()
                if len(parts) >= 2 and parts[0].rstrip(":") in {"MemTotal", "MemAvailable"}:
                    values[parts[0].rstrip(":")] = int(parts[1])
            total = values.get("MemTotal")
            available = values.get("MemAvailable")
            if total and available is not None:
                used = total - available
                memory = {"total_mb": round(total / 1024), "used_mb": round(used / 1024), "used_percent": round(used * 100 / total)}
        except (OSError, ValueError):
            pass
        return {"load_1m": load, "memory": memory}
