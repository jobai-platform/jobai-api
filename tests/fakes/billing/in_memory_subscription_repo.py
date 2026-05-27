from typing import Optional
from uuid import UUID

from app.application.billing.ports import SubscriptionRepository
from app.domain.billing.entities.subscription import Subscription


class InMemorySubscriptionRepository(SubscriptionRepository):
    def __init__(self) -> None:
        self._store: dict[UUID, Subscription] = {}

    async def get_by_user_id(self, user_id: UUID) -> Optional[Subscription]:
        return self._store.get(user_id)

    async def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        return next(
            (s for s in self._store.values() if s.stripe_subscription_id == stripe_subscription_id),
            None,
        )

    async def create(self, subscription: Subscription) -> Subscription:
        self._store[subscription.user_id] = subscription
        return subscription

    async def update(self, subscription: Subscription) -> Optional[Subscription]:
        if subscription.user_id not in self._store:
            return None
        self._store[subscription.user_id] = subscription
        return subscription
