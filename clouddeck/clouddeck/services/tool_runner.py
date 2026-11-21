from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path
from typing import Any


TOOLS: dict[str, dict[str, Any]] = {
    "python": {"id": "python", "executable": "python3", "description": "Run a Python script or command."},
    "godot": {"id": "godot", "executable": "godot", "description": "Run or export a Godot project."},
    "git": {"id": "git", "executable": "git", "description": "Inspect or update a Git repository."},
    "ffmpeg": {"id": "ffmpeg", "executable": "ffmpeg", "description": "Process audio or video."},
}


class ToolRunner:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.jobs_dir = state_dir / "jobs"
        self.jobs_dir.mkdir(parents=True, exist_ok=True)

    def tools(self) -> list[dict[str, Any]]:
        result = []
        private_godot = self.state_dir / "bin" / "godot"
        for tool_id, tool in TOOLS.items():
            executable = str(private_godot) if tool_id == "godot" and private_godot.is_file() else shutil.which(tool["executable"])
            installed = executable is not None
            probe_error = None
            if tool_id == "godot" and private_godot.is_file():
                try:
                    probe = subprocess.run([str(private_godot), "--version"], capture_output=True, timeout=3, check=False)
                    installed = probe.returncode == 0
                    if not installed:
                        probe_error = "binary incompatible with this host"
                except (OSError, subprocess.TimeoutExpired):
                    installed = False
                    probe_error = "binary could not execute on this host"
            entry = {**tool, "installed": installed, "executable": executable or tool["executable"]}
            if probe_error:
                entry["probe_error"] = probe_error
            result.append(entry)
        return result

    def run(self, tool_id: str, args: list[str], timeout_seconds: float = 30.0) -> dict[str, Any]:
        if tool_id not in TOOLS:
            raise ValueError("Unknown tool ID.")
        if len(args) > 64:
            raise ValueError("Too many arguments.")
        normalized: list[str] = []
        for arg in args:
            if len(arg) > 4096:
                raise ValueError("An argument is too long.")
            if "\x00" in arg:
                raise ValueError("Null bytes are not allowed.")
            normalized.append(arg)
        private_godot = self.state_dir / "bin" / "godot"
        executable = str(private_godot) if tool_id == "godot" and private_godot.is_file() else shutil.which(TOOLS[tool_id]["executable"])
        if not executable:
            raise RuntimeError(f"Tool {tool_id} is not installed.")
        timeout_seconds = max(1.0, min(timeout_seconds, 120.0))
        job_id = uuid.uuid4().hex
        try:
            result = subprocess.run(
                [executable, *normalized],
                cwd=str(self.state_dir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
                check=False,
                env={**__import__("os").environ, "PYTHONUNBUFFERED": "1"},
            )
        except subprocess.TimeoutExpired:
            payload = {"id": job_id, "tool": tool_id, "timed_out": True, "exit_code": None, "stdout": "", "stderr": f"Execution exceeded {timeout_seconds:g} seconds."}
            self._save(job_id, payload)
            return payload
        payload = {"id": job_id, "tool": tool_id, "timed_out": False, "exit_code": result.returncode, "stdout": result.stdout[-30_000:], "stderr": result.stderr[-30_000:]}
        self._save(job_id, payload)
        return payload

    def status(self, job_id: str) -> dict[str, Any]:
        if not job_id or len(job_id) != 32:
            raise ValueError("Invalid job ID.")
        path = self.jobs_dir / f"{job_id}.json"
        if not path.is_file():
            raise FileNotFoundError("Job not found.")
        import json
        return json.loads(path.read_text(encoding="utf-8"))

    def _save(self, job_id: str, payload: dict[str, Any]) -> None:
        import json
        (self.jobs_dir / f"{job_id}.json").write_text(json.dumps(payload), encoding="utf-8")
