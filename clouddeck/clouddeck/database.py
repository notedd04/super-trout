from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class Database:
    MAX_EVENTS = 2000

    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connect() as db:
            db.execute("PRAGMA journal_mode=WAL")
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    detail TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    started_at TEXT NOT NULL,
                    stopped_at TEXT,
                    profile_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    status TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_events_created ON events(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_sessions_started ON sessions(started_at DESC);
                """
            )
            db.execute(
                "INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES(?,?,?)",
                ("profile", json.dumps("balanced"), self.now()),
            )

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def get_setting(self, key: str, default: Any = None) -> Any:
        with self.connect() as db:
            row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return json.loads(row["value"]) if row else default

    def set_setting(self, key: str, value: Any) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO settings(key,value,updated_at) VALUES(?,?,?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at",
                (key, json.dumps(value), self.now()),
            )

    def event(self, event_type: str, detail: dict[str, Any]) -> None:
        with self.connect() as db:
            db.execute(
                "INSERT INTO events(created_at,event_type,detail) VALUES(?,?,?)",
                (self.now(), event_type, json.dumps(detail, separators=(",", ":"))),
            )
            db.execute(
                "DELETE FROM events WHERE id <= (SELECT COALESCE(MAX(id), 0) - ? FROM events)",
                (self.MAX_EVENTS,),
            )

    def recent_events(self, limit: int = 20) -> list[dict[str, Any]]:
        with self.connect() as db:
            rows = db.execute(
                "SELECT created_at,event_type,detail FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ).fetchall()
        return [
            {"created_at": row["created_at"], "type": row["event_type"], "detail": json.loads(row["detail"])}
            for row in rows
        ]

    def session_started(self, profile_id: str) -> int:
        with self.connect() as db:
            cursor = db.execute(
                "INSERT INTO sessions(started_at,profile_id,provider,status) VALUES(?,?,?,?)",
                (self.now(), profile_id, "codespaces", "running"),
            )
            return int(cursor.lastrowid)

    def session_stopped(self, session_id: int | None) -> None:
        if session_id is None:
            return
        with self.connect() as db:
            db.execute(
                "UPDATE sessions SET stopped_at=?, status='stopped' WHERE id=? AND stopped_at IS NULL",
                (self.now(), session_id),
            )

    def active_session_id(self) -> int | None:
        with self.connect() as db:
            row = db.execute("SELECT id FROM sessions WHERE stopped_at IS NULL ORDER BY id DESC LIMIT 1").fetchone()
        return int(row["id"]) if row else None
