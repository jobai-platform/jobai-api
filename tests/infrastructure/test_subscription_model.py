from app.infrastructure.persistence.models.subscription import SubscriptionModel
from app.domain.billing.enums import SubscriptionPlan, SubscriptionStatus


import pytest


@pytest.mark.asyncio
async def test_subscription_model_crud(db_session, create_user_in_db):
    # create a user
    user = await create_user_in_db(email="tester@example.com", password=None)

    sub = SubscriptionModel(
        user_id=user.id,
        stripe_customer_id="cus_test",
        stripe_subscription_id="sub_test",
        plan=SubscriptionPlan.PRO.value,
        status=SubscriptionStatus.ACTIVE.value,
    )

    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)

    # Query back
    fetched = await db_session.get(SubscriptionModel, sub.id)
    assert fetched is not None
    assert fetched.user_id == user.id
    assert fetched.plan == SubscriptionPlan.PRO.value
    assert fetched.status == SubscriptionStatus.ACTIVE.value

