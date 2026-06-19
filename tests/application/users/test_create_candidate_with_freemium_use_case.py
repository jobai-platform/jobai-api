from uuid import UUID

import pytest

from app.application.users.use_cases import CreateCandidateWithFreemiumUseCase, UserService
from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus
from tests.fakes.billing.in_memory_subscription_repo import InMemorySubscriptionRepository
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository


class DummyHashingService:
    @staticmethod
    def hash_password(raw_password: str) -> str:
        return f"hashed_{raw_password}"

    @staticmethod
    def verify_password(raw_password: str, hashed_password: str) -> bool:
        return hashed_password == f"hashed_{raw_password}"


class FakeFreemiumUseCase:
    def __init__(self, subscription_repo: InMemorySubscriptionRepository) -> None:
        self.subscription_repo = subscription_repo
        self.calls: list[str] = []

    async def execute(self, user_id: UUID) -> Subscription:
        self.calls.append(str(user_id))
        subscription = Subscription.create_freemium(user_id=user_id)
        await self.subscription_repo.create(subscription)
        return subscription


@pytest.mark.asyncio
async def test_create_candidate_with_freemium_creates_user_and_subscription() -> None:
    user_repo = InMemoryUserRepository()
    subscription_repo = InMemorySubscriptionRepository()
    freemium = FakeFreemiumUseCase(subscription_repo)
    service = UserService(user_repo=user_repo, pwd_hasher=DummyHashingService())
    use_case = CreateCandidateWithFreemiumUseCase(user_service=service, freemium_use_case=freemium)

    user = await use_case.execute(
        email="user@example.com",
        password="securepassword",
        username="testuser",
    )

    persisted = await user_repo.get_by_id(user.id)
    subscription = await subscription_repo.get_by_user_id(user.id)

    assert persisted is not None
    assert user.id is not None
    assert freemium.calls == [str(user.id)]
    assert subscription is not None
    assert subscription.plan == Plan.FREEMIUM
    assert subscription.status == SubscriptionStatus.ACTIVE
