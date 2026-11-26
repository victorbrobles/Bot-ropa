"""Conocimiento de moda de la app: estilos, marcas y referentes de estilo.

Son datos curados (no salen de ninguna API) y orientativos: los precios
son relativos (€ económico, €€ medio, €€€ alto) y cada estilo define sus
prendas clave, su paleta y sus básicos imprescindibles usando los tipos
del catálogo genérico, para poder cruzarlos con "Mi armario".
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Style:
    id: str
    label: str
    emoji: str
    description: str
    tags: frozenset[str]  # estilos de prenda (comodo, elegante...) que lo caracterizan
    palette: tuple[str, ...]  # ids de COLORS, del más al menos característico
    slots: dict[str, tuple[str, ...]]  # parte del cuerpo -> tipos de prenda clave (catálogo)
    essentials: tuple[tuple[str, str | None], ...]  # (tipo, color) básicos del estilo
    accessories: tuple[str, ...]
    modifiers: dict[str, str] = field(default_factory=dict)  # tipo -> detalle ("oversize")


def _s(id, label, emoji, description, tags, palette, slots, essentials, accessories, modifiers=None):
    return Style(id, label, emoji, description, frozenset(tags.split()), tuple(palette.split()),
                 {k: tuple(v.split()) for k, v in slots.items()},
                 tuple((e.split(":")[0], e.split(":")[1] or None) for e in essentials.split()),
                 tuple(accessories), modifiers or {})


STYLES: dict[str, Style] = {s.id: s for s in [
    _s("minimalista", "Minimalista", "◻️", "Pocas prendas, cortes limpios y colores neutros que combinan entre sí.",
       "tranquilo elegante clasico", "negro blanco gris beige azul_marino",
       {"parte_superior": "camiseta jersey_cuello_alto camisa_oxford manga_larga",
        "capa_intermedia": "jersey_fino cardigan blazer",
        "abrigo": "gabardina abrigo_pano acolchada_ligera",
        "parte_inferior": "pantalon_vestir vaqueros chinos falda_midi",
        "pieza_unica": "vestido_manga_larga vestido_verano",
        "calzado": "zapatillas_urbanas mocasines botines"},
       "camiseta:blanco camisa_oxford:blanco jersey_fino:azul_marino vaqueros: pantalon_vestir:negro "
       "gabardina:beige zapatillas_urbanas:blanco",
       ["Reloj de esfera sencilla", "Bolso o mochila de piel lisa", "Cinturón fino de piel"],
       {"vaqueros": "rectos", "pantalon_vestir": "de corte recto"}),
    _s("clasico", "Clásico / preppy", "🎓", "Camisas Oxford, chinos y jerséis de punto: el estilo de siempre, bien hecho.",
       "clasico seguro tranquilo", "azul_marino blanco beige celeste burdeos verde",
       {"parte_superior": "camisa_oxford polo jersey_cuello_alto",
        "capa_intermedia": "jersey_fino blazer cardigan chaleco_acolchado",
        "abrigo": "abrigo_pano gabardina acolchada_ligera",
        "parte_inferior": "chinos vaqueros pantalon_vestir falda_midi",
        "pieza_unica": "vestido_manga_larga",
        "calzado": "mocasines botines zapatos_vestir"},
       "camisa_oxford:celeste polo:azul_marino chinos:beige blazer:azul_marino jersey_fino:burdeos "
       "mocasines:marron abrigo_pano:gris",
       ["Cinturón de piel marrón", "Reloj clásico", "Bufanda de cuadros"]),
    _s("casual", "Casual", "👟", "Cómodo y sencillo para el día a día: vaqueros, camisetas y zapatillas.",
       "relajado comodo", "azul blanco gris beige verde",
       {"parte_superior": "camiseta camiseta_estampada manga_larga camisa_oxford",
        "capa_intermedia": "sudadera cardigan jersey_fino",
        "abrigo": "cazadora_vaquera acolchada_ligera parka",
        "parte_inferior": "vaqueros chinos bermudas falda_midi",
        "pieza_unica": "vestido_verano",
        "calzado": "zapatillas_urbanas lona"},
       "camiseta:blanco camiseta:gris vaqueros: sudadera:gris cazadora_vaquera: zapatillas_urbanas:blanco",
       ["Gorra", "Mochila", "Gafas de sol"]),
    _s("streetwear", "Streetwear", "🛹", "Cultura urbana: sudaderas y prendas amplias, zapatillas protagonistas.",
       "atrevido seguro creativo", "negro blanco gris rojo verde",
       {"parte_superior": "camiseta_estampada camiseta",
        "capa_intermedia": "sudadera forro_polar",
        "abrigo": "plumifero cortavientos parka",
        "parte_inferior": "jogger vaqueros pantalon_corto",
        "calzado": "zapatillas_urbanas lona"},
       "sudadera:negro camiseta_estampada:blanco jogger:gris vaqueros: plumifero:negro zapatillas_urbanas:blanco",
       ["Gorra o gorro beanie", "Riñonera cruzada", "Calcetines altos"],
       {"sudadera": "oversize", "camiseta": "oversize", "camiseta_estampada": "oversize",
        "vaqueros": "anchos", "jogger": "ancho"}),
    _s("deportivo", "Athleisure", "🏃", "Ropa técnica y deportiva también fuera del gimnasio.",
       "deportivo comodo", "negro gris blanco azul verde",
       {"parte_superior": "camiseta_tecnica camiseta",
        "capa_intermedia": "sudadera forro_polar",
        "abrigo": "cortavientos softshell plumifero",
        "parte_inferior": "jogger mallas corto_deporte",
        "calzado": "running zapatillas_urbanas"},
       "camiseta_tecnica:negro jogger:gris sudadera:gris cortavientos:negro running:",
       ["Gorra técnica", "Mochila ligera", "Reloj deportivo"]),
    _s("bohemio", "Bohemio", "🌻", "Tejidos naturales, estampados y prendas fluidas con aire libre.",
       "relajado creativo alegre", "beige marron naranja verde blanco",
       {"parte_superior": "blusa camisa_lino camiseta_estampada",
        "capa_intermedia": "cardigan chal",
        "abrigo": "cazadora_vaquera gabardina",
        "parte_inferior": "falda_midi pantalon_lino vaqueros",
        "pieza_unica": "vestido_verano",
        "calzado": "sandalias botines"},
       "camisa_lino:blanco falda_midi:marron cardigan:beige vestido_verano:naranja botines:marron",
       ["Sombrero de ala ancha", "Bolso de flecos o de cesta", "Collares y pulseras superpuestas"],
       {"vaqueros": "acampanados", "falda_midi": "fluida"}),
    _s("romantico", "Romántico", "🎀", "Tonos suaves, volantes, lazos y tejidos delicados.",
       "alegre tranquilo elegante", "rosa blanco celeste beige burdeos",
       {"parte_superior": "blusa camiseta",
        "capa_intermedia": "cardigan chal",
        "abrigo": "gabardina abrigo_pano",
        "parte_inferior": "falda_midi pantalon_lino",
        "pieza_unica": "vestido_verano vestido_manga_larga",
        "calzado": "mocasines sandalias tacones"},
       "blusa:blanco cardigan:rosa falda_midi:beige vestido_verano:celeste mocasines:negro",
       ["Lazo o pinza para el pelo", "Bolso pequeño", "Pendientes de perla"],
       {"blusa": "con volantes", "falda_midi": "plisada"}),
    _s("elegante", "Elegante", "🖤", "Prendas estructuradas y tejidos nobles para ir siempre arreglado.",
       "elegante seguro clasico", "negro azul_marino gris blanco burdeos beige",
       {"parte_superior": "camisa_vestir jersey_cuello_alto blusa",
        "capa_intermedia": "blazer americana_traje",
        "abrigo": "abrigo_vestir abrigo_pano gabardina",
        "parte_inferior": "pantalon_vestir falda_midi",
        "pieza_unica": "vestido_coctel vestido_manga_larga",
        "calzado": "zapatos_vestir tacones mocasines botines"},
       "camisa_vestir:blanco blazer:negro pantalon_vestir:negro abrigo_vestir:gris jersey_cuello_alto:negro "
       "zapatos_vestir:negro",
       ["Reloj de vestir", "Bolso estructurado", "Cinturón de piel"]),
    _s("rockero", "Rockero", "🎸", "Cuero, negro y botas: actitud por encima de todo.",
       "atrevido seguro", "negro gris blanco burdeos",
       {"parte_superior": "camiseta_estampada camiseta",
        "capa_intermedia": "sudadera cardigan",
        "abrigo": "cazadora_cuero cazadora_vaquera",
        "parte_inferior": "vaqueros falda_midi",
        "calzado": "botines lona"},
       "cazadora_cuero:negro camiseta_estampada:negro vaqueros:negro botines:negro",
       ["Cinturón con tachuelas", "Anillos", "Bandana"],
       {"vaqueros": "pitillo"}),
    _s("vintage", "Vintage / retro", "📻", "Prendas con historia, colores tierra y cortes de otras décadas.",
       "creativo clasico", "marron naranja verde burdeos beige amarillo",
       {"parte_superior": "camisa_estampada polo camiseta_estampada",
        "capa_intermedia": "cardigan jersey_lana",
        "abrigo": "cazadora_vaquera gabardina cazadora_cuero",
        "parte_inferior": "pana vaqueros falda_midi",
        "pieza_unica": "vestido_manga_larga",
        "calzado": "lona mocasines"},
       "pana:marron cardigan:verde camisa_estampada: cazadora_vaquera: lona:beige",
       ["Gafas de sol redondas", "Pañuelo al cuello", "Bolso de piel vintage"]),
    _s("workwear", "Workwear", "🧰", "Prendas de trabajo resistentes: lona, pana, botas y colores tierra.",
       "relajado comodo", "marron beige verde azul_marino gris",
       {"parte_superior": "camiseta camisa_oxford",
        "capa_intermedia": "sudadera chaleco_acolchado forro_polar",
        "abrigo": "parka cazadora_vaquera acolchada_ligera",
        "parte_inferior": "vaqueros pana chinos",
        "calzado": "botines botas_agua"},
       "camiseta:blanco chaleco_acolchado:verde vaqueros: pana:marron parka:beige botines:marron",
       ["Gorro de punto", "Cinturón de lona o piel"],
       {"chinos": "de trabajo", "camisa_oxford": "sobrecamisa"}),
    _s("gorpcore", "Gorpcore / outdoor", "🏔️", "Ropa técnica de montaña para la ciudad: práctica y a prueba de clima.",
       "deportivo comodo", "verde naranja negro gris amarillo",
       {"parte_superior": "camiseta_tecnica manga_larga",
        "capa_intermedia": "forro_polar chaleco_acolchado",
        "abrigo": "softshell chubasquero plumifero cortavientos",
        "parte_inferior": "jogger chinos",
        "calzado": "trail zapatillas_impermeables"},
       "forro_polar:verde softshell:negro plumifero:naranja trail: camiseta_tecnica:gris",
       ["Gorro de punto técnico", "Mochila de montaña", "Riñonera"],
       {"chinos": "técnicos"}),
    _s("old_money", "Lujo discreto", "🥂", "Elegancia sin logos: tejidos nobles, tonos suaves y prendas atemporales.",
       "elegante clasico tranquilo", "beige blanco azul_marino celeste verde marron",
       {"parte_superior": "polo camisa_oxford jersey_cuello_alto",
        "capa_intermedia": "jersey_fino cardigan blazer",
        "abrigo": "abrigo_pano gabardina",
        "parte_inferior": "chinos pantalon_vestir falda_midi",
        "pieza_unica": "vestido_manga_larga",
        "calzado": "mocasines botines"},
       "jersey_fino:beige camisa_oxford:blanco chinos:beige abrigo_pano:beige polo:azul_marino mocasines:marron",
       ["Reloj clásico con correa de piel", "Jersey anudado a los hombros", "Bolso de piel sin logos"],
       {"jersey_fino": "de cachemira o merino"}),
    _s("y2k", "Y2K", "💿", "Los 2000 vuelven: tiro bajo, colores pastel, brillos y bolsos pequeños.",
       "atrevido alegre creativo", "rosa celeste morado blanco negro amarillo",
       {"parte_superior": "top_fiesta camiseta_estampada tirantes",
        "capa_intermedia": "sudadera cardigan",
        "abrigo": "plumifero cazadora_vaquera",
        "parte_inferior": "vaqueros jogger falda_midi",
        "calzado": "zapatillas_urbanas lona"},
       "camiseta_estampada:rosa vaqueros: cardigan:celeste plumifero:negro zapatillas_urbanas:blanco",
       ["Gafas de sol de colores", "Bolso baguette", "Horquillas y bisutería"],
       {"vaqueros": "de tiro bajo", "camiseta_estampada": "ajustada"}),
    _s("mediterraneo", "Mediterráneo", "🌊", "Lino, blanco y azul: ligero, fresco y con aire de vacaciones.",
       "relajado tranquilo alegre", "blanco beige celeste azul azul_marino",
       {"parte_superior": "camisa_lino camiseta polo blusa",
        "capa_intermedia": "cardigan jersey_fino",
        "abrigo": "gabardina cazadora_vaquera",
        "parte_inferior": "pantalon_lino bermudas chinos falda_midi",
        "pieza_unica": "vestido_verano",
        "calzado": "sandalias mocasines lona"},
       "camisa_lino:blanco pantalon_lino:beige polo:azul_marino bermudas:beige sandalias:marron",
       ["Sombrero de paja", "Capazo o cesta", "Gafas de sol"]),
]}


@dataclass(frozen=True)
class Brand:
    id: str
    name: str
    domain: str
    price: int  # 1 €, 2 €€, 3 €€€ (orientativo)
    styles: tuple[str, ...]
    slots: frozenset[str] | None = None  # partes del cuerpo que vende; None = de todo
    sustainable: bool = False
    kind: str = "marca"  # marca | multimarca | segunda_mano

    @property
    def url(self) -> str:
        return f"https://www.{self.domain}"

    def sells(self, slot: str) -> bool:
        return self.slots is None or slot in self.slots


_SHOES = frozenset({"calzado"})
_SPORT = None


def _b(id, name, domain, price, styles, slots=None, sustainable=False, kind="marca"):
    return Brand(id, name, domain, price, tuple(styles.split()),
                 frozenset(slots.split()) if slots else None, sustainable, kind)


BRANDS: dict[str, Brand] = {b.id: b for b in [
    _b("zara", "Zara", "zara.com", 2, "minimalista casual elegante streetwear"),
    _b("mango", "Mango", "mango.com", 2, "minimalista elegante romantico mediterraneo casual"),
    _b("massimo_dutti", "Massimo Dutti", "massimodutti.com", 3, "clasico old_money minimalista elegante"),
    _b("cos", "COS", "cos.com", 3, "minimalista elegante"),
    _b("uniqlo", "Uniqlo", "uniqlo.com", 1, "minimalista casual deportivo"),
    _b("hm", "H&M", "hm.com", 1, "casual minimalista y2k romantico"),
    _b("pull_bear", "Pull&Bear", "pullandbear.com", 1, "casual streetwear y2k"),
    _b("bershka", "Bershka", "bershka.com", 1, "streetwear y2k casual"),
    _b("stradivarius", "Stradivarius", "stradivarius.com", 1, "romantico casual y2k"),
    _b("lefties", "Lefties", "lefties.com", 1, "casual"),
    _b("primark", "Primark", "primark.com", 1, "casual deportivo"),
    _b("springfield", "Springfield", "springfield.com", 1, "casual clasico"),
    _b("arket", "Arket", "arket.com", 2, "minimalista casual"),
    _b("other_stories", "& Other Stories", "stories.com", 2, "romantico bohemio elegante"),
    _b("cortefiel", "Cortefiel", "cortefiel.com", 2, "clasico elegante"),
    _b("scalpers", "Scalpers", "scalperscompany.com", 2, "clasico old_money elegante"),
    _b("el_ganso", "El Ganso", "elganso.com", 2, "clasico vintage old_money"),
    _b("desigual", "Desigual", "desigual.com", 2, "bohemio"),
    _b("levis", "Levi's", "levi.com", 2, "casual vintage workwear rockero",
       "parte_inferior parte_superior abrigo capa_intermedia"),
    _b("carhartt", "Carhartt WIP", "carhartt-wip.com", 2, "workwear streetwear"),
    _b("dickies", "Dickies", "dickies.com", 2, "workwear streetwear"),
    _b("nike", "Nike", "nike.com", 2, "deportivo streetwear"),
    _b("adidas", "adidas", "adidas.com", 2, "deportivo streetwear vintage y2k"),
    _b("new_balance", "New Balance", "newbalance.com", 2, "deportivo casual gorpcore",
       "calzado parte_superior capa_intermedia parte_inferior"),
    _b("vans", "Vans", "vans.com", 2, "streetwear casual rockero", "calzado parte_superior capa_intermedia"),
    _b("converse", "Converse", "converse.com", 2, "casual rockero vintage", "calzado"),
    _b("dr_martens", "Dr. Martens", "drmartens.com", 2, "rockero workwear vintage", "calzado"),
    _b("veja", "Veja", "veja-store.com", 2, "minimalista casual", "calzado", sustainable=True),
    _b("ecoalf", "Ecoalf", "ecoalf.com", 2, "minimalista gorpcore casual", sustainable=True),
    _b("columbia", "Columbia", "columbia.com", 2, "gorpcore", "abrigo capa_intermedia parte_superior parte_inferior calzado"),
    _b("decathlon", "Decathlon", "decathlon.es", 1, "deportivo gorpcore"),
    _b("north_face", "The North Face", "thenorthface.com", 3, "gorpcore streetwear deportivo"),
    _b("patagonia", "Patagonia", "patagonia.com", 3, "gorpcore workwear", sustainable=True),
    _b("stussy", "Stüssy", "stussy.com", 3, "streetwear"),
    _b("ralph_lauren", "Ralph Lauren", "ralphlauren.com", 3, "clasico old_money"),
    _b("tommy", "Tommy Hilfiger", "tommy.com", 3, "clasico casual"),
    _b("lacoste", "Lacoste", "lacoste.com", 3, "clasico deportivo old_money"),
    _b("barbour", "Barbour", "barbour.com", 3, "clasico old_money workwear", "abrigo capa_intermedia parte_superior"),
    _b("hugo_boss", "BOSS", "hugoboss.com", 3, "elegante clasico"),
    _b("ganni", "Ganni", "ganni.com", 3, "romantico bohemio y2k"),
    _b("sezane", "Sézane", "sezane.com", 3, "romantico mediterraneo vintage"),
    _b("bimba_lola", "Bimba y Lola", "bimbaylola.com", 3, "elegante romantico"),
    # Tiendas donde encontrar de todo
    _b("zalando", "Zalando", "zalando.es", 2, "", kind="multimarca"),
    _b("asos", "ASOS", "asos.com", 1, "", kind="multimarca"),
    _b("vinted", "Vinted", "vinted.es", 1, "", sustainable=True, kind="segunda_mano"),
]}


@dataclass(frozen=True)
class Icon:
    """Referente de estilo: personas conocidas cuyo estilo se asocia a ciertos estilos.

    Solo guardamos su nombre y los estilos con los que se le asocia; no
    usamos su imagen ni hablamos en su nombre.
    """
    id: str
    name: str
    styles: tuple[str, ...]


ICONS: dict[str, Icon] = {i.id: i for i in [
    Icon("harry_styles", "Harry Styles", ("vintage", "rockero")),
    Icon("zendaya", "Zendaya", ("elegante", "minimalista")),
    Icon("rosalia", "Rosalía", ("streetwear", "y2k")),
    Icon("bad_bunny", "Bad Bunny", ("streetwear", "y2k")),
    Icon("hailey_bieber", "Hailey Bieber", ("minimalista", "casual")),
    Icon("jacob_elordi", "Jacob Elordi", ("vintage", "workwear", "minimalista")),
    Icon("timothee_chalamet", "Timothée Chalamet", ("vintage", "elegante")),
    Icon("asap_rocky", "A$AP Rocky", ("streetwear", "elegante")),
    Icon("kate_middleton", "Kate Middleton", ("clasico", "elegante")),
    Icon("sofia_richie", "Sofia Richie", ("old_money", "minimalista")),
    Icon("david_beckham", "David Beckham", ("clasico", "casual")),
    Icon("bella_hadid", "Bella Hadid", ("y2k", "vintage")),
    Icon("pedro_pascal", "Pedro Pascal", ("casual", "clasico")),
    Icon("paul_mescal", "Paul Mescal", ("casual", "vintage")),
]}

PRICE_LABELS = {1: "€", 2: "€€", 3: "€€€"}

# Temporada típica (hemisferio norte) -> nivel térmico del catálogo.
SEASONS = {
    12: ("invierno", 4), 1: ("invierno", 4), 2: ("invierno", 4),
    3: ("primavera", 3), 4: ("primavera", 2), 5: ("primavera", 1),
    6: ("verano", 0), 7: ("verano", 0), 8: ("verano", 0),
    9: ("otoño", 1), 10: ("otoño", 2), 11: ("otoño", 3),
}
