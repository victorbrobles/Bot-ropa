"""Adaptador para Open-Meteo (https://open-meteo.com).

Ojo: el plan gratuito es solo para uso NO comercial. Antes de cobrar por el
servicio hay que contratar un plan comercial o cambiar de proveedor.
Datos bajo licencia CC BY 4.0: hay que citar la fuente.
"""

from __future__ import annotations

import httpx

from ...domain.weather import Forecast, HourlyWeather, Location
from ...ports.weather import WeatherServiceError

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
HOURLY_VARS = [
    "temperature_2m",
    "apparent_temperature",
    "precipitation_probability",
    "precipitation",
    "wind_speed_10m",
    "uv_index",
    "weather_code",
    "is_day",
]
ATTRIBUTION = "Datos meteorológicos de Open-Meteo.com (CC BY 4.0)"


class OpenMeteoClient:
    def __init__(self, client: httpx.AsyncClient | None = None, api_key: str | None = None,
                 forecast_url: str = FORECAST_URL, geocoding_url: str = GEOCODING_URL):
        self._client = client or httpx.AsyncClient(timeout=10.0)
        self._api_key = api_key
        self._forecast_url = forecast_url
        self._geocoding_url = geocoding_url

    async def _get(self, url: str, params: dict) -> dict:
        if self._api_key:
            params = {**params, "apikey": self._api_key}
        try:
            response = await self._client.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise WeatherServiceError(f"Open-Meteo no responde: {exc}") from exc

    async def get_forecast(self, latitude: float, longitude: float, days: int = 3) -> Forecast:
        data = await self._get(self._forecast_url, {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": ",".join(HOURLY_VARS),
            "timezone": "auto",
            "timeformat": "unixtime",
            "wind_speed_unit": "kmh",
            "forecast_days": days,
        })
        return parse_forecast(data, Location("Ubicación", latitude, longitude))

    async def search(self, query: str, limit: int = 6) -> list[Location]:
        data = await self._get(self._geocoding_url, {
            "name": query, "count": limit, "language": "es", "format": "json",
        })
        return [
            Location(
                name=r["name"],
                latitude=r["latitude"],
                longitude=r["longitude"],
                region=r.get("admin1"),
                country=r.get("country"),
            )
            for r in data.get("results") or []
        ]

    async def aclose(self) -> None:
        await self._client.aclose()


def parse_forecast(data: dict, location: Location) -> Forecast:
    try:
        h = data["hourly"]
        hours = []
        for i, ts in enumerate(h["time"]):
            temp = h["temperature_2m"][i]
            if temp is None:
                continue
            hours.append(HourlyWeather(
                timestamp=int(ts),
                temperature=float(temp),
                apparent_temperature=float(_or(h["apparent_temperature"][i], temp)),
                precipitation_probability=float(_or(h["precipitation_probability"][i], 0)),
                precipitation=float(_or(h["precipitation"][i], 0)),
                wind_speed=float(_or(h["wind_speed_10m"][i], 0)),
                uv_index=float(_or(h["uv_index"][i], 0)),
                weather_code=int(_or(h["weather_code"][i], 0)),
                is_day=bool(_or(h["is_day"][i], 1)),
            ))
        return Forecast(
            location=location,
            timezone=data.get("timezone", "UTC"),
            utc_offset_seconds=int(data.get("utc_offset_seconds", 0)),
            hours=tuple(hours),
        )
    except (KeyError, IndexError, TypeError) as exc:
        raise WeatherServiceError(f"Respuesta inesperada de Open-Meteo: {exc}") from exc


def _or(value, default):
    return default if value is None else value
