import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.job_posting import EnrichmentStatus, JobPosting
from app.services.enrichment.embeddings import EmbeddingError, embed_documents
from app.services.enrichment.extractor import ExtractionError, JobExtraction, extract_job_fields

logger = logging.getLogger(__name__)


@dataclass
class EnrichResult:
    processed: int
    enriched: int
    failed: int


def _embedding_text(extraction: JobExtraction) -> str:
    return "\n".join(
        [extraction.title_normalized, extraction.summary, ", ".join(extraction.requirements)]
    )


async def enrich_pending_jobs(db: AsyncSession, limit: int | None = None) -> EnrichResult:
    batch_size = limit or settings.enrichment_batch_size

    stmt = (
        select(JobPosting)
        .where(JobPosting.enrichment_status == EnrichmentStatus.PENDING)
        .limit(batch_size)
    )
    pending_jobs = (await db.execute(stmt)).scalars().all()

    if not pending_jobs:
        return EnrichResult(processed=0, enriched=0, failed=0)

    extracted: list[tuple[JobPosting, JobExtraction]] = []
    failed = 0
    for job in pending_jobs:
        try:
            extraction = await extract_job_fields(
                job.title_raw, job.company_raw, job.description_raw
            )
        except ExtractionError:
            logger.warning("Enrichment failed for job %s", job.id, exc_info=True)
            job.enrichment_status = EnrichmentStatus.FAILED
            failed += 1
            continue

        job.title_normalized = extraction.title_normalized
        job.company_normalized = extraction.company_normalized
        job.seniority = extraction.seniority
        job.modality = extraction.modality
        job.salary_min = extraction.salary_min
        job.salary_max = extraction.salary_max
        job.currency = extraction.currency
        job.requirements = extraction.requirements
        job.summary = extraction.summary
        extracted.append((job, extraction))

    if extracted:
        texts = [_embedding_text(extraction) for _, extraction in extracted]
        try:
            embeddings = await embed_documents(texts)
        except EmbeddingError:
            # Si Voyage falla (key faltante, rate limit, lo que sea), no perdemos el
            # análisis de texto que sí funcionó — se guarda sin embedding. Sin
            # embedding esos avisos no van a aparecer en la búsqueda semántica hasta
            # que se reintente, pero no se pierde el trabajo ya hecho.
            logger.warning("Embedding failed for the batch of %d jobs", len(extracted), exc_info=True)
            embeddings = [None] * len(extracted)

        for (job, _), embedding in zip(extracted, embeddings, strict=True):
            job.embedding = embedding
            job.enrichment_status = EnrichmentStatus.DONE
            job.enrichment_model = settings.llm_model

    await db.commit()

    return EnrichResult(processed=len(pending_jobs), enriched=len(extracted), failed=failed)
