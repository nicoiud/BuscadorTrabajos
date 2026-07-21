"""initial schema: sources, job_postings

Revision ID: 0001
Revises:
Create Date: 2026-07-21

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1024


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "sources",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("slug", sa.String(64), nullable=False, unique=True),
        sa.Column(
            "type", sa.Enum("api", "rss", "scrape", name="source_type"), nullable=False
        ),
        sa.Column(
            "region", sa.Enum("latam", "global", name="source_region"), nullable=False
        ),
        sa.Column(
            "language",
            sa.Enum("es", "en", "mixed", name="source_language"),
            nullable=False,
        ),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "rate_limit_seconds", sa.Float(), nullable=False, server_default="3"
        ),
        sa.Column("last_run_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_success_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "config",
            sa.JSON().with_variant(postgresql.JSONB(), "postgresql"),
            nullable=False,
            server_default="{}",
        ),
    )

    op.create_table(
        "job_postings",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "source_id", sa.Uuid(), sa.ForeignKey("sources.id"), nullable=False
        ),
        sa.Column("external_id", sa.String(255), nullable=False),
        sa.Column("url", sa.String(2048), nullable=False),
        sa.Column("title_raw", sa.String(512), nullable=False),
        sa.Column("company_raw", sa.String(255), nullable=False),
        sa.Column("description_raw", sa.Text(), nullable=False),
        sa.Column("location_raw", sa.String(255), nullable=True),
        sa.Column("posted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("scraped_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("language", sa.Enum("es", "en", name="job_language"), nullable=False),
        sa.Column(
            "region",
            sa.Enum("latam", "remote_intl", "other", name="job_region"),
            nullable=False,
        ),
        sa.Column("title_normalized", sa.String(512), nullable=True),
        sa.Column("company_normalized", sa.String(255), nullable=True),
        sa.Column(
            "seniority",
            sa.Enum("junior", "mid", "senior", "lead", "exec", name="seniority"),
            nullable=True,
        ),
        sa.Column(
            "modality",
            sa.Enum("remote", "hybrid", "onsite", name="modality"),
            nullable=True,
        ),
        sa.Column("salary_min", sa.Integer(), nullable=True),
        sa.Column("salary_max", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(8), nullable=True),
        sa.Column("requirements", sa.JSON(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=True),
        sa.Column(
            "enrichment_status",
            sa.Enum("pending", "done", "failed", name="enrichment_status"),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("enrichment_model", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("source_id", "external_id", name="uq_source_external_id"),
    )
    op.create_index("ix_job_postings_region_lang_active", "job_postings", ["region", "language", "is_active"])


def downgrade() -> None:
    op.drop_table("job_postings")
    op.drop_table("sources")
    op.execute("DROP TYPE IF EXISTS enrichment_status")
    op.execute("DROP TYPE IF EXISTS modality")
    op.execute("DROP TYPE IF EXISTS seniority")
    op.execute("DROP TYPE IF EXISTS job_region")
    op.execute("DROP TYPE IF EXISTS job_language")
    op.execute("DROP TYPE IF EXISTS source_language")
    op.execute("DROP TYPE IF EXISTS source_region")
    op.execute("DROP TYPE IF EXISTS source_type")
