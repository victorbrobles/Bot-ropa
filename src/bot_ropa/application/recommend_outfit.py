"""Caso de uso: "¿Qué me pongo?"."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from ..domain.recommender import Outfit, OutfitPreferences, Recommender
from ..domain.weather import Forecast, HourlyWeather, Location, WeatherSummary
from ..ports.weather import WeatherProvider

MAX_HOURS = 16


class InvalidRequest(ValueError):
    pass


@dataclass(frozen=True)
class OutingPlan:
    """Cuándo sales y cuánto tiempo vas a estar fuera."""

    hours: int = 8
    day_offset: int = 0  # 0 = hoy, 1 = mañana
    start_hour: int | None = None  # hora local de salida; None = ahora

    def __post_init__(self):
        if not 1 <= self.hours <= MAX_HOURS:
            raise InvalidRequest(f"Las horas fuera deben estar entre 1 y {MAX_HOURS}")
        if self.day_offset not in (0, 1):
            raise InvalidRequest("Solo se puede planificar para hoy o mañana")
        if self.start_hour is not None and not 0 <= self.start_hour <= 23:
            raise InvalidRequest("La hora de salida debe estar entre 0 y 23")
        if self.start_hour is None and self.day_offset != 0:
            raise InvalidRequest("Indica la hora de salida para mañana")


@dataclass(frozen=True)
class PlaceWeather:
    location: Location
    summary: WeatherSummary
    hours: list[HourlyWeather]
    utc_offset_seconds: int
    timezone: str


@dataclass(frozen=True)
class OutfitResult:
    outfit: Outfit
    overall: WeatherSummary
    places: list[PlaceWeather]
    start_ts: int
    end_ts: int


class RecommendOutfit:
    def __init__(self, weather: WeatherProvider, recommender: Recommender | None = None,
                 clock=time.time):
        self._weather = weather
        self._recommender = recommender or Recommender()
        self._clock = clock

    async def execute(self, origin: Location, plan: OutingPlan, prefs: OutfitPreferences,
                      destination: Location | None = None) -> OutfitResult:
        locations = [origin] + ([destination] if destination else [])
        forecasts = await asyncio.gather(*(
            self._weather.get_forecast(loc.latitude, loc.longitude, days=3) for loc in locations
        ))
        start_ts = self._start_ts(forecasts[0], plan)
        end_ts = start_ts + plan.hours * 3600

        places: list[PlaceWeather] = []
        all_hours: list[HourlyWeather] = []
        for loc, fc in zip(locations, forecasts):
            hours = fc.window(start_ts, end_ts)
            if not hours:
                raise InvalidRequest("No hay previsión para ese horario")
            all_hours.extend(hours)
            places.append(PlaceWeather(loc, WeatherSummary.from_hours(hours), hours,
                                       fc.utc_offset_seconds, fc.timezone))

        overall = WeatherSummary.from_hours(all_hours)
        outfit = self._recommender.recommend(overall, prefs)
        if destination:
            outfit.tips.insert(0, _destination_tip(places[0], places[1]))
        return OutfitResult(outfit, overall, places, start_ts, end_ts)

    def _start_ts(self, forecast: Forecast, plan: OutingPlan) -> int:
        now = int(self._clock())
        if plan.start_hour is None:
            return now - now % 3600
        offset = forecast.utc_offset_seconds
        local_midnight = (now + offset) // 86400 * 86400 - offset
        return local_midnight + plan.day_offset * 86400 + plan.start_hour * 3600


def _destination_tip(origin: PlaceWeather, dest: PlaceWeather) -> str:
    diff = dest.summary.avg_feels - origin.summary.avg_feels
    name = dest.location.name
    if abs(diff) < 2:
        text = f"En {name} hará un tiempo parecido"
    elif diff < 0:
        text = f"En {name} hará unos {abs(diff):.0f} °C menos de sensación"
    else:
        text = f"En {name} hará unos {diff:.0f} °C más de sensación"
    if dest.summary.rain_likely and not origin.summary.rain_likely:
        text += " y puede llover allí"
    return text + ": el outfit cubre las dos zonas."
