"""Rutas HTTP de "Mis outfits"."""

from __future__ import annotations

import json

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, Request, Response, UploadFile
from pydantic import BaseModel, Field

from ...application.outfits import OutfitsService
from ...application.wardrobe import NotFound
from ...domain.options import OCCASIONS
from ...domain.outfits import MAX_PHOTOS, InvalidOutfit, OutfitInfo, SavedOutfit
from .wardrobe_api import _sniff, get_owner, MAX_PHOTO_BYTES

router = APIRouter(prefix="/api/outfits")


def get_service(request: Request) -> OutfitsService:
    return request.app.state.outfits


@router.get("")
async def list_outfits(owner: str = Depends(get_owner), service: OutfitsService = Depends(get_service)):
    return {"outfits": [_outfit(o) for o in service.list(owner)]}


@router.post("", status_code=201)
async def add_outfit(info: str = Form(...), photos: list[UploadFile] = File(default=[]),
                     owner: str = Depends(get_owner), service: OutfitsService = Depends(get_service)):
    if len(photos) > MAX_PHOTOS:
        raise HTTPException(422, f"Máximo {MAX_PHOTOS} fotos por outfit")
    images = []
    for f in photos:
        data = await f.read(MAX_PHOTO_BYTES + 1)
        if len(data) > MAX_PHOTO_BYTES:
            raise HTTPException(413, "La foto es demasiado grande (máximo 6 MB)")
        media_type = _sniff(data)
        if media_type is None:
            raise HTTPException(415, "Formato de imagen no admitido: usa JPG, PNG o WebP")
        from ...domain.wardrobe import Photo
        images.append(Photo(data, media_type))
    try:
        outfit = service.add(owner, OutfitInfo.from_dict(json.loads(info)), images)
    except ValueError as exc:  # incluye InvalidOutfit y JSON mal formado
        raise HTTPException(422, str(exc) if isinstance(exc, InvalidOutfit) else "Datos no válidos") from exc
    return _outfit(outfit)


@router.put("/{outfit_id}")
async def update_outfit(outfit_id: str, data: dict = Body(...), owner: str = Depends(get_owner),
                        service: OutfitsService = Depends(get_service)):
    try:
        return _outfit(service.update(owner, outfit_id, OutfitInfo.from_dict(data)))
    except InvalidOutfit as exc:
        raise HTTPException(422, str(exc)) from exc
    except NotFound as exc:
        raise HTTPException(404, str(exc)) from exc


@router.delete("/{outfit_id}", status_code=204)
async def delete_outfit(outfit_id: str, owner: str = Depends(get_owner), service: OutfitsService = Depends(get_service)):
    try:
        service.delete(owner, outfit_id)
    except NotFound as exc:
        raise HTTPException(404, str(exc)) from exc
    return Response(status_code=204)


@router.post("/{outfit_id}/worn")
async def worn(outfit_id: str, owner: str = Depends(get_owner), service: OutfitsService = Depends(get_service)):
    try:
        return _outfit(service.worn(owner, outfit_id))
    except NotFound as exc:
        raise HTTPException(404, str(exc)) from exc


@router.get("/{outfit_id}/photos/{index}")
async def photo(outfit_id: str, index: int, owner: str = Depends(get_owner),
                service: OutfitsService = Depends(get_service)):
    try:
        data, media_type = service.photo(owner, outfit_id, index)
    except (NotFound, FileNotFoundError) as exc:
        raise HTTPException(404, "Foto no encontrada") from exc
    return Response(data, media_type=media_type, headers={"Cache-Control": "private, max-age=86400"})


class SearchIn(BaseModel):
    query: str = Field(min_length=2, max_length=300)


@router.post("/search")
async def search(body: SearchIn, owner: str = Depends(get_owner), service: OutfitsService = Depends(get_service)):
    try:
        results = service.search(owner, body.query)
    except InvalidOutfit as exc:
        raise HTTPException(422, str(exc)) from exc
    return {"results": [{"outfit": _outfit(r.outfit), "score": r.score, "matched": list(r.matched),
                         "reasons": r.reasons} for r in results[:12]]}


def _outfit(o: SavedOutfit) -> dict:
    info = o.info
    return {
        "id": o.id, **info.to_dict(),
        "occasion_label": OCCASIONS[info.occasion].label if info.occasion else None,
        "photos": [f"/api/outfits/{o.id}/photos/{i}" for i in range(len(o.photos))],
        "worn_count": o.worn_count, "last_worn": o.last_worn,
        "created_at": o.created_at, "updated_at": o.updated_at,
    }
