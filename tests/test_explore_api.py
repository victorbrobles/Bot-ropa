import json

from fastapi.testclient import TestClient

from bot_ropa.adapters.persistence.photos import LocalPhotoStorage
from bot_ropa.adapters.persistence.sqlite_profiles import SqliteProfileRepository
from bot_ropa.adapters.persistence.sqlite_wardrobe import SqliteWardrobeRepository
from bot_ropa.config import Settings
from bot_ropa.main import create_app
from conftest import FakeProductReader, FakeWeather


def client(tmp_path):
    app = create_app(Settings(), provider=FakeWeather(), product_reader=FakeProductReader(),
                     wardrobe_repo=SqliteWardrobeRepository(":memory:"),
                     photo_storage=LocalPhotoStorage(tmp_path), profile_repo=SqliteProfileRepository(":memory:"))
    return TestClient(app)


def test_profile_feed_complete_flow(tmp_path):
    c = client(tmp_path)
    cat = c.get("/api/explore/catalog").json()
    assert len(cat["styles"]) >= 10 and any(b["id"] == "zara" for b in cat["brands"])

    assert c.get("/api/explore/feed").json()["profile_empty"] is True
    saved = c.put("/api/explore/profile", json={"styles": ["streetwear"], "brands": ["nike"], "budget": [1, 2]}).json()
    assert saved["styles"] == ["streetwear"]

    item = c.post("/api/wardrobe/items", data={"details": json.dumps(
        {"name": "Sudadera negra", "base_type": "sudadera", "colors": [{"name": "negro", "palette_id": "negro"}]})}).json()

    feed = c.get("/api/explore/feed", params={"month": 11}).json()
    assert not feed["profile_empty"] and feed["affinity"][0]["id"] == "streetwear"
    assert feed["ideas"] and feed["ideas"][0]["base"][0]["item_id"] == item["id"]
    assert all(b["id"] != "nike" for b in feed["brands"])
    assert feed["news"][0]["name"] == "Nike"

    plan = c.post("/api/explore/complete", json={"pieces": [{"item_id": item["id"]}], "month": 1}).json()
    assert plan["style"]["id"] == "streetwear"
    assert {s["slot"] for s in plan["suggestions"]} >= {"parte_superior", "parte_inferior", "calzado"}

    generic = c.post("/api/explore/complete", json={"pieces": [{"base_type": "vaqueros"}], "style": "clasico"}).json()
    assert generic["style"]["id"] == "clasico"


def test_complete_validation(tmp_path):
    c = client(tmp_path)
    assert c.post("/api/explore/complete", json={"pieces": []}).status_code == 422
    assert c.post("/api/explore/complete", json={"pieces": [{"item_id": "nope"}]}).status_code == 422
    two_tops = {"pieces": [{"base_type": "camiseta"}, {"base_type": "polo"}]}
    assert c.post("/api/explore/complete", json=two_tops).status_code == 422
