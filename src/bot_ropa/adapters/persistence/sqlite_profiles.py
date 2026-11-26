"""Perfiles de estilo en SQLite (una fila por usuario)."""

from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

from ...domain.explore import StyleProfile

SCHEMA = """
CREATE TABLE IF NOT EXISTS style_profiles (
    owner_id    TEXT PRIMARY KEY,
    data        TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
"""


class SqliteProfileRepository:
    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def get(self, owner_id: str) -> StyleProfile:
        with self._lock:
            row = self._conn.execute("SELECT data FROM style_profiles WHERE owner_id = ?", (owner_id,)).fetchone()
        return StyleProfile.from_dict(json.loads(row[0])) if row else StyleProfile()

    def save(self, owner_id: str, profile: StyleProfile) -> None:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO style_profiles VALUES (?, ?, ?) "
                "ON CONFLICT(owner_id) DO UPDATE SET data = excluded.data, updated_at = excluded.updated_at",
                (owner_id, json.dumps(profile.to_dict(), ensure_ascii=False), now))
