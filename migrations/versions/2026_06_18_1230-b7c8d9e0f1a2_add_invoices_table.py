"""Add invoices table.

Revision ID: b7c8d9e0f1a2
Revises: a1b2c3d4e5f6
Create Date: 2026-06-18 12:30:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "b7c8d9e0f1a2"
down_revision: str | Sequence[str] | None = "a1b2c3d4e5f6"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "invoices",
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
        sa.Column("stripe_invoice_id", sa.String(), nullable=True),
        sa.Column("stripe_payment_id", sa.String(), nullable=True),
        sa.Column("amount", sa.Integer(), nullable=True),
        sa.Column("currency", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("paid_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("hosted_invoice_url", sa.String(), nullable=True),
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
    op.create_index("ix_invoices_user_id", "invoices", ["user_id"], schema="public")
    op.create_index(
        "ix_invoices_stripe_customer_id",
        "invoices",
        ["stripe_customer_id"],
        schema="public",
    )
    op.create_index(
        "ix_invoices_stripe_invoice_id",
        "invoices",
        ["stripe_invoice_id"],
        unique=True,
        schema="public",
    )
    op.create_index(
        "ix_invoices_stripe_payment_id",
        "invoices",
        ["stripe_payment_id"],
        schema="public",
    )


def downgrade() -> None:
    op.drop_index("ix_invoices_stripe_payment_id", table_name="invoices", schema="public")
    op.drop_index("ix_invoices_stripe_invoice_id", table_name="invoices", schema="public")
    op.drop_index("ix_invoices_stripe_customer_id", table_name="invoices", schema="public")
    op.drop_index("ix_invoices_user_id", table_name="invoices", schema="public")
    op.drop_table("invoices", schema="public")
