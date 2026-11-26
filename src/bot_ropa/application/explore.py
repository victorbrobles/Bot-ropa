"""Casos de uso de "Explorar outfits"."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from ..domain.explore import (
    GARMENTS, BasePiece, InvalidProfile, StyleProfile, complete_outfit, discover_brands, idea_feed,
    news_links, style_affinity, wardrobe_gaps,
)
from ..domain.options import COLORS, OCCASIONS
from ..domain.style_catalog import STYLES
from ..ports.wardrobe import ProfileRepository, WardrobeRepository


class ExploreService:
    def __init__(self, profiles: ProfileRepository, wardrobe: WardrobeRepository, clock=time.time):
        self._profiles = profiles
        self._wardrobe = wardrobe
        self._clock = clock

    def _month(self, month: int | None) -> int:
        if month and 1 <= month <= 12:
            return month
        return datetime.fromtimestamp(self._clock(), timezone.utc).month

    def profile(self, owner: str) -> StyleProfile:
        return self._profiles.get(owner)

    def save_profile(self, owner: str, data: dict) -> StyleProfile:
        profile = StyleProfile.from_dict(data)
        self._profiles.save(owner, profile)
        return profile

    def feed(self, owner: str, month: int | None = None) -> dict:
        profile = self._profiles.get(owner)
        wardrobe = self._wardrobe.list(owner)
        m = self._month(month)
        discovered = discover_brands(profile, wardrobe)
        return {
            "profile": profile,
            "wardrobe_count": len(wardrobe),
            "affinity": style_affinity(profile, wardrobe),
            "month": m,
            "ideas": idea_feed(profile, wardrobe, m),
            "brands": discovered,
            "gaps": wardrobe_gaps(profile, wardrobe),
            "news": news_links(profile, discovered),
        }

    def brands(self, owner: str):
        return discover_brands(self._profiles.get(owner), self._wardrobe.list(owner), limit=60)

    def complete(self, owner: str, pieces: list[dict], style_id: str | None = None,
                 occasion: str | None = None, month: int | None = None):
        profile = self._profiles.get(owner)
        wardrobe = self._wardrobe.list(owner)
        by_id = {i.id: i for i in wardrobe}
        base: list[BasePiece] = []
        for p in pieces[:6]:
            if p.get("item_id"):
                item = by_id.get(p["item_id"])
                if item is None:
                    raise InvalidProfile("Esa prenda no está en tu armario")
                d = item.details
                base.append(BasePiece(d.base_type, d.colors[0].palette_id if d.colors else None, item.id, d.name,
                                      bool(item.photos)))
            elif p.get("base_type") in GARMENTS:
                color = p.get("color") if p.get("color") in COLORS else None
                base.append(BasePiece(p["base_type"], color))
            else:
                raise InvalidProfile("Prenda no válida")
        if not base:
            raise InvalidProfile("Elige al menos una prenda para completar el look")
        slots = [GARMENTS[b.base_type].slot for b in base]
        if len(slots) != len(set(slots)):
            raise InvalidProfile("Has elegido dos prendas para la misma parte del cuerpo")
        if style_id not in STYLES:
            style_id = style_affinity(profile, wardrobe)[0][0]
        if occasion not in OCCASIONS:
            occasion = None
        return complete_outfit(base, profile, wardrobe, STYLES[style_id], self._month(month), occasion)
