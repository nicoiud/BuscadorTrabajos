import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.job_posting import EnrichmentStatus, JobLanguage, JobRegion, Modality, Seniority


class JobPostingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title_raw: str
    company_raw: str
    description_raw: str
    url: str
    location_raw: str | None
    posted_at: datetime | None
    language: JobLanguage
    region: JobRegion

    # Campos IA — null hasta que corre el enrichment (Fase 2).
    title_normalized: str | None = None
    company_normalized: str | None = None
    seniority: Seniority | None = None
    modality: Modality | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    currency: str | None = None
    requirements: list[str] | None = None
    summary: str | None = None
    enrichment_status: EnrichmentStatus


class JobPostingList(BaseModel):
    total: int
    items: list[JobPostingOut]


class IngestResultOut(BaseModel):
    source_slug: str
    fetched: int
    created: int
    updated: int


class EnrichResultOut(BaseModel):
    processed: int
    enriched: int
    failed: int


class SemanticSearchRequest(BaseModel):
    query: str
    limit: int = 20


class CoverLetterRequest(BaseModel):
    profile_text: str


class CoverLetterOut(BaseModel):
    cover_letter: str
    key_points: list[str]
