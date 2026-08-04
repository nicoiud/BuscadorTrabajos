from datetime import datetime

import httpx

from app.core.config import settings
from app.models.job_posting import JobRegion
from app.models.source import SourceLanguage, SourceRegion, SourceType
from app.services.ingestion.base import RawJobPosting, SourceAdapter
from app.services.ingestion.language_detection import detect_job_language
from app.services.ingestion.text_cleaning import clean_raw_text, clean_raw_text_inline

ADZUNA_API_URL = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"


class AdzunaAdapter(SourceAdapter):
    """Adzuna (https://developer.adzuna.com) — agregador con API oficial (app_id +
    app_key gratuitos). No cubre Argentina; sirve para roles remotos
    internacionales o de otros países de Latam soportados (mx, br). Una instancia
    por país (`ADZUNA_COUNTRIES` en `.env`), igual que Greenhouse/Lever por empresa.

    Sin `ADZUNA_APP_ID`/`ADZUNA_APP_KEY` configuradas, `_configured_adapters()` no
    instancia esta fuente.
    """

    source_type = SourceType.API
    source_region = SourceRegion.GLOBAL
    source_language = SourceLanguage.MIXED

    def __init__(self, country: str):
        self.country = country
        self.slug = f"adzuna-{country}"

    async def fetch(self) -> list[RawJobPosting]:
        url = ADZUNA_API_URL.format(country=self.country)
        headers = {"User-Agent": settings.scraper_user_agent, "Accept": "application/json"}
        params = {
            "app_id": settings.adzuna_app_id,
            "app_key": settings.adzuna_app_key,
            "what": settings.adzuna_query,
            "results_per_page": 50,
            "content-type": "application/json",
        }
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, params=params, headers=headers)
            response.raise_for_status()
            payload = response.json()

        return [self._parse_entry(entry) for entry in payload.get("results", [])]

    @staticmethod
    def _parse_entry(entry: dict) -> RawJobPosting:
        posted_at: datetime | None = None
        date_str = entry.get("created")
        if date_str:
            try:
                posted_at = datetime.fromisoformat(date_str)
            except ValueError:
                posted_at = None

        title = clean_raw_text_inline(entry.get("title", ""))
        company = clean_raw_text_inline((entry.get("company") or {}).get("display_name") or "")
        description = clean_raw_text(entry.get("description") or "")
        location = (entry.get("location") or {}).get("display_name")
        location = clean_raw_text_inline(location) if location else None

        return RawJobPosting(
            external_id=str(entry.get("id") or entry.get("redirect_url") or ""),
            url=entry.get("redirect_url") or "",
            title=title,
            company=company,
            description=description,
            language=detect_job_language(title, description),
            region=JobRegion.REMOTE_INTL,
            location=location,
            posted_at=posted_at,
        )
