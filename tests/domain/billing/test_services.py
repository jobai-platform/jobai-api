from app.domain.billing.services import map_stripe_subscription_status
from app.domain.billing.enums import SubscriptionStatus


def test_map_stripe_subscription_status():
    assert map_stripe_subscription_status("active") == SubscriptionStatus.ACTIVE
    assert map_stripe_subscription_status("trialing") == SubscriptionStatus.ACTIVE
    assert map_stripe_subscription_status("past_due") == SubscriptionStatus.PAST_DUE
    assert map_stripe_subscription_status("canceled") == SubscriptionStatus.CANCELED
    assert map_stripe_subscription_status("unknown_status") == SubscriptionStatus.PENDING

