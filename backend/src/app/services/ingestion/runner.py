import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.job_posting import JobPosting
from app.models.source import Source
from app.services.ingestion.adzuna import AdzunaAdapter
from app.services.ingestion.arbeitnow import ArbeitnowAdapter
from app.services.ingestion.base import SourceAdapter
from app.services.ingestion.greenhouse import GreenhouseAdapter
from app.services.ingestion.jooble import JoobleAdapter
from app.services.ingestion.lever import LeverAdapter
from app.services.ingestion.remoteok import RemoteOkAdapter
from app.services.ingestion.remotive import RemotiveAdapter
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
    # ZonaJobsAdapter deliberadamente NO está acá: su API interna devuelve 403
    # Forbidden a pedidos no-browser (confirmado contra el sitio real), señal de
    # que activamente no quieren tráfico automatizado en ese endpoint — agregar
    # headers para simular un browser real cruzaría la regla de CLAUDE.md de nunca
    # evadir bloqueos. El código queda por si en el futuro aparece una vía
    # legítima (ej. acuerdo de partner), pero no se corre solo.
    adapters: list[SourceAdapter] = [
        RemoteOkAdapter(),
        WeWorkRemotelyAdapter(),
        ArbeitnowAdapter(),
    ]

    for board in _split_csv(settings.greenhouse_boards):
        adapters.append(GreenhouseAdapter(board=board))

    for company in _split_csv(settings.lever_companies):
        adapters.append(LeverAdapter(company=company))

    for category in _split_csv(settings.remotive_categories):
        adapters.append(RemotiveAdapter(category=category))

    # Jooble y Adzuna necesitan una API key gratuita que el usuario tiene que
    # generar aparte (jooble.org/api/about, developer.adzuna.com) — sin key
    # configurada, no tiene sentido intentar el request (fallaría con 401/403 en
    # cada corrida), así que se saltan solas en vez de sumarse siempre.
    if settings.jooble_api_key:
        adapters.append(JoobleAdapter())

    if settings.adzuna_app_id and settings.adzuna_app_key:
        for country in _split_csv(settings.adzuna_countries):
            adapters.append(AdzunaAdapter(country=country))

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
