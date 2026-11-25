import json

import pytest
from fastapi.testclient import TestClient

from bot_ropa.adapters.identify.demo import DemoGarmentIdentifier
from bot_ropa.adapters.persistence.photos import LocalPhotoStorage
from bot_ropa.adapters.persistence.sqlite_wardrobe import SqliteWardrobeRepository
from bot_ropa.config import Settings
from bot_ropa.main import create_app
from conftest import FakeWeather

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
DETAILS = {"name": "Vaqueros rectos", "base_type": "vaqueros", "brand": "Marca",
           "materials": [{"fiber": "algodón", "percent": 98}, {"fiber": "elastano", "percent": 2}],
           "colors": [{"name": "azul oscuro", "palette_id": "azul_marino"}]}


@pytest.fixture
def make_client(tmp_path):
    def make(limit=30):
        app = create_app(Settings(identify_daily_limit=limit), provider=FakeWeather(),
                         identifier=DemoGarmentIdentifier(),
                         wardrobe_repo=SqliteWardrobeRepository(":memory:"),
                         photo_storage=LocalPhotoStorage(tmp_path / "photos"))
        return app
    return make


def test_identify_then_save_list_photo_update_delete(make_client):
    c = TestClient(make_client())
    res = c.post("/api/wardrobe/identify", files=[("photos", ("a.jpg", JPEG, "image/jpeg"))])
    assert res.status_code == 200, res.text
    ident = res.json()
    assert ident["status"] == "parcial" and "composicion" in ident["unconfirmed"]
    assert "vestia_uid" in c.cookies

    res = c.post("/api/wardrobe/items", data={"details": json.dumps(DETAILS), "source": "foto"},
                 files=[("photos", ("a.jpg", JPEG, "image/jpeg"))])
    assert res.status_code == 201, res.text
    item = res.json()
    assert item["details"]["materials_complete"]
    assert item["details"]["slot"] == "parte_inferior"

    items = c.get("/api/wardrobe/items").json()["items"]
    assert [i["id"] for i in items] == [item["id"]]
    photo = c.get(item["photos"][0])
    assert photo.status_code == 200 and photo.content == JPEG

    res = c.put(f"/api/wardrobe/items/{item['id']}", json={**DETAILS, "name": "Mis vaqueros"})
    assert res.json()["details"]["name"] == "Mis vaqueros"

    assert c.delete(f"/api/wardrobe/items/{item['id']}").status_code == 204
    assert c.get("/api/wardrobe/items").json()["items"] == []


def test_wardrobes_are_private(make_client):
    app = make_client()
    alice, bob = TestClient(app), TestClient(app)
    item = alice.post("/api/wardrobe/items", data={"details": json.dumps(DETAILS)},
                      files=[("photos", ("a.jpg", JPEG, "image/jpeg"))]).json()
    assert bob.get("/api/wardrobe/items").json()["items"] == []
    assert bob.get(item["photos"][0]).status_code == 404
    assert bob.delete(f"/api/wardrobe/items/{item['id']}").status_code == 404


def test_rejects_bad_input(make_client):
    c = TestClient(make_client())
    assert c.post("/api/wardrobe/identify").status_code == 422  # nada que identificar
    assert c.post("/api/wardrobe/identify", files=[("photos", ("a.gif", b"GIF89a....", "image/gif"))]).status_code == 415
    assert c.post("/api/wardrobe/identify", data={"product_url": "file:///etc/passwd"}).status_code == 422
    four = [("photos", (f"{i}.jpg", JPEG, "image/jpeg")) for i in range(4)]
    assert c.post("/api/wardrobe/identify", files=four).status_code == 422
    assert c.post("/api/wardrobe/items", data={"details": json.dumps({"base_type": "x"})}).status_code == 422


def test_second_attempt_with_link_and_daily_limit(make_client):
    c = TestClient(make_client(limit=2))
    res = c.post("/api/wardrobe/identify", data={
        "product_url": "https://marca.example/jersey", "description": "jersey verde de merino",
        "rejected": json.dumps(["Marca Demo · Oxford Regular Fit"])})
    assert res.json()["status"] == "identificada"
    assert c.post("/api/wardrobe/identify", data={"description": "x"}).status_code == 200
    assert c.post("/api/wardrobe/identify", data={"description": "x"}).status_code == 429
