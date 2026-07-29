import openai
from openai import AsyncOpenAI

from app.core.config import settings


class EmbeddingError(Exception):
    pass


def get_client() -> AsyncOpenAI:
    return AsyncOpenAI(api_key=settings.embedding_api_key, base_url=settings.embedding_base_url)


async def embed_documents(texts: list[str]) -> list[list[float]]:
    """Embed job-posting text for storage/search. Batches in one call."""
    if not texts:
        return []
    client = get_client()
    try:
        response = await client.embeddings.create(model=settings.embedding_model, input=texts)
    except openai.OpenAIError as exc:
        raise EmbeddingError(f"Error generando embeddings: {exc}") from exc
    return [item.embedding for item in response.data]


async def embed_query(text: str) -> list[float]:
    """Embed a user-typed search query."""
    embeddings = await embed_documents([text])
    return embeddings[0]
