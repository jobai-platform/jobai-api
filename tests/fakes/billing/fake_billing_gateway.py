from uuid import UUID

from app.application.billing.ports import BillingGateway
from app.domain.billing.enums import Plan


class FakeBillingGateway(BillingGateway):
    async def create_checkout_session(
        self, *, email: str, user_id: UUID, plan: str, success_url: str, cancel_url: str
    ) -> str:
        return "https://fake-checkout.stripe.com/session"

    async def create_customer(self, *, email: str, user_id: UUID) -> str:
        return f"cus_fake_{user_id}"

    async def create_subscription(
        self, *, customer_id: str, stripe_price_id: str, user_id: UUID, plan: Plan
    ) -> str:
        return f"sub_fake_{user_id}"

    async def list_prices(self) -> list[dict]:
        return []

    async def verify_and_construct_event(self, payload: bytes, signature: str) -> dict:
        return {}
