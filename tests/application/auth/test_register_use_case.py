"""
Tests TDD pour RegisterUseCase
Bounded Context : users-auth
Layer : application
"""
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

import pytest

from app.application.auth.ports import RefreshTokenRepository, TokenService
from app.application.auth.use_cases import RegisterResult, RegisterUseCase, TokenPair
from app.application.billing.ports import SubscriptionRepository
from app.application.users.ports import PasswordHasher
from app.application.users.use_cases import UserService
from app.domain.billing.entities.subscription import Subscription
from app.domain.billing.enums import Plan, SubscriptionStatus
from app.domain.common.exceptions import BadRequestError, ConflictError, UnauthorizedError
from app.domain.users.refresh_token import RefreshToken
from tests.fakes.billing.in_memory_subscription_repo import InMemorySubscriptionRepository
from tests.fakes.users.in_memory_user_repo import InMemoryUserRepository

# ---------------------------------------------------------------------------
# Fakes locaux
# ---------------------------------------------------------------------------


class FakePasswordHasher(PasswordHasher):
    def hash_password(self, raw: str) -> str:
        return f"hashed:{raw}"

    def verify(self, raw: str, hashed: str) -> bool:
        return hashed == f"hashed:{raw}"


class FakeTokenService(TokenService):
    def __init__(self) -> None:
        self._counter = 0
        self._stored_claims: dict[str, dict] = {}

    def create_access_token(self, subject: str, extra: Mapping[str, object] | None = None) -> str:
        return f"access-{subject}"

    def create_refresh_token(self, subject: str, extra: Mapping[str, object] | None = None) -> str:
        self._counter += 1
        token = f"refresh-{self._counter}-{subject}"
        self._stored_claims[token] = {
            "sub": subject,
            "type": "refresh",
            "jti": f"jti-{self._counter}",
            "exp": datetime.now(UTC) + timedelta(days=7),
        }
        return token

    def decode_token(self, token: str) -> Mapping[str, object]:
        return self._stored_claims[token]

    def validate_refresh_token(self, token: str) -> str:
        claims = self._stored_claims.get(token)
        if not claims or claims.get("type") != "refresh":
            raise UnauthorizedError(code="invalid_token", details="Invalid refresh token")
        return str(claims["sub"])


class FakeRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self) -> None:
        self._store: dict[str, RefreshToken] = {}

    async def save(self, token: RefreshToken) -> None:
        self._store[token.token_hash] = token

    async def find_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return self._store.get(token_hash)

    async def revoke(self, token_hash: str) -> None:
        token = self._store.get(token_hash)
        if token is not None and token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)


class BrokenSubscriptionRepository(SubscriptionRepository):
    """Fake that always fails on create — used to test error propagation."""

    async def get_by_user_id(self, user_id) -> Optional[Subscription]:
        return None

    async def get_by_stripe_subscription_id(self, stripe_subscription_id: str) -> Optional[Subscription]:
        return None

    async def create(self, subscription: Subscription) -> Subscription:
        raise RuntimeError("Subscription storage unavailable")

    async def update(self, subscription: Subscription) -> Optional[Subscription]:
        return None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_use_case(
    user_repo: InMemoryUserRepository | None = None,
    token_service: FakeTokenService | None = None,
    refresh_repo: FakeRefreshTokenRepository | None = None,
    subscription_repo: InMemorySubscriptionRepository | None = None,
) -> tuple[RegisterUseCase, InMemoryUserRepository, FakeTokenService, FakeRefreshTokenRepository, InMemorySubscriptionRepository]:
    user_repo = user_repo or InMemoryUserRepository()
    token_service = token_service or FakeTokenService()
    refresh_repo = refresh_repo or FakeRefreshTokenRepository()
    subscription_repo = subscription_repo or InMemorySubscriptionRepository()
    user_service = UserService(user_repo=user_repo, pwd_hasher=FakePasswordHasher())
    use_case = RegisterUseCase(
        user_service=user_service,
        token_service=token_service,
        refresh_token_repo=refresh_repo,
        subscription_repo=subscription_repo,
    )
    return use_case, user_repo, token_service, refresh_repo, subscription_repo


_VALID_ARGS = {
    "email": "thomas@example.com",
    "password": "SecurePass1!",
    "first_name": "Thomas",
    "last_name": "Dupont",
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_register_returns_result_with_user_and_token_pair() -> None:
    """Le use case crée un Candidate et retourne RegisterResult(user, tokens)."""
    use_case, *_ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    assert isinstance(result, RegisterResult)
    assert isinstance(result.tokens, TokenPair)
    assert result.candidate is not None
    assert result.candidate.id is not None


@pytest.mark.asyncio
async def test_register_user_has_correct_identity_fields() -> None:
    """Le Candidate créé porte bien email, first_name et last_name."""
    use_case, *_ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    assert str(result.candidate.email) == "thomas@example.com"
    assert result.candidate.first_name == "Thomas"
    assert result.candidate.last_name == "Dupont"


@pytest.mark.asyncio
async def test_register_persists_optional_username() -> None:
    use_case, user_repo, *_ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS, username="john.doe")

    persisted = await user_repo.get_by_id(result.candidate.id)
    assert result.candidate.username == "john.doe"
    assert persisted is not None
    assert persisted.username == "john.doe"


