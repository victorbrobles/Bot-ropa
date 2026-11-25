import asyncio
from types import SimpleNamespace as NS

import pytest

from bot_ropa.adapters.identify.claude import ClaudeGarmentIdentifier
from bot_ropa.domain.wardrobe import IdentifyRequest, Photo
from bot_ropa.ports.wardrobe import IdentificationError

RESULT = {
    "status": "identificada", "confidence": 1.7, "message": "Lo he encontrado.",
    "unconfirmed": [], "alternatives": [], "sources": ["https://marca.example/p/1", "ftp://x"],
    "candidate": {
        "name": "Parka Ártica", "base_type": "parka", "brand": "Marca", "model": "Ártica",
        "reference": "123", "colors": [{"name": "verde oliva", "palette_id": "verde", "hex": "#556b2f"}],
        "materials": [{"fiber": "poliéster", "percent": 100}], "pattern": "liso", "levels": [4, 5],
        "waterproof": True, "windproof": True, "occasions": ["diario"], "tags": ["comodo"],
        "fit": "unisex", "product_url": "https://marca.example/p/1", "notes": None,
    },
}


def tool_call(data):
    return NS(type="tool_use", name="submit_garment", input=data)


class FakeClient:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
        self.beta = NS(messages=NS(create=self.create))

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return self.responses.pop(0)


def run(client, request=None):
    request = request or IdentifyRequest(photos=(Photo(b"\xff\xd8\xffdata", "image/jpeg"),),
                                         rejected=("Marca X · Modelo Y",))
    return asyncio.run(ClaudeGarmentIdentifier(client).identify(request))


def test_parses_result_and_sends_photos_tools_and_fallbacks():
    client = FakeClient([NS(stop_reason="tool_use", content=[tool_call(RESULT)])])
    r = run(client)
    assert r.status == "identificada" and r.confidence == 1.0
    assert r.candidate.brand == "Marca" and r.candidate.waterproof
    assert r.sources == ("https://marca.example/p/1",)
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default"
    assert {t.get("name") for t in call["tools"]} >= {"web_search", "web_fetch", "submit_garment"}
    content = call["messages"][0]["content"]
    assert any(b["type"] == "image" for b in content)
    assert "Marca X · Modelo Y" in content[-1]["text"]


def test_resumes_after_pause_turn_and_reminds_if_no_tool_call():
    paused = NS(stop_reason="pause_turn", content=[NS(type="server_tool_use", name="web_search", input={})])
    finished = NS(stop_reason="end_turn", content=[NS(type="text", text="Creo que es una parka")])
    client = FakeClient([paused, finished, NS(stop_reason="tool_use", content=[tool_call(RESULT)])])
    r = run(client)
    assert r.candidate is not None
    roles = [m["role"] for m in client.calls[2]["messages"]]
    assert roles == ["user", "assistant", "assistant", "user"]


def test_refusal_and_never_finishing_raise():
    with pytest.raises(IdentificationError):
        run(FakeClient([NS(stop_reason="refusal", content=[])]))
    with pytest.raises(IdentificationError):
        run(FakeClient([NS(stop_reason="end_turn", content=[])] * 4))


def test_invalid_candidate_becomes_unknown():
    bad = {**RESULT, "candidate": {**RESULT["candidate"], "base_type": "inventado"}}
    r = run(FakeClient([NS(stop_reason="tool_use", content=[tool_call(bad)])]))
    assert r.status == "desconocida" and r.candidate is None
