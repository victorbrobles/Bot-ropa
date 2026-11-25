"""Une todas las pistas (etiquetas, foto, ficha web, descripción) en un borrador de prenda.

Cada dato indica de dónde sale, para que el usuario sepa qué es exacto
(leído en la etiqueta o en la ficha oficial) y qué es una suposición.
"""

from __future__ import annotations

from .catalog import CATALOG
from .garment_analysis import (
    Composition, colors_from_text, guess_base_type, guess_brand, guess_protection,
    nearest_palette, parse_composition, thermal_levels,
)
from .options import COLORS
from .wardrobe import AnalyzeRequest, Identification, ProductInfo

BASE_TYPES = {g.id: g for g in CATALOG}
SOURCE_LABELS = {"etiqueta": "la etiqueta", "web": "la ficha del producto",
                 "foto": "la foto", "descripcion": "tu descripción"}


def identify(req: AnalyzeRequest, product: ProductInfo | None = None,
             product_error: str | None = None) -> Identification:
    prov: dict[str, str] = {}
    draft: dict = {"product_url": product.url if product else req.product_url}

    # --- tipo de prenda
    base_type = None
    if product:
        base_type = guess_base_type(product.name, product.description)
        if base_type:
            prov["base_type"] = "web"
    if not base_type and req.description:
        base_type = guess_base_type(req.description)
        if base_type:
            prov["base_type"] = "descripcion"
    draft["base_type"] = base_type

    # --- marca, modelo y referencia
    if product and product.brand:
        draft["brand"], prov["brand"] = product.brand, "web"
    elif (brand := guess_brand(list(req.brand_lines))):
        draft["brand"], prov["brand"] = brand, "etiqueta"
    if product and product.name:
        draft["model"], prov["model"] = product.name, "web"
    if product and product.reference:
        draft["reference"], prov["reference"] = product.reference, "web"

    # --- composición: etiqueta > ficha > descripción
    comp, comp_source = Composition(), None
    candidates = [("etiqueta", req.label_text)]
    if product:
        candidates.append(("web", " \n ".join(filter(None, [product.material, product.description, product.page_text]))))
    candidates.append(("descripcion", req.description))
    for source, text in candidates:
        if not text:
            continue
        parsed = parse_composition(text)
        if parsed.complete:
            comp, comp_source = parsed, source
            break
        if parsed.main and not comp.main:
            comp, comp_source = parsed, source  # parcial: mejor que nada, pero seguimos buscando
    draft["materials"] = [{"fiber": f.fiber, "percent": f.percent if comp.complete else None}
                          for f in comp.main]
    if comp.main:
        prov["materials"] = comp_source
    if comp.notes():
        draft["notes"] = comp.notes()

    # --- colores: ficha > descripción > foto
    color_ids, color_source = [], None
    for source, text in (("web", product.color if product else None), ("descripcion", req.description)):
        color_ids = colors_from_text(text)
        if color_ids:
            color_source = source
            break
    if color_ids:
        draft["colors"] = [{"name": COLORS[c].label.lower(), "palette_id": c, "hex": COLORS[c].hex} for c in color_ids[:3]]
    elif req.photo_colors:
        colors = []
        for pc in sorted(req.photo_colors, key=lambda c: -c.share)[:3]:
            cid = nearest_palette(pc.hex)
            if cid not in [c["palette_id"] for c in colors]:
                colors.append({"name": COLORS[cid].label.lower(), "palette_id": cid, "hex": pc.hex.lower()})
        draft["colors"], color_source = colors, "foto"
    if color_source:
        prov["colors"] = color_source

    # --- protección y abrigo
    texts = [req.description, req.label_text] + ([product.name, product.description, product.material] if product else [])
    waterproof, windproof = guess_protection(*texts)
    if base_type:
        base = BASE_TYPES[base_type]
        draft["waterproof"] = waterproof or base.waterproof
        draft["windproof"] = windproof or base.windproof
        draft["levels"] = thermal_levels(base_type, comp)
        draft["name"] = product.name if product and product.name else _default_name(base_type, draft)
    else:
        draft["waterproof"], draft["windproof"] = waterproof, windproof
        draft["name"] = product.name if product and product.name else None

    # --- qué falta y estado
    unconfirmed = []
    if not base_type:
        unconfirmed.append("tipo")
    if "brand" not in prov:
        unconfirmed.append("marca")
    if "model" not in prov:
        unconfirmed.append("modelo")
    if not comp.complete:
        unconfirmed.append("composicion")
    if not draft.get("colors"):
        unconfirmed.append("colores")

    useful = len(prov)
    if base_type and "brand" in prov and comp.complete:
        status = "identificada"
    elif useful:
        status = "parcial"
    else:
        status = "desconocida"

    return Identification(
        status=status,
        candidate=draft,
        message=_message(draft, prov, comp, unconfirmed, product_error),
        provenance=prov,
        unconfirmed=tuple(unconfirmed),
        sources=(product.url,) if product else (),
    )


def _default_name(base_type: str, draft: dict) -> str:
    name = BASE_TYPES[base_type].name
    if draft.get("colors"):
        name += f" {draft['colors'][0]['name']}"
    return name


def _message(draft, prov, comp, unconfirmed, product_error) -> str:
    parts = []
    if product_error:
        parts.append(product_error)
    if prov.get("materials") and comp.complete:
        mats = ", ".join(f"{m['percent']:g} % {m['fiber']}" for m in draft["materials"])
        parts.append(f"Composición leída en {SOURCE_LABELS[prov['materials']]}: {mats}.")
    elif draft.get("materials"):
        parts.append("He visto algunos materiales, pero no la composición completa: revisa los porcentajes.")
    if prov.get("brand"):
        parts.append(f"Marca leída en {SOURCE_LABELS[prov['brand']]}: {draft['brand']}.")
    if prov.get("colors") == "foto":
        parts.append("Los colores están calculados a partir de la foto.")
    hints = []
    if "composicion" in unconfirmed:
        hints.append("una foto nítida de la etiqueta de composición")
    if "modelo" in unconfirmed:
        hints.append("el enlace del producto")
    if "tipo" in unconfirmed:
        parts.append("Dinos qué tipo de prenda es.")
    if hints:
        parts.append("Para completarla puedes añadir " + " o ".join(hints) + ".")
    return " ".join(parts) or "No hemos podido leer nada de la prenda."
