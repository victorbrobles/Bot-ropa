import asyncio

import httpx
import pytest

from bot_ropa.adapters.product_page.reader import HttpProductPageReader, parse_product_page
from bot_ropa.ports.wardrobe import ProductPageError

JSONLD_PAGE = """<html><head><title>Tienda</title>
<script type="application/ld+json">{"@context":"https://schema.org","@graph":[
  {"@type":"BreadcrumbList"},
  {"@type":"Product","name":"Jersey merino cuello redondo","brand":{"@type":"Brand","name":"Marca Z"},
   "sku":"MZ-42","color":"Verde botella","material":"100% lana merino",
   "description":"Jersey fino de punto &amp; suave"}]}</script>
</head><body><h1>Jersey</h1></body></html>"""

OG_PAGE = """<html><head><meta property="og:title" content="Camisa Oxford azul">
<meta property="product:brand" content="Marca O"></head>
<body><p>Composición: 100% algodón</p><script>var x = "50% nada";</script></body></html>"""


def test_parses_jsonld_graph():
    p = parse_product_page(JSONLD_PAGE, "https://t.example/p")
    assert (p.name, p.brand, p.reference, p.color) == ("Jersey merino cuello redondo", "Marca Z", "MZ-42", "Verde botella")
    assert p.material == "100% lana merino"
    assert p.description == "Jersey fino de punto & suave"


def test_falls_back_to_open_graph_and_visible_text():
    p = parse_product_page(OG_PAGE, "https://t.example/p")
    assert p.name == "Camisa Oxford azul" and p.brand == "Marca O"
    assert "100% algodón" in p.page_text and "50% nada" not in p.page_text


async def allow(host, port):
    if host.endswith(".internal"):
        raise ProductPageError("Ese enlace no apunta a una web pública.")


def reader(handler, check=allow):
    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False)
    return HttpProductPageReader(client, check_host=check)


def test_reads_page_following_safe_redirects():
    def handler(req):
        if req.url.path == "/old":
            return httpx.Response(301, headers={"location": "/new"})
        return httpx.Response(200, html=JSONLD_PAGE)
    p = asyncio.run(reader(handler).read("https://shop.example/old"))
    assert p.brand == "Marca Z" and p.url == "https://shop.example/new"


def test_blocks_internal_hosts_even_after_redirect():
    def handler(req):
        return httpx.Response(302, headers={"location": "http://admin.internal/secret"})
    with pytest.raises(ProductPageError, match="pública"):
        asyncio.run(reader(handler).read("https://shop.example/p"))
    with pytest.raises(ProductPageError):
        asyncio.run(reader(lambda r: httpx.Response(200)).read("https://shop.example:8080/p"))


def test_real_check_rejects_loopback():
    from bot_ropa.adapters.product_page.reader import _public_host
    with pytest.raises(ProductPageError):
        asyncio.run(_public_host("127.0.0.1", 80))


def test_blocked_shop_gives_friendly_error():
    with pytest.raises(ProductPageError, match="no deja leer"):
        asyncio.run(reader(lambda r: httpx.Response(403)).read("https://shop.example/p"))
