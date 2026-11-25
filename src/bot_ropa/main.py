"""Punto de entrada: monta la app web (API + interfaz) y conecta los adaptadores."""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .adapters.weather import demo, open_meteo
from .adapters.weather.cache import CachedWeatherProvider
from .adapters.persistence.photos import LocalPhotoStorage
from .adapters.persistence.sqlite_wardrobe import SqliteWardrobeRepository
from .adapters.web import wardrobe_api
from .adapters.web.api import router
from .application.wardrobe import WardrobeService
from .application.recommend_outfit import RecommendOutfit
from .config import Settings, get_settings

STATIC_DIR = Path(__file__).parent / "web" / "static"


def create_app(settings: Settings | None = None, provider=None, geocoder=None,
               attribution: str | None = None, identifier=None, wardrobe_repo=None,
               photo_storage=None) -> FastAPI:
    settings = settings or get_settings()
    client = None
    if provider is None:
        if settings.weather_provider == "demo":
            provider = demo.DemoWeatherProvider()
            attribution = attribution or demo.ATTRIBUTION
        else:
            client = open_meteo.OpenMeteoClient(api_key=settings.open_meteo_api_key)
            provider = client
            attribution = attribution or open_meteo.ATTRIBUTION
    geocoder = geocoder or provider

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        if client is not None:
            await client.aclose()

    app = FastAPI(title="Bot Ropa", lifespan=lifespan)
    cached = CachedWeatherProvider(provider, ttl_seconds=settings.weather_cache_minutes * 60)
    app.state.recommend_outfit = RecommendOutfit(cached)
    app.state.geocoder = geocoder
    app.state.attribution = attribution or ""
    app.state.wardrobe = WardrobeService(
        identifier or _make_identifier(settings),
        wardrobe_repo or SqliteWardrobeRepository(settings.database_path),
        photo_storage or LocalPhotoStorage(settings.photos_dir),
        daily_identify_limit=settings.identify_daily_limit,
    )
    app.state.secure_cookies = settings.secure_cookies
    app.include_router(router)
    app.include_router(wardrobe_api.router)
    app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="web")
    return app


def _make_identifier(settings: Settings):
    if settings.garment_identifier == "demo":
        from .adapters.identify.demo import DemoGarmentIdentifier
        return DemoGarmentIdentifier()
    from .adapters.identify.claude import ClaudeGarmentIdentifier
    return ClaudeGarmentIdentifier()


app = create_app()
