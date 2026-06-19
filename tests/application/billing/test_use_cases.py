from datetime import UTC, datetime
from types import SimpleNamespace
import uuid
from uuid import UUID

import pytest

from app.application.billing.dto import CheckoutSessionResult
from app.application.billing.use_cases import (
    AssignFreemiumOnSignupUseCase,
    CreateCheckoutSessionUseCase,
    HandleStripeWebhookUseCase,
)
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
        self.updated_stripe_customer_id = None
        self.updated_user_id = None

    async def get_by_id(self, user_id):
        return self._user

    async def update_stripe_customer_id(
        self, user_id: UUID, stripe_customer_id: str | None
    ) -> None:
        self.updated_user_id = user_id
        self.updated_stripe_customer_id = stripe_customer_id


class FakeBillingPriceRepo:
    def __init__(self, price=None):
        self._price = price

    async def get_active_by_plan(self, plan):
        return self._price


class FakeBillingGateway:
    def __init__(self, checkout_url="https://checkout.test", events=None):
        self.checkout_url = checkout_url
        self.created_sessions = []
        self.created_customer_id = "cus_fake"
        self.created_subscription_id = "sub_fake"
        self.events = events if events is not None else []
        self.create_customer_calls = 0

    async def create_checkout_session(self, *, email, user_id, plan, success_url, cancel_url):
        self.created_sessions.append(
            {
                "email": email,
                "user_id": user_id,
                "plan": plan,
                "success_url": success_url,
                "cancel_url": cancel_url,
            }
        )
        return self.checkout_url

    async def create_customer(self, *, email, user_id):
        self.create_customer_calls += 1
        self.events.append("create_customer")
        return self.created_customer_id

    async def create_subscription(self, *, customer_id, stripe_price_id, user_id, plan):
        return self.created_subscription_id


class FakeTransactionManager:
    def __init__(self, events=None, commit_error=None):
        self.events = events if events is not None else []
        self.commit_error = commit_error

    async def commit(self):
        self.events.append("commit")
        if self.commit_error is not None:
            raise self.commit_error


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
    user_repo = FakeUserRepo(user=fake_user)
    transaction_manager = FakeTransactionManager()
    uc = AssignFreemiumOnSignupUseCase(
        subscription_repository=repo,
        user_repository=user_repo,
        billing_price_repository=FakeBillingPriceRepo(price=_make_freemium_price()),
        billing_gateway=FakeBillingGateway(),
        transaction_manager=transaction_manager,
    )

    sub = await uc.execute(user_id)

    assert repo.get_by_user_id_calls == [user_id]
    assert repo.created is not None
    assert sub.plan == Plan.FREEMIUM
    assert sub.status == SubscriptionStatus.ACTIVE
    # Verify that the user's stripe_customer_id was updated
    assert user_repo.updated_user_id == user_id
    assert user_repo.updated_stripe_customer_id == "cus_fake"


@pytest.mark.asyncio
async def test_assign_freemium_commits_user_before_creating_stripe_customer():
    user_id = uuid.uuid4()
    events = []
    gateway = FakeBillingGateway(events=events)
    uc = AssignFreemiumOnSignupUseCase(
        subscription_repository=FakeSubscriptionRepo(),
        user_repository=FakeUserRepo(user=SimpleNamespace(id=user_id, email="test@example.com")),
        billing_price_repository=FakeBillingPriceRepo(price=_make_freemium_price()),
        billing_gateway=gateway,
        transaction_manager=FakeTransactionManager(events=events),
    )

    await uc.execute(user_id)

    assert events[:2] == ["commit", "create_customer"]


@pytest.mark.asyncio
async def test_assign_freemium_does_not_create_stripe_customer_when_user_commit_fails():
    user_id = uuid.uuid4()
    gateway = FakeBillingGateway()
    uc = AssignFreemiumOnSignupUseCase(
        subscription_repository=FakeSubscriptionRepo(),
        user_repository=FakeUserRepo(user=SimpleNamespace(id=user_id, email="test@example.com")),
        billing_price_repository=FakeBillingPriceRepo(price=_make_freemium_price()),
        billing_gateway=gateway,
        transaction_manager=FakeTransactionManager(
            commit_error=RuntimeError("database unavailable")
        ),
    )

    with pytest.raises(RuntimeError, match="database unavailable"):
        await uc.execute(user_id)

    assert gateway.create_customer_calls == 0


