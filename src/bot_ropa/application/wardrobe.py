"""Casos de uso de "Mi armario"."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from ..domain.wardrobe import (
    SOURCES, GarmentDetails, Identification, IdentifyRequest, Photo, WardrobeItem,
)
from ..ports.wardrobe import GarmentIdentifier, PhotoStorage, WardrobeRepository

MAX_PHOTOS = 3


class LimitExceeded(RuntimeError):
    pass


class NotFound(LookupError):
    pass


class WardrobeService:
    def __init__(self, identifier: GarmentIdentifier, repo: WardrobeRepository,
                 photos: PhotoStorage, daily_identify_limit: int = 30, clock=time.time):
        self._identifier = identifier
        self._repo = repo
        self._photos = photos
        self._limit = daily_identify_limit
        self._clock = clock
        self._usage: dict[tuple[str, int], int] = defaultdict(int)

    # Identificar cuesta dinero (IA + búsquedas): limitamos por usuario y día.
    async def identify(self, owner_id: str, request: IdentifyRequest) -> Identification:
        day = int(self._clock() // 86400)
        key = (owner_id, day)
        if self._usage[key] >= self._limit:
            raise LimitExceeded("Has llegado al límite de identificaciones de hoy. "
                                "Puedes añadir la prenda rellenando los datos a mano.")
        self._usage[key] += 1
        for old in [k for k in self._usage if k[1] < day]:
            del self._usage[old]
        return await self._identifier.identify(request)

    def add(self, owner_id: str, details: GarmentDetails, photos: list[Photo],
            source: str = "foto", confidence: float | None = None) -> WardrobeItem:
        now = _now()
        item = WardrobeItem(
            id=uuid.uuid4().hex,
            owner_id=owner_id,
            details=details,
            source=source if source in SOURCES else "manual",
            confidence=confidence,
            created_at=now,
            updated_at=now,
        )
        item.photos = [self._photos.save(owner_id, item.id, i, p.data, p.media_type)
                       for i, p in enumerate(photos[:MAX_PHOTOS])]
        try:
            self._repo.add(item)
        except Exception:
            self._photos.delete(item.photos)
            raise
        return item

    def list(self, owner_id: str) -> list[WardrobeItem]:
        return self._repo.list(owner_id)

    def get(self, owner_id: str, item_id: str) -> WardrobeItem:
        item = self._repo.get(owner_id, item_id)
        if item is None:
            raise NotFound("Esa prenda no está en tu armario")
        return item

    def update(self, owner_id: str, item_id: str, details: GarmentDetails) -> WardrobeItem:
        item = self.get(owner_id, item_id)
        item.details = details
        item.updated_at = _now()
        self._repo.update(item)
        return item

    def delete(self, owner_id: str, item_id: str) -> None:
        item = self.get(owner_id, item_id)
        self._repo.delete(owner_id, item_id)
        self._photos.delete(item.photos)

    def photo(self, owner_id: str, item_id: str, index: int) -> tuple[bytes, str]:
        item = self.get(owner_id, item_id)
        if not 0 <= index < len(item.photos):
            raise NotFound("Foto no encontrada")
        return self._photos.load(item.photos[index])


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")
