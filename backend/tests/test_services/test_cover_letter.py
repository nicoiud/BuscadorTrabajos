from dataclasses import dataclass, field
from typing import Any

import pytest

from app.services.enrichment import cover_letter
from app.services.enrichment.cover_letter import CoverLetterError, generate_cover_letter


@dataclass
class FakeToolUseBlock:
    input: dict[str, Any]
    type: str = "tool_use"


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


def _patch_client(monkeypatch, response: FakeMessage) -> None:
    monkeypatch.setattr(cover_letter, "get_client", lambda: FakeClient(response))


async def test_generate_cover_letter_parses_tool_use_response(monkeypatch):
    response = FakeMessage(
        content=[
            FakeToolUseBlock(
                input={
                    "cover_letter": "Estimados, me postulo para el puesto de Backend Engineer...",
                    "key_points": ["5 años con Python", "Experiencia en equipos remotos"],
                }
            )
        ]
    )
    _patch_client(monkeypatch, response)

    result = await generate_cover_letter(
        "Backend Engineer", "Acme", "Buscamos un backend engineer...", "Soy dev Python senior"
    )

    assert "me postulo" in result.cover_letter
    assert result.key_points == ["5 años con Python", "Experiencia en equipos remotos"]


async def test_generate_cover_letter_raises_when_no_tool_use_block(monkeypatch):
    _patch_client(monkeypatch, FakeMessage(content=[]))

    with pytest.raises(CoverLetterError):
        await generate_cover_letter("Title", "Company", "Description", "Profile")


async def test_generate_cover_letter_raises_on_missing_field(monkeypatch):
    _patch_client(
        monkeypatch, FakeMessage(content=[FakeToolUseBlock(input={"cover_letter": "X"})])
    )

    with pytest.raises(CoverLetterError):
        await generate_cover_letter("Title", "Company", "Description", "Profile")
