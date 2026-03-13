import pytest
from app.domain.billing.enums import SubscriptionPlan, SubscriptionStatus


def test_new_user_gets_freemium_plan():
    subscription = Subscription.create_freemium(user_id=123)

    assert subscription.user_id == 123
    assert subscription.plan == SubscriptionPlan.FREEMIUM
    assert subscription.status == SubscriptionStatus.ACTIVE


def test_can_activate_paid_plan():
    subscription = Subscription.create_pedding_upgrade(user_id=123, plan=SubscriptionPlan.PRO)

    subscription.activate(stripe_subscription_id="sub_123", stripe_customer_id="cus_123")

    assert subscription.plan == SubscriptionPlan.PRO
    assert subscription.status == SubscriptionStatus.ACTIVE
