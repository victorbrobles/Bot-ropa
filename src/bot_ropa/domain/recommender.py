"""Motor de recomendación de outfits basado en reglas.

Recibe un resumen del tiempo del periodo en que vas a estar fuera y tus
preferencias, y devuelve una combinación de prendas genéricas con colores,
complementos y consejos. Es determinista: misma entrada, misma salida.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .catalog import CATALOG, LEVEL_LABELS, SLOTS, Garment, thermal_level
from .options import COLORS, DENIM, MOODS, NEUTRAL_PAIRINGS, OCCASIONS, Color
from .weather import WeatherSummary

SPORT_OFFSET = 6.0  # al hacer deporte se entra en calor: vístete como si hiciera más
STRONG_WIND = 30.0  # km/h
UMBRELLA_MAX_WIND = 40.0
SNEAKERS = {"lona", "zapatillas_urbanas", "running", "trail", "zapatillas_impermeables"}
DARK_SUIT_COLORS = ("azul_marino", "negro", "gris", "marron")
DEFAULT_PRIMARY = {
    "diario": "azul",
    "trabajo": "celeste",
    "deporte": "azul",
    "fiesta": "negro",
    "etiqueta": "azul_marino",
}


@dataclass(frozen=True)
class OutfitPreferences:
    occasion: str = "diario"
    mood: str | None = None
    color: str | None = None
    fit: str = "cualquiera"

    def __post_init__(self):
        if self.occasion not in OCCASIONS:
            raise ValueError(f"Ocasión desconocida: {self.occasion}")
        if self.mood is not None and self.mood not in MOODS:
            raise ValueError(f"Estado de ánimo desconocido: {self.mood}")
        if self.color is not None and self.color not in COLORS:
            raise ValueError(f"Color desconocido: {self.color}")
        if self.fit not in ("cualquiera", "masculino", "femenino"):
            raise ValueError(f"Tipo de prenda desconocido: {self.fit}")


@dataclass
class OutfitItem:
    slot: str
    garment: Garment
    reason: str
    alternatives: list[Garment] = field(default_factory=list)
    color: Color | None = None

    @property
    def slot_label(self) -> str:
        return SLOTS[self.slot]


@dataclass(frozen=True)
class Accessory:
    id: str
    name: str
    icon: str
    reason: str


@dataclass
class Outfit:
    headline: str
    level: int
    level_label: str
    items: list[OutfitItem]
    accessories: list[Accessory]
    tips: list[str]
    palette: list[Color]


class Recommender:
    def __init__(self, catalog: tuple[Garment, ...] = CATALOG):
        self.catalog = catalog

    # ------------------------------------------------------------------ API
    def recommend(self, weather: WeatherSummary, prefs: OutfitPreferences) -> Outfit:
        ctx = _Context(weather, prefs)
        items: list[OutfitItem] = []

        one_piece = prefs.fit == "femenino" and prefs.occasion in ("fiesta", "etiqueta")
        if one_piece:
            items.append(self._pick(ctx, "pieza_unica", ctx.level_bottom,
                                    self._reason_main(ctx)))
        else:
            items.append(self._pick(ctx, "parte_superior", ctx.level_top,
                                    self._reason_top(ctx)))

        need_mid, need_outer = self._layers(ctx, one_piece)
        if need_mid:
            exclude = {"americana_traje"} if one_piece else set()
            items.append(self._pick(ctx, "capa_intermedia", ctx.level_outer,
                                    f"Para las horas más frescas ({ctx.w.min_feels:.0f} °C de sensación)",
                                    exclude=exclude))
        if need_outer:
            items.append(self._pick(ctx, "abrigo", ctx.level_outer, self._reason_outer(ctx)))

        if not one_piece:
            items.append(self._pick(ctx, "parte_inferior", ctx.level_bottom,
                                    f"Sensación térmica media de {ctx.w.avg_feels:.0f} °C"))
        items.append(self._pick(ctx, "calzado", ctx.level_outer, self._reason_shoes(ctx)))

        palette = self._apply_colors(ctx, items)
        accessories = self._accessories(ctx, palette)
        tips = self._tips(ctx, items)

        order = list(SLOTS)
        items.sort(key=lambda i: order.index(i.slot))
        w = ctx.w
        headline = (f"{LEVEL_LABELS[ctx.level_outer]} · {w.condition_label.lower()} · "
                    f"{w.min_feels:.0f}–{w.max_feels:.0f} °C de sensación")
        return Outfit(
            headline=headline,
            level=ctx.level_outer,
            level_label=LEVEL_LABELS[ctx.level_outer],
            items=items,
            accessories=accessories,
            tips=tips,
            palette=palette,
        )

    # -------------------------------------------------------------- capas
    @staticmethod
    def _layers(ctx: "_Context", one_piece: bool) -> tuple[bool, bool]:
        level, w, occ = ctx.level_outer, ctx.w, ctx.prefs.occasion
        casual = occ in ("diario", "deporte")
        if occ == "etiqueta" and not one_piece:
            # El traje siempre lleva americana; abrigo a partir de frío suave.
            return True, level >= 3 or (level >= 2 and w.rain_likely)
        if level >= 3:
            return True, True
        if level == 2:
            if w.rain_likely or w.max_wind >= STRONG_WIND:
                return False, True
            return True, False
        # Calor o templado: solo protección si llueve o hace mucho viento
        # (en ocasiones formales basta con el paraguas).
        need_outer = casual and (w.rain_likely or w.max_wind >= 35)
        return False, need_outer

    # ------------------------------------------------------------ elección
    def _pick(self, ctx: "_Context", slot: str, level: int, reason: str,
              exclude: set[str] | None = None) -> OutfitItem:
        exclude = exclude or set()
        candidates = [g for g in self.catalog
                      if g.slot == slot and g.id not in exclude and ctx.fit_allowed(g)]
        strict = [g for g in candidates if ctx.prefs.occasion in g.occasions]
        pool = strict or candidates
        if not pool:
            raise LookupError(f"No hay prendas para {slot}")

        scored = sorted(
            ((self._score(ctx, g, level), -i, g) for i, g in enumerate(pool)),
            reverse=True,
        )
        best = scored[0][2]
        alternatives = [g for s, _, g in scored[1:]
                        if level in g.levels and s >= scored[0][0] - 25][:2]
        mood = ctx.mood
        if mood and best.tags & mood.tags:
            reason += f" · encaja con tu ánimo ({mood.label.lower()})"
        return OutfitItem(slot=slot, garment=best, reason=reason, alternatives=alternatives)

    @staticmethod
    def _score(ctx: "_Context", g: Garment, level: int) -> float:
        w, prefs = ctx.w, ctx.prefs
        distance = 0 if level in g.levels else min(abs(level - lv) for lv in g.levels)
        score = -30.0 * distance
        if ctx.mood:
            score += 6 * len(g.tags & ctx.mood.tags)
        if prefs.fit == "cualquiera" and g.fit == "unisex":
            score += 4
        if prefs.fit == "femenino" and g.fit == "femenino":
            score += 3
        if g.slot in ("abrigo", "calzado"):
            if w.rain_likely and g.waterproof:
                score += 25
            elif w.rain_possible and g.waterproof:
                score += 8
            if w.has_snow and g.slot == "calzado" and g.waterproof:
                score += 40
            if w.rain_likely and g.slot == "calzado" and g.id in ("sandalias", "lona"):
                score -= 20
        if w.max_wind >= STRONG_WIND and g.windproof:
            score += 10
        return score

    # ------------------------------------------------------------- colores
    def _apply_colors(self, ctx: "_Context", items: list[OutfitItem]) -> list[Color]:
        prefs, mood = ctx.prefs, ctx.mood
        primary_id = prefs.color or (mood.palette[0] if mood else DEFAULT_PRIMARY[prefs.occasion])
        primary = COLORS[primary_id]
        neutrals = [COLORS[c] for c in NEUTRAL_PAIRINGS[primary_id]]
        if ctx.level_top == 0 and not prefs.color:
            # Con calor, mejor neutros claros.
            neutrals.sort(key=lambda c: not c.light)
        by_slot = {i.slot: i for i in items}

        if prefs.occasion == "etiqueta" and "pieza_unica" not in by_slot:
            suit = primary if primary.id in DARK_SUIT_COLORS else COLORS["azul_marino"]
            by_slot["parte_superior"].color = COLORS["blanco"]
            for slot in ("capa_intermedia", "parte_inferior"):
                if slot in by_slot:
                    by_slot[slot].color = suit
            ctx.accent = None if primary is suit else primary
            if "abrigo" in by_slot:
                by_slot["abrigo"].color = COLORS["negro"] if suit.id != "negro" else COLORS["gris"]
        else:
            protagonist = by_slot.get("pieza_unica") or by_slot["parte_superior"]
            protagonist.color = primary
            rest = [s for s in ("parte_inferior", "abrigo", "capa_intermedia") if s in by_slot]
            for idx, slot in enumerate(rest):
                by_slot[slot].color = neutrals[idx % len(neutrals)]
            if (mood and "capa_intermedia" in by_slot and not prefs.color
                    and prefs.occasion not in ("trabajo", "etiqueta")):
                by_slot["capa_intermedia"].color = COLORS[mood.palette[1]]

        shoes = by_slot["calzado"]
        if shoes.garment.id in SNEAKERS:
            shoes.color = COLORS["gris"] if ctx.w.rain_likely else COLORS["blanco"]
        elif shoes.garment.id in ("botas_agua", "botines"):
            shoes.color = COLORS["marron"]
        elif shoes.garment.id == "sandalias":
            shoes.color = COLORS["beige"]
        else:
            warm = {"beige", "marron", "verde", "naranja", "amarillo"}
            shoes.color = COLORS["marron"] if primary.id in warm else COLORS["negro"]

        for item in items:
            if item.garment.fixed_color == "vaquero":
                item.color = DENIM
            if item.color is None:
                item.color = neutrals[0]

        palette: list[Color] = []
        for item in items:
            if item.color not in palette:
                palette.append(item.color)
        if ctx.accent and ctx.accent not in palette:
            palette.append(ctx.accent)
        return palette

    # --------------------------------------------------------- complementos
    def _accessories(self, ctx: "_Context", palette: list[Color]) -> list[Accessory]:
        w, prefs = ctx.w, ctx.prefs
        acc: list[Accessory] = []
        if w.rain_likely and w.max_wind < UMBRELLA_MAX_WIND:
            acc.append(Accessory("paraguas", "Paraguas", "☂️",
                                 f"{w.max_precip_probability:.0f}% de probabilidad de lluvia"))
        elif w.rain_possible and not w.rain_likely and w.max_wind < UMBRELLA_MAX_WIND:
            acc.append(Accessory("paraguas_plegable", "Paraguas plegable", "🌂",
                                 "Por si acaso: puede caer algo"))
        if w.max_uv >= 3:
            acc.append(Accessory("gafas", "Gafas de sol", "🕶️", f"Índice UV de hasta {w.max_uv:.0f}"))
        if w.max_uv >= 6 and prefs.occasion != "etiqueta":
            name = "Gorra" if prefs.occasion == "deporte" else "Gorra o sombrero"
            acc.append(Accessory("gorra", name, "🧢", "Sol fuerte en las horas centrales"))
        if ctx.level_outer >= 4 or (ctx.level_outer >= 3 and w.max_wind >= 25):
            acc.append(Accessory("bufanda", "Bufanda", "🧣", "Protege el cuello del frío"))
        if ctx.level_outer >= 5 or w.has_snow:
            acc.append(Accessory("gorro", "Gorro", "🧢", "Buena parte del calor se pierde por la cabeza"))
        if w.min_feels + ctx.offset <= 3:
            acc.append(Accessory("guantes", "Guantes", "🧤", f"Mínima de {w.min_feels:.0f} °C de sensación"))
        if prefs.occasion == "etiqueta" and prefs.fit != "femenino":
            name = "Corbata o pajarita"
            reason = "Imprescindible en un evento de etiqueta"
            if ctx.accent:
                name += f" en {ctx.accent.label.lower()}"
                reason = "Tu color, como toque de acento sobre el traje"
            acc.append(Accessory("corbata", name, "👔", reason))
        if prefs.occasion in ("fiesta", "etiqueta") and prefs.fit != "masculino":
            acc.append(Accessory("bolso", "Bolso de mano", "👛", "Para llevar lo justo con estilo"))
        if prefs.occasion == "deporte" or w.max_feels >= 30:
            acc.append(Accessory("agua", "Botella de agua", "💧", "Mantente hidratado"))
        return acc

    # -------------------------------------------------------------- consejos
    def _tips(self, ctx: "_Context", items: list[OutfitItem]) -> list[str]:
        w, prefs, mood = ctx.w, ctx.prefs, ctx.mood
        tips: list[str] = []
        if w.feels_range >= 8:
            tips.append(f"La sensación térmica irá de {w.min_feels:.0f} a {w.max_feels:.0f} °C: "
                        "ve por capas para poder quitarte prendas.")
        if prefs.occasion == "deporte":
            tips.append("Para hacer deporte vístete como si hiciera unos 6 °C más: entrarás en calor enseguida.")
        if w.max_feels >= 30:
            tips.append("Mucho calor: tejidos transpirables, colores claros y bebe agua a menudo.")
        if w.has_storm:
            tips.append("Riesgo de tormenta: evita zonas abiertas y lleva algo impermeable.")
        if w.has_snow:
            tips.append("Puede nevar: calzado con buena suela que no cale.")
        if w.rain_likely and w.max_wind >= UMBRELLA_MAX_WIND:
            tips.append(f"Con rachas de {w.max_wind:.0f} km/h el paraguas sufrirá: mejor una prenda con capucha.")
        if w.max_uv >= 6:
            tips.append(f"Índice UV alto ({w.max_uv:.0f}): ponte protector solar.")
        elif w.max_uv >= 3:
            tips.append("Usa protector solar aunque haya nubes.")
        if prefs.color:
            color = COLORS[prefs.color]
            if prefs.occasion == "etiqueta" and ctx.accent:
                tips.append(f"En etiqueta el {color.label.lower()} luce mejor como acento: "
                            "traje oscuro y tu color en los complementos.")
            else:
                tips.append(f"Tu color, {color.label.lower()}, es el protagonista; "
                            "el resto en neutros que combinan con él.")
        if mood:
            tips.append(mood.note)
        return tips

    # --------------------------------------------------------------- textos
    @staticmethod
    def _reason_top(ctx: "_Context") -> str:
        return f"Máxima de {ctx.w.max_feels:.0f} °C de sensación térmica"

    @staticmethod
    def _reason_main(ctx: "_Context") -> str:
        occ = OCCASIONS[ctx.prefs.occasion].label.lower()
        return f"Pensado para {occ} con {ctx.w.avg_feels:.0f} °C de media"

    @staticmethod
    def _reason_outer(ctx: "_Context") -> str:
        w = ctx.w
        if w.rain_likely:
            return f"{w.max_precip_probability:.0f}% de probabilidad de lluvia"
        if w.max_wind >= STRONG_WIND:
            return f"Viento de hasta {w.max_wind:.0f} km/h"
        return f"Mínima de {w.min_feels:.0f} °C de sensación térmica"

    @staticmethod
    def _reason_shoes(ctx: "_Context") -> str:
        w = ctx.w
        if w.has_snow:
            return "Que no calen: puede nevar"
        if w.rain_likely:
            return "Mejor que no calen: va a llover"
        return {
            "diario": "Cómodo para todo el día",
            "trabajo": "Formal pero cómodo",
            "deporte": "Con buena amortiguación",
            "fiesta": "Para lucirte",
            "etiqueta": "Acorde a la etiqueta",
        }[ctx.prefs.occasion]


class _Context:
    """Datos derivados que comparten todas las reglas."""

    def __init__(self, weather: WeatherSummary, prefs: OutfitPreferences):
        self.w = weather
        self.prefs = prefs
        self.mood = MOODS.get(prefs.mood) if prefs.mood else None
        self.offset = SPORT_OFFSET if prefs.occasion == "deporte" else 0.0
        self.level_top = thermal_level(weather.max_feels + self.offset)
        self.level_outer = thermal_level(weather.min_feels + self.offset)
        self.level_bottom = thermal_level(weather.avg_feels + self.offset)
        self.accent: Color | None = None

    def fit_allowed(self, g: Garment) -> bool:
        if self.prefs.fit == "masculino":
            return g.fit != "femenino"
        if self.prefs.fit == "femenino":
            return g.fit != "masculino"
        return True
