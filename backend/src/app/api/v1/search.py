from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.job import JobPostingList, JobPostingOut, SemanticSearchRequest
from app.services.enrichment.embeddings import embed_query
from app.services.search.semantic import semantic_search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=JobPostingList)
async def semantic_search_jobs(
    body: SemanticSearchRequest, db: AsyncSession = Depends(get_db)
) -> JobPostingList:
    query_embedding = await embed_query(body.query)
    items = await semantic_search(db, query_embedding, limit=body.limit)
    return JobPostingList(total=len(items), items=[JobPostingOut.model_validate(i) for i in items])
