"""Explorar outfits: recomendaciones a partir de tu estilo y tu armario.

Todo son reglas sobre el catálogo de estilos y marcas (gratis y explicable):
cada recomendación lleva su motivo ("porque te gusta el estilo minimalista").
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import quote_plus

from .catalog import CATALOG, SLOTS
from .options import COLORS, NEUTRAL_PAIRINGS, OCCASIONS
from .style_catalog import BRANDS, ICONS, PRICE_LABELS, SEASONS, STYLES, Brand, Style
from .wardrobe import WardrobeItem

GARMENTS = {g.id: g for g in CATALOG}
DENIM_TYPES = {"vaqueros", "cazadora_vaquera"}
MAX_CUSTOM = 30


class InvalidProfile(ValueError):
    pass


# ================================================================== perfil
@dataclass(frozen=True)
class CustomIcon:
    name: str
    styles: tuple[str, ...]


@dataclass(frozen=True)
class StyleProfile:
    styles: tuple[str, ...] = ()
    brands: tuple[str, ...] = ()  # ids del catálogo
    custom_brands: tuple[str, ...] = ()  # nombres libres
    icons: tuple[str, ...] = ()
    custom_icons: tuple[CustomIcon, ...] = ()
    budget: tuple[int, ...] = ()  # 1, 2, 3; vacío = cualquiera
    sustainable: bool = False
    secondhand: bool = False
    fit: str = "cualquiera"

    @property
    def empty(self) -> bool:
        return not (self.styles or self.brands or self.custom_brands or self.icons or self.custom_icons)

    def to_dict(self) -> dict:
        return {
            "styles": list(self.styles), "brands": list(self.brands),
            "custom_brands": list(self.custom_brands), "icons": list(self.icons),
            "custom_icons": [{"name": c.name, "styles": list(c.styles)} for c in self.custom_icons],
            "budget": list(self.budget), "sustainable": self.sustainable,
            "secondhand": self.secondhand, "fit": self.fit,
        }

    @classmethod
    def from_dict(cls, data) -> "StyleProfile":
        if not isinstance(data, dict):
            raise InvalidProfile("Perfil no válido")

        def ids(key, valid):
            return tuple(dict.fromkeys(v for v in data.get(key) or [] if v in valid))

        def names(values):
            out = []
            for v in values or []:
                text = " ".join(str(v).split())[:60]
                if text and text.lower() not in {o.lower() for o in out}:
                    out.append(text)
            return tuple(out[:MAX_CUSTOM])

        customs = []
        for c in (data.get("custom_icons") or [])[:MAX_CUSTOM]:
            if isinstance(c, dict) and (name := " ".join(str(c.get("name", "")).split())[:60]):
                customs.append(CustomIcon(name, tuple(dict.fromkeys(s for s in c.get("styles") or [] if s in STYLES))))
        fit = data.get("fit") if data.get("fit") in ("cualquiera", "masculino", "femenino") else "cualquiera"
        return cls(
            styles=ids("styles", STYLES),
            brands=ids("brands", BRANDS),
            custom_brands=names(data.get("custom_brands")),
            icons=ids("icons", ICONS),
            custom_icons=tuple(customs),
            budget=tuple(sorted({b for b in data.get("budget") or [] if b in PRICE_LABELS})),
            sustainable=bool(data.get("sustainable")),
            secondhand=bool(data.get("secondhand")),
            fit=fit,
        )


# ================================================================ afinidad
def style_affinity(profile: StyleProfile, wardrobe: list[WardrobeItem]) -> list[tuple[str, float]]:
    """Cuánto encaja cada estilo contigo, de más a menos. Explica de dónde sale cada punto."""
    score: dict[str, float] = defaultdict(float)
    for s in profile.styles:
        score[s] += 4  # lo que eliges tú pesa más que lo que deducimos
    for i in profile.icons:
        for s in ICONS[i].styles:
            score[s] += 2
    for c in profile.custom_icons:
        for s in c.styles:
            score[s] += 2
    for b in profile.brands:
        for s in BRANDS[b].styles:
            score[s] += 1
    for brand in owned_brands(wardrobe):
        for s in brand.styles:
            score[s] += 0.5
    for item in wardrobe:  # tus prendas también dicen algo de tu estilo
        for style in STYLES.values():
            if item.details.base_type in {t for ts in style.slots.values() for t in ts}:
                score[style.id] += 0.1 + 0.1 * len(set(item.details.tags) & style.tags)
    if not any(score.values()):
        score.update({"casual": 1.0, "minimalista": 0.9})
    return sorted(((s, round(v, 2)) for s, v in score.items() if v > 0), key=lambda kv: -kv[1])


def owned_brands(wardrobe: list[WardrobeItem]) -> list[Brand]:
    """Marcas del catálogo que ya aparecen en tu armario."""
    by_name = {_norm(b.name): b for b in BRANDS.values()}
    found = {}
    for item in wardrobe:
        brand = by_name.get(_norm(item.details.brand or ""))
        if brand:
            found[brand.id] = brand
    return list(found.values())


def _norm(text: str) -> str:
    return "".join(c for c in text.lower() if c.isalnum())


# ============================================================ temporada
def season_for(month: int) -> tuple[str, int]:
    return SEASONS[month]


# ================================================================ colores
# Neutros habituales para abrigos y calzado, por orden de preferencia.
SLOT_NEUTRALS = {
    "abrigo": ("beige", "negro", "azul_marino", "gris", "marron"),
    "calzado": ("blanco", "negro", "marron"),
}


def pick_color(existing: list[str], style: Style, slot: str, used: set[str]) -> str:
    """Color que combina con lo que ya llevas y con el estilo."""
    accents = [c for c in existing if c in COLORS and not COLORS[c].neutral]
    if slot in SLOT_NEUTRALS:
        allowed = set(NEUTRAL_PAIRINGS[accents[0]]) | set(style.palette) if accents else set(style.palette)
        options = [c for c in SLOT_NEUTRALS[slot] if c in allowed] or list(SLOT_NEUTRALS[slot])
        if slot == "abrigo":  # el calzado sí puede repetir color
            options.sort(key=lambda c: c in used)
        return options[0]
    if accents:
        options = list(NEUTRAL_PAIRINGS[accents[0]])
        options.sort(key=lambda c: (c not in style.palette, c in used))
        return options[0]
    style_accents = [c for c in style.palette if not COLORS[c].neutral]
    if slot in ("parte_superior", "pieza_unica", "capa_intermedia") and style_accents and not used & set(style_accents):
        return style_accents[0]
    neutrals = [c for c in style.palette if COLORS[c].neutral] or ["blanco", "negro", "beige"]
    fresh = [c for c in neutrals if c not in used and c not in existing]
    return (fresh or neutrals)[0]


# =============================================================== enlaces
def shop_links(article: str, brands: list[Brand], secondhand: bool) -> list[dict]:
    """Enlaces para buscar el artículo: en las webs de las marcas, en Google Shopping y de segunda mano."""
    links = [{"label": b.name, "url": f"https://www.google.com/search?q={quote_plus(article)}+site%3A{b.domain}",
              "brand": b.id} for b in brands]
    links.append({"label": "Comparar en Google Shopping",
                  "url": f"https://www.google.com/search?tbm=shop&q={quote_plus(article)}", "brand": None})
    if secondhand:
        links.append({"label": "De segunda mano en Vinted",
                      "url": f"https://www.vinted.es/catalog?search_text={quote_plus(article)}", "brand": "vinted"})
    return links


def brands_for(style: Style, slot: str, profile: StyleProfile, limit: int = 3) -> list[Brand]:
    """Marcas donde buscar una prenda: primero tus favoritas que encajan, luego otras de ese estilo."""
    def ok(b: Brand) -> bool:
        return (b.kind == "marca" and b.sells(slot)
                and (not profile.budget or b.price in profile.budget))

    favorites = [BRANDS[b] for b in profile.brands if ok(BRANDS[b]) and style.id in BRANDS[b].styles]
    others = [b for b in BRANDS.values() if ok(b) and style.id in b.styles and b not in favorites]
    others.sort(key=lambda b: (not (profile.sustainable and b.sustainable), b.price))
    return (favorites + others)[:limit]


# ======================================================= completar un outfit
@dataclass(frozen=True)
class BasePiece:
    base_type: str
    color: str | None = None  # id de paleta
    item_id: str | None = None
    name: str | None = None
    has_photo: bool = False


@dataclass
class Suggestion:
    slot: str
    base_type: str
    color: str
    article: str  # "Gabardina en beige"
    reason: str
    owned: list[WardrobeItem] = field(default_factory=list)  # prendas tuyas que encajan
    use_owned: bool = False  # ya tienes exactamente esto
    links: list[dict] = field(default_factory=list)


@dataclass
class OutfitPlan:
    style: Style
    season: str
    level: int
    base: list[BasePiece]
    suggestions: list[Suggestion]
    accessories: list[str]
    palette: list[str]
    tips: list[str]


def article_name(base_type: str, color: str, style: Style) -> str:
    g = GARMENTS[base_type]
    name = g.name
    if base_type in style.modifiers:
        name += f" {style.modifiers[base_type]}"
    if base_type in DENIM_TYPES:
        return name
    return f"{name} en {COLORS[color].label.lower()}"


def _fit_ok(base_type: str, fit: str) -> bool:
    g = GARMENTS[base_type]
    return fit == "cualquiera" or g.fit in ("unisex", fit)


# Prendas de punto que no tiene sentido llevar debajo de otro jersey.
KNIT_TOPS = {"jersey_cuello_alto"}


def _pick_type(style: Style, slot: str, level: int, fit: str, occasion: str | None,
               owned_types: set[str] = frozenset(), has_mid: bool = False) -> str | None:
    options = [t for t in style.slots.get(slot, ()) if _fit_ok(t, fit)]
    if slot == "parte_superior" and has_mid:
        options = [t for t in options if t not in KNIT_TOPS] or ["camiseta"]
    if not options:
        options = [g.id for g in CATALOG if g.slot == slot and _fit_ok(g.id, fit)]
    if not options:
        return None

    def score(t):
        g = GARMENTS[t]
        distance = 0 if level in g.levels else min(abs(level - lv) for lv in g.levels)
        return (distance, 0 if not occasion or occasion in g.occasions else 1,
                t not in owned_types,  # mejor algo que ya tienes que algo que comprar
                options.index(t))
    return min(options, key=score)


def complete_outfit(base: list[BasePiece], profile: StyleProfile, wardrobe: list[WardrobeItem],
                    style: Style, month: int, occasion: str | None = None) -> OutfitPlan:
    season, level = season_for(month)
    present = {GARMENTS[p.base_type].slot for p in base}
    needed: list[str] = []
    if "pieza_unica" not in present:
        needed += [s for s in ("parte_superior", "parte_inferior") if s not in present]
    if level >= 3 and "capa_intermedia" not in present and style.slots.get("capa_intermedia"):
        needed.append("capa_intermedia")
    if level >= 2 and "abrigo" not in present:
        needed.append("abrigo")
    if "calzado" not in present:
        needed.append("calzado")

    colors = [p.color for p in base if p.color]
    used = set(colors)
    owned_ids = {p.item_id for p in base if p.item_id}
    suggestions = []
    owned_types = {i.details.base_type for i in wardrobe if i.id not in owned_ids}
    for slot in needed:
        base_type = _pick_type(style, slot, level, profile.fit, occasion, owned_types,
                               has_mid="capa_intermedia" in present or "capa_intermedia" in needed)
        if not base_type:
            continue
        color = "vaquero" if base_type in DENIM_TYPES else pick_color(colors, style, slot, used)
        palette_color = "azul" if color == "vaquero" else color
        article = article_name(base_type, palette_color, style)
        owned = _owned_matches(wardrobe, slot, base_type, palette_color, colors, owned_ids)
        exact = bool(owned) and owned[0].details.base_type == base_type and (
            color == "vaquero" or any(c.palette_id == palette_color for c in owned[0].details.colors))
        reason = _reason(slot, base, style, season, palette_color, colors)
        suggestions.append(Suggestion(
            slot=slot, base_type=base_type, color=color if color != "vaquero" else "azul",
            article=article, reason=reason, owned=owned, use_owned=exact,
            links=[] if exact else shop_links(article, brands_for(style, slot, profile), profile.secondhand),
        ))
        if color != "vaquero":
            used.add(color)
            colors.append(color)
    tips = []
    if level >= 3:
        tips.append(f"En {season} conviene llevar una capa de abrigo que puedas quitarte en interiores.")
    if any(s.use_owned for s in suggestions):
        tips.append("Parte de este look ya lo tienes en tu armario: ¡no hace falta comprar nada!")
    return OutfitPlan(style=style, season=season, level=level, base=base, suggestions=suggestions,
                      accessories=list(style.accessories[:2]), palette=list(dict.fromkeys(colors)), tips=tips)


def _owned_matches(wardrobe, slot, base_type, color, outfit_colors, exclude) -> list[WardrobeItem]:
    """Prendas tuyas que podrían cumplir esa función, mejor cuanto más se parecen."""
    def score(item):
        d = item.details
        same_type = d.base_type == base_type
        same_color = any(c.palette_id == color for c in d.colors)
        return (not same_type, not same_color)
    candidates = [i for i in wardrobe if i.id not in exclude and i.details.slot == slot]
    good = [i for i in candidates if i.details.base_type == base_type
            or any(c.palette_id == color for c in i.details.colors)]
    return sorted(good, key=score)[:2]


def _reason(slot, base, style, season, color, colors) -> str:
    color_label = COLORS[color].label.lower()
    if base:
        names = ", ".join((p.name or GARMENTS[p.base_type].name).lower() for p in base[:2])
        if COLORS[color].neutral and any(c in COLORS and not COLORS[c].neutral for c in colors[:1]):
            return f"El {color_label} equilibra el color de tu {names}."
        return f"Combina con tu {names} y encaja con el estilo {style.label.lower()}."
    return f"Básico del estilo {style.label.lower()} para {season}."


# ================================================================ ideas
@dataclass
class LookIdea:
    title: str
    style: Style
    reason: str
    anchor: WardrobeItem | None
    plan: OutfitPlan


def idea_feed(profile: StyleProfile, wardrobe: list[WardrobeItem], month: int, limit: int = 6) -> list[LookIdea]:
    """Looks completos para tus estilos favoritos, construidos alrededor de tus propias prendas."""
    season, level = season_for(month)
    affinity = style_affinity(profile, wardrobe)
    ideas: list[LookIdea] = []
    used_anchors: set[str] = set()
    for style_id, _ in affinity[:3]:
        style = STYLES[style_id]
        anchors = _anchors(style, wardrobe, level, used_anchors)[:2] or [None]
        for anchor in anchors:
            base = [] if anchor is None else [BasePiece(anchor.details.base_type,
                                                        anchor.details.colors[0].palette_id if anchor.details.colors else None,
                                                        anchor.id, anchor.details.name, bool(anchor.photos))]
            plan = complete_outfit(base, profile, wardrobe, style, month)
            title = f"{style.label} de {season}"
            if anchor:
                used_anchors.add(anchor.id)
                title = f"{style.label} con tu {anchor.details.name.lower()}"
            ideas.append(LookIdea(title, style, _why(style, profile), anchor, plan))
            if len(ideas) >= limit:
                return ideas
    return ideas


def _anchors(style: Style, wardrobe, level, used) -> list[WardrobeItem]:
    key_types = {t for ts in style.slots.values() for t in ts}
    fits = [i for i in wardrobe if i.id not in used and i.details.base_type in key_types
            and i.details.slot in ("parte_superior", "parte_inferior", "pieza_unica", "capa_intermedia", "abrigo")
            and (level in i.details.levels or not i.details.levels)]
    fits.sort(key=lambda i: -len(set(i.details.tags) & style.tags))
    return fits


def _why(style: Style, profile: StyleProfile) -> str:
    if style.id in profile.styles:
        return f"Porque te gusta el estilo {style.label.lower()}."
    icons = [ICONS[i].name for i in profile.icons if style.id in ICONS[i].styles]
    icons += [c.name for c in profile.custom_icons if style.id in c.styles]
    if icons:
        return f"Inspirado en el estilo de {icons[0]}."
    brands = [BRANDS[b].name for b in profile.brands if style.id in BRANDS[b].styles]
    if brands:
        return f"Encaja con lo que vende {brands[0]}."
    return "Encaja con la ropa que ya tienes."


# =========================================================== descubrir marcas
@dataclass
class BrandPick:
    brand: Brand
    score: float
    reasons: list[str]


def discover_brands(profile: StyleProfile, wardrobe: list[WardrobeItem], limit: int = 12) -> list[BrandPick]:
    """Marcas que no tienes ni sigues y que encajan con tu estilo y tu presupuesto."""
    affinity = dict(style_affinity(profile, wardrobe))
    known = set(profile.brands) | {b.id for b in owned_brands(wardrobe)}
    custom = {_norm(n) for n in profile.custom_brands}
    favorites = [BRANDS[b] for b in profile.brands]
    picks = []
    for b in BRANDS.values():
        if b.kind != "marca" or b.id in known or _norm(b.name) in custom:
            continue
        reasons = []
        score = sum(affinity.get(s, 0) for s in b.styles) / max(len(b.styles), 1) * 2
        top = max(b.styles, key=lambda s: affinity.get(s, 0))
        if affinity.get(top, 0) > 0:
            reasons.append(f"Encaja con tu estilo {STYLES[top].label.lower()}")
        similar = [f.name for f in favorites if set(f.styles) & set(b.styles) and abs(f.price - b.price) <= 1]
        if similar:
            score += 1
            reasons.append(f"Si te gusta {similar[0]}")
        if profile.budget:
            if b.price in profile.budget:
                score += 0.5
            else:
                score -= 3
        if profile.sustainable and b.sustainable:
            score += 1.5
            reasons.append("Marca con enfoque sostenible")
        if score > 0 and reasons:
            picks.append(BrandPick(b, round(score, 2), reasons))
    picks.sort(key=lambda p: -p.score)
    return picks[:limit]


# ======================================================= lo que le falta
@dataclass
class Essential:
    style: Style
    base_type: str
    color: str | None
    article: str
    owned: WardrobeItem | None
    links: list[dict]


def wardrobe_gaps(profile: StyleProfile, wardrobe: list[WardrobeItem], styles: int = 2) -> list[Essential]:
    """Básicos de tus estilos favoritos: cuáles tienes y cuáles te faltan."""
    out = []
    seen = set()
    for style_id, _ in style_affinity(profile, wardrobe)[:styles]:
        style = STYLES[style_id]
        for base_type, color in style.essentials:
            if (base_type, color) in seen or not _fit_ok(base_type, profile.fit):
                continue
            seen.add((base_type, color))
            owned = next((i for i in wardrobe if i.details.base_type == base_type and (
                color is None or any(c.palette_id == color for c in i.details.colors))), None)
            article = article_name(base_type, color or "azul", style) if (color or base_type in DENIM_TYPES) \
                else GARMENTS[base_type].name
            links = [] if owned else shop_links(article, brands_for(style, GARMENTS[base_type].slot, profile),
                                                profile.secondhand)
            out.append(Essential(style, base_type, color, article, owned, links))
    return out


def news_links(profile: StyleProfile, discovered: list[BrandPick], limit: int = 8) -> list[dict]:
    """Accesos a las novedades de tus marcas (y de las que te recomendamos)."""
    brands = [BRANDS[b] for b in profile.brands] + [p.brand for p in discovered]
    out, seen = [], set()
    for b in brands:
        if b.id in seen or b.kind != "marca":
            continue
        seen.add(b.id)
        out.append({"brand": b.id, "name": b.name, "url": b.url, "favorite": b.id in profile.brands,
                    "search": f"https://www.google.com/search?q={quote_plus(b.name + ' nueva colección')}"})
        if len(out) >= limit:
            break
    return out


SLOT_LABELS = SLOTS
OCCASION_IDS = set(OCCASIONS)
