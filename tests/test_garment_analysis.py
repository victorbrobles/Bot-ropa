import pytest

from bot_ropa.domain.garment_analysis import (
    colors_from_text, guess_base_type, guess_brand, guess_protection, nearest_palette,
    parse_composition, thermal_levels,
)


def shares(comp):
    return [(f.fiber, f.percent) for f in comp.main]


@pytest.mark.parametrize("text, expected", [
    ("95% COTTON 5% ELASTANE\n95% ALGODÓN 5% ELASTANO\n95% COTON 5% ÉLASTHANNE",
     [("algodón", 95), ("elastano", 5)]),
    ("ALGODÓN 100%\nCOTTON 100%", [("algodón", 100)]),
    ("100%\nALGODON", [("algodón", 100)]),  # el OCR parte la línea
    ("80% CO 20% PES", [("algodón", 80), ("poliéster", 20)]),  # códigos textiles
    ("52% lana merino 48% poliamida", [("lana merino", 52), ("poliamida", 48)]),
    ("Composición: 60% algodón, 40% poliéster reciclado. Lavar a 30º",
     [("algodón", 60), ("poliéster reciclado", 40)]),
    ("70,5 % viscosa 29,5 % lino", [("viscosa", 70.5), ("lino", 29.5)]),
])
def test_composition_formats(text, expected):
    comp = parse_composition(text)
    assert comp.complete
    assert shares(comp) == expected


def test_composition_sections():
    comp = parse_composition("EXTERIOR 100% POLIAMIDA\nFORRO / LINING 100% POLIÉSTER\n"
                             "RELLENO / FILLING 90% PLUMÓN 10% PLUMA")
    assert shares(comp) == [("poliamida", 100)]
    assert "Relleno: 90 % plumón, 10 % pluma" in comp.notes()
    assert "Forro: 100 % poliéster" in comp.notes()


def test_incomplete_composition_is_flagged():
    comp = parse_composition("60% algodón ... (texto ilegible)")
    assert not comp.complete and shares(comp) == [("algodón", 60)]
    assert not parse_composition("Lavar a máquina 30º").main


def test_brand_skips_sizes_and_origin():
    assert guess_brand(["MADE IN PORTUGAL", "M", "Talla 42", "RN 12345", "Levi's"]) == "Levi's"
    assert guess_brand(["%%$#@", "XL"]) is None


@pytest.mark.parametrize("text, expected", [
    ("Parka acolchada con capucha", "parka"),
    ("Cazadora vaquera oversize", "cazadora_vaquera"),
    ("Slim fit jeans", "vaqueros"),
    ("Jersey de punto de cuello alto", "jersey_cuello_alto"),
    ("Hoodie básica", "sudadera"),
    ("Camisa Oxford regular fit", "camisa_oxford"),
    ("Zapatillas de running", "running"),
    ("Vestido midi de cóctel", "vestido_coctel"),
    ("Pantalón chino", "chinos"),
    ("Algo indescriptible", None),
])
def test_guess_base_type(text, expected):
    assert guess_base_type(text) == expected


def test_colors_and_protection():
    assert nearest_palette("#2f5d43") == "verde"
    assert nearest_palette("#0b1a3a") == "azul_marino"
    assert colors_from_text("Azul marino y blanco") == ["azul_marino", "blanco"]
    assert colors_from_text("Parka negra con detalles blancos") == ["negro", "blanco"]
    assert guess_protection("Chaqueta impermeable GORE-TEX") == (True, False)


def test_warm_fibers_extend_levels():
    wool = parse_composition("100% lana")
    linen = parse_composition("100% lino")
    assert max(thermal_levels("jersey_fino", wool)) == 5
    assert min(thermal_levels("camisa_oxford", linen)) == 0
