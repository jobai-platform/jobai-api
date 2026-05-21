"""
Tests TDD pour RegisterUseCase
Bounded Context : users-auth
Layer : application
"""
from collections.abc import Mapping
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest

from app.application.auth.ports import RefreshTokenRepository, TokenService
from app.application.auth.use_cases import RegisterResult, RegisterUseCase, TokenPair
from app.application.users.ports import PasswordHasher
from app.application.users.use_cases import UserService
from app.domain.common.exceptions import BadRequestError, ConflictError
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


class FakeRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self) -> None:
        self.persisted: dict[str, tuple[UUID, datetime]] = {}
        self.revoked: set[str] = set()

    async def is_revoked(self, jti: str) -> bool:
        return jti in self.revoked

    async def revoke(self, jti: str) -> None:
        self.revoked.add(jti)

    async def persist(self, *, jti: str, user_id: UUID, expires_at: datetime) -> None:
        self.persisted[jti] = (user_id, expires_at)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_use_case(
    user_repo: InMemoryUserRepository | None = None,
    token_service: FakeTokenService | None = None,
    refresh_repo: FakeRefreshTokenRepository | None = None,
) -> tuple[RegisterUseCase, InMemoryUserRepository, FakeTokenService, FakeRefreshTokenRepository]:
    user_repo = user_repo or InMemoryUserRepository()
    token_service = token_service or FakeTokenService()
    refresh_repo = refresh_repo or FakeRefreshTokenRepository()
    user_service = UserService(user_repo=user_repo, pwd_hasher=FakePasswordHasher())
    use_case = RegisterUseCase(
        user_service=user_service,
        token_service=token_service,
        refresh_token_repo=refresh_repo,
    )
    return use_case, user_repo, token_service, refresh_repo


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
    use_case, _, _, _ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    assert isinstance(result, RegisterResult)
    assert isinstance(result.tokens, TokenPair)
    assert result.user is not None
    assert result.user.id is not None


@pytest.mark.asyncio
async def test_register_user_has_correct_identity_fields() -> None:
    """Le Candidate créé porte bien email, first_name et last_name."""
    use_case, _, _, _ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    assert str(result.user.email) == "thomas@example.com"
    assert result.user.first_name == "Thomas"
    assert result.user.last_name == "Dupont"


@pytest.mark.asyncio
async def test_register_password_is_hashed_not_plain() -> None:
    """Le mot de passe est hashé — il n'est jamais stocké en clair."""
    use_case, user_repo, _, _ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    persisted = await user_repo.get_by_id(result.user.id)
    assert persisted is not None
    assert persisted.hashed_password != _VALID_ARGS["password"]
    assert persisted.hashed_password == f"hashed:{_VALID_ARGS['password']}"


@pytest.mark.asyncio
async def test_register_issues_access_token_and_refresh_token() -> None:
    """Les tokens sont bien générés pour le Candidate nouvellement créé."""
    use_case, _, _, _ = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    user_id = str(result.user.id)
    assert result.tokens.access_token == f"access-{user_id}"
    assert "refresh" in result.tokens.refresh_token
    assert result.tokens.token_type == "Bearer"


@pytest.mark.asyncio
async def test_register_persists_refresh_token_jti_in_repository() -> None:
    """Le jti du refresh_token est persisté pour permettre rotation et révocation."""
    use_case, _, token_service, refresh_repo = _make_use_case()

    result = await use_case.execute(**_VALID_ARGS)

    assert len(refresh_repo.persisted) == 1
    jti, (persisted_user_id, expires_at) = next(iter(refresh_repo.persisted.items()))
    assert persisted_user_id == result.user.id
    assert expires_at > datetime.now(UTC)


@pytest.mark.asyncio
async def test_register_raises_conflict_on_duplicate_email() -> None:
    """ConflictError si le même email est déjà enregistré."""
    use_case, _, _, _ = _make_use_case()
    await use_case.execute(**_VALID_ARGS)

    with pytest.raises(ConflictError):
        await use_case.execute(**_VALID_ARGS)


@pytest.mark.asyncio
async def test_register_raises_bad_request_on_short_password() -> None:
    """BadRequestError si le mot de passe fait moins de 8 caractères (validation application)."""
    use_case, _, _, _ = _make_use_case()

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
    use_case, _, _, refresh_repo = _make_use_case()
    await use_case.execute(**_VALID_ARGS)
    initial_count = len(refresh_repo.persisted)

    with pytest.raises(ConflictError):
        await use_case.execute(**_VALID_ARGS)

    assert len(refresh_repo.persisted) == initial_count
