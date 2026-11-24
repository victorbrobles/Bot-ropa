"""Modelos del tiempo. Python puro: no conoce ninguna API concreta."""

from __future__ import annotations

from dataclasses import dataclass
from statistics import mean


@dataclass(frozen=True)
class Location:
    name: str
    latitude: float
    longitude: float
    region: str | None = None
    country: str | None = None

    @property
    def label(self) -> str:
        parts = [self.name, self.region, self.country]
        return ", ".join(p for p in parts if p)


@dataclass(frozen=True)
class HourlyWeather:
    timestamp: int  # Unix, UTC
    temperature: float  # °C
    apparent_temperature: float  # sensación térmica, °C
    precipitation_probability: float  # 0-100 %
    precipitation: float  # mm
    wind_speed: float  # km/h
    uv_index: float
    weather_code: int  # código WMO
    is_day: bool = True


@dataclass(frozen=True)
class Forecast:
    location: Location
    timezone: str
    utc_offset_seconds: int
    hours: tuple[HourlyWeather, ...]

    def window(self, start_ts: int, end_ts: int) -> list[HourlyWeather]:
        """Horas cuyo inicio cae en [start_ts, end_ts)."""
        return [h for h in self.hours if start_ts <= h.timestamp < end_ts]


# --- Códigos WMO -> descripción en español -------------------------------------

_CONDITIONS: list[tuple[set[int], str, str, str]] = [
    ({0}, "despejado", "Despejado", "☀️"),
    ({1}, "poco_nuboso", "Poco nuboso", "🌤️"),
    ({2}, "nuboso", "Intervalos nubosos", "⛅"),
    ({3}, "cubierto", "Cubierto", "☁️"),
    ({45, 48}, "niebla", "Niebla", "🌫️"),
    ({51, 53, 55, 56, 57}, "llovizna", "Llovizna", "🌦️"),
    ({61, 63, 65, 66, 67}, "lluvia", "Lluvia", "🌧️"),
    ({80, 81, 82}, "chubascos", "Chubascos", "🌦️"),
    ({71, 73, 75, 77, 85, 86}, "nieve", "Nieve", "❄️"),
    ({95, 96, 99}, "tormenta", "Tormenta", "⛈️"),
]

SNOW_CODES = {71, 73, 75, 77, 85, 86}
STORM_CODES = {95, 96, 99}
RAIN_CODES = {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82, 95, 96, 99}


def describe_code(code: int) -> tuple[str, str, str]:
    """Devuelve (clave, descripción, icono) para un código WMO."""
    for codes, key, label, icon in _CONDITIONS:
        if code in codes:
            return key, label, icon
    return "desconocido", "Variable", "🌡️"


# Prioridad para elegir la condición "más relevante" del periodo.
_SEVERITY = ["tormenta", "nieve", "lluvia", "chubascos", "llovizna", "niebla",
             "cubierto", "nuboso", "poco_nuboso", "despejado", "desconocido"]


@dataclass(frozen=True)
class WeatherSummary:
    hours: int
    min_temp: float
    max_temp: float
    min_feels: float
    max_feels: float
    avg_feels: float
    max_precip_probability: float
    total_precipitation: float
    max_wind: float
    max_uv: float
    has_snow: bool
    has_storm: bool
    rain_hours: int
    condition_key: str
    condition_label: str
    condition_icon: str

    @property
    def feels_range(self) -> float:
        return self.max_feels - self.min_feels

    @property
    def rain_likely(self) -> bool:
        return (self.max_precip_probability >= 50 or self.total_precipitation >= 1.0
                or self.rain_hours >= 2)

    @property
    def rain_possible(self) -> bool:
        return self.max_precip_probability >= 30 or self.rain_hours >= 1

    @classmethod
    def from_hours(cls, hours: list[HourlyWeather]) -> "WeatherSummary":
        if not hours:
            raise ValueError("No hay datos del tiempo para ese periodo")
        feels = [h.apparent_temperature for h in hours]
        temps = [h.temperature for h in hours]
        keys = [describe_code(h.weather_code)[0] for h in hours]
        # Condición dominante: la más severa que ocupe al menos 2 horas
        # (o 1 si el periodo es corto); si no, la más frecuente.
        threshold = 2 if len(hours) >= 4 else 1
        condition = None
        for key in _SEVERITY:
            if keys.count(key) >= threshold:
                condition = key
                break
        if condition is None:
            condition = max(set(keys), key=keys.count)
        code = next(h.weather_code for h in hours if describe_code(h.weather_code)[0] == condition)
        _, label, icon = describe_code(code)
        return cls(
            hours=len(hours),
            min_temp=min(temps),
            max_temp=max(temps),
            min_feels=min(feels),
            max_feels=max(feels),
            avg_feels=mean(feels),
            max_precip_probability=max(h.precipitation_probability for h in hours),
            total_precipitation=sum(h.precipitation for h in hours),
            max_wind=max(h.wind_speed for h in hours),
            max_uv=max(h.uv_index for h in hours),
            has_snow=any(h.weather_code in SNOW_CODES for h in hours),
            has_storm=any(h.weather_code in STORM_CODES for h in hours),
            rain_hours=sum(1 for h in hours if h.weather_code in RAIN_CODES),
            condition_key=condition,
            condition_label=label,
            condition_icon=icon,
        )
