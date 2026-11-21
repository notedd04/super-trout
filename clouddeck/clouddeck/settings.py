from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WEB_ROOT = ROOT / "web"


@dataclass(frozen=True)
class Settings:
    state_dir: Path
    codespace_name: str
    forwarding_domain: str
    app_port: int
    display: str
    auth_file: Path

    @classmethod
    def load(cls) -> "Settings":
        state_dir = Path(os.environ.get("CLOUDDECK_STATE_DIR", str(Path.home() / ".clouddeck"))).expanduser()
        return cls(
            state_dir=state_dir,
            codespace_name=os.environ.get("CODESPACE_NAME", "local-workspace"),
            forwarding_domain=os.environ.get("GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN", "app.github.dev"),
            app_port=int(os.environ.get("CLOUDDECK_APP_PORT", "8080")),
            display=os.environ.get("CLOUDDECK_DISPLAY", ":1"),
            auth_file=state_dir / "auth.json",
        )

    def public_url(self) -> str:
        if self.codespace_name == "local-workspace":
            return f"http://127.0.0.1:{self.app_port}/"
        return f"https://{self.codespace_name}-{self.app_port}.{self.forwarding_domain}/"

    def load_auth(self) -> dict[str, str]:
        if not self.auth_file.exists():
            raise RuntimeError("CloudDeck auth configuration is missing. Run scripts/setup.sh again.")
        payload = json.loads(self.auth_file.read_text(encoding="utf-8"))
        if not isinstance(payload.get("password_hash"), str) or not isinstance(payload.get("cookie_secret"), str):
            raise RuntimeError("CloudDeck auth configuration is invalid.")
        return payload
