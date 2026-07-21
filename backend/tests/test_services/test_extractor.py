from dataclasses import dataclass, field
from typing import Any

import pytest

from app.services.enrichment import extractor
from app.services.enrichment.extractor import ExtractionError, extract_job_fields


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
    monkeypatch.setattr(extractor, "get_client", lambda: FakeClient(response))


async def test_extract_job_fields_parses_tool_use_response(monkeypatch):
    response = FakeMessage(
        content=[
            FakeToolUseBlock(
                input={
                    "title_normalized": "Senior Backend Engineer",
                    "company_normalized": "Acme Remote",
                    "seniority": "senior",
                    "modality": "remote",
                    "salary_min": 80000,
                    "salary_max": 110000,
                    "currency": "USD",
                    "requirements": ["Python", "PostgreSQL", "AWS"],
                    "summary": "Build and scale Acme's backend platform.",
                }
            )
        ]
    )
    _patch_client(monkeypatch, response)

    result = await extract_job_fields("Senior Backend Eng", "Acme", "We need a backend eng...")

    assert result.title_normalized == "Senior Backend Engineer"
    assert result.seniority == "senior"
    assert result.modality == "remote"
    assert result.requirements == ["Python", "PostgreSQL", "AWS"]
    assert result.salary_min == 80000


async def test_extract_job_fields_raises_when_no_tool_use_block(monkeypatch):
    response = FakeMessage(content=[])
    _patch_client(monkeypatch, response)

    with pytest.raises(ExtractionError):
        await extract_job_fields("Title", "Company", "Description")


async def test_extract_job_fields_raises_on_missing_field(monkeypatch):
    response = FakeMessage(
        content=[FakeToolUseBlock(input={"title_normalized": "X"})]  # missing required fields
    )
    _patch_client(monkeypatch, response)

    with pytest.raises(ExtractionError):
        await extract_job_fields("Title", "Company", "Description")
