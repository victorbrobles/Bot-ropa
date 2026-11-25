"""Lee la ficha de un producto a partir de su enlace (sin coste: una petición HTTP).

Casi todas las tiendas publican datos estructurados (JSON-LD de schema.org o
etiquetas Open Graph) con el nombre, la marca, la referencia, el color y a
veces el material. Si la tienda bloquea las peticiones automáticas, se avisa
al usuario para que complete los datos.

Seguridad: como la URL la elige el usuario, solo se permiten destinos
públicos (nada de localhost ni redes internas), en cada redirección.
"""

from __future__ import annotations

import asyncio
import html
import ipaddress
import json
import re
import socket
from urllib.parse import urljoin, urlsplit

import httpx

from ...domain.wardrobe import ProductInfo
from ...ports.wardrobe import ProductPageError

MAX_BYTES = 3 * 1024 * 1024
MAX_REDIRECTS = 4
HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; VestiaBot/0.1; ficha de producto)",
    "Accept": "text/html,application/xhtml+xml",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
}


async def _public_host(host: str, port: int) -> None:
    try:
        infos = await asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except OSError as exc:
        raise ProductPageError("No encontramos esa web. Revisa el enlace.") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        if not ip.is_global:
            raise ProductPageError("Ese enlace no apunta a una web pública.")


class HttpProductPageReader:
    def __init__(self, client: httpx.AsyncClient | None = None, check_host=_public_host):
        self._client = client or httpx.AsyncClient(timeout=10.0, headers=HEADERS, follow_redirects=False)
        self._check_host = check_host

    async def read(self, url: str) -> ProductInfo:
        page_url = url
        for _ in range(MAX_REDIRECTS + 1):
            parts = urlsplit(page_url)
            if parts.scheme not in ("http", "https") or not parts.hostname:
                raise ProductPageError("El enlace no es válido.")
            port = parts.port or (443 if parts.scheme == "https" else 80)
            if port not in (80, 443):
                raise ProductPageError("Ese enlace no apunta a una web pública.")
            await self._check_host(parts.hostname, port)
            try:
                async with self._client.stream("GET", page_url) as res:
                    if res.is_redirect and "location" in res.headers:
                        page_url = urljoin(page_url, res.headers["location"])
                        continue
                    if res.status_code in (401, 403, 429):
                        raise ProductPageError("Esa tienda no deja leer su web automáticamente. "
                                               "Completa los datos a mano o escribe una descripción.")
                    if res.status_code >= 400:
                        raise ProductPageError("No hemos podido abrir esa página (¿enlace caducado?).")
                    if "html" not in res.headers.get("content-type", "html"):
                        raise ProductPageError("Ese enlace no es una página de producto.")
                    body = bytearray()
                    async for chunk in res.aiter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_BYTES:
                            break
                    text = body.decode(res.encoding or "utf-8", errors="replace")
            except httpx.HTTPError as exc:
                raise ProductPageError("La web de la tienda no responde.") from exc
            return parse_product_page(text, page_url)
        raise ProductPageError("Demasiadas redirecciones en ese enlace.")

    async def aclose(self) -> None:
        await self._client.aclose()


# ------------------------------------------------------------------ parseo
_JSONLD = re.compile(r"<script[^>]+type=[\"']application/ld\+json[\"'][^>]*>(.*?)</script>", re.S | re.I)
_META = re.compile(r"<meta\s+[^>]*>", re.I)
_ATTR = re.compile(r"([a-zA-Z:_-]+)\s*=\s*([\"'])(.*?)\2", re.S)
_TITLE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)
_TAGS = re.compile(r"<(script|style|noscript|svg)[^>]*>.*?</\1>|<[^>]+>", re.S | re.I)


def parse_product_page(page: str, url: str) -> ProductInfo:
    product = _jsonld_product(page)
    meta = _metas(page)
    title = _TITLE.search(page)

    def first(*values):
        return next((_clean(v) for v in values if _clean(v)), None)

    brand = product.get("brand")
    if isinstance(brand, list):
        brand = brand[0] if brand else None
    if isinstance(brand, dict):
        brand = brand.get("name")
    offers = product.get("offers")
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    visible = _clean(_TAGS.sub(" ", page[:600_000]), 40_000)
    return ProductInfo(
        url=url,
        name=first(product.get("name"), meta.get("og:title"), title.group(1) if title else None),
        brand=first(brand, meta.get("product:brand"), meta.get("og:brand")),
        reference=first(product.get("sku"), product.get("mpn"), product.get("productID"),
                        (offers or {}).get("sku") if isinstance(offers, dict) else None),
        color=first(product.get("color"), meta.get("product:color")),
        material=first(product.get("material"), meta.get("product:material")),
        description=first(product.get("description"), meta.get("og:description"), meta.get("description")),
        page_text=visible,
    )


def _jsonld_product(page: str) -> dict:
    for block in _JSONLD.findall(page):
        try:
            data = json.loads(html.unescape(block.strip()))
        except ValueError:
            continue
        for node in _walk(data):
            types = node.get("@type")
            types = types if isinstance(types, list) else [types]
            if any(t in ("Product", "ProductGroup", "IndividualProduct") for t in types):
                return node
    return {}


def _walk(data):
    if isinstance(data, dict):
        yield data
        for key in ("@graph", "hasVariant", "mainEntity", "itemListElement"):
            if key in data:
                yield from _walk(data[key])
    elif isinstance(data, list):
        for item in data:
            yield from _walk(item)


def _metas(page: str) -> dict:
    out = {}
    for tag in _META.findall(page[:300_000]):
        attrs = {k.lower(): v for k, _, v in _ATTR.findall(tag)}
        key = attrs.get("property") or attrs.get("name")
        if key and "content" in attrs:
            out.setdefault(key.lower(), html.unescape(attrs["content"]))
    return out


def _clean(value, limit: int = 600):
    if value is None or isinstance(value, (dict, list)):
        return None
    text = " ".join(html.unescape(str(value)).split())
    return text[:limit] or None
