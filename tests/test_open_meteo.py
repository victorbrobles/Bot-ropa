import asyncio

import httpx
import pytest

from bot_ropa.adapters.weather.open_meteo import OpenMeteoClient
from bot_ropa.ports.weather import WeatherServiceError

FORECAST = {
    "timezone": "Europe/Madrid",
    "utc_offset_seconds": 3600,
    "hourly": {
        "time": [1764000000, 1764003600],
        "temperature_2m": [12.3, None],
        "apparent_temperature": [10.1, 9.0],
        "precipitation_probability": [40, 50],
        "precipitation": [0.2, 0.0],
        "wind_speed_10m": [14.0, 10.0],
        "uv_index": [None, 1.0],
        "weather_code": [61, 3],
        "is_day": [1, 1],
    },
}


def make_client(handler):
    return OpenMeteoClient(httpx.AsyncClient(transport=httpx.MockTransport(handler)))


def test_parses_forecast_and_skips_missing_hours():
    seen = {}

    def handler(request):
        seen.update(request.url.params)
        return httpx.Response(200, json=FORECAST)

    fc = asyncio.run(make_client(handler).get_forecast(40.4, -3.7))
    assert seen["timeformat"] == "unixtime" and seen["timezone"] == "auto"
    assert len(fc.hours) == 1
    h = fc.hours[0]
    assert (h.temperature, h.apparent_temperature, h.uv_index, h.weather_code) == (12.3, 10.1, 0.0, 61)
    assert fc.utc_offset_seconds == 3600


def test_geocoding():
    def handler(request):
        return httpx.Response(200, json={"results": [
            {"name": "Sevilla", "latitude": 37.38, "longitude": -5.97, "admin1": "Andalucía", "country": "España"}]})

    results = asyncio.run(make_client(handler).search("Sevi"))
    assert results[0].label == "Sevilla, Andalucía, España"


def test_errors_are_wrapped():
    with pytest.raises(WeatherServiceError):
        asyncio.run(make_client(lambda r: httpx.Response(500)).get_forecast(0, 0))
