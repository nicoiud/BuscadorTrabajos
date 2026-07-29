import json
from datetime import datetime

import httpx

from app.core.config import settings
from app.models.job_posting import JobRegion
from app.services.ingestion.base import RawJobPosting, SourceAdapter
from app.services.ingestion.language_detection import detect_job_language

REMOTEOK_API_URL = "https://remoteok.com/api"


class RemoteOkAdapter(SourceAdapter):
    """RemoteOK public JSON API — no API key required."""

    slug = "remoteok"

    async def fetch(self) -> list[RawJobPosting]:
        headers = {"User-Agent": settings.scraper_user_agent, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(REMOTEOK_API_URL, headers=headers)
            response.raise_for_status()
            # RemoteOK no siempre declara `charset=utf-8` en el Content-Type, y la
            # detección automática de httpx puede terminar decodificando los bytes
            # UTF-8 como Latin-1 (mojibake tipo "Ã¡" en vez de "á"). Forzamos UTF-8
            # explícitamente en vez de confiar en response.json().
            payload = json.loads(response.content.decode("utf-8"))

        postings: list[RawJobPosting] = []
        for entry in payload:
            # The first array element is a legal notice, not a job posting.
            if not isinstance(entry, dict) or "id" not in entry or "position" not in entry:
                continue
            postings.append(self._parse_entry(entry))
        return postings

    @staticmethod
    def _parse_entry(entry: dict) -> RawJobPosting:
        posted_at: datetime | None = None
        date_str = entry.get("date")
        if date_str:
            try:
                posted_at = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
            except ValueError:
                posted_at = None

        title = entry.get("position", "").strip()
        description = entry.get("description", "") or ""

        return RawJobPosting(
            external_id=str(entry["id"]),
            url=entry.get("url") or f"https://remoteok.com/remote-jobs/{entry['id']}",
            title=title,
            company=entry.get("company", "").strip(),
            description=description,
            # RemoteOK agrega avisos en varios idiomas (predominantemente inglés,
            # pero también portugués y español) — no se puede asumir "en" a ciegas.
            language=detect_job_language(title, description),
            region=JobRegion.REMOTE_INTL,
            location=entry.get("location") or None,
            posted_at=posted_at,
        )
