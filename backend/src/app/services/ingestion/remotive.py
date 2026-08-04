from datetime import datetime

import httpx

from app.core.config import settings
from app.models.job_posting import JobRegion
from app.models.source import SourceLanguage, SourceRegion, SourceType
from app.services.ingestion.base import RawJobPosting, SourceAdapter
from app.services.ingestion.language_detection import detect_job_language
from app.services.ingestion.text_cleaning import clean_raw_text, clean_raw_text_inline

REMOTIVE_API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveAdapter(SourceAdapter):
    """Remotive (https://remotive.com) — API JSON pública, sin key. Una instancia
    por categoría (`REMOTIVE_CATEGORIES` en `.env`), igual que Greenhouse/Lever por
    empresa — cada categoría es su propia request.
    """

    source_type = SourceType.API
    source_region = SourceRegion.GLOBAL
    source_language = SourceLanguage.EN

    def __init__(self, category: str):
        self.category = category
        self.slug = f"remotive-{category}"

    async def fetch(self) -> list[RawJobPosting]:
        headers = {"User-Agent": settings.scraper_user_agent, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(
                REMOTIVE_API_URL, params={"category": self.category}, headers=headers
            )
            response.raise_for_status()
            payload = response.json()

        return [self._parse_entry(entry) for entry in payload.get("jobs", [])]

    @staticmethod
    def _parse_entry(entry: dict) -> RawJobPosting:
        posted_at: datetime | None = None
        date_str = entry.get("publication_date")
        if date_str:
            try:
                posted_at = datetime.fromisoformat(date_str)
            except ValueError:
                posted_at = None

        title = clean_raw_text_inline(entry.get("title", ""))
        company = clean_raw_text_inline(entry.get("company_name", ""))
        description = clean_raw_text(entry.get("description") or "")
        location = entry.get("candidate_required_location")
        location = clean_raw_text_inline(location) if location else None

        return RawJobPosting(
            external_id=str(entry["id"]),
            url=entry.get("url") or "",
            title=title,
            company=company,
            description=description,
            language=detect_job_language(title, description),
            region=JobRegion.REMOTE_INTL,
            location=location,
            posted_at=posted_at,
        )
