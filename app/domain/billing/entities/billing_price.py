import logging
from dataclasses import dataclass
from uuid import UUID

from app.domain.billing.enums import Plan

logger = logging.getLogger(__name__)


@dataclass
class BillingPrice:
    plan: Plan
    stripe_price_id: str
    stripe_product_id: str
    currency: str
    amount: float
    interval: str
    active: bool
    id: UUID | None = None

    @classmethod
    def create(
        cls,
        *,
        plan: Plan,
        stripe_price_id: str,
        stripe_product_id: str,
        currency: str,
        amount: float,
        interval: str,
        active: bool,
    ) -> "BillingPrice":
        if amount < 0:
            logger.error("Invalid billing price amount: %f", amount)
            raise ValueError("Billing price amount cannot be negative")

        if not stripe_price_id:
            logger.error("Invalid billing price id: %r", stripe_price_id)
            raise ValueError("Billing price id cannot be None")

        if not stripe_product_id:
            logger.error("Invalid billing price id: %r", stripe_price_id)
            raise ValueError("Billing price id cannot be None")

        if not currency:
            logger.error("Currency is required")
            raise ValueError("Currency is required")

        if not interval:
            logger.error("Interval is required")
            raise ValueError("Interval is required")

        return cls(
            plan=plan,
            stripe_price_id=stripe_price_id,
            stripe_product_id=stripe_product_id,
            currency=currency,
            amount=amount,
            interval=interval,
            active=active,
        )
