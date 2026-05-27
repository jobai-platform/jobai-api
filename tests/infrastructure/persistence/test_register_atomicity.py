"""
Tests d'intégration — atomicité RegisterUseCase (user + subscription)
Bounded Context : users-auth + billing
Layer : infrastructure

Vérifie que la création d'un Candidate et de sa Subscription Freemium
partagent la même session : flush sans commit, rollback = tout ou rien.
"""
from uuid import uuid4

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus
from app.domain.users.entities import Candidate, CandidateRole
from app.domain.users.value_objects import Email, HashedPassword
from app.infrastructure.persistence.repositories.subscription_sqlalchemy import SubscriptionSQLAlchemyRepository
from app.infrastructure.persistence.repositories.user_sqlalchemy import SqlAlchemyUserRepository


def _candidate() -> Candidate:
    uid = uuid4()
    return Candidate(
        id=uid,
        email=Email.from_raw(f"atomic-{uid.hex[:8]}@example.com"),
        hashed_password=HashedPassword("hashed"),
        first_name="Test",
        last_name="User",
        role=CandidateRole.USER,
    )


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_and_subscription_both_visible_in_same_session(db_session: AsyncSession) -> None:
    """Happy path : user et subscription sont visibles dans la même session après flush."""
    user_repo = SqlAlchemyUserRepository(db_session)
    sub_repo = SubscriptionSQLAlchemyRepository(db_session)

    candidate = _candidate()
    saved = await user_repo.create(candidate)
    await sub_repo.create(Subscription.create_freemium(user_id=saved.id))

    fetched_user = await user_repo.get_by_id(saved.id)
    fetched_sub = await sub_repo.get_by_user_id(saved.id)

    assert fetched_user is not None
    assert fetched_sub is not None
    assert fetched_sub.plan == Plan.FREEMIUM
    assert fetched_sub.status == SubscriptionStatus.ACTIVE
    assert fetched_sub.user_id == saved.id


@pytest.mark.asyncio
@pytest.mark.integration
async def test_user_not_visible_after_rollback_on_subscription_failure(db_session: AsyncSession) -> None:
    """Atomicité : si la subscription échoue (doublon user_id unique), le rollback efface le user."""
    user_repo = SqlAlchemyUserRepository(db_session)
    sub_repo = SubscriptionSQLAlchemyRepository(db_session)

    # Créer un premier user avec sa subscription (flushed, pas committed)
    first = _candidate()
    saved_first = await user_repo.create(first)
    await sub_repo.create(Subscription.create_freemium(user_id=saved_first.id))

    # Créer un deuxième user, puis tenter une subscription avec le même user_id (doublon → IntegrityError)
    second = _candidate()
    saved_second = await user_repo.create(second)
    second_id = saved_second.id

    try:
        duplicate_sub = Subscription(
            user_id=saved_first.id,   # user_id déjà utilisé → unique constraint violation
            plan=Plan.FREEMIUM,
            status=SubscriptionStatus.ACTIVE,
        )
        await sub_repo.create(duplicate_sub)
    except IntegrityError:
        await db_session.rollback()

    # Après rollback, le second user ne doit pas être persisté
    after_rollback = await user_repo.get_by_id(second_id)
    assert after_rollback is None, (
        "Le Candidate ne doit pas être persisté si la Subscription échoue dans la même transaction"
    )
