from bot_ropa.domain.identification import identify
from bot_ropa.domain.wardrobe import AnalyzeRequest, PhotoColor, ProductInfo


def test_photo_only_reads_labels_and_colors_but_asks_for_type():
    r = identify(AnalyzeRequest(
        label_text="95% ALGODÓN 5% ELASTANO", brand_lines=("HECHO EN ESPAÑA", "Marca X"),
        photo_colors=(PhotoColor("#1f2f55", 0.8),)))
    assert r.status == "parcial"
    c = r.candidate
    assert c["base_type"] is None and "tipo" in r.unconfirmed
    assert c["brand"] == "Marca X" and r.provenance["brand"] == "etiqueta"
    assert c["materials"] == [{"fiber": "algodón", "percent": 95}, {"fiber": "elastano", "percent": 5}]
    assert r.provenance["materials"] == "etiqueta"
    assert c["colors"][0]["palette_id"] == "azul_marino" and r.provenance["colors"] == "foto"
    assert "Composición leída en la etiqueta" in r.message


def test_product_page_completes_everything():
    product = ProductInfo(url="https://tienda.example/p/1", name="Parka técnica impermeable Ártica",
                          brand="Marca Y", reference="AR-123", color="Verde oliva",
                          material="Exterior: 100% poliéster. Relleno: 80% plumón 20% pluma")
    r = identify(AnalyzeRequest(product_url=product.url), product)
    assert r.status == "identificada"
    c = r.candidate
    assert c["base_type"] == "parka" and c["waterproof"]
    assert c["model"] == "Parka técnica impermeable Ártica" and c["reference"] == "AR-123"
    assert c["colors"][0]["palette_id"] == "verde"
    assert "Relleno" in c["notes"]
    assert 5 in c["levels"]
    assert r.sources == ("https://tienda.example/p/1",)


def test_label_wins_over_web_for_composition():
    product = ProductInfo(url="https://x.example", name="Jersey", material="100% algodón")
    r = identify(AnalyzeRequest(label_text="70% lana 30% poliamida", product_url="https://x.example"), product)
    assert r.provenance["materials"] == "etiqueta"
    assert r.candidate["materials"][0]["fiber"] == "lana"


def test_description_only_and_product_error():
    r = identify(AnalyzeRequest(description="vaqueros negros de algodón 100%", product_url="https://x.example"),
                 None, "Esa tienda no deja leer su web automáticamente.")
    assert r.candidate["base_type"] == "vaqueros"
    assert r.candidate["colors"][0]["palette_id"] == "negro"
    assert r.message.startswith("Esa tienda no deja")
