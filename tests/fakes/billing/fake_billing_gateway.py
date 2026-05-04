from uuid import UUID

from app.application.billing.ports import BillingGateway
from app.domain.billing.enums import Plan


class FakeBillingGateway(BillingGateway):
    async def create_checkout_session(
        self,
        *,
        _email: str,
        _user_id: UUID,
        _plan: str,
        _success_url: str,
        _cancel_url: str,
        _attempt: int = 1,
    ) -> str:
        return "https://fake-checkout.stripe.com/session"

    async def create_customer(
        self,
        *,
        _email: str,
        _user_id: UUID,
    ) -> str:
        return f"cus_fake_{_user_id}"

    async def create_subscription(
        self,
        *,
        _customer_id: str,
        _stripe_price_id: str,
        user_id: UUID,
        _plan: Plan,
    ) -> str:
        return f"sub_fake_{user_id}"

    async def list_prices(self) -> list[dict]:
        return []

    async def verify_and_construct_event(
        self,
        _payload: bytes,
        _signature: str,
    ) -> dict:
        return {}
