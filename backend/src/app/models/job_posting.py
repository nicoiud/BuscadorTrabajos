import enum
import uuid
from datetime import datetime

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

EMBEDDING_DIM = 1024  # voyage-3 embedding size


class JobLanguage(str, enum.Enum):
    ES = "es"
    EN = "en"


class JobRegion(str, enum.Enum):
    LATAM = "latam"
    REMOTE_INTL = "remote_intl"
    OTHER = "other"


class Seniority(str, enum.Enum):
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    EXEC = "exec"


class Modality(str, enum.Enum):
    REMOTE = "remote"
    HYBRID = "hybrid"
    ONSITE = "onsite"


class EnrichmentStatus(str, enum.Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class JobPosting(Base):
    __tablename__ = "job_postings"
    __table_args__ = (UniqueConstraint("source_id", "external_id", name="uq_source_external_id"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    source_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(), ForeignKey("sources.id"), nullable=False
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(String(2048), nullable=False)

    title_raw: Mapped[str] = mapped_column(String(512), nullable=False)
    company_raw: Mapped[str] = mapped_column(String(255), nullable=False)
    description_raw: Mapped[str] = mapped_column(Text, nullable=False)
    location_raw: Mapped[str | None] = mapped_column(String(255), nullable=True)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    language: Mapped[JobLanguage] = mapped_column(Enum(JobLanguage, name="job_language"))
    region: Mapped[JobRegion] = mapped_column(Enum(JobRegion, name="job_region"))

    # AI-enriched fields — nullable until the enrichment pipeline (Phase 2) processes them.
    title_normalized: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company_normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seniority: Mapped[Seniority | None] = mapped_column(
        Enum(Seniority, name="seniority"), nullable=True
    )
    modality: Mapped[Modality | None] = mapped_column(
        Enum(Modality, name="modality"), nullable=True
    )
    salary_min: Mapped[int | None] = mapped_column(nullable=True)
    salary_max: Mapped[int | None] = mapped_column(nullable=True)
    currency: Mapped[str | None] = mapped_column(String(8), nullable=True)
    requirements: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    # SQLite has no pgvector extension; tests store the same list[float] as JSON so
    # enrichment persistence is still exercised without a real Postgres.
    embedding: Mapped[list[float] | None] = mapped_column(
        Vector(EMBEDDING_DIM).with_variant(JSON(), "sqlite"), nullable=True
    )
    enrichment_status: Mapped[EnrichmentStatus] = mapped_column(
        Enum(EnrichmentStatus, name="enrichment_status"),
        nullable=False,
        default=EnrichmentStatus.PENDING,
    )
    enrichment_model: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
