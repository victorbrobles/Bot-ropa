"""Mi armario: prendas reales del usuario.

Cada prenda guarda lo que sabemos de ella con exactitud (marca, modelo,
referencia, colores, composición) y los atributos que usa el recomendador
(tipo base del catálogo, niveles térmicos, impermeable, ocasiones...).

`GarmentDetails.from_dict` es el ÚNICO punto de entrada de datos externos
(respuesta de la IA o formulario del usuario): limpia y valida todo.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from .catalog import CATALOG, SLOTS
from .options import COLORS, OCCASIONS

BASE_TYPES = {g.id: g for g in CATALOG}
STYLE_TAGS = ("alegre", "atrevido", "deportivo", "tranquilo", "relajado", "comodo",
              "seguro", "elegante", "clasico", "creativo")
FITS = ("unisex", "masculino", "femenino")
PATTERNS = ("liso", "rayas", "cuadros", "estampado", "lunares", "otro")
SOURCES = ("foto", "enlace", "descripcion", "manual")
MAX_TEXT = 200


class InvalidGarment(ValueError):
    pass


def _text(value: Any, limit: int = MAX_TEXT) -> str | None:
    if value is None:
        return None
    text = " ".join(str(value).split())
    return text[:limit] or None


def _url(value: Any) -> str | None:
    text = _text(value, 500)
    if text and text.lower().startswith(("http://", "https://")):
        return text
    return None


@dataclass(frozen=True)
class Material:
    fiber: str  # "algodón", "poliéster reciclado"...
    percent: float | None = None  # None si no se conoce el porcentaje

    @classmethod
    def from_dict(cls, data: Any) -> "Material | None":
        if not isinstance(data, dict):
            return None
        fiber = _text(data.get("fiber"), 60)
        if not fiber:
            return None
        percent = data.get("percent")
        try:
            percent = None if percent in (None, "") else round(float(percent), 1)
        except (TypeError, ValueError):
            percent = None
        if percent is not None and not 0 < percent <= 100:
            percent = None
        return cls(fiber.lower(), percent)


@dataclass(frozen=True)
class GarmentColor:
    name: str  # nombre comercial o descriptivo: "azul marino", "verde salvia"
    palette_id: str  # color más cercano de nuestra paleta (para combinar)
    hex: str | None = None

    @classmethod
    def from_dict(cls, data: Any) -> "GarmentColor | None":
        if not isinstance(data, dict):
            return None
        palette_id = data.get("palette_id")
        if palette_id not in COLORS:
            return None
        name = _text(data.get("name"), 60) or COLORS[palette_id].label
        hex_ = _text(data.get("hex"), 7)
        if hex_ and not (hex_.startswith("#") and len(hex_) == 7
                         and all(c in "0123456789abcdefABCDEF" for c in hex_[1:])):
            hex_ = None
        return cls(name.lower(), palette_id, hex_ or COLORS[palette_id].hex)


@dataclass(frozen=True)
class GarmentDetails:
    name: str
    base_type: str  # id del catálogo genérico al que equivale
    brand: str | None = None
    model: str | None = None
    reference: str | None = None  # referencia / SKU / código de artículo
    colors: tuple[GarmentColor, ...] = ()
    materials: tuple[Material, ...] = ()
    pattern: str = "liso"
    levels: tuple[int, ...] = ()  # niveles térmicos en los que es cómoda (0-5)
    waterproof: bool = False
    windproof: bool = False
    occasions: tuple[str, ...] = ()
    tags: tuple[str, ...] = ()
    fit: str = "unisex"
    product_url: str | None = None
    notes: str | None = None

    @property
    def slot(self) -> str:
        return BASE_TYPES[self.base_type].slot

    @property
    def materials_complete(self) -> bool:
        """True si la composición suma 100 % (la conocemos con exactitud)."""
        total = sum(m.percent or 0 for m in self.materials)
        return bool(self.materials) and all(m.percent for m in self.materials) and abs(total - 100) <= 1

    def to_dict(self) -> dict:
        data = asdict(self)
        data["slot"] = self.slot
        return data

    @classmethod
    def from_dict(cls, data: Any) -> "GarmentDetails":
        if not isinstance(data, dict):
            raise InvalidGarment("Datos de prenda no válidos")
        base_type = data.get("base_type")
        if base_type not in BASE_TYPES:
            raise InvalidGarment("Indica qué tipo de prenda es")
        base = BASE_TYPES[base_type]
        name = _text(data.get("name")) or base.name

        colors = [c for c in map(GarmentColor.from_dict, data.get("colors") or []) if c][:6]
        materials = [m for m in map(Material.from_dict, data.get("materials") or []) if m][:8]
        total = sum(m.percent or 0 for m in materials)
        if total > 101:
            raise InvalidGarment("La composición suma más del 100 %")

        levels = sorted({int(lv) for lv in data.get("levels") or []
                         if isinstance(lv, (int, float)) and 0 <= int(lv) <= 5})
        occasions = [o for o in dict.fromkeys(data.get("occasions") or []) if o in OCCASIONS]
        tags = [t for t in dict.fromkeys(data.get("tags") or []) if t in STYLE_TAGS]
        pattern = data.get("pattern") if data.get("pattern") in PATTERNS else "liso"
        fit = data.get("fit") if data.get("fit") in FITS else base.fit

        return cls(
            name=name,
            base_type=base_type,
            brand=_text(data.get("brand"), 80),
            model=_text(data.get("model"), 120),
            reference=_text(data.get("reference"), 60),
            colors=tuple(colors),
            materials=tuple(materials),
            pattern=pattern,
            # Si no sabemos nada mejor, heredamos lo del tipo base.
            levels=tuple(levels) or tuple(sorted(base.levels)),
            waterproof=bool(data.get("waterproof", base.waterproof)),
            windproof=bool(data.get("windproof", base.windproof)),
            occasions=tuple(occasions) or tuple(sorted(base.occasions)),
            tags=tuple(tags) or tuple(sorted(base.tags)),
            fit=fit,
            product_url=_url(data.get("product_url")),
            notes=_text(data.get("notes"), 500),
        )


@dataclass
class WardrobeItem:
    id: str
    owner_id: str
    details: GarmentDetails
    photos: list[str] = field(default_factory=list)  # rutas internas de almacenamiento
    source: str = "foto"
    confidence: float | None = None
    created_at: str = ""
    updated_at: str = ""


@dataclass(frozen=True)
class Photo:
    data: bytes
    media_type: str  # image/jpeg | image/png | image/webp


# ------------------------------------------------------------- identificación
@dataclass(frozen=True)
class ProductInfo:
    """Datos leídos de la ficha de un producto en la web de la tienda."""
    url: str
    name: str | None = None
    brand: str | None = None
    reference: str | None = None
    color: str | None = None
    material: str | None = None
    description: str | None = None
    page_text: str | None = None  # texto visible (para buscar la composición)


@dataclass(frozen=True)
class PhotoColor:
    hex: str  # #rrggbb
    share: float  # proporción de la prenda (0-1)


@dataclass(frozen=True)
class AnalyzeRequest:
    """Todo lo que sabemos de la prenda. Se calcula gratis en el navegador."""
    label_text: str | None = None  # OCR de la etiqueta de composición
    brand_lines: tuple[str, ...] = ()  # OCR de la etiqueta de marca, de más a menos destacado
    photo_colors: tuple[PhotoColor, ...] = ()
    product_url: str | None = None
    description: str | None = None

    def __post_init__(self):
        if not (self.label_text or self.brand_lines or self.photo_colors
                or self.product_url or self.description):
            raise InvalidGarment("Sube una foto, pega un enlace o describe la prenda")


@dataclass(frozen=True)
class Identification:
    status: str  # identificada | parcial | desconocida
    candidate: dict  # borrador de GarmentDetails; base_type puede faltar
    message: str  # explicación para el usuario
    provenance: dict = field(default_factory=dict)  # campo -> etiqueta | foto | web | descripcion | tipo
    unconfirmed: tuple[str, ...] = ()
    sources: tuple[str, ...] = ()

    STATUSES = ("identificada", "parcial", "desconocida")


SLOT_LABELS = SLOTS
