from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models.job_posting import JobLanguage, JobRegion


@dataclass(frozen=True)
class RawJobPosting:
    """Output of a SourceAdapter. Pure I/O data — no AI-derived fields here."""

    external_id: str
    url: str
    title: str
    company: str
    description: str
    language: JobLanguage
    region: JobRegion
    location: str | None = None
    posted_at: datetime | None = None


class SourceAdapter(ABC):
    """Common interface every job source (API, RSS, scrape) implements."""

    slug: str

    @abstractmethod
    async def fetch(self) -> list[RawJobPosting]:
        """Fetch and parse postings from the source. Never writes to the DB."""
        raise NotImplementedError
