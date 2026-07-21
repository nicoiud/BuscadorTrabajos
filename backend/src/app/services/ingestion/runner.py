from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job_posting import JobPosting
from app.models.source import Source, SourceLanguage, SourceRegion, SourceType
from app.services.ingestion.base import SourceAdapter

# Static registration of default config per known source slug. Real per-source
# tuning (rate limits, enable/disable) lives in the `sources` table and can be
# edited without a code change once seeded.
_SOURCE_DEFAULTS: dict[str, dict] = {
    "remoteok": {
        "type": SourceType.API,
        "region": SourceRegion.GLOBAL,
        "language": SourceLanguage.EN,
    },
}


@dataclass
class IngestResult:
    source_slug: str
    fetched: int
    created: int
    updated: int


async def _get_or_create_source(db: AsyncSession, slug: str) -> Source:
    result = await db.execute(select(Source).where(Source.slug == slug))
    source = result.scalar_one_or_none()
    if source is not None:
        return source

    defaults = _SOURCE_DEFAULTS.get(slug)
    if defaults is None:
        raise ValueError(f"No default config registered for source '{slug}'")

    source = Source(slug=slug, **defaults)
    db.add(source)
    await db.flush()
    return source


async def ingest_source(db: AsyncSession, adapter: SourceAdapter) -> IngestResult:
    source = await _get_or_create_source(db, adapter.slug)

    raw_postings = await adapter.fetch()
    now = datetime.now(UTC)

    existing_result = await db.execute(
        select(JobPosting).where(JobPosting.source_id == source.id)
    )
    existing_by_external_id = {jp.external_id: jp for jp in existing_result.scalars().all()}

    created = 0
    updated = 0
    for raw in raw_postings:
        job = existing_by_external_id.get(raw.external_id)
        if job is None:
            job = JobPosting(
                source_id=source.id,
                external_id=raw.external_id,
                scraped_at=now,
            )
            db.add(job)
            created += 1
        else:
            updated += 1

        job.url = raw.url
        job.title_raw = raw.title
        job.company_raw = raw.company
        job.description_raw = raw.description
        job.location_raw = raw.location
        job.posted_at = raw.posted_at
        job.language = raw.language
        job.region = raw.region
        job.is_active = True

    source.last_run_at = now
    source.last_success_at = now

    await db.commit()

    return IngestResult(
        source_slug=adapter.slug,
        fetched=len(raw_postings),
        created=created,
        updated=updated,
    )
