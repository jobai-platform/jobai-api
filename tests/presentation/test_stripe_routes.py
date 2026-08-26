from datetime import UTC, datetime

import pytest

from app.application.billing.dto import CheckoutSessionResult
from app.domain.billing.enums import Plan, SubscriptionStatus
from app.infrastructure.persistence.models.billing_profile import BillingProfileModel
from app.infrastructure.persistence.models.subscription import SubscriptionModel


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
async def test_get_billing_profile_returns_snapshot(client, create_user_in_db, db_session):
    user = await create_user_in_db(email="billing-profile@test.com", password=None, stripe_customer_id="cus_bp")
    db_session.add(
        BillingProfileModel(
            user_id=user.id,
            stripe_customer_id="cus_bp",
            contact_first_name="Ada",
            contact_last_name="Lovelace",
            contact_email="ada@example.com",
            payment_method_id="pm_123",
            payment_method_brand="visa",
            payment_method_last4="4242",
            payment_method_exp_month=12,
            payment_method_exp_year=2027,
            payment_method_holder_name="Ada Lovelace",
            payment_method_country="GB",
            payment_method_funding="credit",
            payment_method_wallet="apple_pay",
        )
    )
    await db_session.commit()

    from app import main as app_module
    from app.presentation.security.deps import get_current_user_id

    app_module.app.dependency_overrides[get_current_user_id] = lambda: user.id

    response = await client.get("/api/v1/stripe/billing-profile")

    assert response.status_code == 200
    body = response.json()
    assert body["user_id"] == str(user.id)
    assert body["stripe_customer_id"] == "cus_bp"
    assert body["contact_full_name"] == "Ada Lovelace"
    assert body["payment_method_snapshot"]["brand"] == "visa"
    assert body["payment_method_snapshot"]["last4"] == "4242"
    assert body["payment_method_snapshot"]["masked_display"] == "visa •••• 4242"


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


@pytest.mark.asyncio
async def test_get_my_subscription_returns_full_summary(client, create_user_in_db, db_session):
    user = await create_user_in_db(email="summary@test.com")
    current_period_start = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    current_period_end = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    canceled_at = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)

    subscription = SubscriptionModel(
        user_id=user.id,
        stripe_customer_id="cus_summary",
        stripe_subscription_id="sub_summary",
        plan=Plan.PRO.value,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=False,
        canceled_at=canceled_at,
        amount=2900,
        currency="eur",
    )
    db_session.add(subscription)
    await db_session.commit()

    from app import main as app_module
    from app.presentation.security.deps import get_current_user_id

    app_module.app.dependency_overrides[get_current_user_id] = lambda: user.id

    resp = await client.get("/api/v1/stripe/subscriptions/me")

    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == str(user.id)
    assert body["plan"] == Plan.PRO.value
    assert body["status"] == SubscriptionStatus.ACTIVE.value
    assert body["stripe_customer_id"] == "cus_summary"
    assert body["stripe_subscription_id"] == "sub_summary"
    assert body["current_period_start"] in {"2026-06-01T12:00:00+00:00", "2026-06-01T12:00:00Z"}
    assert body["current_period_end"] in {"2026-07-01T12:00:00+00:00", "2026-07-01T12:00:00Z"}
    assert body["cancel_at_period_end"] is False
    assert body["canceled_at"] in {"2026-06-15T12:00:00+00:00", "2026-06-15T12:00:00Z"}
    assert body["amount"] == 2900
    assert body["currency"] == "eur"


@pytest.mark.asyncio
async def test_get_my_subscription_returns_404_when_missing(client, create_user_in_db):
    user = await create_user_in_db(email="missing@test.com")

    from app import main as app_module
    from app.presentation.security.deps import get_current_user_id

    app_module.app.dependency_overrides[get_current_user_id] = lambda: user.id

    resp = await client.get("/api/v1/stripe/subscriptions/me")

    assert resp.status_code == 404
    body = resp.json()
    assert body["code"] == "subscription_not_found"
