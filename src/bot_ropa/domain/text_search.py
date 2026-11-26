"""Búsqueda de texto en español, sencilla y gratuita (BM25 + sinónimos).

Sirve para encontrar, entre tus outfits guardados, los que mejor encajan con
lo que describes ("cena con amigos un sábado"). Sin IA: normaliza las
palabras (minúsculas, sin acentos, plurales), las agrupa por significado
("boda", "ceremonia" y "gala" cuentan como el mismo concepto) y puntúa con
BM25, el algoritmo clásico de los buscadores.
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

STOPWORDS = set("""
a al algo algun alguna algunas alguno algunos ante antes aqui asi bajo bien cada como con contra cual cuando
de del desde donde dos e el ella ellas ellos en entre era es esa esas ese eso esos esta estaba estar este esto
estos fue ha hace hacer hasta hay la las le les lo los mas me mi mis mucho muy nada ni no nos nosotros o os otra
otro para pero poco por porque que quien se ser si sin sobre su sus tal tambien te tengo ti tiene toda todo
tu tus un una unas uno unos y ya yo voy vamos ir quiero ponerme poner llevar puesto algo hoy dia
""".split())

# Conceptos: palabras que significan lo mismo para elegir ropa.
CONCEPTS: dict[str, tuple[str, ...]] = {
    "#etiqueta": ("boda", "bodas", "bautizo", "comunion", "gala", "ceremonia", "etiqueta", "evento", "graduacion",
                  "invitada", "invitado", "padrino", "madrina", "coctel"),
    "#fiesta": ("fiesta", "cumpleanos", "cumple", "discoteca", "noche", "salir", "copas", "concierto", "festival",
                "fiestas", "nochevieja", "party", "bar"),
    "#trabajo": ("trabajo", "oficina", "reunion", "entrevista", "curro", "presentacion", "cliente", "clientes",
                 "laboral", "trabajar"),
    "#cita": ("cena", "cenar", "restaurante", "cita", "comida", "comer", "romantica", "romantico", "aniversario",
              "brunch"),
    "#verano": ("playa", "piscina", "vacaciones", "verano", "calor", "caluroso", "agosto", "julio", "junio", "sol"),
    "#invierno": ("invierno", "frio", "nieve", "navidad", "helando", "diciembre", "enero", "febrero", "esqui"),
    "#entretiempo": ("primavera", "otono", "entretiempo", "fresco", "templado"),
    "#deporte": ("deporte", "gimnasio", "gym", "correr", "running", "entrenar", "entreno", "padel", "tenis",
                 "futbol", "yoga", "pilates", "senderismo", "montana", "excursion", "bici"),
    "#diario": ("casual", "diario", "finde", "fin", "semana", "paseo", "pasear", "compras", "recados", "tranquilo",
                "relajado", "planes", "amigos", "amigas", "familia", "domingo", "sabado"),
    "#lluvia": ("lluvia", "llueve", "lluvioso", "llover", "chubasco", "tormenta"),
    "#elegante": ("elegante", "arreglado", "arreglada", "formal", "vestir", "sofisticado", "chic", "traje"),
    "#comodo": ("comodo", "comoda", "comodidad", "chandal", "sport"),
    "#viaje": ("viaje", "viajar", "avion", "tren", "aeropuerto", "maleta", "escapada"),
}
_WORD_TO_CONCEPT: dict[str, str] = {}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "").replace("ñ", "n")
    return "".join(c for c in text if not unicodedata.combining(c)).lower()


def stem(word: str) -> str:
    """Raíz aproximada en español: quita plurales y la vocal final (boda/bodas -> bod)."""
    if len(word) > 4 and word.endswith("es"):
        word = word[:-2]
    elif len(word) > 3 and word.endswith("s"):
        word = word[:-1]
    if len(word) > 4 and word[-1] in "aeo":
        word = word[:-1]
    return word


for _concept, _words in CONCEPTS.items():
    for _w in _words:
        _WORD_TO_CONCEPT[stem(_w)] = _concept

_TOKEN = re.compile(r"[a-z0-9]+")


def tokens(text: str) -> list[str]:
    """Raíces + conceptos de un texto, sin palabras vacías."""
    out = []
    for word in _TOKEN.findall(normalize(text)):
        if word in STOPWORDS or len(word) < 2:
            continue
        root = stem(word)
        out.append(root)
        if root in _WORD_TO_CONCEPT:
            out.append(_WORD_TO_CONCEPT[root])
    return out


@dataclass(frozen=True)
class Hit:
    doc_id: str
    score: float
    matched: tuple[str, ...]  # palabras de la consulta que han coincidido (tal como las escribió)


class BM25:
    def __init__(self, docs: dict[str, str], k1: float = 1.4, b: float = 0.6):
        self.k1, self.b = k1, b
        self.docs = {doc_id: Counter(tokens(text)) for doc_id, text in docs.items()}
        self.lengths = {d: sum(c.values()) for d, c in self.docs.items()}
        self.avg = (sum(self.lengths.values()) / len(self.docs)) if self.docs else 0
        self.df = Counter(t for c in self.docs.values() for t in c)

    def idf(self, term: str) -> float:
        n, df = len(self.docs), self.df.get(term, 0)
        return math.log(1 + (n - df + 0.5) / (df + 0.5))

    def search(self, query: str) -> list[Hit]:
        words = [w for w in _TOKEN.findall(normalize(query)) if w not in STOPWORDS and len(w) >= 2]
        # Cada palabra de la consulta aporta su raíz y, si la tiene, su concepto.
        terms: list[tuple[str, str, float]] = []
        for w in words:
            root = stem(w)
            terms.append((root, w, 1.0))
            if root in _WORD_TO_CONCEPT:
                terms.append((_WORD_TO_CONCEPT[root], w, 0.8))  # sinónimos: algo menos que la palabra exacta
        hits = []
        for doc_id, counts in self.docs.items():
            score, matched = 0.0, []
            length = self.lengths[doc_id] or 1
            for term, original, weight in terms:
                tf = counts.get(term, 0)
                if not tf:
                    continue
                norm = tf * (self.k1 + 1) / (tf + self.k1 * (1 - self.b + self.b * length / (self.avg or 1)))
                score += weight * self.idf(term) * norm
                if original not in matched:
                    matched.append(original)
            if score > 0:
                hits.append(Hit(doc_id, round(score, 3), tuple(matched)))
        return sorted(hits, key=lambda h: -h.score)
