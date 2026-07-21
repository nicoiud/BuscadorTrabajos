import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models.job_posting import JobLanguage, JobRegion


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


class JobPostingList(BaseModel):
    total: int
    items: list[JobPostingOut]


class IngestResultOut(BaseModel):
    source_slug: str
    fetched: int
    created: int
    updated: int
