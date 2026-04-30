from sqlalchemy import Boolean, DateTime, Integer, String, func, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.constants.general import DB_SCHEMA
from app.infrastructure.config.database import Base


class BillingPriceModel(Base):
    __tablename__ = "billing_prices"
    __table_args__ = (
        UniqueConstraint("stripe_price_id", name="uq_billing_price_stripe_id"),
        {"schema": DB_SCHEMA}
    )

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    plan: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    stripe_price_id: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    stripe_product_id: Mapped[str] = mapped_column(String(255), nullable=False)
    currency: Mapped[str] = mapped_column(String(10), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    interval: Mapped[str] = mapped_column(String(50), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="true")
    created_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[str] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
