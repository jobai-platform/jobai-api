"""add refresh tokens table

Revision ID: bf37b1a4c2d9
Revises: aac3238ce036
Create Date: 2026-05-20 18:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


revision: str = "bf37b1a4c2d9"
down_revision: Union[str, Sequence[str], None] = "aac3238ce036"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("id", UUID(as_uuid=True), nullable=False),
        sa.Column("jti", sa.String(length=64), nullable=False),
        sa.Column("user_id", UUID(as_uuid=True), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["public.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("jti", name="uq_refresh_tokens_jti"),
        schema="public",
    )
    op.create_index("ix_public_refresh_tokens_jti", "refresh_tokens", ["jti"], unique=False, schema="public")
    op.create_index("ix_public_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False, schema="public")
    op.create_index("ix_public_refresh_tokens_revoked_at", "refresh_tokens", ["revoked_at"], unique=False, schema="public")


def downgrade() -> None:
    op.drop_index("ix_public_refresh_tokens_revoked_at", table_name="refresh_tokens", schema="public")
    op.drop_index("ix_public_refresh_tokens_user_id", table_name="refresh_tokens", schema="public")
    op.drop_index("ix_public_refresh_tokens_jti", table_name="refresh_tokens", schema="public")
    op.drop_table("refresh_tokens", schema="public")
