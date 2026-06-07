"""add password reset tokens

Revision ID: e2f5b7719c31
Revises: c4a9e8b3f012
Create Date: 2026-06-07 12:00:00.000000

"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision: str = "e2f5b7719c31"
down_revision: str | Sequence[str] | None = "c4a9e8b3f012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "password_reset_tokens",
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("candidate_id", UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("consumed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["candidate_id"], ["public.users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("token_hash"),
        schema="public",
    )
    op.create_index(
        "ix_public_password_reset_tokens_candidate_id",
        "password_reset_tokens",
        ["candidate_id"],
        unique=False,
        schema="public",
    )
    op.create_index(
        "ix_public_password_reset_tokens_consumed_at",
        "password_reset_tokens",
        ["consumed_at"],
        unique=False,
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_public_password_reset_tokens_consumed_at",
        table_name="password_reset_tokens",
        schema="public",
    )
    op.drop_index(
        "ix_public_password_reset_tokens_candidate_id",
        table_name="password_reset_tokens",
        schema="public",
    )
    op.drop_table("password_reset_tokens", schema="public")
