import pytest
from uuid import uuid4

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
