"""Catálogo de prendas genéricas.

Mientras no exista "Mi armario", el recomendador elige de este catálogo.
Cuando exista, las prendas del usuario tendrán estos mismos atributos.

Niveles térmicos (según sensación térmica):
    0: ≥24 °C   1: 18-24   2: 13-18   3: 8-13   4: 3-8   5: <3
"""

from __future__ import annotations

from dataclasses import dataclass

ALL_LEVELS = frozenset(range(6))

# El orden es el que se muestra al usuario.
SLOTS = {
    "pieza_unica": "Prenda principal",
    "parte_superior": "Parte de arriba",
    "parte_inferior": "Parte de abajo",
    "capa_intermedia": "Capa intermedia",
    "abrigo": "Abrigo",
    "calzado": "Calzado",
}


@dataclass(frozen=True)
class Garment:
    id: str
    name: str
    slot: str
    icon: str
    levels: frozenset[int]
    occasions: frozenset[str]
    tags: frozenset[str] = frozenset()
    fit: str = "unisex"  # unisex | masculino | femenino
    waterproof: bool = False
    windproof: bool = False
    fixed_color: str | None = None  # p. ej. vaquero


def _g(id, name, slot, icon, levels, occasions, tags="", fit="unisex",
       waterproof=False, windproof=False, fixed_color=None) -> Garment:
    return Garment(
        id=id, name=name, slot=slot, icon=icon,
        levels=frozenset(levels), occasions=frozenset(occasions.split()),
        tags=frozenset(tags.split()), fit=fit,
        waterproof=waterproof, windproof=windproof, fixed_color=fixed_color,
    )


