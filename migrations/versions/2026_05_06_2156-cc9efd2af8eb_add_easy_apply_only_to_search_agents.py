"""add easy_apply_only to search_agents

Revision ID: cc9efd2af8eb
Revises: 568ce812c1e5
Create Date: 2026-05-06 21:56:01.368467

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc9efd2af8eb'
down_revision: Union[str, Sequence[str], None] = '568ce812c1e5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'search_agents',
        sa.Column('easy_apply_only', sa.Boolean(), nullable=True),
        schema='public',
    )


def downgrade() -> None:
    op.drop_column('search_agents', 'easy_apply_only', schema='public')
