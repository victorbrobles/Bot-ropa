"""Proveedor de demostración: datos sintéticos y deterministas, sin red.

Útil para desarrollar la interfaz sin depender de una API externa
(WEATHER_PROVIDER=demo). Nunca usar en producción.
"""

from __future__ import annotations

import math
import time

from ...domain.weather import Forecast, HourlyWeather, Location

ATTRIBUTION = "Datos de demostración (no reales)"

_CITIES = [
    Location("Madrid", 40.4168, -3.7038, "Comunidad de Madrid", "España"),
    Location("Barcelona", 41.3874, 2.1686, "Cataluña", "España"),
    Location("Valencia", 39.4699, -0.3763, "Comunidad Valenciana", "España"),
    Location("Sevilla", 37.3891, -5.9845, "Andalucía", "España"),
    Location("Bilbao", 43.2630, -2.9350, "País Vasco", "España"),
    Location("A Coruña", 43.3623, -8.4115, "Galicia", "España"),
    Location("Zaragoza", 41.6488, -0.8891, "Aragón", "España"),
    Location("Málaga", 36.7213, -4.4214, "Andalucía", "España"),
    Location("Granada", 37.1773, -3.5986, "Andalucía", "España"),
    Location("Oviedo", 43.3619, -5.8494, "Asturias", "España"),
    Location("Palma", 39.5696, 2.6502, "Islas Baleares", "España"),
    Location("Las Palmas de Gran Canaria", 28.1235, -15.4363, "Canarias", "España"),
    Location("Lisboa", 38.7223, -9.1393, "Lisboa", "Portugal"),
    Location("París", 48.8566, 2.3522, "Isla de Francia", "Francia"),
    Location("Londres", 51.5072, -0.1276, "Inglaterra", "Reino Unido"),
]


class DemoWeatherProvider:
    def __init__(self, now: float | None = None):
        self._now = now

    async def get_forecast(self, latitude: float, longitude: float, days: int = 3) -> Forecast:
        now = self._now if self._now is not None else time.time()
        offset = round(longitude / 15) * 3600
        local_midnight = int((now + offset) // 86400 * 86400 - offset)
        # Clima base: más frío cuanto más al norte; cada zona tiene su "carácter".
        seed = abs(math.sin(latitude * 12.9898 + longitude * 78.233)) * 1000
        base = 27 - (latitude - 28) * 0.7 - (seed % 9)
        rainy = (seed % 10) > 6
        hours = []
        for i in range(days * 24):
            ts = local_midnight + i * 3600
            hour = i % 24
            day = i // 24
            daily = -math.cos((hour - 3) / 24 * 2 * math.pi) * 5
            temp = base + daily + day * ((seed % 5) - 2)
            wind = 8 + (seed % 25) + 6 * math.sin(hour / 4)
            rain_prob = max(0.0, min(100.0, (70 if rainy else 10) + 25 * math.sin((hour + day * 5) / 3)))
            raining = rain_prob >= 60
            sunny = 8 <= hour <= 19
            uv = max(0.0, (9 - (latitude - 28) * 0.15) * math.sin((hour - 7) / 12 * math.pi)) if sunny else 0.0
            code = (63 if temp > 1 else 73) if raining else (0 if rain_prob < 20 else 2)
            hours.append(HourlyWeather(
                timestamp=ts,
                temperature=round(temp, 1),
                apparent_temperature=round(temp - wind * 0.12, 1),
                precipitation_probability=round(rain_prob),
                precipitation=1.2 if raining else 0.0,
                wind_speed=round(wind, 1),
                uv_index=round(uv * (0.4 if raining else 1), 1),
                weather_code=code,
                is_day=sunny,
            ))
        return Forecast(
            location=Location("Ubicación", latitude, longitude),
            timezone="Demo",
            utc_offset_seconds=offset,
            hours=tuple(hours),
        )

    async def search(self, query: str, limit: int = 6) -> list[Location]:
        q = _normalize(query)
        return [c for c in _CITIES if q in _normalize(c.label)][:limit]


def _normalize(text: str) -> str:
    table = str.maketrans("áéíóúüñ", "aeiouun")
    return text.lower().translate(table).strip()