@pytest.mark.asyncio
async def test_assign_freemium_on_signup_returns_existing():
    existing = Subscription.create_freemium(user_id=uuid.uuid4())
    repo = FakeSubscriptionRepo(existing=existing)
    uc = AssignFreemiumOnSignupUseCase(
        subscription_repository=repo,
        user_repository=FakeUserRepo(),
        billing_price_repository=FakeBillingPriceRepo(),
        billing_gateway=FakeBillingGateway(),
        transaction_manager=FakeTransactionManager(),
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
        await uc.execute(
            user_id=fake_user.id, target_plan=Plan.FREEMIUM.value, success_url="a", cancel_url="b"
        )

    # invalid plan
    with pytest.raises(ValueError):
        await uc.execute(
            user_id=fake_user.id, target_plan="unknown", success_url="a", cancel_url="b"
        )

    # user not found
    uc_no_user = CreateCheckoutSessionUseCase(
        user_repository=FakeUserRepo(user=None), billing_gateway=fake_gateway
    )
    with pytest.raises(ValueError):
        await uc_no_user.execute(
            user_id=uuid.uuid4(), target_plan=Plan.PRO.value, success_url="a", cancel_url="b"
        )

    # success
    result = await uc.execute(
        user_id=fake_user.id, target_plan=Plan.PRO.value, success_url="ok", cancel_url="nok"
    )
    assert isinstance(result, CheckoutSessionResult)
    assert result.checkout_url == fake_gateway.checkout_url
    assert (
        fake_gateway.created_sessions
        and fake_gateway.created_sessions[0]["email"] == fake_user.email
    )


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
                "current_period_start": int(datetime(2026, 6, 1, 12, 0, tzinfo=UTC).timestamp()),
                "current_period_end": int(datetime(2026, 7, 1, 12, 0, tzinfo=UTC).timestamp()),
                "cancel_at_period_end": False,
                "amount": 2900,
                "currency": "eur",
            }
        },
    }

    await uc.execute(event)
    assert repo.created is not None
    assert repo.created.plan == Plan.PRO
    assert repo.created.status == SubscriptionStatus.PENDING
    assert repo.created.stripe_customer_id == "cus_123"
    assert repo.created.stripe_subscription_id == "sub_123"
    assert repo.created.current_period_start == datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    assert repo.created.current_period_end == datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    assert repo.created.cancel_at_period_end is False
    assert repo.created.amount == 2900
    assert repo.created.currency == "eur"

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
                "amount": 5900,
                "currency": "chf",
            }
        },
    }

    await uc2.execute(event2)
    assert repo2.updated is not None
    assert repo2.updated.plan == Plan.ENTERPRISE
    assert repo2.updated.status == SubscriptionStatus.PENDING
    assert repo2.updated.stripe_customer_id == "cus_999"
    assert repo2.updated.stripe_subscription_id == "sub_999"
    assert repo2.updated.amount == 5900
    assert repo2.updated.currency == "chf"


@pytest.mark.asyncio
async def test_handle_subscription_deleted_marks_canceled():
    user_id = uuid.uuid4()
    sub = Subscription.create_freemium(user_id=user_id)
    sub.assign_paid_plan(
        plan=Plan.PRO,
        stripe_customer_id="c",
        stripe_subscription_id="sub_del",
        status=SubscriptionStatus.ACTIVE,
    )

    repo = FakeSubscriptionRepo(existing=sub)
    uc = HandleStripeWebhookUseCase(subscription_repository=repo)

    event = {"type": "customer.subscription.deleted", "data": {"object": {"id": "sub_del"}}}

    await uc.execute(event)
    assert repo.updated is not None
    assert repo.updated.status == SubscriptionStatus.CANCELED


@pytest.mark.asyncio
async def test_handle_subscription_update_persists_stripe_summary_fields():
    user_id = uuid.uuid4()
    existing = Subscription.create_freemium(user_id=user_id)
    existing.assign_paid_plan(
        plan=Plan.PRO,
        stripe_customer_id="cus_321",
        stripe_subscription_id="sub_321",
        status=SubscriptionStatus.PENDING,
    )
    repo = FakeSubscriptionRepo(existing=existing)
    uc = HandleStripeWebhookUseCase(subscription_repository=repo)

    event = {
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_321",
                "status": "past_due",
                "current_period_start": int(datetime(2026, 6, 1, 12, 0, tzinfo=UTC).timestamp()),
                "current_period_end": int(datetime(2026, 7, 1, 12, 0, tzinfo=UTC).timestamp()),
                "cancel_at_period_end": True,
                "canceled_at": int(datetime(2026, 6, 15, 12, 0, tzinfo=UTC).timestamp()),
                "items": {
                    "data": [
                        {
                            "price": {
                                "unit_amount": 4900,
                                "currency": "chf",
                            }
                        }
                    ]
                },
            }
        },
    }

    await uc.execute(event)

    assert repo.updated is not None
    assert repo.updated.status == SubscriptionStatus.PAST_DUE
    assert repo.updated.current_period_start == datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    assert repo.updated.current_period_end == datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    assert repo.updated.cancel_at_period_end is True
    assert repo.updated.canceled_at == datetime(2026, 6, 15, 12, 0, tzinfo=UTC)
    assert repo.updated.amount == 4900
    assert repo.updated.currency == "chf"


@pytest.mark.asyncio
async def test_handle_checkout_session_completed_keeps_optional_fields_when_missing():
    user_id = uuid.uuid4()
    repo = FakeSubscriptionRepo(existing=None)
    uc = HandleStripeWebhookUseCase(subscription_repository=repo)

    event = {
        "type": "checkout.session.completed",
        "data": {
            "object": {
                "metadata": {"user_id": str(user_id), "plan": Plan.PRO.value},
                "customer": "cus_missing",
                "subscription": "sub_missing",
            }
        },
    }

    await uc.execute(event)

    assert repo.created is not None
    assert repo.created.current_period_start is None
    assert repo.created.current_period_end is None
    assert repo.created.cancel_at_period_end is None
    assert repo.created.canceled_at is None
    assert repo.created.amount is None
    assert repo.created.currency is None
