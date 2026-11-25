from __future__ import annotations

from bot_ropa.domain.weather import Forecast, HourlyWeather, Location, WeatherSummary

NOW = 1_764_000_000  # instante fijo para los tests
NOW_HOUR = NOW - NOW % 3600


def hour(ts=NOW_HOUR, temp=20.0, feels=None, prob=0.0, rain=0.0, wind=5.0, uv=0.0, code=0):
    return HourlyWeather(ts, temp, temp if feels is None else feels, prob, rain, wind, uv, code)


def summary(temps, **kw) -> WeatherSummary:
    return WeatherSummary.from_hours([hour(NOW_HOUR + i * 3600, t, **kw) for i, t in enumerate(temps)])


class FakeWeather:
    """Proveedor falso: el tiempo de cada zona se fija por latitud."""

    def __init__(self, by_lat: dict[float, dict] | None = None, offset: int = 3600, now: float = NOW):
        self.by_lat = by_lat or {}
        self.now = int(now)
        self.offset = offset
        self.calls = 0

    async def get_forecast(self, latitude, longitude, days=3):
        self.calls += 1
        cfg = self.by_lat.get(latitude, {})
        start = (self.now + self.offset) // 86400 * 86400 - self.offset
        hours = tuple(hour(start + i * 3600, cfg.get("temp", 15.0), prob=cfg.get("prob", 0.0),
                           code=cfg.get("code", 0), wind=cfg.get("wind", 5.0))
                      for i in range(days * 24))
        return Forecast(Location("x", latitude, longitude), "Europe/Madrid", self.offset, hours)

    async def search(self, query, limit=6):
        return [Location("Madrid", 40.42, -3.70, "Comunidad de Madrid", "España")]


class FakeProductReader:
    """Lector de fichas falso: devuelve lo configurado o lanza el error indicado."""

    def __init__(self, product=None, error=None):
        self.product, self.error, self.calls = product, error, []

    async def read(self, url):
        from bot_ropa.domain.wardrobe import ProductInfo
        from bot_ropa.ports.wardrobe import ProductPageError
        self.calls.append(url)
        if self.error:
            raise ProductPageError(self.error)
        return self.product or ProductInfo(url=url)

    async def aclose(self):
        pass
