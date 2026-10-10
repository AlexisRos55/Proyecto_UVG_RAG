"""guest users: credentials optional only for the guest role (ADR-0019)

Revision ID: c4e8a1f0b2d7
Revises: b7f3c2d91a40
Create Date: 2026-10-09 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = 'c4e8a1f0b2d7'
down_revision: Union[str, Sequence[str], None] = 'b7f3c2d91a40'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema.

    A guest is a user without email or password. The columns become nullable,
    and a CHECK keeps every non-guest account with both credentials, so the
    relaxation cannot weaken institutional accounts. Existing rows are unaffected.
    """
    op.alter_column('users', 'email', existing_type=sa.Text(), nullable=True)
    op.alter_column('users', 'password_hash', existing_type=sa.Text(), nullable=True)
    op.create_check_constraint(
        'ck_users_credentials_unless_guest',
        'users',
        "role = 'guest' OR (email IS NOT NULL AND password_hash IS NOT NULL)",
    )


def downgrade() -> None:
    """Downgrade schema: guest sessions are temporary, so they are removed first."""
    op.execute("DELETE FROM users WHERE role = 'guest'")
    op.drop_constraint('ck_users_credentials_unless_guest', 'users', type_='check')
    op.alter_column('users', 'password_hash', existing_type=sa.Text(), nullable=False)
    op.alter_column('users', 'email', existing_type=sa.Text(), nullable=False)
