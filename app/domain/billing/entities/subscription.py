from dataclasses import dataclass
from typing import Optional
from uuid import UUID

from app.domain.billing.enums import Plan, SubscriptionStatus


@dataclass
class Subscription:
    user_id: UUID
    plan: Plan
    status: SubscriptionStatus
    stripe_customer_id: Optional[str] = None
    stripe_subscription_id: Optional[str] = None

    @classmethod
    def create_freemium(cls, user_id: UUID) -> "Subscription":
        return cls(
            user_id=user_id,
            plan=Plan.FREEMIUM,
            status=SubscriptionStatus.ACTIVE
        )


    def assign_paid_plan(
        self,
        *,
        plan: Plan,
        stripe_customer_id: Optional[str],
        stripe_subscription_id: Optional[str],
        status: SubscriptionStatus = SubscriptionStatus.PENDING,
    ) -> None:
        self.plan = plan
        self.status = status
        self.stripe_customer_id = stripe_customer_id
        self.stripe_subscription_id = stripe_subscription_id


    def update_status(self, status: SubscriptionStatus) -> None:
        self.status = status
