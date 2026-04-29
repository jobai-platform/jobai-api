import pytest
import uuid

from types import SimpleNamespace

from app.application.billing.use_cases import (
    AssignFreemiumOnSignupUseCase,
    CreateCheckoutSessionUseCase,
    HandleStripeWebhookUseCase,
)
from app.application.billing.dto import CheckoutSessionResult
from app.domain.billing.entities.billing_price import BillingPrice
from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus


class FakeSubscriptionRepo:
    def __init__(self, existing=None):
        self._existing = existing
        self.created = None
        self.updated = None
        self.get_by_user_id_calls = []
        self.get_by_stripe_subscription_id_calls = []

    async def get_by_user_id(self, user_id):
        self.get_by_user_id_calls.append(user_id)
        return self._existing

    async def get_by_stripe_subscription_id(self, stripe_subscription_id):
        self.get_by_stripe_subscription_id_calls.append(stripe_subscription_id)
        if self._existing and self._existing.stripe_subscription_id == stripe_subscription_id:
            return self._existing
        return None

    async def create(self, subscription: Subscription):
        self.created = subscription
        return subscription

    async def update(self, subscription: Subscription):
        self.updated = subscription
        return subscription


class FakeUserRepo:
    def __init__(self, user=None):
        self._user = user

    async def get_by_id(self, user_id):
        return self._user


class FakeBillingPriceRepo:
    def __init__(self, price=None):
        self._price = price

    async def get_active_by_plan(self, plan):
        return self._price


class FakeBillingGateway:
    def __init__(self, checkout_url="https://checkout.test"):
        self.checkout_url = checkout_url
        self.created_sessions = []
        self.created_customer_id = "cus_fake"
        self.created_subscription_id = "sub_fake"

    async def create_checkout_session(self, *, email, user_id, plan, success_url, cancel_url):
        self.created_sessions.append(dict(email=email, user_id=user_id, plan=plan, success_url=success_url, cancel_url=cancel_url))
        return self.checkout_url

    async def create_customer(self, *, email, user_id):
        return self.created_customer_id

    async def create_subscription(self, *, customer_id, stripe_price_id, user_id, plan):
        return self.created_subscription_id


def _make_freemium_price() -> BillingPrice:
    return BillingPrice.create(
        plan=Plan.FREEMIUM,
        stripe_price_id="price_free",
        stripe_product_id="prod_free",
        currency="chf",
        amount=0,
        interval="month",
        active=True,
    )


@pytest.mark.asyncio
async def test_assign_freemium_on_signup_creates_if_not_exists():
    user_id = uuid.uuid4()
    fake_user = SimpleNamespace(id=user_id, email="test@example.com")
    repo = FakeSubscriptionRepo(existing=None)
    uc = AssignFreemiumOnSignupUseCase(
        subscription_repository=repo,
        user_repository=FakeUserRepo(user=fake_user),
        billing_price_repository=FakeBillingPriceRepo(price=_make_freemium_price()),
        billing_gateway=FakeBillingGateway(),
    )

    sub = await uc.execute(user_id)

    assert repo.get_by_user_id_calls == [user_id]
    assert repo.created is not None
    assert sub.plan == Plan.FREEMIUM
    assert sub.status == SubscriptionStatus.ACTIVE


@pytest.mark.asyncio
async def test_assign_freemium_on_signup_returns_existing():
    existing = Subscription.create_freemium(user_id=uuid.uuid4())
    repo = FakeSubscriptionRepo(existing=existing)
    uc = AssignFreemiumOnSignupUseCase(
        subscription_repository=repo,
        user_repository=FakeUserRepo(),
        billing_price_repository=FakeBillingPriceRepo(),
        billing_gateway=FakeBillingGateway(),
    )

    out = await uc.execute(existing.user_id)
    assert out is existing
    assert repo.created is None


@pytest.mark.asyncio
async def test_create_checkout_session_errors_and_success():
    # errors: freemium
    fake_gateway = FakeBillingGateway()
    fake_user = SimpleNamespace(id=uuid.uuid4(), email="test@example.com")
    user_repo = FakeUserRepo(user=fake_user)
    uc = CreateCheckoutSessionUseCase(user_repository=user_repo, billing_gateway=fake_gateway)

    with pytest.raises(ValueError):
        await uc.execute(user_id=fake_user.id, target_plan=Plan.FREEMIUM.value, success_url="a", cancel_url="b")

    # invalid plan
    with pytest.raises(ValueError):
        await uc.execute(user_id=fake_user.id, target_plan="unknown", success_url="a", cancel_url="b")

    # user not found
    uc_no_user = CreateCheckoutSessionUseCase(user_repository=FakeUserRepo(user=None), billing_gateway=fake_gateway)
    with pytest.raises(ValueError):
        await uc_no_user.execute(user_id=uuid.uuid4(), target_plan=Plan.PRO.value, success_url="a", cancel_url="b")

    # success
    result = await uc.execute(user_id=fake_user.id, target_plan=Plan.PRO.value, success_url="ok", cancel_url="nok")
    assert isinstance(result, CheckoutSessionResult)
    assert result.checkout_url == fake_gateway.checkout_url
    assert fake_gateway.created_sessions and fake_gateway.created_sessions[0]["email"] == fake_user.email


@pytest.mark.asyncio
async def test_handle_stripe_webhook_checkout_session_completed_creates_and_updates():
    # case 1: no existing subscription -> create
    repo = FakeSubscriptionRepo(existing=None)
    uc = HandleStripeWebhookUseCase(subscription_repository=repo)

    user_id = uuid.uuid4()
    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": str(user_id), "plan": Plan.PRO.value},
                "customer": "cus_123",
                "subscription": "sub_123",
            }
        }
    }

    await uc.execute(event)
    assert repo.created is not None
    assert repo.created.plan == Plan.PRO
    assert repo.created.status == SubscriptionStatus.PENDING
    assert repo.created.stripe_customer_id == "cus_123"
    assert repo.created.stripe_subscription_id == "sub_123"

    # case 2: existing subscription -> update
    existing = Subscription.create_freemium(user_id=user_id)
    repo2 = FakeSubscriptionRepo(existing=existing)
    uc2 = HandleStripeWebhookUseCase(subscription_repository=repo2)

    event2 = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": str(user_id), "plan": Plan.ENTERPRISE.value},
                "customer": "cus_999",
                "subscription": "sub_999",
            }
        }
    }

    await uc2.execute(event2)
    assert repo2.updated is not None
    assert repo2.updated.plan == Plan.ENTERPRISE
    assert repo2.updated.status == SubscriptionStatus.PENDING
    assert repo2.updated.stripe_customer_id == "cus_999"
    assert repo2.updated.stripe_subscription_id == "sub_999"


@pytest.mark.asyncio
async def test_handle_subscription_deleted_marks_canceled():
    user_id = uuid.uuid4()
    sub = Subscription.create_freemium(user_id=user_id)
    sub.assign_paid_plan(plan=Plan.PRO, stripe_customer_id="c", stripe_subscription_id="sub_del", status=SubscriptionStatus.ACTIVE)

    repo = FakeSubscriptionRepo(existing=sub)
    uc = HandleStripeWebhookUseCase(subscription_repository=repo)

    event = {
        "type": "customer.subscription.deleted",
        "data": {"object": {"id": "sub_del"}}
    }

    await uc.execute(event)
    assert repo.updated is not None
    assert repo.updated.status == SubscriptionStatus.CANCELED
