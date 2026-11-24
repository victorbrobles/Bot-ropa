"""Rutas HTTP. Traduce JSON <-> casos de uso; no contiene lógica de negocio."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ...application.recommend_outfit import InvalidRequest, OutingPlan, OutfitResult, RecommendOutfit
from ...domain.options import COLORS, FITS, MOODS, OCCASIONS
from ...domain.recommender import OutfitPreferences
from ...domain.weather import HourlyWeather, Location, WeatherSummary, describe_code
from ...ports.weather import Geocoder, WeatherServiceError
from .schemas import LocationIn, OutfitRequestIn

router = APIRouter(prefix="/api")


def get_use_case(request: Request) -> RecommendOutfit:
    return request.app.state.recommend_outfit


def get_geocoder(request: Request) -> Geocoder:
    return request.app.state.geocoder


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.get("/options")
async def options():
    return {
        "moods": [{"id": m.id, "label": m.label, "icon": m.icon} for m in MOODS.values()],
        "occasions": [{"id": o.id, "label": o.label, "icon": o.icon} for o in OCCASIONS.values()],
        "colors": [{"id": c.id, "label": c.label, "hex": c.hex} for c in COLORS.values()],
        "fits": [{"id": k, "label": v} for k, v in FITS.items()],
        "max_hours": 16,
    }


@router.get("/locations")
async def search_locations(q: str = Query(..., min_length=2, max_length=80),
                           geocoder: Geocoder = Depends(get_geocoder)):
    try:
        results = await geocoder.search(q)
    except WeatherServiceError as exc:
        raise HTTPException(502, "El buscador de localidades no responde") from exc
    return {"results": [_location(r) for r in results]}


@router.post("/outfit")
async def outfit(body: OutfitRequestIn, request: Request,
                 use_case: RecommendOutfit = Depends(get_use_case)):
    try:
        prefs = OutfitPreferences(occasion=body.occasion, mood=body.mood,
                                  color=body.color, fit=body.fit)
        plan = OutingPlan(hours=body.hours, day_offset=body.day_offset, start_hour=body.start_hour)
        result = await use_case.execute(
            _to_location(body.origin), plan, prefs,
            _to_location(body.destination) if body.destination else None,
        )
    except (ValueError, InvalidRequest) as exc:
        raise HTTPException(422, str(exc)) from exc
    except WeatherServiceError as exc:
        raise HTTPException(502, "El servicio del tiempo no responde, inténtalo en un momento") from exc
    return _result(result, request.app.state.attribution)


# ------------------------------------------------------------- serialización
def _to_location(loc: LocationIn) -> Location:
    return Location(loc.name, loc.latitude, loc.longitude, loc.region, loc.country)


def _location(loc: Location) -> dict:
    return {"name": loc.name, "latitude": loc.latitude, "longitude": loc.longitude,
            "region": loc.region, "country": loc.country, "label": loc.label}


def _color(c) -> dict | None:
    return {"id": c.id, "label": c.label, "hex": c.hex} if c else None


def _summary(s: WeatherSummary) -> dict:
    return {
        "condition": {"key": s.condition_key, "label": s.condition_label, "icon": s.condition_icon},
        "min_temp": round(s.min_temp), "max_temp": round(s.max_temp),
        "min_feels": round(s.min_feels), "max_feels": round(s.max_feels),
        "precip_probability": round(s.max_precip_probability),
        "precipitation_mm": round(s.total_precipitation, 1),
        "max_wind": round(s.max_wind), "max_uv": round(s.max_uv, 1),
        "rain_likely": s.rain_likely, "snow": s.has_snow, "storm": s.has_storm,
    }


def _hour(h: HourlyWeather, offset: int) -> dict:
    _, label, icon = describe_code(h.weather_code)
    if not h.is_day and h.weather_code in (0, 1):
        icon = "🌙"
    return {
        "timestamp": h.timestamp,
        "local_hour": (h.timestamp + offset) % 86400 // 3600,
        "temperature": round(h.temperature),
        "feels_like": round(h.apparent_temperature),
        "precip_probability": round(h.precipitation_probability),
        "icon": icon, "label": label,
    }


def _result(r: OutfitResult, attribution: str) -> dict:
    o = r.outfit
    return {
        "outfit": {
            "headline": o.headline,
            "level": o.level,
            "level_label": o.level_label,
            "items": [{
                "slot": i.slot, "slot_label": i.slot_label,
                "id": i.garment.id, "name": i.garment.name, "icon": i.garment.icon,
                "color": _color(i.color), "reason": i.reason,
                "alternatives": [a.name for a in i.alternatives],
            } for i in o.items],
            "accessories": [{"id": a.id, "name": a.name, "icon": a.icon, "reason": a.reason}
                            for a in o.accessories],
            "tips": o.tips,
            "palette": [_color(c) for c in o.palette],
        },
        "weather": {
            "overall": _summary(r.overall),
            "start_ts": r.start_ts,
            "end_ts": r.end_ts,
            "places": [{
                "location": _location(p.location),
                "timezone": p.timezone,
                "summary": _summary(p.summary),
                "hours": [_hour(h, p.utc_offset_seconds) for h in p.hours],
            } for p in r.places],
        },
        "attribution": attribution,
    }
