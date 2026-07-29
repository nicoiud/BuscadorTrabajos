"""job_language: agregar valores pt y other

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-29

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # RemoteOK trae avisos en portugués (y ocasionalmente otros idiomas) además de
    # español/inglés — antes de esto el adapter mandaba "en" hardcodeado sin importar
    # el idioma real del texto. IF NOT EXISTS hace esto seguro de re-correr.
    op.execute("ALTER TYPE job_language ADD VALUE IF NOT EXISTS 'pt'")
    op.execute("ALTER TYPE job_language ADD VALUE IF NOT EXISTS 'other'")


def downgrade() -> None:
    # Postgres no soporta DROP VALUE en un enum nativo sin recrear el tipo entero
    # (y reasignar la columna) — no vale la pena para un downgrade. Si hace falta
    # revertir, hay que hacerlo a mano.
    pass
