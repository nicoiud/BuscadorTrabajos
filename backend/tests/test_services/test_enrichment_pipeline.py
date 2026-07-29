from datetime import UTC, datetime

from sqlalchemy import select

from app.models.job_posting import EnrichmentStatus, JobLanguage, JobPosting, JobRegion
from app.models.source import Source, SourceLanguage, SourceRegion, SourceType
from app.services.enrichment import pipeline
from app.services.enrichment.extractor import ExtractionError, JobExtraction


async def _make_pending_job(db_session, external_id: str, title: str) -> JobPosting:
    source = (
        await db_session.execute(select(Source).where(Source.slug == "test-source"))
    ).scalar_one_or_none()
    if source is None:
        source = Source(
            slug="test-source",
            type=SourceType.API,
            region=SourceRegion.GLOBAL,
            language=SourceLanguage.EN,
        )
        db_session.add(source)
        await db_session.flush()

    job = JobPosting(
        source_id=source.id,
        external_id=external_id,
        url=f"https://example.com/{external_id}",
        title_raw=title,
        company_raw="Acme",
        description_raw="Some raw description",
        scraped_at=datetime.now(UTC),
        language=JobLanguage.EN,
        region=JobRegion.REMOTE_INTL,
    )
    db_session.add(job)
    await db_session.flush()
    return job


def _fake_extraction(title: str) -> JobExtraction:
    return JobExtraction(
        title_normalized=title,
        company_normalized="Acme",
        seniority="senior",
        modality="remote",
        requirements=["Python", "SQL"],
        summary=f"Summary for {title}",
        salary_min=None,
        salary_max=None,
        currency=None,
    )


async def test_enrich_pending_jobs_updates_fields_and_embedding(db_session, monkeypatch):
    job = await _make_pending_job(db_session, "1", "Backend Engineer")
    await db_session.commit()

    async def fake_extract(title_raw, company_raw, description_raw):
        return _fake_extraction("Backend Engineer")

    async def fake_embed(texts):
        return [[0.1] * 3 for _ in texts]

    monkeypatch.setattr(pipeline, "extract_job_fields", fake_extract)
    monkeypatch.setattr(pipeline, "embed_documents", fake_embed)

    result = await pipeline.enrich_pending_jobs(db_session, limit=10)

    assert result.processed == 1
    assert result.enriched == 1
    assert result.failed == 0

    await db_session.refresh(job)
    assert job.enrichment_status == EnrichmentStatus.DONE
    assert job.title_normalized == "Backend Engineer"
    assert job.requirements == ["Python", "SQL"]
    assert job.embedding == [0.1, 0.1, 0.1]


async def test_enrich_pending_jobs_marks_failed_on_extraction_error(db_session, monkeypatch):
    job = await _make_pending_job(db_session, "2", "Broken Job")
    await db_session.commit()

    async def fake_extract(title_raw, company_raw, description_raw):
        raise ExtractionError("boom")

    async def fake_embed(texts):
        raise AssertionError("should not be called when extraction fails")

    monkeypatch.setattr(pipeline, "extract_job_fields", fake_extract)
    monkeypatch.setattr(pipeline, "embed_documents", fake_embed)

    result = await pipeline.enrich_pending_jobs(db_session, limit=10)

    assert result.processed == 1
    assert result.enriched == 0
    assert result.failed == 1

    await db_session.refresh(job)
    assert job.enrichment_status == EnrichmentStatus.FAILED


async def test_enrich_pending_jobs_one_failure_does_not_abort_the_rest_of_the_batch(
    db_session, monkeypatch
):
    # Regresión: en producción, un aviso que el modelo no pudo extraer bien (Groq
    # rechazó la respuesta con 400) tiraba abajo todo el POST /jobs/enrich en vez de
    # marcar solo ese aviso como failed y seguir con los demás.
    broken_job = await _make_pending_job(db_session, "broken", "Broken Job")
    ok_job = await _make_pending_job(db_session, "ok", "Backend Engineer")
    await db_session.commit()

    async def fake_extract(title_raw, company_raw, description_raw):
        if title_raw == "Broken Job":
            raise ExtractionError("provider rejected the tool call")
        return _fake_extraction(title_raw)

    async def fake_embed(texts):
        return [[0.1] * 3 for _ in texts]

    monkeypatch.setattr(pipeline, "extract_job_fields", fake_extract)
    monkeypatch.setattr(pipeline, "embed_documents", fake_embed)

    result = await pipeline.enrich_pending_jobs(db_session, limit=10)

    assert result.processed == 2
    assert result.enriched == 1
    assert result.failed == 1

    await db_session.refresh(broken_job)
    await db_session.refresh(ok_job)
    assert broken_job.enrichment_status == EnrichmentStatus.FAILED
    assert ok_job.enrichment_status == EnrichmentStatus.DONE
    assert ok_job.title_normalized == "Backend Engineer"


async def test_enrich_pending_jobs_noop_when_nothing_pending(db_session):
    result = await pipeline.enrich_pending_jobs(db_session, limit=10)

    assert result == pipeline.EnrichResult(processed=0, enriched=0, failed=0)
