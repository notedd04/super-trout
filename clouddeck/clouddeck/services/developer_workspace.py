from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path
from typing import Any


SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,99}$")


class DeveloperWorkspace:
    def __init__(self, state_dir: Path) -> None:
        self.root = state_dir / "developer" / "workspaces"
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, name: str) -> Path:
        if not SAFE_NAME.fullmatch(name) or not name.endswith(".py"):
            raise ValueError("Use a .py filename containing only letters, numbers, dots, underscores or hyphens.")
        target = (self.root / name).resolve()
        if target.parent != self.root.resolve():
            raise ValueError("The filename must stay inside the developer workspace.")
        return target

    def save(self, name: str, code: str) -> dict[str, Any]:
        if len(code) > 100_000:
            raise ValueError("Python source must be 100 KB or smaller.")
        target = self._resolve(name)
        target.write_text(code, encoding="utf-8")
        return {"name": name, "bytes": len(code.encode("utf-8"))}

    def list_files(self) -> list[dict[str, Any]]:
        return [
            {"name": path.name, "bytes": path.stat().st_size}
            for path in sorted(self.root.glob("*.py"), key=lambda item: item.name.lower())[:200]
        ]

    def read(self, name: str) -> dict[str, Any]:
        target = self._resolve(name)
        if not target.is_file():
            raise FileNotFoundError("The Python file does not exist.")
        code = target.read_text(encoding="utf-8")
        return {"name": name, "code": code}

    def run(self, name: str, timeout_seconds: float = 10.0) -> dict[str, Any]:
        target = self._resolve(name)
        if not target.is_file():
            raise FileNotFoundError("The Python file does not exist.")
        timeout_seconds = max(1.0, min(timeout_seconds, 30.0))
        try:
            result = subprocess.run(
                [sys.executable, "-B", str(target)],
                cwd=str(self.root),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"},
            )
        except subprocess.TimeoutExpired:
            return {
                "name": name,
                "timed_out": True,
                "exit_code": None,
                "stdout": "",
                "stderr": f"Execution exceeded {timeout_seconds:g} seconds.",
            }
        return {
            "name": name,
            "timed_out": False,
            "exit_code": result.returncode,
            "stdout": result.stdout[-30_000:],
            "stderr": result.stderr[-30_000:],
        }
