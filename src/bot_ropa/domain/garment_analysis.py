"""Análisis gratuito de prendas: reglas sobre texto y colores.

Las entradas vienen de procesos sin coste:
- texto de las etiquetas leído con OCR en el navegador del usuario,
- colores dominantes calculados en el navegador a partir de la foto,
- datos de la ficha del producto (si el usuario pega un enlace),
- la descripción que escriba el usuario.

Aquí no hay red ni IA: solo reglas deterministas y fáciles de probar.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field

from .catalog import CATALOG
from .options import COLORS

BASE_TYPES = {g.id: g for g in CATALOG}


def normalize(text: str) -> str:
    """Minúsculas y sin acentos, para comparar."""
    text = unicodedata.normalize("NFKD", text or "")
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


# =============================================================== composición
# Sinónimos (es, en, fr, it, pt, de) y códigos textiles europeos -> nombre en español.
_FIBERS: list[tuple[str, tuple[str, ...]]] = [
    ("lana merino", ("lana merino", "merino wool", "merino", "laine merinos", "merinowolle")),
    ("algodón orgánico", ("algodon organico", "organic cotton", "coton biologique", "coton bio", "cotone biologico")),
    ("algodón", ("algodon", "cotton", "coton", "cotone", "baumwolle", "algodao", "co", "cot")),
    ("poliéster reciclado", ("poliester reciclado", "recycled polyester", "polyester recycle", "poliestere riciclato")),
    ("poliéster", ("poliester", "polyester", "poliestere", "pes", "pl")),
    ("elastano", ("elastano", "elastane", "elasthan", "spandex", "lycra", "elastan", "ea", "el")),
    ("cachemira", ("cachemira", "cashmere", "cachemire", "kaschmir", "caxemira", "wp")),
    ("lana", ("lana", "wool", "laine", "wolle", "la", "wo")),
    ("lino", ("lino", "linen", "lin", "leinen", "linho", "li")),
    ("lyocell", ("lyocell", "tencel", "ly", "cly")),
    ("modal", ("modal", "md", "cmd")),
    ("viscosa", ("viscosa", "viscose", "rayon", "viskose", "vi", "cv")),
    ("poliamida", ("poliamida", "polyamide", "poliammide", "polyamid", "nailon", "nylon", "pa")),
    ("acrílico", ("acrilico", "acrylic", "acrylique", "acrilica", "polyacryl", "pan", "pc")),
    ("seda", ("seda", "silk", "soie", "seta", "seide", "se")),
    ("cuero", ("cuero", "leather", "cuir", "pelle", "leder", "piel")),
    ("plumón", ("plumon", "down", "duvet", "piumino", "daunen", "penugem")),
    ("pluma", ("pluma", "plumas", "feather", "feathers", "plume", "plumes", "piuma", "federn")),
    ("polipropileno", ("polipropileno", "polypropylene", "pp")),
    ("alpaca", ("alpaca", "alpaga")),
    ("mohair", ("mohair", "mohaire")),
    ("angora", ("angora",)),
    ("cáñamo", ("canamo", "hemp", "chanvre", "canapa", "hanf")),
    ("elastomultiéster", ("elastomultiester", "elastomultiestere", "elastomultiester")),
]
_FIBER_LOOKUP: dict[str, str] = {}
for _name, _words in _FIBERS:
    for _w in _words:
        _FIBER_LOOKUP.setdefault(_w, _name)
_LONGEST = max(len(w.split()) for w in _FIBER_LOOKUP)

# Palabras que empiezan una sección distinta del tejido principal.
_SECTIONS = {
    "forro": "Forro", "lining": "Forro", "doublure": "Forro", "fodera": "Forro", "futter": "Forro",
    "relleno": "Relleno", "filling": "Relleno", "padding": "Relleno", "rembourrage": "Relleno",
    "imbottitura": "Relleno", "fullung": "Relleno", "wadding": "Relleno",
    "bolsillos": "Bolsillos", "pocketing": "Bolsillos", "pockets": "Bolsillos", "poches": "Bolsillos",
    "capucha": "Capucha", "hood": "Capucha", "puños": "Puños", "punos": "Puños", "ribbing": "Puños",
    "aplicacion": "Aplicaciones", "trim": "Aplicaciones",
}
_WORD = re.compile(r"[a-z]+")
_PERCENT = re.compile(r"(\d{1,3}(?:[.,]\d{1,2})?)\s*%")


@dataclass(frozen=True)
class FiberShare:
    fiber: str
    percent: float


@dataclass
class Composition:
    main: list[FiberShare] = field(default_factory=list)  # tejido principal
    others: dict[str, list[FiberShare]] = field(default_factory=dict)  # forro, relleno...

    @property
    def complete(self) -> bool:
        return bool(self.main) and abs(sum(f.percent for f in self.main) - 100) <= 1

    def notes(self) -> str | None:
        parts = [f"{name}: " + ", ".join(f"{_fmt(f.percent)} % {f.fiber}" for f in shares)
                 for name, shares in self.others.items()]
        return "; ".join(parts) or None


def _fmt(n: float) -> str:
    return str(int(n)) if n == int(n) else f"{n:.1f}"


def _fiber_at(words: list[str], i: int) -> tuple[str | None, int]:
    """Fibra que empieza en words[i] (prueba primero las de varias palabras)."""
    for size in range(_LONGEST, 0, -1):
        chunk = " ".join(words[i:i + size])
        if len(words[i:i + size]) == size and chunk in _FIBER_LOOKUP:
            return _FIBER_LOOKUP[chunk], size
    return None, 1


def parse_composition(text: str) -> Composition:
    """Extrae la composición de una etiqueta textil (OCR) o de una ficha de producto.

    Las etiquetas suelen repetir la composición en varios idiomas
    ("100% COTTON / 100% ALGODÓN / 100% COTON"): nos quedamos con el primer
    grupo que suma 100 % y lo demás se descarta o se asigna a forro/relleno.
    """
    tokens: list[tuple[str, object]] = []  # ("pct", float) | ("fiber", str) | ("section", str)
    for line in normalize(text).replace("|", "\n").splitlines():
        pos = 0
        for m in _PERCENT.finditer(line):
            tokens.extend(_word_tokens(line[pos:m.start()]))
            tokens.append(("pct", float(m.group(1).replace(",", "."))))
            pos = m.end()
        tokens.extend(_word_tokens(line[pos:]))

    # Emparejado secuencial: cada porcentaje con la fibra contigua, en el orden en
    # que aparezcan ("95% algodón" o "algodón 95%"), aunque el OCR parta la línea.
    pairs: list[tuple[str | None, FiberShare]] = []
    section: str | None = None
    pending: tuple[str, object] | None = None
    for kind, value in tokens:
        if kind == "section":
            section, pending = value, None
        elif kind == "pct":
            if pending and pending[0] == "fiber":
                if 0 < value <= 100:
                    pairs.append((section, FiberShare(pending[1], value)))
                pending = None
            else:
                pending = (kind, value)
        elif kind == "fiber":
            if pending and pending[0] == "pct":
                if 0 < pending[1] <= 100:
                    pairs.append((section, FiberShare(value, pending[1])))
                pending = None
            else:
                pending = (kind, value)

    comp = Composition()
    group: list[FiberShare] = []
    group_section: str | None = None
    for sec, share in pairs:
        if sec != group_section and group:
            group = []
        group_section = sec
        group.append(share)
        total = sum(s.percent for s in group)
        if abs(total - 100) <= 1:
            merged = _merge(group)
            if sec is None and not comp.main:
                comp.main = merged
            elif sec and sec not in comp.others:
                comp.others[sec] = merged
            group = []
        elif total > 101:
            group = [share] if abs(share.percent - 100) > 1 else []
            if abs(share.percent - 100) <= 1 and sec is None and not comp.main:
                comp.main = [share]
    if not comp.main:
        # Sin un grupo completo: devolvemos lo leído (sin repetir fibras) para que el usuario lo revise.
        seen = {}
        for sec, share in pairs:
            if sec is None and share.fiber not in seen:
                seen[share.fiber] = share
        comp.main = list(seen.values())
    return comp


def _word_tokens(chunk: str) -> list[tuple[str, object]]:
    words = _WORD.findall(chunk)
    out: list[tuple[str, object]] = []
    i = 0
    while i < len(words):
        if words[i] in _SECTIONS:
            out.append(("section", _SECTIONS[words[i]]))
            i += 1
            continue
        fiber, size = _fiber_at(words, i)
        if fiber:
            out.append(("fiber", fiber))
        i += size
    return out


def _merge(shares: list[FiberShare]) -> list[FiberShare]:
    out: dict[str, float] = {}
    for s in shares:
        out[s.fiber] = out.get(s.fiber, 0) + s.percent
    return [FiberShare(f, p) for f, p in sorted(out.items(), key=lambda kv: -kv[1])]


# ==================================================================== marca
_NOT_BRAND = re.compile(
    r"made in|hecho en|fabricado|talla|size|taille|\brn\b|\bca\b|lavar|wash|%|www\.|http|\d{3,}", re.I)
_SIZE = re.compile(r"(xxs|xs|s|m|l|xl|xxl|xxxl|\d{1,2}|eur?|usa?|mex|uk|[a-z]\d*)", re.I)


def guess_brand(lines: list[str]) -> str | None:
    """Elige la marca entre las líneas de la etiqueta (ordenadas de más a menos destacada)."""
    for line in lines:
        text = " ".join(line.split()).strip(" .,:;-_*·'\"")
        letters = sum(c.isalpha() for c in text)
        if letters < 2 or len(text) > 30 or _NOT_BRAND.search(text) or _SIZE.fullmatch(text):
            continue
        if letters / max(len(text.replace(" ", "")), 1) < 0.7:
            continue  # demasiados símbolos: probablemente ruido del OCR
        return text
    return None


# ================================================================ tipo de prenda
# Del más específico al más general.
_TYPE_RULES: list[tuple[str, str]] = [
    (r"cazadora vaquera|chaqueta vaquera|denim jacket|jean jacket|trucker", "cazadora_vaquera"),
    (r"botas? de agua|rain ?boots?|wellington", "botas_agua"),
    (r"zapatillas? (de )?(running|correr)|running shoes?", "running"),
    (r"trail", "trail"),
    (r"pantalon(es)? cortos? deportivos?|running shorts?", "corto_deporte"),
    (r"camiseta (tecnica|deportiva)|running (t-?shirt|top)|sports? (t-?shirt|top)", "camiseta_tecnica"),
    (r"termica|thermal|base ?layer", "termica"),
    (r"(vestido|dress)\b.*\b(largo|gala|maxi)|gown|evening dress", "vestido_gala"),
    (r"vestido de punto|knit(ted)? dress|sweater dress", "vestido_manga_larga"),
    (r"(vestido|dress)\b.*\b(coctel|cocktail|fiesta|party)|(coctel|cocktail|party) dress", "vestido_coctel"),
    (r"vestido|dress\b", "vestido_verano"),
    (r"\bmono\b|jumpsuit|playsuit", "mono"),
    (r"falda de punto|knit(ted)? skirt", "falda_punto"),
    (r"falda|skirt|jupe", "falda_midi"),
    (r"americana de traje|suit jacket", "americana_traje"),
    (r"pantalon de traje|suit trousers|suit pants", "pantalon_traje"),
    (r"blazer|americana", "blazer"),
    (r"plumifero|plumas\b|puffer|down jacket|doudoune|anorak acolchado", "plumifero"),
    (r"parka", "parka"),
    (r"gabardina|trench", "gabardina"),
    (r"chubasquero|rain ?jacket|raincoat|impermeable", "chubasquero"),
    (r"cortavientos|windbreaker|wind ?jacket", "cortavientos"),
    (r"softshell|chaqueta tecnica|hardshell|shell jacket", "softshell"),
    (r"chaleco|gilet|vest\b", "chaleco_acolchado"),
    (r"cazadora|biker|bomber|leather jacket|chaqueta de cuero|chaqueta de piel", "cazadora_cuero"),
    (r"abrigo largo|overcoat", "abrigo_vestir"),
    (r"abrigo|coat|manteau", "abrigo_pano"),
    (r"acolchad|quilted|padded", "acolchada_ligera"),
    (r"forro polar|polar|fleece", "forro_polar"),
    (r"sudadera|hoodie|sweatshirt|sweat\b|capucha", "sudadera"),
    (r"cardigan|chaqueta de punto", "cardigan"),
    (r"cuello alto|turtleneck|roll ?neck|mock neck", "jersey_cuello_alto"),
    (r"jersey (grueso|de lana)|chunky|cable knit|ochos", "jersey_lana"),
    (r"jersey|sweater|pullover|jumper|punto|knit", "jersey_fino"),
    (r"camisa de vestir|dress shirt|formal shirt", "camisa_vestir"),
    (r"camisa de lino|linen shirt", "camisa_lino"),
    (r"camisa estampada|printed shirt|hawaiian", "camisa_estampada"),
    (r"blusa|blouse", "blusa"),
    (r"camisa|shirt\b|overshirt|oxford", "camisa_oxford"),
    (r"\bpolo\b", "polo"),
    (r"tirantes|tank ?top|camiseta sin mangas|sleeveless", "tirantes"),
    (r"top\b|crop", "top_fiesta"),
    (r"manga larga|long ?sleeve", "manga_larga"),
    (r"camiseta estampada|graphic t|printed t", "camiseta_estampada"),
    (r"camiseta|t-?shirt|\btee\b", "camiseta"),
    (r"vaquero|jeans?\b|denim", "vaqueros"),
    (r"chino", "chinos"),
    (r"bermuda", "bermudas"),
    (r"pantalon(es)? cortos?|shorts?\b", "pantalon_corto"),
    (r"jogger|chandal|sweatpants|track ?pants", "jogger"),
    (r"mallas|leggings|tights", "mallas"),
    (r"pana|corduroy", "pana"),
    (r"pantalon de lino|linen trousers|linen pants", "pantalon_lino"),
    (r"pantalon|trousers|pants", "pantalon_vestir"),
    (r"sandalia|sandal", "sandalias"),
    (r"tacon|heels?|stiletto|salones", "tacones"),
    (r"mocasin|loafer", "mocasines"),
    (r"botin|chelsea|ankle boots?|botas?|boots?", "botines"),
    (r"lona|canvas|converse", "lona"),
    (r"zapatillas?|sneakers?|trainers?|deportivas", "zapatillas_urbanas"),
    (r"zapatos?|oxford shoes?|derby|brogue", "zapatos_vestir"),
]


def guess_base_type(*texts: str | None) -> str | None:
    text = normalize(" ".join(t for t in texts if t))
    if not text.strip():
        return None
    for pattern, base_type in _TYPE_RULES:
        if base_type in BASE_TYPES and re.search(pattern, text):
            return base_type
    return None


def guess_protection(*texts: str | None) -> tuple[bool, bool]:
    text = normalize(" ".join(t for t in texts if t))
    waterproof = bool(re.search(r"impermeable|waterproof|gore-?tex|resistente al agua|water ?resistant|encerad|waxed", text))
    windproof = bool(re.search(r"cortavientos|windproof|windstopper|wind ?resistant", text))
    return waterproof, windproof


# ==================================================================== colores
def _hex_to_rgb(hex_: str) -> tuple[int, int, int]:
    h = hex_.lstrip("#")
    return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)


def _lab(rgb: tuple[int, int, int]) -> tuple[float, float, float]:
    def lin(c):
        c /= 255
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(c) for c in rgb)
    x = (0.4124 * r + 0.3576 * g + 0.1805 * b) / 0.95047
    y = 0.2126 * r + 0.7152 * g + 0.0722 * b
    z = (0.0193 * r + 0.1192 * g + 0.9505 * b) / 1.08883

    def f(t):
        return t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


_PALETTE_LAB = {cid: _lab(_hex_to_rgb(c.hex)) for cid, c in COLORS.items()}
HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def nearest_palette(hex_: str) -> str:
    """Color de nuestra paleta más parecido a la vista (distancia en espacio Lab)."""
    lab = _lab(_hex_to_rgb(hex_))
    return min(_PALETTE_LAB, key=lambda cid: sum((a - b) ** 2 for a, b in zip(lab, _PALETTE_LAB[cid])))


_COLOR_WORDS: list[tuple[str, str]] = [
    (r"azul marino|navy|marine", "azul_marino"), (r"celeste|azul claro|light blue|sky blue|bleu ciel", "celeste"),
    (r"azul|blue|bleu|blu\b", "azul"), (r"burdeos|granate|burgundy|bordeaux|maroon|wine", "burdeos"),
    (r"roj[oa]s?|red\b|rouge", "rojo"), (r"rosa|pink|rose", "rosa"), (r"amarill[oa]s?|mostaza|yellow|jaune|mustard", "amarillo"),
    (r"naranja|orange|teja|terracota", "naranja"), (r"morad[oa]s?|lila|violeta|purple|violet|lilac", "morado"),
    (r"verde|green|vert|khaki|caqui|oliva|olive", "verde"), (r"beige|camel|arena|sand|crudo|ecru|cream|crema|hueso|stone", "beige"),
    (r"marron(es)?|brown|chocolate|tabaco|cognac|tan\b|brun", "marron"), (r"gris(es)?|grey|gray|antracita|charcoal", "gris"),
    (r"negr[oa]s?|black|noir|nero", "negro"), (r"blanc[oa]s?|white|blanc|bianco", "blanco"),
]


def colors_from_text(text: str | None) -> list[str]:
    t = normalize(text or "")
    found = []
    for pattern, cid in _COLOR_WORDS:
        if re.search(pattern, t) and cid not in found:
            found.append(cid)
            t = re.sub(pattern, " ", t)  # que "azul marino" no cuente también como "azul"
    return found


# ============================================================ niveles térmicos
_WARM = {"lana", "lana merino", "cachemira", "plumón", "pluma", "alpaca", "mohair", "angora"}
_COOL = {"lino", "cáñamo", "seda"}


def thermal_levels(base_type: str, comp: Composition) -> list[int]:
    levels = set(BASE_TYPES[base_type].levels)
    shares = comp.main + [s for group in comp.others.values() for s in group]
    warm = sum(s.percent for s in shares if s.fiber in _WARM)
    cool = sum(s.percent for s in comp.main if s.fiber in _COOL)
    if warm >= 50 and max(levels) < 5:
        levels.add(max(levels) + 1)  # abriga más de lo normal para su tipo
    if cool >= 50 and min(levels) > 0:
        levels.add(min(levels) - 1)  # más fresca de lo normal
    return sorted(levels)
