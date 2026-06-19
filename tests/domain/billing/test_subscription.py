from datetime import UTC, datetime
from uuid import uuid4

import pytest

from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus


def test_new_user_gets_freemium_plan():
    user_id = uuid4()
    billing_price_id = uuid4()

    subscription = Subscription.create_freemium(
        user_id=user_id,
        stripe_customer_id="cus_free",
        stripe_subscription_id="sub_free",
        billing_price_id=billing_price_id,
    )

    assert subscription.user_id == user_id
    assert subscription.plan == Plan.FREEMIUM
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.stripe_customer_id == "cus_free"
    assert subscription.stripe_subscription_id == "sub_free"
    assert subscription.billing_price_id == billing_price_id
    assert subscription.current_period_start is None
    assert subscription.current_period_end is None
    assert subscription.cancel_at_period_end is None
    assert subscription.canceled_at is None
    assert subscription.amount is None
    assert subscription.currency is None


def test_subscription_can_store_stripe_period_and_financial_fields():
    user_id = uuid4()
    current_period_start = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    current_period_end = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    canceled_at = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)

    subscription = Subscription(
        user_id=user_id,
        plan=Plan.PRO,
        status=SubscriptionStatus.ACTIVE,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=True,
        canceled_at=canceled_at,
        amount=2900,
        currency="eur",
    )

    assert subscription.user_id == user_id
    assert subscription.plan == Plan.PRO
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.current_period_start == current_period_start
    assert subscription.current_period_end == current_period_end
    assert subscription.cancel_at_period_end is True
    assert subscription.canceled_at == canceled_at
    assert subscription.amount == 2900
    assert subscription.currency == "eur"


def test_assign_paid_plan_and_update_status():
    user_id = uuid4()
    billing_price_id = uuid4()

    sub = Subscription.create_freemium(user_id=user_id)

    sub.assign_paid_plan(
        plan=Plan.PRO,
        stripe_customer_id="cus_1",
        stripe_subscription_id="sub_1",
        billing_price_id=billing_price_id,
        status=SubscriptionStatus.PENDING,
    )

    assert sub.plan == Plan.PRO
    assert sub.status == SubscriptionStatus.PENDING
    assert sub.stripe_customer_id == "cus_1"
    assert sub.stripe_subscription_id == "sub_1"
    assert sub.billing_price_id == billing_price_id

    sub.update_status(SubscriptionStatus.ACTIVE)

    assert sub.status == SubscriptionStatus.ACTIVE


def test_cannot_assign_freemium_as_paid_plan():
    sub = Subscription.create_freemium(user_id=uuid4())

    with pytest.raises(ValueError):
        sub.assign_paid_plan(
            plan=Plan.FREEMIUM,
            stripe_customer_id="cus_1",
            stripe_subscription_id="sub_1",
            billing_price_id=1.0,
        )
