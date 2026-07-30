from datetime import datetime

import httpx

from app.core.config import settings
from app.models.job_posting import JobRegion
from app.models.source import SourceLanguage, SourceRegion, SourceType
from app.services.ingestion.base import RawJobPosting, SourceAdapter
from app.services.ingestion.language_detection import detect_job_language
from app.services.ingestion.text_cleaning import clean_raw_text, clean_raw_text_inline

GREENHOUSE_API_URL = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"


class GreenhouseAdapter(SourceAdapter):
    """Genérico para cualquier empresa que publique sus búsquedas en Greenhouse
    (API pública de job board, pensada para este uso — no es scraping).

    Una instancia = una empresa (`board` es el slug que usa esa empresa en
    Greenhouse, ej. "stripe" para boards.greenhouse.io/stripe). El `slug` de la
    fuente en nuestra base es distinto por empresa, así que cada una se guarda
    como su propio `Source` — ver `SourceAdapter.source_defaults()`.
    """

    source_type = SourceType.API
    source_region = SourceRegion.GLOBAL
    source_language = SourceLanguage.MIXED

    def __init__(self, board: str, company_name: str | None = None):
        self.board = board
        self.company_name = company_name or board.replace("-", " ").title()
        self.slug = f"greenhouse-{board}"

    async def fetch(self) -> list[RawJobPosting]:
        url = GREENHOUSE_API_URL.format(board=self.board)
        headers = {"User-Agent": settings.scraper_user_agent, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params={"content": "true"}, headers=headers)
            response.raise_for_status()
            payload = response.json()

        return [self._parse_entry(entry) for entry in payload.get("jobs", [])]

    def _parse_entry(self, entry: dict) -> RawJobPosting:
        posted_at: datetime | None = None
        date_str = entry.get("updated_at") or entry.get("first_published")
        if date_str:
            try:
                posted_at = datetime.fromisoformat(date_str)
            except ValueError:
                posted_at = None

        title = clean_raw_text_inline(entry.get("title", ""))
        # `content` es el HTML completo de la descripción (solo viene con
        # ?content=true); sin eso, no hay descripción disponible en el listado.
        description = clean_raw_text(entry.get("content") or "")
        location = (entry.get("location") or {}).get("name")
        location = clean_raw_text_inline(location) if location else None

        return RawJobPosting(
            external_id=str(entry["id"]),
            url=entry.get("absolute_url") or "",
            title=title,
            company=self.company_name,
            description=description,
            language=detect_job_language(title, description),
            region=JobRegion.REMOTE_INTL,
            location=location,
            posted_at=posted_at,
        )
