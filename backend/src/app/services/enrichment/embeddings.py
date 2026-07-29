import voyageai

from app.core.config import settings


class EmbeddingError(Exception):
    pass


def get_client() -> voyageai.AsyncClient:
    return voyageai.AsyncClient(api_key=settings.voyage_api_key)


async def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed job-posting text for storage/search. Batches in one call."""
    if not texts:
        return []
    client = get_client()
    try:
        result = await client.embed(texts, model=settings.voyage_model, input_type="document")
    except Exception as exc:
        raise EmbeddingError(f"Error generando embeddings: {exc}") from exc
    return result.embeddings


async def embed_query(text: str) -> list[float]:
    """Embed a user-typed search query. Uses Voyage's asymmetric query mode."""
    client = get_client()
    try:
        result = await client.embed([text], model=settings.voyage_model, input_type="query")
    except Exception as exc:
        raise EmbeddingError(f"Error generando embeddings: {exc}") from exc
    return result.embeddings[0]
