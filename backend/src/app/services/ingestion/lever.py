from datetime import UTC, datetime

import httpx

from app.core.config import settings
from app.models.job_posting import JobRegion
from app.models.source import SourceLanguage, SourceRegion, SourceType
from app.services.ingestion.base import RawJobPosting, SourceAdapter
from app.services.ingestion.language_detection import detect_job_language
from app.services.ingestion.text_cleaning import clean_raw_text, clean_raw_text_inline

LEVER_API_URL = "https://api.lever.co/v0/postings/{company}"


class LeverAdapter(SourceAdapter):
    """Genérico para cualquier empresa que publique sus búsquedas en Lever (API
    pública de job board). Una instancia = una empresa, igual que GreenhouseAdapter.
    """

    source_type = SourceType.API
    source_region = SourceRegion.GLOBAL
    source_language = SourceLanguage.MIXED

    def __init__(self, company: str, company_name: str | None = None):
        self.company = company
        self.company_name = company_name or company.replace("-", " ").title()
        self.slug = f"lever-{company}"

    async def fetch(self) -> list[RawJobPosting]:
        url = LEVER_API_URL.format(company=self.company)
        headers = {"User-Agent": settings.scraper_user_agent, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params={"mode": "json"}, headers=headers)
            response.raise_for_status()
            payload = response.json()

        return [self._parse_entry(entry) for entry in payload]

    def _parse_entry(self, entry: dict) -> RawJobPosting:
        posted_at: datetime | None = None
        created_at_ms = entry.get("createdAt")
        if isinstance(created_at_ms, (int, float)):
            posted_at = datetime.fromtimestamp(created_at_ms / 1000, tz=UTC)

        title = clean_raw_text_inline(entry.get("text", ""))
        # `descriptionPlain` ya viene sin HTML cuando Lever lo provee; si no está,
        # fallback a `description` (HTML) limpiado con nuestro pipeline.
        description = entry.get("descriptionPlain") or ""
        description = clean_raw_text(description) if description else clean_raw_text(
            entry.get("description") or ""
        )
        location = (entry.get("categories") or {}).get("location")
        location = clean_raw_text_inline(location) if location else None

        return RawJobPosting(
            external_id=str(entry["id"]),
            url=entry.get("hostedUrl") or "",
            title=title,
            company=self.company_name,
            description=description,
            language=detect_job_language(title, description),
            region=JobRegion.REMOTE_INTL,
            location=location,
            posted_at=posted_at,
        )
