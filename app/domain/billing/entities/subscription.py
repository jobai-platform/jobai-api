from dataclasses import dataclass
from datetime import datetime
import logging
from uuid import UUID

from app.domain.billing.enums import Plan, SubscriptionStatus

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Subscription:
    user_id: UUID
    plan: Plan
    status: SubscriptionStatus
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    billing_price_id: UUID | None = None
    current_period_start: datetime | None = None
    current_period_end: datetime | None = None
    cancel_at_period_end: bool | None = None
    canceled_at: datetime | None = None
    amount: int | None = None
    currency: str | None = None

    @classmethod
    def create_freemium(
        cls,
        user_id: UUID,
        stripe_customer_id: str | None = None,
        stripe_subscription_id: str | None = None,
        billing_price_id: UUID | None = None,
        current_period_start: datetime | None = None,
        current_period_end: datetime | None = None,
        cancel_at_period_end: bool | None = None,
        canceled_at: datetime | None = None,
        amount: int | None = None,
        currency: str | None = None,
    ) -> "Subscription":
        return cls(
            user_id=user_id,
            plan=Plan.FREEMIUM,
            status=SubscriptionStatus.ACTIVE,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            billing_price_id=billing_price_id,
            current_period_start=current_period_start,
            current_period_end=current_period_end,
            cancel_at_period_end=cancel_at_period_end,
            canceled_at=canceled_at,
            amount=amount,
            currency=currency,
        )

    def assign_paid_plan(
        self,
        *,
        plan: Plan,
        stripe_customer_id: str | None,
        stripe_subscription_id: str | None,
        billing_price_id: UUID | None = None,
        status: SubscriptionStatus = SubscriptionStatus.PENDING,
        current_period_start: datetime | None = None,
        current_period_end: datetime | None = None,
        cancel_at_period_end: bool | None = None,
        canceled_at: datetime | None = None,
        amount: int | None = None,
        currency: str | None = None,
    ) -> None:
        if plan == Plan.FREEMIUM:
            logger.warning(
                "Attempted to assign freemium plan using assign_paid_plan method. "
                "This is not allowed."
            )
            raise ValueError(
                "Cannot assign freemium plan using this method. Use create_freemium instead."
            )

        self.plan = plan
        self.status = status
        self.stripe_customer_id = stripe_customer_id
        self.stripe_subscription_id = stripe_subscription_id
        self.billing_price_id = billing_price_id
        self.current_period_start = current_period_start
        self.current_period_end = current_period_end
        self.cancel_at_period_end = cancel_at_period_end
        self.canceled_at = canceled_at
        self.amount = amount
        self.currency = currency

    def update_status(self, status: SubscriptionStatus) -> None:
        self.status = status
