from __future__ import annotations

import json
import base64
from pathlib import Path
from typing import Any

import httpx


class AIProvider:
    def __init__(self, state_dir: Path) -> None:
        self.state_dir = state_dir
        self.config_path = state_dir / "ai.json"
        self.key_path = state_dir / "ai-api-key.txt"

    def status(self) -> dict[str, Any]:
        config = self._config()
        return {
            "configured": bool(config.get("base_url") and config.get("model") and self.key_path.is_file()),
            "base_url": config.get("base_url", "https://openrouter.ai/api/v1"),
            "model": config.get("model", ""),
        }

    def configure(self, base_url: str, model: str) -> dict[str, Any]:
        base_url = base_url.strip().rstrip("/")
        model = model.strip()
        if not base_url.startswith(("https://", "http://127.0.0.1", "http://localhost")):
            raise ValueError("Use HTTPS or a loopback local-model URL.")
        if len(model) > 200:
            raise ValueError("Model name is too long.")
        self.state_dir.mkdir(parents=True, exist_ok=True)
        self.config_path.write_text(json.dumps({"base_url": base_url, "model": model}), encoding="utf-8")
        self.config_path.chmod(0o600)
        return self.status()

    def set_key(self, api_key: str) -> dict[str, Any]:
        api_key = api_key.strip()
        if not api_key:
            raise ValueError("API key is required.")
        if len(api_key) > 4096:
            raise ValueError("API key is too long.")
        self.key_path.write_text(api_key, encoding="utf-8")
        self.key_path.chmod(0o600)
        return self.status()

    def chat(self, messages: list[dict[str, str]], max_tokens: int = 1024) -> dict[str, Any]:
        config = self._config()
        if not self.key_path.is_file():
            raise RuntimeError("Configure an AI API key first.")
        if not config.get("base_url") or not config.get("model"):
            raise RuntimeError("Configure a base URL and model first.")
        if len(messages) > 12:
            raise ValueError("A request can contain at most 12 messages.")
        normalized: list[dict[str, str]] = []
        for message in messages:
            role = message.get("role")
            content = message.get("content", "")
            if role not in {"system", "user", "assistant"}:
                raise ValueError("Message role must be system, user or assistant.")
            if len(content) > 32_000:
                raise ValueError("Message content must be 32 KB or smaller.")
            normalized.append({"role": role, "content": content})
        api_key = self.key_path.read_text(encoding="utf-8").strip()
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": config["model"], "messages": normalized, "max_tokens": max(64, min(max_tokens, 4096))},
            )
        if response.status_code >= 400:
            raise RuntimeError(f"AI provider returned HTTP {response.status_code}.")
        payload = response.json()
        try:
            choice = payload["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("AI provider returned an unexpected response.") from error
        return {"role": choice.get("role", "assistant"), "content": choice.get("content", "")}

    def review_screenshot(self, screenshot_path: Path, prompt: str, max_tokens: int = 1024) -> dict[str, Any]:
        config = self._config()
        if not self.key_path.is_file():
            raise RuntimeError("Configure an AI API key first.")
        if not config.get("base_url") or not config.get("model"):
            raise RuntimeError("Configure a base URL and model first.")
        if not screenshot_path.is_file():
            raise RuntimeError("No desktop screenshot is available.")
        if len(prompt) > 32_000:
            raise ValueError("Prompt must be 32 KB or smaller.")
        encoded = base64.b64encode(screenshot_path.read_bytes()).decode("ascii")
        api_key = self.key_path.read_text(encoding="utf-8").strip()
        payload = {
            "model": config["model"],
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{encoded}"}},
                ],
            }],
            "max_tokens": max(64, min(max_tokens, 4096)),
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json=payload,
            )
        if response.status_code >= 400:
            raise RuntimeError(f"AI provider returned HTTP {response.status_code}.")
        try:
            choice = response.json()["choices"][0]["message"]
        except (KeyError, IndexError, TypeError) as error:
            raise RuntimeError("AI provider returned an unexpected response.") from error
        return {"role": choice.get("role", "assistant"), "content": choice.get("content", "")}

    def _config(self) -> dict[str, str]:
        if not self.config_path.is_file():
            return {}
        try:
            payload = json.loads(self.config_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
        return payload if isinstance(payload, dict) else {}
