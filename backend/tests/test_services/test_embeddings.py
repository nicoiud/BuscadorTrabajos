from dataclasses import dataclass, field
from typing import Any

import openai
import pytest

from app.services.enrichment import embeddings
from app.services.enrichment.embeddings import EmbeddingError


@dataclass
class FakeEmbeddingItem:
    embedding: list[float]


@dataclass
class FakeEmbeddingResponse:
    data: list[FakeEmbeddingItem] = field(default_factory=list)


class FakeEmbeddingsEndpoint:
    def __init__(self, response: FakeEmbeddingResponse):
        self._response = response
        self.calls: list[dict[str, Any]] = []

    async def create(self, **kwargs: Any) -> FakeEmbeddingResponse:
        self.calls.append(kwargs)
        return self._response


class FakeEmbeddingClient:
    def __init__(self, response: FakeEmbeddingResponse):
        self.embeddings = FakeEmbeddingsEndpoint(response)


class FakeFailingEmbeddingClient:
    class embeddings:
        @staticmethod
        async def create(**kwargs: Any):
            raise openai.OpenAIError("simulated provider error")


async def test_embed_documents_returns_one_vector_per_text(monkeypatch):
    fake_response = FakeEmbeddingResponse(
        data=[FakeEmbeddingItem(embedding=[0.1, 0.2]), FakeEmbeddingItem(embedding=[0.3, 0.4])]
    )
    fake_client = FakeEmbeddingClient(fake_response)
    monkeypatch.setattr(embeddings, "get_client", lambda: fake_client)

    result = await embeddings.embed_documents(["job one", "job two"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    assert fake_client.embeddings.calls[0]["input"] == ["job one", "job two"]


async def test_embed_documents_returns_empty_list_without_calling_api(monkeypatch):
    fake_client = FakeEmbeddingClient(FakeEmbeddingResponse())
    monkeypatch.setattr(embeddings, "get_client", lambda: fake_client)

    result = await embeddings.embed_documents([])

    assert result == []
    assert fake_client.embeddings.calls == []


async def test_embed_query_returns_single_vector(monkeypatch):
    fake_response = FakeEmbeddingResponse(data=[FakeEmbeddingItem(embedding=[0.5, 0.6])])
    fake_client = FakeEmbeddingClient(fake_response)
    monkeypatch.setattr(embeddings, "get_client", lambda: fake_client)

    result = await embeddings.embed_query("remote python backend jobs")

    assert result == [0.5, 0.6]


async def test_embed_documents_wraps_provider_errors(monkeypatch):
    monkeypatch.setattr(embeddings, "get_client", lambda: FakeFailingEmbeddingClient())

    with pytest.raises(EmbeddingError):
        await embeddings.embed_documents(["some job text"])


async def test_embed_query_wraps_provider_errors(monkeypatch):
    monkeypatch.setattr(embeddings, "get_client", lambda: FakeFailingEmbeddingClient())

    with pytest.raises(EmbeddingError):
        await embeddings.embed_query("some query")
