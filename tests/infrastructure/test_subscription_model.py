from datetime import UTC, datetime

import pytest

from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus
from app.infrastructure.persistence.models.subscription import SubscriptionModel
from app.infrastructure.persistence.repositories.subscription_sqlalchemy import (
    SubscriptionSQLAlchemyRepository,
)


@pytest.mark.asyncio
async def test_subscription_model_crud(db_session, create_user_in_db):
    # create a user
    user = await create_user_in_db(email="tester@example.com", password=None)
    current_period_start = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    current_period_end = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    canceled_at = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)

    sub = SubscriptionModel(
        user_id=user.id,
        stripe_customer_id="cus_test",
        stripe_subscription_id="sub_test",
        plan=Plan.PRO.value,
        status=SubscriptionStatus.ACTIVE.value,
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=True,
        canceled_at=canceled_at,
        amount=2900,
        currency="eur",
    )

    db_session.add(sub)
    await db_session.commit()
    await db_session.refresh(sub)

    # Query back
    fetched = await db_session.get(SubscriptionModel, sub.id)
    assert fetched is not None
    assert fetched.user_id == user.id
    assert fetched.plan == Plan.PRO.value
    assert fetched.status == SubscriptionStatus.ACTIVE.value
    assert fetched.current_period_start == current_period_start
    assert fetched.current_period_end == current_period_end
    assert fetched.cancel_at_period_end is True
    assert fetched.canceled_at == canceled_at
    assert fetched.amount == 2900
    assert fetched.currency == "eur"


@pytest.mark.asyncio
async def test_subscription_repository_maps_stripe_summary_fields(db_session, create_user_in_db):
    user = await create_user_in_db(email="repo@test.com", password=None)
    repo = SubscriptionSQLAlchemyRepository(session=db_session)
    current_period_start = datetime(2026, 6, 1, 12, 0, tzinfo=UTC)
    current_period_end = datetime(2026, 7, 1, 12, 0, tzinfo=UTC)
    canceled_at = datetime(2026, 6, 15, 12, 0, tzinfo=UTC)

    subscription = Subscription(
        user_id=user.id,
        plan=Plan.PRO,
        status=SubscriptionStatus.PAST_DUE,
        stripe_customer_id="cus_repo",
        stripe_subscription_id="sub_repo",
        current_period_start=current_period_start,
        current_period_end=current_period_end,
        cancel_at_period_end=False,
        canceled_at=canceled_at,
        amount=4900,
        currency="chf",
    )

    created = await repo.create(subscription)

    assert created.current_period_start == current_period_start
    assert created.current_period_end == current_period_end
    assert created.cancel_at_period_end is False
    assert created.canceled_at == canceled_at
    assert created.amount == 4900
    assert created.currency == "chf"

    created.amount = 5900
    created.currency = "eur"
    updated = await repo.update(created)

    assert updated is not None
    assert updated.amount == 5900
    assert updated.currency == "eur"
