from dataclasses import dataclass, field
from typing import Any

from app.services.enrichment import field_answer
from app.services.enrichment.field_answer import generate_field_answer


@dataclass
class FakeTextBlock:
    text: str
    type: str = "text"


@dataclass
class FakeMessage:
    content: list[Any] = field(default_factory=list)


class FakeMessages:
    def __init__(self, response: FakeMessage):
        self._response = response

    async def create(self, **kwargs):
        return self._response


class FakeClient:
    def __init__(self, response: FakeMessage):
        self.messages = FakeMessages(response)


async def test_generate_field_answer_returns_trimmed_text(monkeypatch):
    response = FakeMessage(content=[FakeTextBlock(text="  Disponibilidad inmediata.  ")])
    monkeypatch.setattr(field_answer, "get_client", lambda: FakeClient(response))

    result = await generate_field_answer("¿Cuál es tu disponibilidad?", "Perfil de prueba")

    assert result == "Disponibilidad inmediata."


async def test_generate_field_answer_returns_empty_string_without_text_block(monkeypatch):
    monkeypatch.setattr(field_answer, "get_client", lambda: FakeClient(FakeMessage(content=[])))

    result = await generate_field_answer("Campo", "Perfil")

    assert result == ""
