"""Caché en memoria de previsiones por zona (evita llamadas repetidas)."""

from __future__ import annotations

import time

from ...domain.weather import Forecast
from ...ports.weather import WeatherProvider


class CachedWeatherProvider:
    def __init__(self, inner: WeatherProvider, ttl_seconds: int = 1800, max_entries: int = 2000):
        self._inner = inner
        self._ttl = ttl_seconds
        self._max = max_entries
        self._store: dict[tuple, tuple[float, Forecast]] = {}

    async def get_forecast(self, latitude: float, longitude: float, days: int = 3) -> Forecast:
        # ~1 km de precisión: suficiente para el tiempo y agrupa usuarios cercanos.
        key = (round(latitude, 2), round(longitude, 2), days)
        hit = self._store.get(key)
        if hit and time.monotonic() - hit[0] < self._ttl:
            return hit[1]
        forecast = await self._inner.get_forecast(latitude, longitude, days)
        if len(self._store) >= self._max:
            self._store.pop(next(iter(self._store)))
        self._store[key] = (time.monotonic(), forecast)
        return forecast
