import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.job_posting import JobPosting
from app.models.source import Source
from app.services.ingestion.base import SourceAdapter
from app.services.ingestion.greenhouse import GreenhouseAdapter
from app.services.ingestion.lever import LeverAdapter
from app.services.ingestion.remoteok import RemoteOkAdapter
from app.services.ingestion.weworkremotely import WeWorkRemotelyAdapter

logger = logging.getLogger(__name__)


@dataclass
class IngestResult:
    source_slug: str
    fetched: int
    created: int
    updated: int
    error: str | None = None


async def _get_or_create_source(db: AsyncSession, adapter: SourceAdapter) -> Source:
    result = await db.execute(select(Source).where(Source.slug == adapter.slug))
    source = result.scalar_one_or_none()
    if source is not None:
        return source

    source = Source(slug=adapter.slug, **adapter.source_defaults())
    db.add(source)
    await db.flush()
    return source


async def ingest_source(db: AsyncSession, adapter: SourceAdapter) -> IngestResult:
    source = await _get_or_create_source(db, adapter)

    if not source.enabled:
        # Kill-switch por fuente (CLAUDE.md) — se puede apagar una fuente puntual
        # editando `sources.enabled` sin tocar código ni redeployar.
        return IngestResult(
            source_slug=adapter.slug, fetched=0, created=0, updated=0, error="fuente deshabilitada"
        )

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


def _configured_adapters() -> list[SourceAdapter]:
    adapters: list[SourceAdapter] = [RemoteOkAdapter(), WeWorkRemotelyAdapter()]

    for board in _split_csv(settings.greenhouse_boards):
        adapters.append(GreenhouseAdapter(board=board))

    for company in _split_csv(settings.lever_companies):
        adapters.append(LeverAdapter(company=company))

    return adapters


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


async def ingest_all_sources(db: AsyncSession) -> list[IngestResult]:
    """Corre todas las fuentes configuradas (RemoteOK + empresas de Greenhouse/Lever
    en `GREENHOUSE_BOARDS`/`LEVER_COMPANIES`). Una fuente que falla (red, HTTP,
    parseo) no aborta las demás — queda registrada con `error` seteado."""
    results: list[IngestResult] = []
    for adapter in _configured_adapters():
        try:
            results.append(await ingest_source(db, adapter))
        except Exception as exc:
            logger.warning("Ingestion failed for source %s", adapter.slug, exc_info=True)
            # Si `ingest_source` explotó a mitad de camino puede haber quedado
            # estado sin commitear en la sesión (ej. `db.add(job)` de un aviso ya
            # procesado antes del error) — se descarta para que la fuente que sigue
            # arranque en un estado limpio.
            await db.rollback()
            results.append(
                IngestResult(source_slug=adapter.slug, fetched=0, created=0, updated=0, error=str(exc))
            )
    return results
