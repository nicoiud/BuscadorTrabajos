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


def _enum(python_enum_cls: type[enum.Enum], name: str) -> Enum:
    # Sin values_callable, SQLAlchemy manda el .name del enum (ej. "PENDING") en vez
    # del .value (ej. "pending") — pero el tipo enum de Postgres, creado por la
    # migración, solo acepta los valores en minúscula. Sin esto, cualquier insert
    # rompe con "invalid input value for enum ...".
    # create_constraint=True no cambia nada en Postgres (el enum nativo ya valida
    # solo), pero en SQLite (usado en tests) hace que se genere un CHECK constraint
    # real — sin esto, SQLite acepta cualquier string sin validar nada.
    return Enum(
        python_enum_cls,
        name=name,
        values_callable=lambda obj: [e.value for e in obj],
        create_constraint=True,
    )


class JobLanguage(str, enum.Enum):
    ES = "es"
    EN = "en"
    PT = "pt"
    OTHER = "other"


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

    language: Mapped[JobLanguage] = mapped_column(_enum(JobLanguage, "job_language"))
    region: Mapped[JobRegion] = mapped_column(_enum(JobRegion, "job_region"))

    # AI-enriched fields — nullable until the enrichment pipeline (Phase 2) processes them.
    title_normalized: Mapped[str | None] = mapped_column(String(512), nullable=True)
    company_normalized: Mapped[str | None] = mapped_column(String(255), nullable=True)
    seniority: Mapped[Seniority | None] = mapped_column(_enum(Seniority, "seniority"), nullable=True)
    modality: Mapped[Modality | None] = mapped_column(_enum(Modality, "modality"), nullable=True)
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
        _enum(EnrichmentStatus, "enrichment_status"),
        nullable=False,
        default=EnrichmentStatus.PENDING,
    )
    enrichment_model: Mapped[str | None] = mapped_column(String(64), nullable=True)

    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
