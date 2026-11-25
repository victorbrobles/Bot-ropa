import json

import pytest
from fastapi.testclient import TestClient

from bot_ropa.adapters.persistence.photos import LocalPhotoStorage
from bot_ropa.adapters.persistence.sqlite_wardrobe import SqliteWardrobeRepository
from bot_ropa.config import Settings
from bot_ropa.main import create_app
from bot_ropa.domain.wardrobe import ProductInfo
from conftest import FakeProductReader, FakeWeather

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 100
DETAILS = {"name": "Vaqueros rectos", "base_type": "vaqueros", "brand": "Marca",
           "materials": [{"fiber": "algodón", "percent": 98}, {"fiber": "elastano", "percent": 2}],
           "colors": [{"name": "azul oscuro", "palette_id": "azul_marino"}]}


@pytest.fixture
def make_client(tmp_path):
    def make(limit=30, reader=None):
        app = create_app(Settings(link_reads_daily_limit=limit), provider=FakeWeather(),
                         product_reader=reader or FakeProductReader(),
                         wardrobe_repo=SqliteWardrobeRepository(":memory:"),
                         photo_storage=LocalPhotoStorage(tmp_path / "photos"))
        return app
    return make


def test_identify_then_save_list_photo_update_delete(make_client):
    c = TestClient(make_client())
    res = c.post("/api/wardrobe/analyze", json={
        "label_text": "98% COTTON 2% ELASTANE", "brand_lines": ["Marca"],
        "photo_colors": [{"hex": "#1f2f55", "share": 0.7}], "description": "vaqueros rectos"})
    assert res.status_code == 200, res.text
    ident = res.json()
    assert ident["status"] == "identificada"
    assert ident["candidate"]["materials_complete"] and ident["candidate"]["base_type_name"] == "Vaqueros"
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
    assert c.post("/api/wardrobe/analyze", json={}).status_code == 422  # nada que analizar
    assert c.post("/api/wardrobe/analyze", json={"product_url": "file:///etc/passwd"}).status_code == 422
    assert c.post("/api/wardrobe/analyze", json={"photo_colors": [{"hex": "rojo", "share": 1}]}).status_code == 422
    assert c.post("/api/wardrobe/items", data={"details": json.dumps({"base_type": "x"})}).status_code == 422
    bad = c.post("/api/wardrobe/items", data={"details": json.dumps(DETAILS)},
                 files=[("photos", ("a.gif", b"GIF89a....", "image/gif"))])
    assert bad.status_code == 415
    four = [("photos", (f"{i}.jpg", JPEG, "image/jpeg")) for i in range(4)]
    assert c.post("/api/wardrobe/items", data={"details": json.dumps(DETAILS)}, files=four).status_code == 422


def test_product_link_and_daily_limit(make_client):
    product = ProductInfo(url="https://shop.example/p", name="Jersey de lana merino", brand="Marca Z",
                          material="100% lana merino", color="verde")
    reader = FakeProductReader(product)
    c = TestClient(make_client(limit=1, reader=reader))
    res = c.post("/api/wardrobe/analyze", json={"product_url": "https://shop.example/p"}).json()
    assert res["status"] == "identificada" and res["candidate"]["brand"] == "Marca Z"
    assert res["provenance"]["materials"] == "web"
    assert reader.calls == ["https://shop.example/p"]
    assert c.post("/api/wardrobe/analyze", json={"product_url": "https://shop.example/p"}).status_code == 429
    # Sin enlace no hay límite: el análisis es local y gratuito.
    assert c.post("/api/wardrobe/analyze", json={"description": "camiseta"}).status_code == 200


def test_shop_that_blocks_us_still_returns_a_draft(make_client):
    c = TestClient(make_client(reader=FakeProductReader(error="Esa tienda no deja leer su web automáticamente.")))
    res = c.post("/api/wardrobe/analyze", json={"product_url": "https://shop.example/p",
                                                "description": "sudadera gris"}).json()
    assert res["candidate"]["base_type"] == "sudadera"
    assert res["message"].startswith("Esa tienda no deja")
