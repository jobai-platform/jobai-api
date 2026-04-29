import logging
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.domain.billing.enums import Plan, SubscriptionStatus

logger = logging.getLogger(__name__)

@dataclass
class Subscription:
    user_id: UUID
    plan: Plan
    status: SubscriptionStatus
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None
    billing_price_id: Optional[UUID] = None

    @classmethod
    def create_freemium(
        cls,
        user_id: UUID,
        stripe_customer_id: Optional[str] = None,
        stripe_subscription_id: Optional[str] = None,
        billing_price_id: Optional[UUID] = None,
    ) -> "Subscription":
        return cls(
            user_id=user_id,
            plan=Plan.FREEMIUM,
            status=SubscriptionStatus.ACTIVE,
            stripe_customer_id=stripe_customer_id,
            stripe_subscription_id=stripe_subscription_id,
            billing_price_id=billing_price_id,
        )


    def assign_paid_plan(
        self,
        *,
        plan: Plan,
        stripe_customer_id: Optional[str],
        stripe_subscription_id: Optional[str],
        billing_price_id: Optional[UUID] = None,
        status: SubscriptionStatus = SubscriptionStatus.PENDING,
    ) -> None:
        if plan == Plan.FREEMIUM:
            logger.warning("Attempted to assign freemium plan using assign_paid_plan method. This is not allowed.")
            raise ValueError("Cannot assign freemium plan using this method. Use create_freemium instead.")

        self.plan = plan
        self.status = status
        self.stripe_customer_id = stripe_customer_id
        self.stripe_subscription_id = stripe_subscription_id
        self.billing_price_id = billing_price_id

    def update_status(self, status: SubscriptionStatus) -> None:
        self.status = status
