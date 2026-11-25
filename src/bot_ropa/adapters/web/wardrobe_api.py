"""Rutas HTTP de "Mi armario"."""

from __future__ import annotations

import json
import re
import secrets

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, Response, UploadFile

from ...application.wardrobe import MAX_PHOTOS, LimitExceeded, NotFound, WardrobeService
from ...domain.catalog import SLOTS
from ...domain.options import COLORS
from ...domain.wardrobe import (
    BASE_TYPES, GarmentDetails, Identification, IdentifyRequest, InvalidGarment, Photo, WardrobeItem,
)
from ...ports.wardrobe import IdentificationError

router = APIRouter(prefix="/api/wardrobe")

COOKIE = "vestia_uid"
_UID = re.compile(r"^[A-Za-z0-9_-]{32}$")
MAX_PHOTO_BYTES = 6 * 1024 * 1024


def get_service(request: Request) -> WardrobeService:
    return request.app.state.wardrobe


def get_owner(request: Request, response: Response) -> str:
    """Usuario anónimo identificado por cookie hasta que haya cuentas de verdad."""
    uid = request.cookies.get(COOKIE)
    if not uid or not _UID.match(uid):
        uid = secrets.token_urlsafe(24)
        response.set_cookie(COOKIE, uid, max_age=2 * 365 * 86400, httponly=True,
                            samesite="lax", secure=request.app.state.secure_cookies)
    return uid


async def _read_photos(files: list[UploadFile]) -> list[Photo]:
    if len(files) > MAX_PHOTOS:
        raise HTTPException(422, f"Máximo {MAX_PHOTOS} fotos por prenda")
    photos = []
    for f in files:
        data = await f.read(MAX_PHOTO_BYTES + 1)
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(413, "La foto es demasiado grande (máximo 6 MB)")
        media_type = _sniff(data)
        if media_type is None:
            raise HTTPException(415, "Formato de imagen no admitido: usa JPG, PNG o WebP")
        photos.append(Photo(data, media_type))
    return photos


def _sniff(data: bytes) -> str | None:
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _clean_url(url: str | None) -> str | None:
    url = (url or "").strip()
    if not url:
        return None
    if not re.match(r"^https?://[^\s/$.?#][^\s]*$", url, re.I) or len(url) > 500:
        raise HTTPException(422, "El enlace no es válido (debe empezar por http:// o https://)")
    return url


@router.post("/identify")
async def identify(
    photos: list[UploadFile] = File(default=[]),
    product_url: str | None = Form(None),
    description: str | None = Form(None),
    rejected: str | None = Form(None),
    owner: str = Depends(get_owner),
    service: WardrobeService = Depends(get_service),
):
    try:
        rejected_list = json.loads(rejected) if rejected else []
        if not isinstance(rejected_list, list):
            raise ValueError
    except ValueError:
        raise HTTPException(422, "Formato de candidatos descartados no válido") from None
    try:
        request = IdentifyRequest(
            photos=tuple(await _read_photos(photos)),
            product_url=_clean_url(product_url),
            description=(description or "").strip()[:1500] or None,
            rejected=tuple(str(r)[:200] for r in rejected_list[:5]),
        )
        result = await service.identify(owner, request)
    except InvalidGarment as exc:
        raise HTTPException(422, str(exc)) from exc
    except LimitExceeded as exc:
        raise HTTPException(429, str(exc)) from exc
    except IdentificationError as exc:
        raise HTTPException(502, str(exc)) from exc
    return _identification(result)


@router.get("/items")
async def list_items(owner: str = Depends(get_owner), service: WardrobeService = Depends(get_service)):
    return {"items": [_item(i) for i in service.list(owner)]}


@router.post("/items", status_code=201)
async def add_item(
    details: str = Form(...),
    photos: list[UploadFile] = File(default=[]),
    source: str = Form("foto"),
    confidence: float | None = Form(None),
    owner: str = Depends(get_owner),
    service: WardrobeService = Depends(get_service),
):
    try:
        parsed = GarmentDetails.from_dict(json.loads(details))
    except (ValueError, InvalidGarment) as exc:
        raise HTTPException(422, str(exc) if isinstance(exc, InvalidGarment) else "Datos no válidos") from exc
    item = service.add(owner, parsed, await _read_photos(photos), source, confidence)
    return _item(item)


@router.put("/items/{item_id}")
async def update_item(item_id: str, details: dict = Body(...), owner: str = Depends(get_owner),
                      service: WardrobeService = Depends(get_service)):
    try:
        item = service.update(owner, item_id, GarmentDetails.from_dict(details))
    except InvalidGarment as exc:
        raise HTTPException(422, str(exc)) from exc
    except NotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    return _item(item)


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(item_id: str, owner: str = Depends(get_owner),
                      service: WardrobeService = Depends(get_service)):
    try:
        service.delete(owner, item_id)
    except NotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)


@router.get("/items/{item_id}/photos/{index}")
async def item_photo(item_id: str, index: int, owner: str = Depends(get_owner),
                     service: WardrobeService = Depends(get_service)):
    try:
        data, media_type = service.photo(owner, item_id, index)
    except (NotFound, FileNotFoundError) as exc:
        raise HTTPException(404, "Foto no encontrada") from exc
    return Response(data, media_type=media_type,
                    headers={"Cache-Control": "private, max-age=86400"})


# ------------------------------------------------------------- serialización
def _details(d: GarmentDetails) -> dict:
    data = d.to_dict()
    base = BASE_TYPES[d.base_type]
    data.update(
        slot_label=SLOTS[d.slot],
        base_type_name=base.name,
        icon=base.icon,
        materials_complete=d.materials_complete,
        colors=[{**c, "palette_label": COLORS[c["palette_id"]].label} for c in data["colors"]],
    )
    return data


def _item(item: WardrobeItem) -> dict:
    return {
        "id": item.id,
        "details": _details(item.details),
        "photos": [f"/api/wardrobe/items/{item.id}/photos/{i}" for i in range(len(item.photos))],
        "source": item.source,
        "confidence": item.confidence,
        "created_at": item.created_at,
        "updated_at": item.updated_at,
    }


def _identification(r: Identification) -> dict:
    return {
        "status": r.status,
        "confidence": round(r.confidence, 2),
        "message": r.message,
        "unconfirmed": list(r.unconfirmed),
        "candidate": _details(r.candidate) if r.candidate else None,
        "alternatives": [{"label": a.label, "product_url": a.product_url} for a in r.alternatives],
        "sources": list(r.sources),
    }
