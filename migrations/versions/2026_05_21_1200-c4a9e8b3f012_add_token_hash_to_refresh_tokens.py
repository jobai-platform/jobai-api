"""add token_hash to refresh_tokens

Revision ID: c4a9e8b3f012
Revises: bf37b1a4c2d9
Create Date: 2026-05-21 12:00:00.000000

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "c4a9e8b3f012"
down_revision: Union[str, Sequence[str], None] = "bf37b1a4c2d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "refresh_tokens",
        sa.Column("token_hash", sa.String(length=64), nullable=True),
        schema="public",
    )
    op.create_index(
        "ix_public_refresh_tokens_token_hash",
        "refresh_tokens",
        ["token_hash"],
        unique=True,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_public_refresh_tokens_token_hash", table_name="refresh_tokens", schema="public")
    op.drop_column("refresh_tokens", "token_hash", schema="public")
