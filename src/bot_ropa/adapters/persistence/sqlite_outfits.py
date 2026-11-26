"""Outfits guardados en SQLite."""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from ...domain.outfits import OutfitInfo, SavedOutfit

SCHEMA = """
CREATE TABLE IF NOT EXISTS saved_outfits (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    info        TEXT NOT NULL,
    photos      TEXT NOT NULL DEFAULT '[]',
    worn_count  INTEGER NOT NULL DEFAULT 0,
    last_worn   TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_outfits_owner ON saved_outfits(owner_id, created_at);
"""


class SqliteOutfitRepository:
    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def add(self, o: SavedOutfit) -> None:
        with self._lock, self._conn:
            self._conn.execute("INSERT INTO saved_outfits VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                               (o.id, o.owner_id, json.dumps(o.info.to_dict(), ensure_ascii=False),
                                json.dumps(o.photos), o.worn_count, o.last_worn, o.created_at, o.updated_at))

    def update(self, o: SavedOutfit) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE saved_outfits SET info = ?, photos = ?, worn_count = ?, last_worn = ?, updated_at = ? "
                "WHERE id = ? AND owner_id = ?",
                (json.dumps(o.info.to_dict(), ensure_ascii=False), json.dumps(o.photos), o.worn_count,
                 o.last_worn, o.updated_at, o.id, o.owner_id))

    def get(self, owner_id: str, outfit_id: str) -> SavedOutfit | None:
        with self._lock:
            row = self._conn.execute("SELECT * FROM saved_outfits WHERE id = ? AND owner_id = ?",
                                     (outfit_id, owner_id)).fetchone()
        return _row(row) if row else None

    def list(self, owner_id: str) -> list[SavedOutfit]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM saved_outfits WHERE owner_id = ? ORDER BY created_at DESC",
                                      (owner_id,)).fetchall()
        return [_row(r) for r in rows]

    def delete(self, owner_id: str, outfit_id: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute("DELETE FROM saved_outfits WHERE id = ? AND owner_id = ?", (outfit_id, owner_id))
        return cur.rowcount > 0


def _row(r: sqlite3.Row) -> SavedOutfit:
    return SavedOutfit(id=r["id"], owner_id=r["owner_id"], info=OutfitInfo.from_dict(json.loads(r["info"])),
                       photos=json.loads(r["photos"]), worn_count=r["worn_count"], last_worn=r["last_worn"],
                       created_at=r["created_at"], updated_at=r["updated_at"])
