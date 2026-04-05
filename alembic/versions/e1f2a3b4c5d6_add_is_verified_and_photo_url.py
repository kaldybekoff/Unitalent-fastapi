"""add is_verified and photo_url

Revision ID: e1f2a3b4c5d6
Revises: b3e1f2a4c5d6
Create Date: 2026-04-05 12:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e1f2a3b4c5d6'
down_revision: Union[str, Sequence[str], None] = 'b3e1f2a4c5d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('candidates', sa.Column('photo_url', sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column('candidates', 'photo_url')
    op.drop_column('users', 'is_verified')
