from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.job_posting import JobLanguage, JobPosting, JobRegion
from app.schemas.job import EnrichResultOut, IngestResultOut, JobPostingList, JobPostingOut
from app.services.enrichment.pipeline import enrich_pending_jobs
from app.services.ingestion.remoteok import RemoteOkAdapter
from app.services.ingestion.runner import ingest_source

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("", response_model=JobPostingList)
async def list_jobs(
    db: AsyncSession = Depends(get_db),
    q: str | None = Query(default=None, description="Búsqueda por palabra clave"),
    region: JobRegion | None = Query(default=None),
    language: JobLanguage | None = Query(default=None),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> JobPostingList:
    filters = [JobPosting.is_active.is_(True)]
    if q:
        like = f"%{q}%"
        filters.append(
            or_(JobPosting.title_raw.ilike(like), JobPosting.description_raw.ilike(like))
        )
    if region:
        filters.append(JobPosting.region == region)
    if language:
        filters.append(JobPosting.language == language)

    total_stmt = select(func.count()).select_from(JobPosting).where(*filters)
    total = (await db.execute(total_stmt)).scalar_one()

    stmt = (
        select(JobPosting)
        .where(*filters)
        .order_by(JobPosting.posted_at.desc().nulls_last(), JobPosting.scraped_at.desc())
        .limit(limit)
        .offset(offset)
    )
    items = (await db.execute(stmt)).scalars().all()

    return JobPostingList(total=total, items=[JobPostingOut.model_validate(i) for i in items])


@router.post("/ingest/remoteok", response_model=IngestResultOut)
async def trigger_remoteok_ingestion(db: AsyncSession = Depends(get_db)) -> IngestResultOut:
    result = await ingest_source(db, RemoteOkAdapter())
    return IngestResultOut(**result.__dict__)


@router.post("/enrich", response_model=EnrichResultOut)
async def trigger_enrichment(
    db: AsyncSession = Depends(get_db),
    limit: int | None = Query(default=None, ge=1, le=100),
) -> EnrichResultOut:
    result = await enrich_pending_jobs(db, limit=limit)
    return EnrichResultOut(**result.__dict__)
