from uuid import UUID

from app.application.billing.ports import BillingProfileRepository
from app.domain.billing.entities.billing_profile import BillingProfile


class InMemoryBillingProfileRepository(BillingProfileRepository):
    def __init__(self) -> None:
        self._profiles_by_user_id: dict[UUID, BillingProfile] = {}
        self._profiles_by_stripe_customer_id: dict[str, BillingProfile] = {}

    async def get_by_user_id(self, user_id: UUID) -> BillingProfile | None:
        return self._profiles_by_user_id.get(user_id)

    async def get_by_stripe_customer_id(self, stripe_customer_id: str) -> BillingProfile | None:
        return self._profiles_by_stripe_customer_id.get(stripe_customer_id)

    async def upsert(self, profile: BillingProfile) -> BillingProfile:
        self._profiles_by_user_id[profile.user_id] = profile
        if profile.stripe_customer_id:
            self._profiles_by_stripe_customer_id[profile.stripe_customer_id] = profile
        return profile
