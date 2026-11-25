"""Identificación de prendas con Claude (visión + búsqueda y lectura web).

Claude mira las fotos (logos, etiquetas de marca y composición, forma, tejido),
abre el enlace si lo hay, busca la ficha oficial del producto y devuelve el
resultado llamando a la herramienta `submit_garment`, cuyo esquema es estricto.
"""

from __future__ import annotations

import base64
import logging

import anthropic

from ...domain.catalog import CATALOG, LEVEL_LABELS
from ...domain.options import COLORS, OCCASIONS
from ...domain.wardrobe import (
    FITS, PATTERNS, STYLE_TAGS, AlternativeMatch, GarmentDetails, Identification,
    IdentifyRequest, InvalidGarment,
)
from ...ports.wardrobe import IdentificationError

log = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"
MAX_ROUNDS = 4  # pause_turn de la búsqueda web + un recordatorio si no llama a la herramienta


def _nullable(schema: dict) -> dict:
    return {"anyOf": [schema, {"type": "null"}]}


def _obj(properties: dict) -> dict:
    return {"type": "object", "properties": properties,
            "required": list(properties), "additionalProperties": False}


_STR = {"type": "string"}

GARMENT_SCHEMA = _obj({
    "name": {**_STR, "description": "Nombre corto y descriptivo en español, p. ej. 'Camisa Oxford slim'"},
    "base_type": {"type": "string", "enum": [g.id for g in CATALOG],
                  "description": "Tipo genérico más parecido del catálogo"},
    "brand": _nullable(_STR),
    "model": _nullable({**_STR, "description": "Nombre del modelo o línea según la marca"}),
    "reference": _nullable({**_STR, "description": "Referencia, SKU o código de artículo"}),
    "colors": {"type": "array", "items": _obj({
        "name": {**_STR, "description": "Nombre del color en español (comercial si se conoce)"},
        "palette_id": {"type": "string", "enum": list(COLORS)},
        "hex": {**_STR, "description": "Color aproximado en formato #rrggbb"},
    })},
    "materials": {"type": "array", "items": _obj({
        "fiber": {**_STR, "description": "Fibra en español: algodón, poliéster reciclado, lana merino..."},
        "percent": _nullable({"type": "number"}),
    })},
    "pattern": {"type": "string", "enum": list(PATTERNS)},
    "levels": {"type": "array", "items": {"type": "integer", "enum": list(range(6))}},
    "waterproof": {"type": "boolean"},
    "windproof": {"type": "boolean"},
    "occasions": {"type": "array", "items": {"type": "string", "enum": list(OCCASIONS)}},
    "tags": {"type": "array", "items": {"type": "string", "enum": list(STYLE_TAGS)}},
    "fit": {"type": "string", "enum": list(FITS)},
    "product_url": _nullable({**_STR, "description": "URL de la ficha del producto (preferible la web oficial)"}),
    "notes": _nullable(_STR),
})

SUBMIT_TOOL = {
    "name": "submit_garment",
    "description": "Entrega el resultado final de la identificación de la prenda. Llámala una sola vez, al final.",
    "strict": True,
    "input_schema": _obj({
        "status": {"type": "string", "enum": list(Identification.STATUSES),
                   "description": "identificada: marca y modelo confirmados; parcial: tipo y atributos "
                                  "claros pero falta confirmar marca/modelo/composición; desconocida: no hay "
                                  "información suficiente"},
        "confidence": {"type": "number", "description": "Confianza de 0 a 1 en que el candidato es la prenda exacta"},
        "message": {**_STR, "description": "Explicación breve en español para el usuario: qué has visto, "
                                           "qué has confirmado y cómo"},
        "unconfirmed": {"type": "array", "items": {"type": "string", "enum": [
            "marca", "modelo", "referencia", "composicion", "colores", "tipo"]}},
        "candidate": _nullable(GARMENT_SCHEMA),
        "alternatives": {"type": "array", "items": _obj({
            "label": {**_STR, "description": "Marca y modelo alternativos posibles"},
            "product_url": _nullable(_STR),
        })},
        "sources": {"type": "array", "items": _STR},
    }),
}

TOOLS = [
    {"type": "web_search_20260209", "name": "web_search", "max_uses": 6},
    {"type": "web_fetch_20260209", "name": "web_fetch", "max_uses": 4},
    SUBMIT_TOOL,
]

_CATALOG_LINES = "\n".join(f"- {g.id}: {g.name}" for g in CATALOG)
_LEVEL_LINES = "\n".join(f"- {k}: {v}" for k, v in LEVEL_LABELS.items())