@pytest.mark.asyncio
async def test_register_without_username_persists_none() -> None:
    use_case, user_repo, *_ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    persisted = await user_repo.get_by_id(result.candidate.id)
    assert result.candidate.username is None
    assert persisted is not None
    assert persisted.username is None


@pytest.mark.asyncio
async def test_register_raises_conflict_on_duplicate_username() -> None:
    use_case, *_ = _make_use_case()
    await use_case.execute(**_VALID_ARGS, username="john.doe")

    with pytest.raises(ConflictError) as exc_info:
        await use_case.execute(
            **(_VALID_ARGS | {"email": "other@example.com"}),
            username="john.doe",
        )

    assert exc_info.value.code == "username_already_exists"


@pytest.mark.asyncio
async def test_register_password_is_hashed_not_plain() -> None:
    """Le mot de passe est hashé — il n'est jamais stocké en clair."""
    use_case, user_repo, *_ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    persisted = await user_repo.get_by_id(result.candidate.id)
    assert persisted is not None
    assert str(persisted.hashed_password) != _VALID_ARGS["password"]
    assert str(persisted.hashed_password) == f"hashed:{_VALID_ARGS['password']}"


@pytest.mark.asyncio
async def test_register_issues_access_token_and_refresh_token() -> None:
    """Les tokens sont bien générés pour le Candidate nouvellement créé."""
    use_case, *_ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    user_id = str(result.candidate.id)
    assert result.tokens.access_token == f"access-{user_id}"
    assert "refresh" in result.tokens.refresh_token
    assert result.tokens.token_type == "Bearer"


@pytest.mark.asyncio
async def test_register_persists_refresh_token_in_repository() -> None:
    """Le refresh_token est persisté (par hash) pour permettre rotation et révocation."""
    use_case, _, token_service, refresh_repo, _ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    assert len(refresh_repo._store) == 1
    stored = next(iter(refresh_repo._store.values()))
    assert stored.user_id == result.candidate.id
    assert stored.expires_at > datetime.now(UTC)


@pytest.mark.asyncio
async def test_register_raises_conflict_on_duplicate_email() -> None:
    """ConflictError si le même email est déjà enregistré."""
    use_case, *_ = _make_use_case()
    await use_case.execute(**_VALID_ARGS)

    with pytest.raises(ConflictError):
        await use_case.execute(**_VALID_ARGS)


@pytest.mark.asyncio
async def test_register_raises_bad_request_on_short_password() -> None:
    """BadRequestError si le mot de passe fait moins de 8 caractères (validation application)."""
    use_case, *_ = _make_use_case()

    with pytest.raises(BadRequestError):
        await use_case.execute(
            email="thomas@example.com",
            password="tiny",
            first_name="Thomas",
            last_name="Dupont",
        )


@pytest.mark.asyncio
async def test_register_does_not_persist_refresh_token_on_conflict() -> None:
    """Aucun refresh_token n'est persisté si la création du Candidate échoue."""
    use_case, _, _, refresh_repo, _ = _make_use_case()
    await use_case.execute(**_VALID_ARGS)
    initial_count = len(refresh_repo._store)

    with pytest.raises(ConflictError):
        await use_case.execute(**_VALID_ARGS)

    assert len(refresh_repo._store) == initial_count


@pytest.mark.asyncio
async def test_register_assigns_freemium_subscription() -> None:
    """Subscription plan=FREEMIUM active est créée pour le Candidate — vérifiée via FakeRepository."""
    use_case, _, _, _, subscription_repo = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    subscription = await subscription_repo.get_by_user_id(result.candidate.id)
    assert subscription is not None
    assert subscription.plan == Plan.FREEMIUM
    assert subscription.status == SubscriptionStatus.ACTIVE
    assert subscription.user_id == result.candidate.id


@pytest.mark.asyncio
async def test_register_does_not_return_result_if_freemium_assignment_fails() -> None:
    """Si l'assignation Freemium échoue, le use case propage l'erreur — pas de RegisterResult retourné."""
    use_case, *_ = _make_use_case(subscription_repo=BrokenSubscriptionRepository())

    with pytest.raises(RuntimeError, match="Subscription storage unavailable"):
        await use_case.execute(**_VALID_ARGS)
