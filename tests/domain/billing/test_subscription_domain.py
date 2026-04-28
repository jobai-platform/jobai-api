from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus


def test_new_user_gets_freemium_plan():
    subscription = Subscription.create_freemium(user_id=123)

    assert subscription.user_id == 123
    assert subscription.plan == Plan.FREEMIUM
    assert subscription.status == SubscriptionStatus.ACTIVE


def test_assign_paid_plan_and_update_status():
    sub = Subscription.create_freemium(user_id=1)
    sub.assign_paid_plan(
        plan=Plan.PRO,
        stripe_customer_id="cus_1",
        stripe_subscription_id="sub_1",
        status=SubscriptionStatus.PENDING,
    )

    assert sub.plan == Plan.PRO
    assert sub.status == SubscriptionStatus.PENDING
    assert sub.stripe_customer_id == "cus_1"
    assert sub.stripe_subscription_id == "sub_1"

    sub.update_status(SubscriptionStatus.ACTIVE)
    assert sub.status == SubscriptionStatus.ACTIVE

