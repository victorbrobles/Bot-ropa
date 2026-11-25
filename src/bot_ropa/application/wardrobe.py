"""Casos de uso de "Mi armario"."""

from __future__ import annotations

import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone

from ..domain.identification import identify
from ..domain.wardrobe import (
    SOURCES, AnalyzeRequest, GarmentDetails, Identification, Photo, WardrobeItem,
)
from ..ports.wardrobe import PhotoStorage, ProductPageError, ProductPageReader, WardrobeRepository

MAX_PHOTOS = 3


class LimitExceeded(RuntimeError):
    pass


class NotFound(LookupError):
    pass


class WardrobeService:
    def __init__(self, product_reader: ProductPageReader, repo: WardrobeRepository,
                 photos: PhotoStorage, daily_link_limit: int = 60, clock=time.time):
        self._reader = product_reader
        self._repo = repo
        self._photos = photos
        self._limit = daily_link_limit
        self._clock = clock
        self._usage: dict[tuple[str, int], int] = defaultdict(int)

    async def analyze(self, owner_id: str, request: AnalyzeRequest) -> Identification:
        """Analiza la prenda sin coste. Solo leer un enlace hace una petición a otra web,
        así que esas lecturas se limitan por usuario y día para evitar abusos."""
        product, product_error = None, None
        if request.product_url:
            self._count_link_read(owner_id)
            try:
                product = await self._reader.read(request.product_url)
            except ProductPageError as exc:
                product_error = str(exc)
        return identify(request, product, product_error)

    def _count_link_read(self, owner_id: str) -> None:
        day = int(self._clock() // 86400)
        key = (owner_id, day)
        if self._usage[key] >= self._limit:
            raise LimitExceeded("Has leído muchos enlaces hoy. Completa los datos a mano o vuelve mañana.")
        self._usage[key] += 1
        for old in [k for k in self._usage if k[1] < day]:
            del self._usage[old]

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
