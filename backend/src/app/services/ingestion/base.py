from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime

from app.models.job_posting import JobLanguage, JobRegion
from app.models.source import SourceLanguage, SourceRegion, SourceType


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
    source_type: SourceType
    source_region: SourceRegion
    source_language: SourceLanguage

    @abstractmethod
    async def fetch(self) -> list[RawJobPosting]:
        """Fetch and parse postings from the source. Never writes to the DB."""
        raise NotImplementedError

    def source_defaults(self) -> dict:
        """Config used to create the `sources` row the first time this adapter
        runs. Adapters parametrizados por empresa (Greenhouse, Lever) tienen un
        `slug` distinto por instancia, así que estos defaults no pueden vivir en un
        diccionario estático por slug fijo — cada adapter los expone a sí mismo."""
        return {
            "type": self.source_type,
            "region": self.source_region,
            "language": self.source_language,
        }
