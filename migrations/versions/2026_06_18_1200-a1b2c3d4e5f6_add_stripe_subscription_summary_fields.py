"""Add Stripe subscription summary fields.

Revision ID: a1b2c3d4e5f6
Revises: 509e32610a76
Create Date: 2026-06-18 12:00:00.000000

"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: str | Sequence[str] | None = "509e32610a76"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "subscriptions",
        sa.Column("current_period_start", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "subscriptions",
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "subscriptions",
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=True),
        schema="public",
    )
    op.add_column(
        "subscriptions",
        sa.Column("canceled_at", sa.DateTime(timezone=True), nullable=True),
        schema="public",
    )
    op.add_column(
        "subscriptions", sa.Column("amount", sa.Integer(), nullable=True), schema="public"
    )
    op.add_column(
        "subscriptions", sa.Column("currency", sa.String(), nullable=True), schema="public"
    )


def downgrade() -> None:
    op.drop_column("subscriptions", "currency", schema="public")
    op.drop_column("subscriptions", "amount", schema="public")
    op.drop_column("subscriptions", "canceled_at", schema="public")
    op.drop_column("subscriptions", "cancel_at_period_end", schema="public")
    op.drop_column("subscriptions", "current_period_end", schema="public")
    op.drop_column("subscriptions", "current_period_start", schema="public")
