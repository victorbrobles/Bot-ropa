"""Mis outfits: looks completos guardados con foto y descripción.

Para elegir qué ponerte, describes el plan y buscamos entre tus outfits el
que mejor encaja (búsqueda de texto con sinónimos, ver text_search.py).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .options import COLORS, OCCASIONS
from .style_catalog import SEASONS
from .text_search import BM25, Hit
from .wardrobe import WardrobeItem

SEASON_IDS = ("primavera", "verano", "otoño", "invierno")
MAX_PHOTOS = 4
MAX_DESCRIPTION = 1000


class InvalidOutfit(ValueError):
    pass


@dataclass(frozen=True)
class OutfitInfo:
    description: str
    occasion: str | None = None
    seasons: tuple[str, ...] = ()
    item_ids: tuple[str, ...] = ()  # prendas de "Mi armario" que aparecen

    @classmethod
    def from_dict(cls, data) -> "OutfitInfo":
        if not isinstance(data, dict):
            raise InvalidOutfit("Datos no válidos")
        description = " ".join(str(data.get("description") or "").split())[:MAX_DESCRIPTION]
        if len(description) < 3:
            raise InvalidOutfit("Escribe una descripción del outfit (para qué es, cómo es…)")
        occasion = data.get("occasion") if data.get("occasion") in OCCASIONS else None
        seasons = tuple(dict.fromkeys(s for s in data.get("seasons") or [] if s in SEASON_IDS))
        item_ids = tuple(dict.fromkeys(str(i)[:64] for i in data.get("item_ids") or []))[:12]
        return cls(description, occasion, seasons, item_ids)

    def to_dict(self) -> dict:
        return {"description": self.description, "occasion": self.occasion,
                "seasons": list(self.seasons), "item_ids": list(self.item_ids)}


@dataclass
class SavedOutfit:
    id: str
    owner_id: str
    info: OutfitInfo
    photos: list[str] = field(default_factory=list)
    worn_count: int = 0
    last_worn: str | None = None  # fecha ISO
    created_at: str = ""
    updated_at: str = ""


def search_text(outfit: SavedOutfit, items: dict[str, WardrobeItem]) -> str:
    """Todo lo que describe el outfit, para el buscador."""
    info = outfit.info
    parts = [info.description, info.description]  # la descripción pesa el doble
    if info.occasion:
        parts.append(OCCASIONS[info.occasion].label)
        parts.append({"etiqueta": "boda gala elegante", "fiesta": "fiesta noche", "trabajo": "trabajo oficina",
                      "deporte": "deporte", "diario": "diario casual"}[info.occasion])
    parts += list(info.seasons)
    for item_id in info.item_ids:
        item = items.get(item_id)
        if item:
            d = item.details
            parts.append(d.name)
            parts += [COLORS[c.palette_id].label for c in d.colors]
            if d.brand:
                parts.append(d.brand)
    return " ".join(parts)


@dataclass
class Recommendation:
    outfit: SavedOutfit
    score: float
    matched: tuple[str, ...]
    reasons: list[str]


def recommend(query: str, outfits: list[SavedOutfit], items: dict[str, WardrobeItem],
              today: date) -> list[Recommendation]:
    """Outfits ordenados por lo bien que encajan con la descripción."""
    if not outfits:
        return []
    by_id = {o.id: o for o in outfits}
    hits: list[Hit] = BM25({o.id: search_text(o, items) for o in outfits}).search(query)
    season = SEASONS[today.month][0]
    query_has_season = any(s in query.lower() for s in ("verano", "invierno", "otoño", "otono", "primavera"))
    results = []
    for hit in hits:
        o = by_id[hit.doc_id]
        score = hit.score
        reasons = [f"Coincide con: {', '.join(hit.matched)}"]
        if not query_has_season and o.info.seasons:
            if season in o.info.seasons:
                score *= 1.15
                reasons.append(f"Es de {season}")
            else:
                score *= 0.85
        if o.last_worn:
            days = (today - date.fromisoformat(o.last_worn)).days
            if days <= 7:
                score *= 0.8  # te lo pusiste hace nada: mejor variar
                reasons.append("Te lo pusiste hace menos de una semana")
        results.append(Recommendation(o, round(score, 3), hit.matched, reasons))
    return sorted(results, key=lambda r: -r.score)
