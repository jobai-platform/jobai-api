"""Stripe sync prices

Revision ID: 0cf3f33ef9af
Revises: 8f0c147e01db
Create Date: 2026-04-29 13:29:37.641092

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '0cf3f33ef9af'
down_revision: Union[str, Sequence[str], None] = '8f0c147e01db'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_prices",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            nullable=False,
        ),
        sa.Column("plan", sa.String(length=50), nullable=False),
        sa.Column("stripe_price_id", sa.String(length=255), nullable=False),
        sa.Column("stripe_product_id", sa.String(length=255), nullable=False),
        sa.Column("currency", sa.String(length=10), nullable=False),
        sa.Column("amount", sa.Integer(), nullable=False),
        sa.Column("interval", sa.String(length=50), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "stripe_price_id",
            name="uq_billing_prices_stripe_price_id",
        ),
    )

    op.create_index(
        "ix_billing_prices_plan",
        "billing_prices",
        ["plan"],
        unique=False,
    )

    op.add_column(
        "subscriptions",
        sa.Column(
            "billing_price_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
    )

    op.create_foreign_key(
        "fk_subscriptions_billing_price_id_billing_prices",
        "subscriptions",
        "billing_prices",
        ["billing_price_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint(
        "fk_subscriptions_billing_price_id_billing_prices",
        "subscriptions",
        type_="foreignkey",
    )
    op.drop_column("subscriptions", "billing_price_id")
    op.drop_index("ix_billing_prices_plan", table_name="billing_prices")
    op.drop_table("billing_prices")
