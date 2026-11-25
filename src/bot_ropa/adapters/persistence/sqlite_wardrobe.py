"""Repositorio del armario en SQLite (fichero local, sin servidor).

Para producción con muchos usuarios se puede cambiar por Postgres
implementando el mismo puerto.
"""

from __future__ import annotations

import json
import sqlite3
import threading
from pathlib import Path

from ...domain.wardrobe import GarmentDetails, WardrobeItem

SCHEMA = """
CREATE TABLE IF NOT EXISTS wardrobe_items (
    id          TEXT PRIMARY KEY,
    owner_id    TEXT NOT NULL,
    details     TEXT NOT NULL,
    photos      TEXT NOT NULL DEFAULT '[]',
    source      TEXT NOT NULL,
    confidence  REAL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_wardrobe_owner ON wardrobe_items(owner_id, created_at);
"""


class SqliteWardrobeRepository:
    def __init__(self, path: str | Path):
        if str(path) != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock, self._conn:
            self._conn.executescript(SCHEMA)

    def add(self, item: WardrobeItem) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "INSERT INTO wardrobe_items VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (item.id, item.owner_id, json.dumps(item.details.to_dict(), ensure_ascii=False),
                 json.dumps(item.photos), item.source, item.confidence,
                 item.created_at, item.updated_at),
            )

    def update(self, item: WardrobeItem) -> None:
        with self._lock, self._conn:
            self._conn.execute(
                "UPDATE wardrobe_items SET details = ?, photos = ?, updated_at = ? "
                "WHERE id = ? AND owner_id = ?",
                (json.dumps(item.details.to_dict(), ensure_ascii=False), json.dumps(item.photos),
                 item.updated_at, item.id, item.owner_id),
            )

    def get(self, owner_id: str, item_id: str) -> WardrobeItem | None:
        with self._lock:
            row = self._conn.execute(
                "SELECT * FROM wardrobe_items WHERE id = ? AND owner_id = ?", (item_id, owner_id)
            ).fetchone()
        return _row_to_item(row) if row else None

    def list(self, owner_id: str) -> list[WardrobeItem]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM wardrobe_items WHERE owner_id = ? ORDER BY created_at DESC", (owner_id,)
            ).fetchall()
        return [_row_to_item(r) for r in rows]

    def delete(self, owner_id: str, item_id: str) -> bool:
        with self._lock, self._conn:
            cur = self._conn.execute(
                "DELETE FROM wardrobe_items WHERE id = ? AND owner_id = ?", (item_id, owner_id))
        return cur.rowcount > 0


def _row_to_item(row: sqlite3.Row) -> WardrobeItem:
    return WardrobeItem(
        id=row["id"],
        owner_id=row["owner_id"],
        details=GarmentDetails.from_dict(json.loads(row["details"])),
        photos=json.loads(row["photos"]),
        source=row["source"],
        confidence=row["confidence"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )
