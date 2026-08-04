from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.models.job_posting import JobRegion
from app.models.source import SourceLanguage, SourceRegion, SourceType
from app.services.ingestion.base import RawJobPosting, SourceAdapter
from app.services.ingestion.language_detection import detect_job_language
from app.services.ingestion.text_cleaning import clean_raw_text, clean_raw_text_inline

ARBEITNOW_API_URL = "https://www.arbeitnow.com/api/job-board-api"


class ArbeitnowAdapter(SourceAdapter):
    """Arbeitnow (https://arbeitnow.com) — API JSON pública, sin key, orientada a
    tech/remoto. No tiene parámetro de búsqueda; se trae la primera página (los
    ~100 avisos más recientes) y se deja que el filtrado por preferencias/búsqueda
    pase en el frontend, igual que con RemoteOK.
    """

    slug = "arbeitnow"
    source_type = SourceType.API
    source_region = SourceRegion.GLOBAL
    source_language = SourceLanguage.EN

    async def fetch(self) -> list[RawJobPosting]:
        headers = {"User-Agent": settings.scraper_user_agent, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(ARBEITNOW_API_URL, headers=headers)
            response.raise_for_status()
            payload = response.json()

        return [self._parse_entry(entry) for entry in payload.get("data", [])]

    @staticmethod
    def _parse_entry(entry: dict) -> RawJobPosting:
        posted_at: datetime | None = None
        created_at = entry.get("created_at")
        if isinstance(created_at, (int, float)):
            posted_at = datetime.fromtimestamp(created_at, tz=UTC)

        title = clean_raw_text_inline(entry.get("title", ""))
        company = clean_raw_text_inline(entry.get("company_name", ""))
        description = clean_raw_text(entry.get("description") or "")
        location = entry.get("location")
        location = clean_raw_text_inline(location) if location else None

        return RawJobPosting(
            external_id=str(entry.get("slug") or entry.get("url") or ""),
            url=entry.get("url") or "",
            title=title,
            company=company,
            description=description,
            language=detect_job_language(title, description),
            region=JobRegion.REMOTE_INTL,
            location=location,
            posted_at=posted_at,
        )
