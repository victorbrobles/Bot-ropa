"""Puertos: lo que el dominio necesita del exterior, sin saber quién lo da."""

from __future__ import annotations

from typing import Protocol

from ..domain.weather import Forecast, Location


class WeatherProvider(Protocol):
    async def get_forecast(self, latitude: float, longitude: float, days: int = 3) -> Forecast:
        """Previsión horaria para unas coordenadas."""
        ...


class Geocoder(Protocol):
    async def search(self, query: str, limit: int = 6) -> list[Location]:
        """Busca localidades por nombre."""
        ...


class WeatherServiceError(RuntimeError):
    """El proveedor del tiempo no ha podido responder."""
