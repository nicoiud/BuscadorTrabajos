import voyageai

from app.core.config import settings


def get_client() -> voyageai.AsyncClient:
    return voyageai.AsyncClient(api_key=settings.voyage_api_key)


async def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed job-posting text for storage/search. Batches in one call."""
    if not texts:
        return []
    client = get_client()
    result = await client.embed(texts, model=settings.voyage_model, input_type="document")
    return result.embeddings


async def embed_query(text: str) -> list[float]:
    """Embed a user-typed search query. Uses Voyage's asymmetric query mode."""
    client = get_client()
    result = await client.embed([text], model=settings.voyage_model, input_type="query")
    return result.embeddings[0]
