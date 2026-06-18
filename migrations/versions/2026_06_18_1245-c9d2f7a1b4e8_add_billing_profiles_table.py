"""Add billing profiles table.

Revision ID: c9d2f7a1b4e8
Revises: b7c8d9e0f1a2
Create Date: 2026-06-18 12:45:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "c9d2f7a1b4e8"
down_revision: str | Sequence[str] | None = "b7c8d9e0f1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "billing_profiles",
        sa.Column(
            "id",
            sa.UUID(),
            server_default=sa.text("gen_random_uuid()"),
            primary_key=True,
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.UUID(),
            sa.ForeignKey("public.users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("contact_first_name", sa.String(), nullable=True),
        sa.Column("contact_last_name", sa.String(), nullable=True),
        sa.Column("contact_email", sa.String(), nullable=True),
        sa.Column("address_line1", sa.String(), nullable=True),
        sa.Column("address_line2", sa.String(), nullable=True),
        sa.Column("address_city", sa.String(), nullable=True),
        sa.Column("address_state", sa.String(), nullable=True),
        sa.Column("address_postal_code", sa.String(), nullable=True),
        sa.Column("address_country", sa.String(), nullable=True),
        sa.Column("payment_method_id", sa.String(), nullable=True),
        sa.Column("payment_method_brand", sa.String(), nullable=True),
        sa.Column("payment_method_last4", sa.String(length=4), nullable=True),
        sa.Column("payment_method_exp_month", sa.Integer(), nullable=True),
        sa.Column("payment_method_exp_year", sa.Integer(), nullable=True),
        sa.Column("payment_method_holder_name", sa.String(), nullable=True),
        sa.Column("payment_method_country", sa.String(), nullable=True),
        sa.Column("payment_method_funding", sa.String(), nullable=True),
        sa.Column("payment_method_wallet", sa.String(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            onupdate=sa.func.now(),
            nullable=False,
        ),
        schema="public",
    )
    op.create_index(
        "ix_billing_profiles_user_id",
        "billing_profiles",
        ["user_id"],
        unique=True,
        schema="public",
    )
    op.create_index(
        "ix_billing_profiles_stripe_customer_id",
        "billing_profiles",
        ["stripe_customer_id"],
        unique=True,
        schema="public",
    )
    op.create_index(
        "ix_billing_profiles_contact_email",
        "billing_profiles",
        ["contact_email"],
        schema="public",
    )
    op.create_index(
        "ix_billing_profiles_payment_method_id",
        "billing_profiles",
        ["payment_method_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index(
        "ix_billing_profiles_payment_method_id",
        table_name="billing_profiles",
        schema="public",
    )
    op.drop_index(
        "ix_billing_profiles_contact_email",
        table_name="billing_profiles",
        schema="public",
    )
    op.drop_index(
        "ix_billing_profiles_stripe_customer_id",
        table_name="billing_profiles",
        schema="public",
    )
    op.drop_index(
        "ix_billing_profiles_user_id",
        table_name="billing_profiles",
        schema="public",
    )
    op.drop_table("billing_profiles", schema="public")
