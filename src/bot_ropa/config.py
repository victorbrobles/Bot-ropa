from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    weather_provider: Literal["open_meteo", "demo"] = "open_meteo"
    weather_cache_minutes: int = 30
    open_meteo_api_key: str | None = None  # solo con plan comercial


@lru_cache
def get_settings() -> Settings:
    return Settings()
