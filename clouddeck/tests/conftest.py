from __future__ import annotations

import base64
import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
TEST_STATE = Path(tempfile.mkdtemp(prefix="clouddeck-tests-"))
os.environ["CLOUDDECK_STATE_DIR"] = str(TEST_STATE)
os.environ["CODESPACES"] = "true"
os.environ["CODESPACE_NAME"] = "clouddeck-test"
os.environ["GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN"] = "app.github.dev"

from clouddeck.security import hash_password  # noqa: E402

TEST_PASSWORD = "clouddeck-test-access-key-2026"
(TEST_STATE / "auth.json").write_text(
    json.dumps({
        "password_hash": hash_password(TEST_PASSWORD),
        "cookie_secret": base64.urlsafe_b64encode(b"C" * 32).decode("ascii"),
    }),
    encoding="utf-8",
)


def pytest_sessionfinish(session, exitstatus):
    # The temporary state is disposable; do not touch any user files.
    import shutil
    shutil.rmtree(TEST_STATE, ignore_errors=True)
