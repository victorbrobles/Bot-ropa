"""Casos de uso de "Mis outfits"."""

from __future__ import annotations

import time
import uuid
from datetime import date, datetime, timezone

from ..domain.outfits import MAX_PHOTOS, InvalidOutfit, OutfitInfo, Recommendation, SavedOutfit, recommend
from ..domain.wardrobe import Photo
from ..ports.wardrobe import OutfitRepository, PhotoStorage, WardrobeRepository
from .wardrobe import NotFound


class OutfitsService:
    def __init__(self, repo: OutfitRepository, photos: PhotoStorage, wardrobe: WardrobeRepository, clock=time.time):
        self._repo = repo
        self._photos = photos
        self._wardrobe = wardrobe
        self._clock = clock

    def _today(self) -> date:
        return datetime.fromtimestamp(self._clock(), timezone.utc).date()

    def _check_items(self, owner: str, info: OutfitInfo) -> OutfitInfo:
        owned = {i.id for i in self._wardrobe.list(owner)}
        return OutfitInfo(info.description, info.occasion, info.seasons,
                          tuple(i for i in info.item_ids if i in owned))

    def add(self, owner: str, info: OutfitInfo, photos: list[Photo]) -> SavedOutfit:
        if not photos:
            raise InvalidOutfit("Sube al menos una foto del outfit")
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        outfit = SavedOutfit(id=uuid.uuid4().hex, owner_id=owner, info=self._check_items(owner, info),
                             created_at=now, updated_at=now)
        outfit.photos = [self._photos.save(owner, outfit.id, i, p.data, p.media_type)
                         for i, p in enumerate(photos[:MAX_PHOTOS])]
        try:
            self._repo.add(outfit)
        except Exception:
            self._photos.delete(outfit.photos)
            raise
        return outfit

    def list(self, owner: str) -> list[SavedOutfit]:
        return self._repo.list(owner)

    def get(self, owner: str, outfit_id: str) -> SavedOutfit:
        outfit = self._repo.get(owner, outfit_id)
        if outfit is None:
            raise NotFound("Ese outfit no existe")
        return outfit

    def update(self, owner: str, outfit_id: str, info: OutfitInfo) -> SavedOutfit:
        outfit = self.get(owner, outfit_id)
        outfit.info = self._check_items(owner, info)
        outfit.updated_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self._repo.update(outfit)
        return outfit

    def delete(self, owner: str, outfit_id: str) -> None:
        outfit = self.get(owner, outfit_id)
        self._repo.delete(owner, outfit_id)
        self._photos.delete(outfit.photos)

    def worn(self, owner: str, outfit_id: str) -> SavedOutfit:
        outfit = self.get(owner, outfit_id)
        today = self._today().isoformat()
        if outfit.last_worn != today:  # una vez por día como mucho
            outfit.worn_count += 1
            outfit.last_worn = today
            self._repo.update(outfit)
        return outfit

    def photo(self, owner: str, outfit_id: str, index: int) -> tuple[bytes, str]:
        outfit = self.get(owner, outfit_id)
        if not 0 <= index < len(outfit.photos):
            raise NotFound("Foto no encontrada")
        return self._photos.load(outfit.photos[index])

    def search(self, owner: str, query: str) -> list[Recommendation]:
        query = " ".join(query.split())[:300]
        if len(query) < 2:
            raise InvalidOutfit("Describe para qué quieres el outfit")
        items = {i.id: i for i in self._wardrobe.list(owner)}
        return recommend(query, self._repo.list(owner), items, self._today())
