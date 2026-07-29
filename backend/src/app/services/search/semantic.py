from sqlalchemy import ColumnElement, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_posting import EnrichmentStatus, JobPosting


async def semantic_search(
    db: AsyncSession,
    query_embedding: list[float],
    limit: int = 20,
    extra_filters: list[ColumnElement[bool]] | None = None,
) -> list[JobPosting]:
    """Rank active, enriched jobs by cosine distance to the query embedding.

    Requires Postgres+pgvector — the `<=>` operator pgvector's SQLAlchemy
    integration compiles to has no equivalent on other dialects.
    """
    stmt = (
        select(JobPosting)
        .where(
            JobPosting.is_active.is_(True),
            JobPosting.enrichment_status == EnrichmentStatus.DONE,
            JobPosting.embedding.is_not(None),
            *(extra_filters or []),
        )
        .order_by(JobPosting.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )
    return list((await db.execute(stmt)).scalars().all())
