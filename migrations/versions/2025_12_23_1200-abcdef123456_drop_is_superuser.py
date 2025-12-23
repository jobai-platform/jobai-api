"""drop is_superuser column from users table

Revision ID: 202512231200abcdef123456
Revises: 16cb4c36c81d
Create Date: 2025-12-23 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '202512231200abcdef123456'
down_revision: Union[str, Sequence[str], None] = '16cb4c36c81d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the `is_superuser` column from `public.users`.

    Using batch_alter_table keeps this migration safe across multiple DB backends.
    """
    with op.batch_alter_table('users', schema='public') as batch_op:
        batch_op.drop_column('is_superuser')


def downgrade() -> None:
    """Re-create the `is_superuser` column on `public.users`.

    We add a server_default of false to ensure existing rows in a downgrade
    won't violate NOT NULL constraints; this mirrors a safe rollback.
    """
    with op.batch_alter_table('users', schema='public') as batch_op:
        batch_op.add_column(
            sa.Column('is_superuser', sa.Boolean(), nullable=False, server_default=sa.text('false'))
        )
