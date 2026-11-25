"""Identificador de demostración: respuestas fijas, sin red ni coste.

Sirve para desarrollar la interfaz (GARMENT_IDENTIFIER=demo). Nunca en producción.
"""

from __future__ import annotations

from ...domain.wardrobe import AlternativeMatch, GarmentDetails, Identification, IdentifyRequest


class DemoGarmentIdentifier:
    async def identify(self, request: IdentifyRequest) -> Identification:
        if request.rejected or request.product_url or request.description:
            text = (request.description or "").strip()
            return Identification(
                status="identificada",
                confidence=0.9,
                candidate=GarmentDetails.from_dict({
                    "name": text[:60] or "Jersey de punto de lana merino",
                    "base_type": "jersey_fino",
                    "brand": "Marca Demo",
                    "model": "Merino Crew",
                    "reference": "DEMO-0002",
                    "colors": [{"name": "verde botella", "palette_id": "verde", "hex": "#2f5d43"}],
                    "materials": [{"fiber": "lana merino", "percent": 100}],
                    "levels": [2, 3, 4],
                    "occasions": ["diario", "trabajo"],
                    "tags": ["clasico", "tranquilo"],
                    "product_url": request.product_url,
                }),
                message="(Demo) Con los datos que has dado, la ficha del producto coincide.",
                sources=tuple(u for u in [request.product_url] if u),
            )
        return Identification(
            status="parcial",
            confidence=0.55,
            candidate=GarmentDetails.from_dict({
                "name": "Camisa Oxford de manga larga",
                "base_type": "camisa_oxford",
                "brand": "Marca Demo",
                "model": "Oxford Regular Fit",
                "reference": None,
                "colors": [{"name": "azul celeste", "palette_id": "celeste", "hex": "#a9c8ea"}],
                "materials": [{"fiber": "algodón", "percent": None}],
                "levels": [1, 2, 3],
                "occasions": ["diario", "trabajo"],
                "tags": ["clasico"],
            }),
            message="(Demo) Parece una camisa Oxford de algodón. He visto el logo, pero no la etiqueta "
                    "de composición, así que los porcentajes no están confirmados.",
            unconfirmed=("modelo", "referencia", "composicion"),
            alternatives=(AlternativeMatch("Otra Marca · Oxford Slim"),),
        )
