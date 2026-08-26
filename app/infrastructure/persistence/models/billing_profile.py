from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.general import DB_SCHEMA
from app.infrastructure.config.database import Base


class BillingProfileModel(Base):
    __tablename__ = "billing_profiles"
    __table_args__ = {"schema": DB_SCHEMA}

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey(f"{DB_SCHEMA}.users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        unique=True,
        index=True,
    )
    contact_first_name: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_last_name: Mapped[str | None] = mapped_column(String, nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    address_line1: Mapped[str | None] = mapped_column(String, nullable=True)
    address_line2: Mapped[str | None] = mapped_column(String, nullable=True)
    address_city: Mapped[str | None] = mapped_column(String, nullable=True)
    address_state: Mapped[str | None] = mapped_column(String, nullable=True)
    address_postal_code: Mapped[str | None] = mapped_column(String, nullable=True)
    address_country: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_method_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    payment_method_brand: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_method_last4: Mapped[str | None] = mapped_column(String(4), nullable=True)
    payment_method_exp_month: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_method_exp_year: Mapped[int | None] = mapped_column(Integer, nullable=True)
    payment_method_holder_name: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_method_country: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_method_funding: Mapped[str | None] = mapped_column(String, nullable=True)
    payment_method_wallet: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
