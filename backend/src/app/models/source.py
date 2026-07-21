import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Enum, Float, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SourceType(str, enum.Enum):
    API = "api"
    RSS = "rss"
    SCRAPE = "scrape"


class SourceRegion(str, enum.Enum):
    LATAM = "latam"
    GLOBAL = "global"


class SourceLanguage(str, enum.Enum):
    ES = "es"
    EN = "en"
    MIXED = "mixed"


class Source(Base):
    __tablename__ = "sources"

    id: Mapped[uuid.UUID] = mapped_column(Uuid(), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    type: Mapped[SourceType] = mapped_column(Enum(SourceType, name="source_type"), nullable=False)
    region: Mapped[SourceRegion] = mapped_column(
        Enum(SourceRegion, name="source_region"), nullable=False
    )
    language: Mapped[SourceLanguage] = mapped_column(
        Enum(SourceLanguage, name="source_language"), nullable=False
    )
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    rate_limit_seconds: Mapped[float] = mapped_column(Float, nullable=False, default=3.0)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_success_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    config: Mapped[dict] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=False, default=dict
    )
