import logging
from datetime import UTC, datetime

import feedparser
import httpx

from app.core.config import settings
from app.models.job_posting import JobRegion
from app.models.source import SourceLanguage, SourceRegion, SourceType
from app.services.ingestion.base import RawJobPosting, SourceAdapter
from app.services.ingestion.language_detection import detect_job_language
from app.services.ingestion.text_cleaning import clean_raw_text, clean_raw_text_inline

logger = logging.getLogger(__name__)


class WeWorkRemotelyAdapter(SourceAdapter):
    """We Work Remotely publica sus avisos como feeds RSS por categoría — pensado
    para agregadores, no scraping. `WEWORKREMOTELY_FEED_URLS` (una o más URLs de
    categoría separadas por coma) controla qué categorías se traen.
    """

    slug = "weworkremotely"
    source_type = SourceType.RSS
    source_region = SourceRegion.GLOBAL
    source_language = SourceLanguage.EN

    async def fetch(self) -> list[RawJobPosting]:
        feed_urls = [u.strip() for u in settings.weworkremotely_feed_urls.split(",") if u.strip()]
        headers = {"User-Agent": settings.scraper_user_agent}

        postings: list[RawJobPosting] = []
        seen_ids: set[str] = set()
        async with httpx.AsyncClient(timeout=15.0) as client:
            for feed_url in feed_urls:
                try:
                    response = await client.get(feed_url, headers=headers)
                    response.raise_for_status()
                    feed = feedparser.parse(response.content)
                except Exception:
                    # Una categoría con URL vieja/rota no debería tirar abajo las
                    # demás — se loguea y se sigue con el resto.
                    logger.warning("No se pudo traer el feed RSS %s", feed_url, exc_info=True)
                    continue

                for entry in feed.entries:
                    posting = self._parse_entry(entry)
                    if posting is not None and posting.external_id not in seen_ids:
                        seen_ids.add(posting.external_id)
                        postings.append(posting)

        return postings

    @staticmethod
    def _parse_entry(entry) -> RawJobPosting | None:
        external_id = entry.get("id") or entry.get("link")
        if not external_id:
            return None

        # El título del RSS de WWR viene como "Empresa: Puesto".
        raw_title = entry.get("title", "")
        if ": " in raw_title:
            company_part, _, title_part = raw_title.partition(": ")
        else:
            company_part, title_part = "", raw_title

        title = clean_raw_text_inline(title_part)
        company = clean_raw_text_inline(company_part) or "Empresa sin especificar"
        description = clean_raw_text(entry.get("summary") or entry.get("description") or "")

        posted_at: datetime | None = None
        if entry.get("published_parsed"):
            posted_at = datetime(*entry.published_parsed[:6], tzinfo=UTC)

        return RawJobPosting(
            external_id=str(external_id),
            url=entry.get("link", ""),
            title=title,
            company=company,
            description=description,
            language=detect_job_language(title, description),
            region=JobRegion.REMOTE_INTL,
            location=None,
            posted_at=posted_at,
        )
