import asyncio

import pytest

from bot_ropa.application.recommend_outfit import InvalidRequest, OutingPlan, RecommendOutfit
from bot_ropa.domain.recommender import OutfitPreferences
from bot_ropa.domain.weather import Location
from conftest import NOW, NOW_HOUR, FakeWeather

MADRID = Location("Madrid", 40.0, -3.7)
BILBAO = Location("Bilbao", 43.0, -2.9)


def run(coro):
    return asyncio.run(coro)


def test_now_window_starts_at_current_hour():
    uc = RecommendOutfit(FakeWeather(), clock=lambda: NOW)
    result = run(uc.execute(MADRID, OutingPlan(hours=5), OutfitPreferences()))
    assert result.start_ts == NOW_HOUR
    assert len(result.places[0].hours) == 5


def test_tomorrow_at_given_local_hour():
    uc = RecommendOutfit(FakeWeather(offset=3600), clock=lambda: NOW)
    result = run(uc.execute(MADRID, OutingPlan(hours=3, day_offset=1, start_hour=9), OutfitPreferences()))
    local = result.start_ts + 3600
    assert local % 86400 == 9 * 3600
    assert (local // 86400) == (NOW + 3600) // 86400 + 1


def test_destination_weather_is_combined():
    weather = FakeWeather({40.0: {"temp": 20}, 43.0: {"temp": 6, "prob": 90, "code": 63}})
    uc = RecommendOutfit(weather, clock=lambda: NOW)
    result = run(uc.execute(MADRID, OutingPlan(hours=4), OutfitPreferences(), destination=BILBAO))
    assert len(result.places) == 2
    assert result.overall.min_feels == 6
    assert "Bilbao" in result.outfit.tips[0]
    assert any(i.slot == "abrigo" for i in result.outfit.items)


def test_invalid_plans():
    with pytest.raises(InvalidRequest):
        OutingPlan(hours=0)
    with pytest.raises(InvalidRequest):
        OutingPlan(hours=4, day_offset=1)  # mañana sin hora
