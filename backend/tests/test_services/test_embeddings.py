from dataclasses import dataclass, field
from typing import Any

from app.services.enrichment import embeddings


@dataclass
class FakeEmbedResult:
    embeddings: list[list[float]] = field(default_factory=list)


class FakeVoyageClient:
    def __init__(self, embeddings_by_call: list[list[list[float]]]):
        self._embeddings_by_call = embeddings_by_call
        self.calls: list[dict[str, Any]] = []

    async def embed(self, texts, model, input_type):
        self.calls.append({"texts": texts, "model": model, "input_type": input_type})
        return FakeEmbedResult(embeddings=self._embeddings_by_call.pop(0))


async def test_embed_documents_returns_one_vector_per_text(monkeypatch):
    fake_client = FakeVoyageClient([[[0.1, 0.2], [0.3, 0.4]]])
    monkeypatch.setattr(embeddings, "get_client", lambda: fake_client)

    result = await embeddings.embed_documents(["job one", "job two"])

    assert result == [[0.1, 0.2], [0.3, 0.4]]
    assert fake_client.calls[0]["input_type"] == "document"


async def test_embed_documents_returns_empty_list_without_calling_api(monkeypatch):
    fake_client = FakeVoyageClient([])
    monkeypatch.setattr(embeddings, "get_client", lambda: fake_client)

    result = await embeddings.embed_documents([])

    assert result == []
    assert fake_client.calls == []


async def test_embed_query_returns_single_vector(monkeypatch):
    fake_client = FakeVoyageClient([[[0.5, 0.6]]])
    monkeypatch.setattr(embeddings, "get_client", lambda: fake_client)

    result = await embeddings.embed_query("remote python backend jobs")

    assert result == [0.5, 0.6]
    assert fake_client.calls[0]["input_type"] == "query"
