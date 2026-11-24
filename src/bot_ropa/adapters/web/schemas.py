"""Esquemas de entrada/salida de la API HTTP."""

from __future__ import annotations

from pydantic import BaseModel, Field


class LocationIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    region: str | None = None
    country: str | None = None


class OutfitRequestIn(BaseModel):
    origin: LocationIn
    destination: LocationIn | None = None
    hours: int = Field(8, ge=1, le=16)
    day_offset: int = Field(0, ge=0, le=1)
    start_hour: int | None = Field(None, ge=0, le=23)
    occasion: str = "diario"
    mood: str | None = None
    color: str | None = None
    fit: str = "cualquiera"
