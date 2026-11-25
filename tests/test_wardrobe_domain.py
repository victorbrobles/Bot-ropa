import pytest

from bot_ropa.domain.wardrobe import AnalyzeRequest, GarmentDetails, InvalidGarment


def test_from_dict_cleans_and_fills_defaults():
    d = GarmentDetails.from_dict({
        "name": "  Camisa   Oxford  ",
        "base_type": "camisa_oxford",
        "colors": [{"name": "Azul", "palette_id": "azul", "hex": "#123456"},
                   {"name": "x", "palette_id": "fucsia_neon"}],
        "materials": [{"fiber": "Algodón", "percent": "100"}],
        "occasions": ["trabajo", "boda_vikinga"],
        "product_url": "javascript:alert(1)",
    })
    assert d.name == "Camisa Oxford"
    assert [c.palette_id for c in d.colors] == ["azul"]
    assert d.materials[0].fiber == "algodón" and d.materials_complete
    assert d.occasions == ("trabajo",)
    assert d.product_url is None
    assert d.levels  # heredados del tipo base
    assert d.slot == "parte_superior"


def test_unknown_type_and_impossible_composition_are_rejected():
    with pytest.raises(InvalidGarment):
        GarmentDetails.from_dict({"base_type": "nave_espacial"})
    with pytest.raises(InvalidGarment):
        GarmentDetails.from_dict({"base_type": "vaqueros", "materials": [
            {"fiber": "algodón", "percent": 80}, {"fiber": "elastano", "percent": 40}]})


def test_unknown_percentages_mean_incomplete_composition():
    d = GarmentDetails.from_dict({"base_type": "vaqueros", "materials": [{"fiber": "algodón", "percent": None}]})
    assert not d.materials_complete


def test_round_trip():
    d = GarmentDetails.from_dict({"base_type": "parka", "brand": "X", "waterproof": True,
                                  "materials": [{"fiber": "poliéster", "percent": 100}]})
    assert GarmentDetails.from_dict(d.to_dict()) == d


def test_identify_request_needs_something():
    with pytest.raises(InvalidGarment):
        AnalyzeRequest()
