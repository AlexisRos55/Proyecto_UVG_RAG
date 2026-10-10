"""add structured sources to messages (ADR-0014)

Revision ID: b7f3c2d91a40
Revises: 8a8e46d41275
Create Date: 2026-09-24 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7f3c2d91a40'
down_revision: Union[str, Sequence[str], None] = '8a8e46d41275'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    Additive and nullable: existing messages keep `source_document_names` and
    simply have no structured citations.
    """
    op.add_column('messages', sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('messages', 'sources')
