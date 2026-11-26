import json
from datetime import date

import pytest
from fastapi.testclient import TestClient

from bot_ropa.adapters.persistence.photos import LocalPhotoStorage
from bot_ropa.adapters.persistence.sqlite_outfits import SqliteOutfitRepository
from bot_ropa.adapters.persistence.sqlite_profiles import SqliteProfileRepository
from bot_ropa.adapters.persistence.sqlite_wardrobe import SqliteWardrobeRepository
from bot_ropa.config import Settings
from bot_ropa.domain.outfits import InvalidOutfit, OutfitInfo, SavedOutfit, recommend
from bot_ropa.domain.text_search import BM25, stem, tokens
from bot_ropa.main import create_app
from conftest import FakeProductReader, FakeWeather

JPEG = b"\xff\xd8\xff\xe0" + b"0" * 64


def outfit(id, description, occasion=None, seasons=(), last_worn=None, worn=0):
    return SavedOutfit(id=id, owner_id="u", info=OutfitInfo(description, occasion, tuple(seasons)),
                       worn_count=worn, last_worn=last_worn)


def test_tokens_normalize_plurals_accents_and_concepts():
    assert stem("bodas") == stem("boda")
    t = tokens("Cena romántica en un restaurante")
    assert "#cita" in t and "en" not in t


def test_bm25_finds_synonyms():
    index = BM25({"a": "Traje azul para la boda de mi prima", "b": "Chándal para el gimnasio"})
    assert index.search("ceremonia elegante")[0].doc_id == "a"
    assert index.search("voy al gym")[0].doc_id == "b"
    assert index.search("xyz qwerty") == []


def test_recommend_ranks_by_text_then_season_and_variety():
    outfits = [
        outfit("boda", "Vestido largo verde para boda de tarde", "etiqueta", ["verano"]),
        outfit("cena", "Camisa blanca y vaqueros para cenar con amigos"),
        outfit("cena2", "Jersey negro y pantalón de vestir para cena en restaurante", seasons=["invierno"]),
        outfit("gym", "Mallas y camiseta técnica para el gimnasio", "deporte"),
    ]
    today = date(2026, 12, 10)
    results = recommend("cena el sábado con amigos", outfits, {}, today)
    assert [r.outfit.id for r in results][:2] == ["cena", "cena2"]
    assert "amigos" in results[0].matched
    # La de invierno gana si hablo de restaurante en diciembre
    winter = recommend("restaurante", outfits, {}, today)
    assert winter[0].outfit.id == "cena2" and "Es de invierno" in winter[0].reasons
    # Si me lo puse ayer, se penaliza
    outfits[1].last_worn = "2026-12-09"
    again = recommend("cenar con amigos", outfits, {}, today)
    assert any("menos de una semana" in r for r in again[0].reasons) or again[0].outfit.id != "cena"
    assert recommend("boda", outfits, {}, today)[0].outfit.id == "boda"


def test_info_validation():
    with pytest.raises(InvalidOutfit):
        OutfitInfo.from_dict({"description": " "})
    info = OutfitInfo.from_dict({"description": "Para la ofi", "occasion": "nope", "seasons": ["verano", "x"]})
    assert info.occasion is None and info.seasons == ("verano",)


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(), provider=FakeWeather(), product_reader=FakeProductReader(),
                     wardrobe_repo=SqliteWardrobeRepository(":memory:"), photo_storage=LocalPhotoStorage(tmp_path),
                     profile_repo=SqliteProfileRepository(":memory:"), outfit_repo=SqliteOutfitRepository(":memory:"))
    return TestClient(app)


def post_outfit(c, info, photos=1):
    return c.post("/api/outfits", data={"info": json.dumps(info)},
                  files=[("photos", (f"{i}.jpg", JPEG, "image/jpeg")) for i in range(photos)])


def test_outfit_api_flow(client):
    c = client
    item = c.post("/api/wardrobe/items", data={"details": json.dumps(
        {"name": "Americana azul", "base_type": "blazer", "colors": [{"name": "azul", "palette_id": "azul_marino"}]})}).json()
    res = post_outfit(c, {"description": "Look para la oficina con americana", "occasion": "trabajo",
                          "item_ids": [item["id"], "ajeno"]}, photos=2)
    assert res.status_code == 201, res.text
    o = res.json()
    assert o["item_ids"] == [item["id"]] and len(o["photos"]) == 2
    assert c.get(o["photos"][1]).content == JPEG
    post_outfit(c, {"description": "Pantalón corto y camiseta para la playa", "seasons": ["verano"]})

    hits = c.post("/api/outfits/search", json={"query": "reunión importante en el trabajo"}).json()["results"]
    assert hits[0]["outfit"]["id"] == o["id"]
    # También encuentra por las prendas enlazadas (nombre y color)
    assert c.post("/api/outfits/search", json={"query": "algo azul marino"}).json()["results"][0]["outfit"]["id"] == o["id"]

    worn = c.post(f"/api/outfits/{o['id']}/worn").json()
    assert worn["worn_count"] == 1 and c.post(f"/api/outfits/{o['id']}/worn").json()["worn_count"] == 1

    upd = c.put(f"/api/outfits/{o['id']}", json={"description": "Oficina, viernes", "occasion": "trabajo"}).json()
    assert upd["description"] == "Oficina, viernes"
    assert c.delete(f"/api/outfits/{o['id']}").status_code == 204
    assert len(c.get("/api/outfits").json()["outfits"]) == 1


def test_outfit_api_validation_and_privacy(client, tmp_path):
    c = client
    assert post_outfit(c, {"description": "Sin foto"}, photos=0).status_code == 422
    assert post_outfit(c, {"description": ""}).status_code == 422
    assert post_outfit(c, {"description": "x" * 10}, photos=5).status_code == 422
    o = post_outfit(c, {"description": "Mi outfit secreto"}).json()
    other = TestClient(c.app)
    assert other.get("/api/outfits").json()["outfits"] == []
    assert other.get(o["photos"][0]).status_code == 404
    assert other.post("/api/outfits/search", json={"query": "secreto"}).json()["results"] == []
