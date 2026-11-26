import pytest

from bot_ropa.domain.explore import (
    BasePiece, InvalidProfile, StyleProfile, complete_outfit, discover_brands, idea_feed,
    owned_brands, pick_color, style_affinity, wardrobe_gaps,
)
from bot_ropa.domain.options import COLORS
from bot_ropa.domain.style_catalog import BRANDS, ICONS, STYLES
from bot_ropa.domain.wardrobe import GarmentDetails, WardrobeItem
from bot_ropa.domain.catalog import CATALOG

GARMENT_IDS = {g.id for g in CATALOG}


def item(id, base_type, color, brand=None, name=None):
    d = GarmentDetails.from_dict({"name": name or base_type, "base_type": base_type, "brand": brand,
                                  "colors": [{"name": color, "palette_id": color}]})
    return WardrobeItem(id=id, owner_id="u", details=d)


def test_catalog_is_consistent():
    for s in STYLES.values():
        assert all(t in GARMENT_IDS for ts in s.slots.values() for t in ts), s.id
        assert all(t in GARMENT_IDS for t, _ in s.essentials), s.id
        assert all(c in COLORS for c in s.palette)
        assert all(c is None or c in COLORS for _, c in s.essentials)
    for b in BRANDS.values():
        assert all(st in STYLES for st in b.styles), b.id
    for i in ICONS.values():
        assert all(st in STYLES for st in i.styles), i.id


def test_profile_validation_drops_unknown_and_dedupes():
    p = StyleProfile.from_dict({"styles": ["minimalista", "inventado", "minimalista"], "brands": ["zara", "x"],
                                "custom_brands": [" Mi Marca ", "mi marca", ""], "budget": [1, 7],
                                "custom_icons": [{"name": "Mi prima", "styles": ["casual", "nope"]}]})
    assert p.styles == ("minimalista",) and p.brands == ("zara",)
    assert p.custom_brands == ("Mi Marca",) and p.budget == (1,)
    assert p.custom_icons[0].styles == ("casual",)
    assert StyleProfile.from_dict(p.to_dict()) == p
    with pytest.raises(InvalidProfile):
        StyleProfile.from_dict("hola")


def test_affinity_combines_styles_icons_brands_and_wardrobe():
    p = StyleProfile(styles=("minimalista",), icons=("asap_rocky",), brands=("carhartt",))
    ranking = dict(style_affinity(p, [item("1", "sudadera", "negro", brand="Carhartt WIP")]))
    assert ranking["minimalista"] == max(ranking.values())
    assert ranking["streetwear"] > ranking.get("romantico", 0)
    assert style_affinity(StyleProfile(), [])[0][0] == "casual"  # sin datos: algo razonable


def test_owned_brands_matches_names_loosely():
    assert [b.id for b in owned_brands([item("1", "camiseta", "blanco", brand="levis")])] == ["levis"]


def test_pick_color_balances_accents_with_neutrals():
    style = STYLES["minimalista"]
    assert COLORS[pick_color(["rojo"], style, "parte_inferior", set())].neutral
    assert pick_color([], STYLES["romantico"], "parte_superior", set()) == "rosa"


def test_complete_outfit_fills_missing_slots_for_winter_and_reuses_wardrobe():
    wardrobe = [item("j", "vaqueros", "azul_marino"), item("t", "camiseta", "verde", name="Camiseta verde"),
                item("c", "abrigo_pano", "gris", name="Abrigo gris")]
    plan = complete_outfit([BasePiece("camiseta", "verde", "t", "Camiseta verde")], StyleProfile(), wardrobe,
                           STYLES["minimalista"], month=1)
    slots = [s.slot for s in plan.suggestions]
    assert slots == ["parte_inferior", "capa_intermedia", "abrigo", "calzado"]
    bottom = plan.suggestions[0]
    assert bottom.owned and bottom.owned[0].id == "j"
    for s in plan.suggestions:
        if not s.use_owned:
            assert s.links and any("google" in l["url"] for l in s.links)
    # Con un color protagonista, el resto en neutros
    assert all(COLORS[s.color].neutral for s in plan.suggestions if s.color != "azul")


def test_summer_outfit_skips_coat_and_dress_skips_top_and_bottom():
    plan = complete_outfit([BasePiece("vestido_verano", "rosa")], StyleProfile(fit="femenino"), [],
                           STYLES["romantico"], month=7)
    assert [s.slot for s in plan.suggestions] == ["calzado"]


def test_masculine_profile_gets_no_feminine_suggestions():
    plan = complete_outfit([BasePiece("camisa_oxford", "blanco")], StyleProfile(fit="masculino"), [],
                           STYLES["romantico"], month=4)
    from bot_ropa.domain.explore import GARMENTS
    assert all(GARMENTS[s.base_type].fit != "femenino" for s in plan.suggestions)


def test_idea_feed_builds_looks_around_wardrobe_items():
    wardrobe = [item("s", "sudadera", "negro", name="Sudadera negra")]
    ideas = idea_feed(StyleProfile(styles=("streetwear",)), wardrobe, month=11)
    assert ideas[0].anchor.id == "s"
    assert "streetwear" in ideas[0].reason.lower()
    assert idea_feed(StyleProfile(styles=("minimalista",)), [], month=6)  # sin armario también hay ideas


def test_discover_brands_excludes_known_and_respects_budget_and_sustainability():
    p = StyleProfile(styles=("gorpcore",), brands=("north_face",), budget=(1, 2), sustainable=True)
    picks = discover_brands(p, [item("1", "forro_polar", "verde", brand="Columbia")])
    ids = [x.brand.id for x in picks]
    assert "north_face" not in ids and "columbia" not in ids
    assert ids[0] in {"ecoalf", "decathlon"}
    assert all(BRANDS[i].price in (1, 2) for i in ids[:3])
    assert any("sostenible" in r for x in picks for r in x.reasons)


def test_gaps_mark_owned_and_missing_essentials():
    gaps = wardrobe_gaps(StyleProfile(styles=("minimalista",)), [item("1", "camiseta", "blanco")], styles=1)
    owned = [g for g in gaps if g.owned]
    assert len(owned) == 1 and owned[0].base_type == "camiseta"
    assert all(g.links for g in gaps if not g.owned)


def test_no_knit_under_a_knit_and_sensible_coat_and_shoe_colors():
    plan = complete_outfit([BasePiece("jersey_fino", "verde")], StyleProfile(), [], STYLES["minimalista"], month=11)
    by_slot = {s.slot: s for s in plan.suggestions}
    assert by_slot["parte_superior"].base_type != "jersey_cuello_alto"
    assert by_slot["abrigo"].color in ("beige", "negro", "azul_marino", "gris", "marron")
    assert by_slot["calzado"].color in ("blanco", "negro", "marron")
