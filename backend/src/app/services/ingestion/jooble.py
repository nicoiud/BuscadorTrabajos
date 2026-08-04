from datetime import datetime

import httpx

from app.core.config import settings
from app.models.job_posting import JobRegion
from app.models.source import SourceLanguage, SourceRegion, SourceType
from app.services.ingestion.base import RawJobPosting, SourceAdapter
from app.services.ingestion.language_detection import detect_job_language
from app.services.ingestion.text_cleaning import clean_raw_text, clean_raw_text_inline

JOOBLE_API_URL = "https://jooble.org/api/{key}"


class JoobleAdapter(SourceAdapter):
    """Jooble (https://jooble.org/api/about) — agregador con API oficial (key
    gratuita) que sí cubre Argentina, a diferencia de Adzuna. Distinto de un
    scraper: Jooble ya tiene el acuerdo de acceso con las fuentes que indexa, acá
    solo consumimos su API pública con la key del usuario.

    `JOOBLE_KEYWORDS`/`JOOBLE_LOCATION` en `.env` controlan la búsqueda; sin
    `JOOBLE_API_KEY` configurada, `_configured_adapters()` no instancia esta fuente.
    """

    slug = "jooble"
    source_type = SourceType.API
    source_region = SourceRegion.LATAM
    source_language = SourceLanguage.ES

    async def fetch(self) -> list[RawJobPosting]:
        url = JOOBLE_API_URL.format(key=settings.jooble_api_key)
        headers = {"User-Agent": settings.scraper_user_agent, "Content-Type": "application/json"}
        body = {"keywords": settings.jooble_keywords, "location": settings.jooble_location}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(url, json=body, headers=headers)
            response.raise_for_status()
            payload = response.json()

        return [self._parse_entry(entry) for entry in payload.get("jobs", [])]

    @staticmethod
    def _parse_entry(entry: dict) -> RawJobPosting:
        posted_at: datetime | None = None
        date_str = entry.get("updated")
        if date_str:
            try:
                posted_at = datetime.fromisoformat(date_str)
            except ValueError:
                posted_at = None

        title = clean_raw_text_inline(entry.get("title", ""))
        company = clean_raw_text_inline(entry.get("company") or "Empresa sin especificar")
        description = clean_raw_text(entry.get("snippet") or "")
        location = entry.get("location")
        location = clean_raw_text_inline(location) if location else None

        return RawJobPosting(
            external_id=str(entry.get("id") or entry.get("link") or ""),
            url=entry.get("link") or "",
            title=title,
            company=company,
            description=description,
            language=detect_job_language(title, description),
            region=JobRegion.LATAM,
            location=location,
            posted_at=posted_at,
        )
