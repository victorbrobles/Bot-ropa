"""Fotos de las prendas en disco local.

En producción conviene un almacenamiento de objetos (S3, R2...) con el
mismo puerto.
"""

from __future__ import annotations

import re
from pathlib import Path

EXTENSIONS = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
MEDIA_TYPES = {v: k for k, v in EXTENSIONS.items()}
_SAFE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


class LocalPhotoStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, owner_id: str, item_id: str, index: int, data: bytes, media_type: str) -> str:
        if not (_SAFE.match(owner_id) and _SAFE.match(item_id)):
            raise ValueError("Identificador no válido")
        ext = EXTENSIONS[media_type]
        rel = f"{owner_id}/{item_id}_{index}.{ext}"
        path = self._resolve(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return rel

    def load(self, rel: str) -> tuple[bytes, str]:
        path = self._resolve(rel)
        return path.read_bytes(), MEDIA_TYPES[path.suffix.lstrip(".")]

    def delete(self, paths: list[str]) -> None:
        for rel in paths:
            try:
                self._resolve(rel).unlink(missing_ok=True)
            except ValueError:
                continue

    def _resolve(self, rel: str) -> Path:
        path = (self.root / rel).resolve()
        if self.root not in path.parents:
            raise ValueError("Ruta fuera del almacenamiento")
        return path