SYSTEM = f"""Eres un experto en producto textil y moda. Identificas con exactitud prendas concretas para el \
armario digital de una app que recomienda qué ponerse según el tiempo. Lo que guardes se usará para \
saber cuánto abriga, si protege de la lluvia o del viento y cómo combinar colores, así que la exactitud \
importa más que la rapidez.

Cómo trabajar:
1. Examina las fotos con detalle: logotipos, etiquetas de marca, talla y composición, códigos de \
artículo, forma, cuello, cierres, costuras, tejido y color.
2. Si el usuario da un enlace, ábrelo con web_fetch y usa los datos de esa ficha.
3. Usa web_search para encontrar la ficha del producto, priorizando la web oficial de la marca, y \
confirmar modelo, referencia, composición y nombre comercial del color.
4. Cuando termines, llama a submit_garment una sola vez.

Honestidad (muy importante):
- No inventes. Una marca o modelo solo es seguro si lo ves en la foto o lo confirma una ficha de producto \
que encaja con lo que se ve. Si no puedes confirmarlo, déjalo en null y añádelo a `unconfirmed`.
- La composición solo es exacta si la lees en la etiqueta o en la ficha oficial. Si la estimas por el \
aspecto del tejido, pon los porcentajes a null y añade "composicion" a `unconfirmed`.
- Si el usuario ya rechazó candidatos, no los vuelvas a proponer.
- `confidence` refleja la probabilidad de que el candidato sea exactamente esa prenda.
- Escribe todo en español.

Atributos para el recomendador:
- base_type: el tipo genérico más parecido de este catálogo:
{_CATALOG_LINES}
- levels: niveles térmicos (según sensación térmica) en los que la prenda es cómoda, teniendo en cuenta \
su tipo, grosor y materiales (lana, plumón o forro abrigan más; lino o algodón fino, menos):
{_LEVEL_LINES}
  (0: 24 °C o más · 1: 18-24 · 2: 13-18 · 3: 8-13 · 4: 3-8 · 5: menos de 3)
- waterproof/windproof solo si la prenda lo es de verdad (membrana, tejido técnico, encerado...).
- colors: del más al menos predominante, con el id de paleta más cercano.
"""


class ClaudeGarmentIdentifier:
    def __init__(self, client: anthropic.AsyncAnthropic | None = None, model: str = MODEL):
        self._client = client or anthropic.AsyncAnthropic(timeout=240.0, max_retries=2)
        self._model = model

    async def identify(self, request: IdentifyRequest) -> Identification:
        messages: list[dict] = [{"role": "user", "content": _user_content(request)}]
        for _ in range(MAX_ROUNDS):
            response = await self._create(messages)
            if response.stop_reason == "refusal":
                raise IdentificationError("No se ha podido analizar esta imagen")
            call = next((b for b in response.content
                         if b.type == "tool_use" and b.name == "submit_garment"), None)
            if call is not None:
                return _to_identification(call.input)
            messages.append({"role": "assistant", "content": response.content})
            if response.stop_reason != "pause_turn":
                # Terminó sin entregar: se lo recordamos una vez más.
                messages.append({"role": "user", "content":
                                 "Entrega ahora el resultado llamando a submit_garment con lo que hayas averiguado."})
        raise IdentificationError("La identificación no ha terminado; inténtalo de nuevo")

    async def _create(self, messages: list[dict]):
        try:
            return await self._client.beta.messages.create(
                model=self._model,
                max_tokens=16000,
                system=SYSTEM,
                tools=TOOLS,
                messages=messages,
                output_config={"effort": "high"},
                # Si un filtro de seguridad rechaza la petición, la API la reintenta
                # en el modelo de respaldo adecuado dentro de la misma llamada.
                betas=["server-side-fallback-2026-07-01"],
                fallbacks="default",
            )
        except anthropic.AuthenticationError as exc:
            raise IdentificationError("Falta configurar la clave de la API de Anthropic") from exc
        except anthropic.RateLimitError as exc:
            raise IdentificationError("Hay muchas peticiones ahora mismo; inténtalo en un minuto") from exc
        except anthropic.BadRequestError as exc:
            log.error("Petición rechazada por la API: %s", exc.message)
            raise IdentificationError("No se ha podido procesar la foto") from exc
        except (anthropic.APIStatusError, anthropic.APIConnectionError) as exc:
            log.error("Error de la API de Anthropic: %s", exc)
            raise IdentificationError("El servicio de identificación no responde") from exc


def _user_content(req: IdentifyRequest) -> list[dict]:
    content: list[dict] = []
    for i, photo in enumerate(req.photos, 1):
        content.append({"type": "text", "text": f"Foto {i}:"})
        content.append({"type": "image", "source": {
            "type": "base64", "media_type": photo.media_type,
            "data": base64.standard_b64encode(photo.data).decode("ascii")}})
    lines = ["Identifica esta prenda para guardarla en mi armario."]
    if req.product_url:
        lines.append(f"Enlace del producto: {req.product_url}")
    if req.description:
        lines.append(f"Lo que sé de ella: {req.description}")
    if req.rejected:
        lines.append("NO es ninguna de estas (ya las he descartado): " + "; ".join(req.rejected))
    content.append({"type": "text", "text": "\n".join(lines)})
    return content


def _to_identification(data: dict) -> Identification:
    candidate = None
    if data.get("candidate"):
        try:
            candidate = GarmentDetails.from_dict(data["candidate"])
        except InvalidGarment:
            candidate = None
    status = data.get("status") if data.get("status") in Identification.STATUSES else "desconocida"
    if candidate is None:
        status = "desconocida"
    try:
        confidence = min(1.0, max(0.0, float(data.get("confidence") or 0)))
    except (TypeError, ValueError):
        confidence = 0.0
    alternatives = tuple(
        AlternativeMatch(str(a.get("label"))[:120], a.get("product_url"))
        for a in data.get("alternatives") or [] if isinstance(a, dict) and a.get("label")
    )[:3]
    sources = tuple(s for s in data.get("sources") or []
                    if isinstance(s, str) and s.startswith(("http://", "https://")))[:6]
    return Identification(
        status=status,
        confidence=confidence,
        candidate=candidate,
        message=str(data.get("message") or "")[:600],
        unconfirmed=tuple(dict.fromkeys(data.get("unconfirmed") or [])),
        alternatives=alternatives,
        sources=sources,
    )
