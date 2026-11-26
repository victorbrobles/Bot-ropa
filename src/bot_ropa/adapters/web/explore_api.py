"""Rutas HTTP de "Explorar outfits"."""

from __future__ import annotations

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field

from ...application.explore import ExploreService
from ...domain.catalog import SLOTS
from ...domain.explore import InvalidProfile, OutfitPlan, StyleProfile
from ...domain.options import COLORS
from ...domain.style_catalog import BRANDS, ICONS, PRICE_LABELS, STYLES
from .wardrobe_api import _item, get_owner

router = APIRouter(prefix="/api/explore")


def get_service(request: Request) -> ExploreService:
    return request.app.state.explore


@router.get("/catalog")
async def catalog():
    return {
        "styles": [{"id": s.id, "label": s.label, "emoji": s.emoji, "description": s.description,
                    "palette": [COLORS[c].hex for c in s.palette]} for s in STYLES.values()],
        "brands": [_brand(b) for b in BRANDS.values()],
        "icons": [{"id": i.id, "name": i.name, "styles": list(i.styles)} for i in ICONS.values()],
        "prices": [{"id": k, "label": v} for k, v in PRICE_LABELS.items()],
    }


@router.get("/profile")
async def get_profile(owner: str = Depends(get_owner), service: ExploreService = Depends(get_service)):
    return service.profile(owner).to_dict()


@router.put("/profile")
async def put_profile(data: dict = Body(...), owner: str = Depends(get_owner),
                      service: ExploreService = Depends(get_service)):
    try:
        return service.save_profile(owner, data).to_dict()
    except InvalidProfile as exc:
        raise HTTPException(422, str(exc)) from exc


@router.get("/feed")
async def feed(month: int | None = Query(None, ge=1, le=12), owner: str = Depends(get_owner),
               service: ExploreService = Depends(get_service)):
    f = service.feed(owner, month)
    profile: StyleProfile = f["profile"]
    return {
        "profile_empty": profile.empty,
        "wardrobe_count": f["wardrobe_count"],
        "affinity": [{"id": s, "label": STYLES[s].label, "emoji": STYLES[s].emoji, "score": v}
                     for s, v in f["affinity"][:5]],
        "ideas": [{"title": i.title, "style": i.style.id, "reason": i.reason, **_plan(i.plan)} for i in f["ideas"]],
        "brands": [_pick(p) for p in f["brands"]],
        "gaps": [{"style": e.style.label, "article": e.article, "slot_label": SLOTS[_slot(e.base_type)],
                  "color": _color(e.color), "owned": _item(e.owned) if e.owned else None, "links": e.links}
                 for e in f["gaps"]],
        "news": f["news"],
    }


@router.get("/brands")
async def brands(owner: str = Depends(get_owner), service: ExploreService = Depends(get_service)):
    return {"brands": [_pick(p) for p in service.brands(owner)]}


class PieceIn(BaseModel):
    item_id: str | None = Field(None, max_length=64)
    base_type: str | None = Field(None, max_length=40)
    color: str | None = Field(None, max_length=20)


class CompleteIn(BaseModel):
    pieces: list[PieceIn] = Field(max_length=6)
    style: str | None = None
    occasion: str | None = None
    month: int | None = Field(None, ge=1, le=12)


@router.post("/complete")
async def complete(body: CompleteIn, owner: str = Depends(get_owner),
                   service: ExploreService = Depends(get_service)):
    try:
        plan = service.complete(owner, [p.model_dump() for p in body.pieces], body.style, body.occasion, body.month)
    except InvalidProfile as exc:
        raise HTTPException(422, str(exc)) from exc
    return _plan(plan)


# ------------------------------------------------------------ serialización
def _slot(base_type: str) -> str:
    from ...domain.explore import GARMENTS
    return GARMENTS[base_type].slot


def _color(cid: str | None):
    if not cid or cid not in COLORS:
        return None
    c = COLORS[cid]
    return {"id": c.id, "label": c.label, "hex": c.hex}


def _brand(b) -> dict:
    return {"id": b.id, "name": b.name, "url": b.url, "price": b.price, "price_label": PRICE_LABELS[b.price],
            "styles": [{"id": s, "label": STYLES[s].label} for s in b.styles], "sustainable": b.sustainable,
            "kind": b.kind, "slots": sorted(b.slots) if b.slots else None}


def _pick(p) -> dict:
    return {**_brand(p.brand), "score": p.score, "reasons": p.reasons}


def _plan(plan: OutfitPlan) -> dict:
    from ...domain.explore import GARMENTS
    return {
        "style": {"id": plan.style.id, "label": plan.style.label, "emoji": plan.style.emoji},
        "season": plan.season,
        "base": [{"name": b.name or GARMENTS[b.base_type].name, "base_type": b.base_type, "item_id": b.item_id,
                  "icon": GARMENTS[b.base_type].icon, "slot_label": SLOTS[GARMENTS[b.base_type].slot],
                  "color": _color(b.color),
                  "photo": f"/api/wardrobe/items/{b.item_id}/photos/0" if b.item_id and b.has_photo else None} for b in plan.base],
        "suggestions": [{
            "slot": s.slot, "slot_label": SLOTS[s.slot], "base_type": s.base_type,
            "icon": GARMENTS[s.base_type].icon, "article": s.article, "color": _color(s.color),
            "reason": s.reason, "use_owned": s.use_owned, "links": s.links,
            "owned": [_item(i) for i in s.owned],
        } for s in plan.suggestions],
        "accessories": plan.accessories,
        "palette": [c for c in (_color(c) for c in plan.palette) if c],
        "tips": plan.tips,
    }
