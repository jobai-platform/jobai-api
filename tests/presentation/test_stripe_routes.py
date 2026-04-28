import pytest

from app.application.billing.dto import CheckoutSessionResult


class FakeCreateCheckoutUseCase:
    def __init__(self, url="https://checkout.test"):
        self.url = url

    async def execute(self, user_id, target_plan, success_url, cancel_url):
        return CheckoutSessionResult(checkout_url=self.url)


class FakeBillingGateway:
    def __init__(self, event=None):
        self.event = event

    async def verify_and_construct_event(self, payload: bytes, signature: str):
        return self.event or {}


class FakeHandleWebhookUseCase:
    def __init__(self):
        self.handled = []

    async def execute(self, event):
        self.handled.append(event)


@pytest.mark.asyncio
async def test_checkout_session_route(client, create_user_in_db):
    user = await create_user_in_db(email="route@test.com")

    fake_uc = FakeCreateCheckoutUseCase()

    from app import main as app_module
    from app.core.dependency import get_create_checkout_session_use_case
    from app.presentation.security.deps import get_current_user_id

    app_module.app.dependency_overrides[get_create_checkout_session_use_case] = lambda: fake_uc
    app_module.app.dependency_overrides[get_current_user_id] = lambda: user.id

    payload = {"plan": "pro", "success_url": "https://ok", "cancel_url": "https://nok"}

    resp = await client.post("/api/v1/stripe/checkout-session", json=payload)

    assert resp.status_code == 202
    body = resp.json()
    assert body["checkout_url"].rstrip("/") == fake_uc.url.rstrip("/")


@pytest.mark.asyncio
async def test_webhook_route(client):
    fake_gateway = FakeBillingGateway(event={"type": "test.event"})
    fake_uc = FakeHandleWebhookUseCase()

    from app import main as app_module
    from app.core.dependency import get_billing_gateway, get_handle_stripe_webhook_use_case

    app_module.app.dependency_overrides[get_billing_gateway] = lambda: fake_gateway
    app_module.app.dependency_overrides[get_handle_stripe_webhook_use_case] = lambda: fake_uc

    payload = b"{}"
    headers = {"Stripe-Signature": "sig"}

    resp = await client.post("/api/v1/stripe/webhook", content=payload, headers=headers)

    assert resp.status_code == 200
    assert fake_uc.handled and fake_uc.handled[0]["type"] == "test.event"

