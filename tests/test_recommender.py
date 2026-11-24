import pytest

from bot_ropa.domain.recommender import OutfitPreferences, Recommender
from conftest import summary

rec = Recommender()


def slots(outfit):
    return {i.slot: i.garment.id for i in outfit.items}


def acc(outfit):
    return {a.id for a in outfit.accessories}


def test_hot_sunny_day_is_light_and_needs_sun_protection():
    outfit = rec.recommend(summary([28, 31, 33, 32], uv=8), OutfitPreferences())
    s = slots(outfit)
    assert "abrigo" not in s and "capa_intermedia" not in s
    assert s["parte_inferior"] in {"pantalon_corto", "bermudas"}
    assert {"gafas", "gorra", "agua"} <= acc(outfit)
    assert any("calor" in t.lower() for t in outfit.tips)


def test_cold_rainy_day_needs_waterproof_layers_and_umbrella():
    outfit = rec.recommend(summary([5, 6, 7, 6], prob=90, rain=2, code=63), OutfitPreferences())
    by_slot = {i.slot: i.garment for i in outfit.items}
    assert by_slot["abrigo"].waterproof
    assert by_slot["calzado"].waterproof
    assert "capa_intermedia" in by_slot
    assert {"paraguas", "bufanda"} <= acc(outfit)


def test_strong_wind_with_rain_drops_umbrella():
    outfit = rec.recommend(summary([12, 13], prob=90, rain=3, wind=55, code=63), OutfitPreferences())
    assert "paraguas" not in acc(outfit)
    assert any("capucha" in t for t in outfit.tips)


def test_freezing_adds_hat_and_gloves():
    outfit = rec.recommend(summary([-3, -1, 0]), OutfitPreferences())
    assert {"gorro", "guantes", "bufanda"} <= acc(outfit)
    assert slots(outfit)["abrigo"] in {"plumifero", "parka", "abrigo_pano"}


def test_wide_range_suggests_layers():
    outfit = rec.recommend(summary([9, 14, 21, 23]), OutfitPreferences())
    assert any("capas" in t for t in outfit.tips)


def test_black_tie_uses_suit_and_accent_color_goes_to_tie():
    outfit = rec.recommend(summary([16, 18]), OutfitPreferences(occasion="etiqueta", color="rojo"))
    s = slots(outfit)
    assert s["capa_intermedia"] == "americana_traje"
    assert s["parte_inferior"] == "pantalon_traje"
    assert s["calzado"] in {"zapatos_vestir", "tacones"}
    ties = [a for a in outfit.accessories if a.id == "corbata"]
    assert ties and "rojo" in ties[0].name


def test_feminine_party_outfit_is_a_dress_with_bag():
    outfit = rec.recommend(summary([20, 22]), OutfitPreferences(occasion="fiesta", fit="femenino"))
    s = slots(outfit)
    assert s["pieza_unica"].startswith("vestido") or s["pieza_unica"] == "mono"
    assert "parte_superior" not in s and "parte_inferior" not in s
    assert "bolso" in acc(outfit)


def test_masculine_never_gets_feminine_garments():
    for occ in ("diario", "trabajo", "fiesta", "etiqueta", "deporte"):
        outfit = rec.recommend(summary([10, 20]), OutfitPreferences(occasion=occ, fit="masculino"))
        assert all(i.garment.fit != "femenino" for i in outfit.items)
        assert all(a.fit != "femenino" for i in outfit.items for a in i.alternatives)


def test_sport_dresses_warmer_and_uses_sport_garments():
    outfit = rec.recommend(summary([8, 9]), OutfitPreferences(occasion="deporte"))
    s = slots(outfit)
    assert s["calzado"] in {"running", "trail"}
    assert s["parte_superior"] in {"camiseta_tecnica", "termica_deporte"}
    assert any("6 °C" in t for t in outfit.tips)


def test_user_color_goes_to_main_garment():
    outfit = rec.recommend(summary([19, 21]), OutfitPreferences(color="verde"))
    top = next(i for i in outfit.items if i.slot == "parte_superior")
    assert top.color.id == "verde"


def test_mood_changes_style_and_palette():
    neutral = rec.recommend(summary([19, 21]), OutfitPreferences())
    happy = rec.recommend(summary([19, 21]), OutfitPreferences(mood="feliz"))
    top = next(i for i in happy.items if i.slot == "parte_superior")
    assert top.garment.id == "camiseta_estampada"
    assert top.color.id == "amarillo"
    assert slots(neutral) != slots(happy) or neutral.palette != happy.palette


@pytest.mark.parametrize("occasion", ["diario", "trabajo", "deporte", "fiesta", "etiqueta"])
@pytest.mark.parametrize("fit", ["cualquiera", "masculino", "femenino"])
@pytest.mark.parametrize("temps", [[-5, -2], [4, 7], [10, 12], [15, 17], [20, 22], [30, 35]])
def test_every_combination_gives_a_complete_outfit(occasion, fit, temps):
    outfit = rec.recommend(summary(temps), OutfitPreferences(occasion=occasion, fit=fit))
    s = slots(outfit)
    assert "calzado" in s
    assert "pieza_unica" in s or {"parte_superior", "parte_inferior"} <= set(s)
    assert all(i.color is not None for i in outfit.items)


def test_invalid_preferences_are_rejected():
    with pytest.raises(ValueError):
        OutfitPreferences(occasion="boda_vikinga")
    with pytest.raises(ValueError):
        OutfitPreferences(color="fucsia_neon")
