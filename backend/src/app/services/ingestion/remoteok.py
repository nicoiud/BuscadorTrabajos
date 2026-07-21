from datetime import datetime

import httpx

from app.core.config import settings
from app.models.job_posting import JobLanguage, JobRegion
from app.services.ingestion.base import RawJobPosting, SourceAdapter

REMOTEOK_API_URL = "https://remoteok.com/api"


class RemoteOkAdapter(SourceAdapter):
    """RemoteOK public JSON API — no API key required."""

    slug = "remoteok"

    async def fetch(self) -> list[RawJobPosting]:
        headers = {"User-Agent": settings.scraper_user_agent, "Accept": "application/json"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(REMOTEOK_API_URL, headers=headers)
            response.raise_for_status()
            payload = response.json()

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

        return RawJobPosting(
            external_id=str(entry["id"]),
            url=entry.get("url") or f"https://remoteok.com/remote-jobs/{entry['id']}",
            title=entry.get("position", "").strip(),
            company=entry.get("company", "").strip(),
            description=entry.get("description", "") or "",
            language=JobLanguage.EN,
            region=JobRegion.REMOTE_INTL,
            location=entry.get("location") or None,
            posted_at=posted_at,
        )
