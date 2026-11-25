import time

from fastapi.testclient import TestClient

from bot_ropa.config import Settings
from bot_ropa.main import create_app
from bot_ropa.adapters.persistence.sqlite_wardrobe import SqliteWardrobeRepository
from bot_ropa.adapters.identify.demo import DemoGarmentIdentifier
from conftest import FakeWeather


def client():
    return TestClient(create_app(Settings(weather_provider="demo"), provider=FakeWeather(now=time.time()),
                                 attribution="Datos de prueba", identifier=DemoGarmentIdentifier(),
                                 wardrobe_repo=SqliteWardrobeRepository(":memory:")))


def test_options():
    data = client().get("/api/options").json()
    assert {m["id"] for m in data["moods"]} >= {"feliz", "cansado"}
    assert {o["id"] for o in data["occasions"]} == {"diario", "trabajo", "deporte", "fiesta", "etiqueta"}


def test_locations():
    data = client().get("/api/locations", params={"q": "Madrid"}).json()
    assert data["results"][0]["name"] == "Madrid"


def test_outfit_endpoint():
    body = {
        "origin": {"name": "Madrid", "latitude": 40.4, "longitude": -3.7},
        "hours": 6, "occasion": "trabajo", "mood": "seguro", "color": "azul",
    }
    res = client().post("/api/outfit", json=body)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["outfit"]["items"]
    assert data["weather"]["places"][0]["hours"]
    assert data["attribution"] == "Datos de prueba"


def test_outfit_validation_errors():
    c = client()
    base = {"origin": {"name": "X", "latitude": 40, "longitude": -3}}
    assert c.post("/api/outfit", json={**base, "occasion": "boda"}).status_code == 422
    assert c.post("/api/outfit", json={**base, "hours": 40}).status_code == 422
    assert c.post("/api/outfit", json={"origin": {"name": "X", "latitude": 200, "longitude": 0}}).status_code == 422


def test_frontend_is_served():
    res = client().get("/")
    assert res.status_code == 200
    assert "¿Qué me pongo?" in res.text


def test_forecasts_are_cached():
    weather = FakeWeather(now=time.time())
    c = TestClient(create_app(Settings(), provider=weather, identifier=DemoGarmentIdentifier(),
                              wardrobe_repo=SqliteWardrobeRepository(":memory:")))
    body = {"origin": {"name": "X", "latitude": 40.4, "longitude": -3.7}}
    c.post("/api/outfit", json=body)
    c.post("/api/outfit", json={**body, "mood": "feliz"})
    assert weather.calls == 1