CATALOG: tuple[Garment, ...] = (
    # --- Parte de arriba ---------------------------------------------------
    _g("tirantes", "Camiseta de tirantes", "parte_superior", "🎽", {0}, "diario deporte", "relajado deportivo"),
    _g("camiseta", "Camiseta de manga corta", "parte_superior", "👕", {0, 1, 2}, "diario", "relajado comodo"),
    _g("camiseta_estampada", "Camiseta estampada", "parte_superior", "👕", {0, 1, 2}, "diario fiesta", "alegre creativo atrevido"),
    _g("camiseta_tecnica", "Camiseta técnica transpirable", "parte_superior", "🎽", {0, 1, 2, 3}, "deporte", "deportivo comodo"),
    _g("termica_deporte", "Camiseta térmica deportiva", "parte_superior", "🎽", {4, 5}, "deporte", "deportivo comodo"),
    _g("manga_larga", "Camiseta de manga larga", "parte_superior", "👕", {2, 3, 4}, "diario", "comodo relajado tranquilo"),
    _g("termica", "Camiseta térmica de manga larga", "parte_superior", "👕", {5}, "diario trabajo", "comodo"),
    _g("polo", "Polo", "parte_superior", "👕", {0, 1, 2}, "diario trabajo", "clasico tranquilo"),
    _g("camisa_lino", "Camisa de lino", "parte_superior", "👔", {0, 1}, "diario trabajo fiesta", "relajado elegante tranquilo"),
    _g("camisa_oxford", "Camisa Oxford", "parte_superior", "👔", {1, 2, 3, 4, 5}, "diario trabajo", "clasico seguro"),
    _g("camisa_estampada", "Camisa estampada", "parte_superior", "👔", {0, 1, 2}, "fiesta diario", "atrevido creativo alegre"),
    _g("camisa_vestir", "Camisa de vestir", "parte_superior", "👔", ALL_LEVELS, "etiqueta trabajo fiesta", "elegante clasico"),
    _g("blusa", "Blusa", "parte_superior", "👚", {0, 1, 2, 3}, "trabajo fiesta diario", "elegante alegre", fit="femenino"),
    _g("top_fiesta", "Top de fiesta", "parte_superior", "👚", {0, 1, 2}, "fiesta", "atrevido seguro alegre", fit="femenino"),
    _g("jersey_cuello_alto", "Jersey fino de cuello alto", "parte_superior", "🧶", {3, 4, 5}, "trabajo fiesta diario", "elegante seguro clasico"),

    # --- Capa intermedia ------------------------------------------------------
    _g("sudadera", "Sudadera", "capa_intermedia", "🧥", {2, 3}, "diario deporte", "comodo relajado deportivo"),
    _g("jersey_fino", "Jersey de punto fino", "capa_intermedia", "🧶", {2, 3, 4}, "diario trabajo", "clasico tranquilo"),
    _g("jersey_lana", "Jersey grueso de lana", "capa_intermedia", "🧶", {4, 5}, "diario", "comodo tranquilo"),
    _g("cardigan", "Cárdigan", "capa_intermedia", "🧶", {2, 3}, "diario trabajo", "tranquilo comodo creativo"),
    _g("blazer", "Blazer", "capa_intermedia", "🧥", {1, 2, 3, 4}, "trabajo fiesta", "elegante seguro clasico"),
    _g("americana_traje", "Americana de traje", "capa_intermedia", "🤵", ALL_LEVELS, "etiqueta", "elegante seguro"),
    _g("chal", "Chal o estola", "capa_intermedia", "🧣", {1, 2, 3}, "etiqueta fiesta", "elegante", fit="femenino"),
    _g("forro_polar", "Forro polar", "capa_intermedia", "🧥", {3, 4, 5}, "diario deporte", "comodo deportivo"),
    _g("chaleco_acolchado", "Chaleco acolchado", "capa_intermedia", "🦺", {3, 4}, "diario", "relajado comodo"),

    # --- Abrigo ---------------------------------------------------------------
    _g("chubasquero", "Chubasquero ligero", "abrigo", "🧥", {0, 1, 2}, "diario deporte", "deportivo comodo", waterproof=True, windproof=True),
    _g("cortavientos", "Cortavientos", "abrigo", "🧥", {1, 2}, "diario deporte", "deportivo", windproof=True),
    _g("cazadora_vaquera", "Cazadora vaquera", "abrigo", "🧥", {2}, "diario fiesta", "relajado alegre creativo", fixed_color="vaquero"),
    _g("cazadora_cuero", "Cazadora de cuero", "abrigo", "🧥", {2, 3}, "diario fiesta", "atrevido seguro", windproof=True),
    _g("gabardina", "Gabardina", "abrigo", "🧥", {2, 3}, "diario trabajo fiesta etiqueta", "elegante clasico", waterproof=True, windproof=True),
    _g("softshell", "Chaqueta técnica impermeable", "abrigo", "🧥", {2, 3, 4}, "diario deporte", "deportivo comodo", waterproof=True, windproof=True),
    _g("acolchada_ligera", "Chaqueta acolchada ligera", "abrigo", "🧥", {3}, "diario trabajo", "comodo tranquilo", windproof=True),
    _g("abrigo_pano", "Abrigo de paño", "abrigo", "🧥", {3, 4, 5}, "diario trabajo fiesta", "elegante clasico seguro", windproof=True),
    _g("abrigo_vestir", "Abrigo largo de vestir", "abrigo", "🧥", {2, 3, 4, 5}, "etiqueta fiesta", "elegante seguro", windproof=True),
    _g("plumifero", "Plumífero", "abrigo", "🧥", {4, 5}, "diario deporte", "comodo deportivo", windproof=True),
    _g("parka", "Parka impermeable", "abrigo", "🧥", {4, 5}, "diario trabajo", "comodo relajado", waterproof=True, windproof=True),

    # --- Parte de abajo -------------------------------------------------------
    _g("pantalon_corto", "Pantalón corto", "parte_inferior", "🩳", {0}, "diario", "relajado alegre"),
    _g("bermudas", "Bermudas chinas", "parte_inferior", "🩳", {0, 1}, "diario", "relajado clasico"),
    _g("corto_deporte", "Pantalón corto deportivo", "parte_inferior", "🩳", {0, 1, 2}, "deporte", "deportivo"),
    _g("mallas", "Mallas deportivas largas", "parte_inferior", "👖", {2, 3, 4, 5}, "deporte", "deportivo comodo"),
    _g("vaqueros", "Vaqueros", "parte_inferior", "👖", {1, 2, 3, 4, 5}, "diario fiesta", "relajado clasico seguro", fixed_color="vaquero"),
    _g("chinos", "Pantalón chino", "parte_inferior", "👖", {0, 1, 2, 3, 4}, "diario trabajo", "clasico tranquilo"),
    _g("pantalon_lino", "Pantalón de lino", "parte_inferior", "👖", {0, 1}, "diario trabajo fiesta", "relajado elegante tranquilo"),
    _g("pantalon_vestir", "Pantalón de vestir", "parte_inferior", "👖", ALL_LEVELS, "trabajo fiesta", "elegante clasico seguro"),
    _g("pantalon_traje", "Pantalón de traje", "parte_inferior", "👖", ALL_LEVELS, "etiqueta", "elegante"),
    _g("jogger", "Pantalón jogger", "parte_inferior", "👖", {2, 3, 4}, "diario deporte", "comodo relajado deportivo"),
    _g("pana", "Pantalón de pana", "parte_inferior", "👖", {4, 5}, "diario trabajo", "comodo clasico creativo"),
    _g("falda_midi", "Falda midi", "parte_inferior", "👗", {0, 1, 2, 3}, "diario trabajo fiesta", "elegante alegre tranquilo", fit="femenino"),
    _g("falda_punto", "Falda de punto con medias", "parte_inferior", "👗", {3, 4, 5}, "diario trabajo", "comodo elegante", fit="femenino"),

    # --- Pieza única ----------------------------------------------------------
    _g("vestido_verano", "Vestido ligero", "pieza_unica", "👗", {0, 1}, "diario fiesta", "alegre relajado", fit="femenino"),
    _g("vestido_coctel", "Vestido de cóctel", "pieza_unica", "👗", {0, 1, 2, 3, 4}, "fiesta", "elegante atrevido seguro", fit="femenino"),
    _g("vestido_manga_larga", "Vestido de manga larga", "pieza_unica", "👗", {3, 4, 5}, "fiesta trabajo", "elegante seguro", fit="femenino"),
    _g("vestido_gala", "Vestido largo de gala", "pieza_unica", "👗", ALL_LEVELS, "etiqueta", "elegante seguro", fit="femenino"),
    _g("mono", "Mono", "pieza_unica", "🩱", {0, 1, 2}, "fiesta diario", "atrevido creativo", fit="femenino"),

    # --- Calzado ---------------------------------------------------------------
    _g("sandalias", "Sandalias", "calzado", "🩴", {0}, "diario fiesta", "relajado alegre"),
    _g("lona", "Zapatillas de lona", "calzado", "👟", {0, 1, 2}, "diario", "relajado alegre creativo"),
    _g("zapatillas_urbanas", "Zapatillas urbanas", "calzado", "👟", {0, 1, 2, 3, 4}, "diario fiesta", "comodo relajado seguro"),
    _g("running", "Zapatillas deportivas", "calzado", "👟", ALL_LEVELS, "deporte", "deportivo comodo"),
    _g("trail", "Zapatillas de trail impermeables", "calzado", "👟", {2, 3, 4, 5}, "deporte", "deportivo comodo", waterproof=True),
    _g("zapatillas_impermeables", "Zapatillas impermeables", "calzado", "👟", {1, 2, 3, 4, 5}, "diario", "comodo", waterproof=True),
    _g("mocasines", "Mocasines", "calzado", "👞", {0, 1, 2, 3}, "diario trabajo fiesta", "clasico elegante tranquilo"),
    _g("zapatos_vestir", "Zapatos de vestir", "calzado", "👞", ALL_LEVELS, "etiqueta trabajo fiesta", "elegante clasico"),
    _g("tacones", "Zapatos de tacón", "calzado", "👠", ALL_LEVELS, "fiesta etiqueta", "elegante atrevido seguro", fit="femenino"),
    _g("botines", "Botines", "calzado", "🥾", {3, 4, 5}, "diario trabajo fiesta", "clasico seguro elegante"),
    _g("botas_agua", "Botas impermeables", "calzado", "🥾", {3, 4, 5}, "diario", "comodo", waterproof=True),
)


def thermal_level(feels_like: float) -> int:
    if feels_like >= 24:
        return 0
    if feels_like >= 18:
        return 1
    if feels_like >= 13:
        return 2
    if feels_like >= 8:
        return 3
    if feels_like >= 3:
        return 4
    return 5


LEVEL_LABELS = {
    0: "Calor",
    1: "Templado",
    2: "Fresco",
    3: "Frío suave",
    4: "Frío",
    5: "Mucho frío",
}
