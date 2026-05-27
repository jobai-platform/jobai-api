"""
Tests TDD pour JWTTokenServiceAdapter.validate_refresh_token
Bounded Context : users-auth
Layer : infrastructure
"""
from datetime import UTC, datetime, timedelta

import pytest
from jose import jwt as jose_jwt

from app.domain.common.exceptions import UnauthorizedError
from app.infrastructure.security.jwt_service import JWTSettings, JWTService, JWTTokenServiceAdapter

_TEST_SETTINGS = JWTSettings(
    secret="test-secret-key",
    algorithm="HS256",
    access_token_expire_minutes=60,
    refresh_token_expire_days=7,
)


@pytest.fixture
def adapter() -> JWTTokenServiceAdapter:
    return JWTTokenServiceAdapter(service=JWTService(cfg=_TEST_SETTINGS))


class TestValidateRefreshToken:

    def test_returns_sub_for_valid_refresh_token(self, adapter: JWTTokenServiceAdapter) -> None:
        """Returns the subject (user_id) when given a valid refresh token."""
        token = adapter.create_refresh_token(subject="user-123")

        sub = adapter.validate_refresh_token(token)

        assert sub == "user-123"

    def test_raises_unauthorized_for_access_token(self, adapter: JWTTokenServiceAdapter) -> None:
        """Raises UnauthorizedError when token type is 'access', not 'refresh'."""
        access_token = adapter.create_access_token(subject="user-123")

        with pytest.raises(UnauthorizedError):
            adapter.validate_refresh_token(access_token)

    def test_raises_unauthorized_for_malformed_token(self, adapter: JWTTokenServiceAdapter) -> None:
        """Raises UnauthorizedError when token is not a valid JWT."""
        with pytest.raises(UnauthorizedError):
            adapter.validate_refresh_token("not.a.valid.jwt")

    def test_raises_unauthorized_for_empty_string(self, adapter: JWTTokenServiceAdapter) -> None:
        """Raises UnauthorizedError for an empty string."""
        with pytest.raises(UnauthorizedError):
            adapter.validate_refresh_token("")


class TestRefreshTokenTTL:

    def test_refresh_token_expires_in_days_not_minutes(self) -> None:
        """Refresh token TTL doit être en jours (7 jours) — régression JOB-86."""
        service = JWTService(cfg=_TEST_SETTINGS)
        before = datetime.now(UTC)

        token = service.create_refresh_token(subject="user-123")

        claims = jose_jwt.decode(
            token,
            _TEST_SETTINGS.secret,
            algorithms=[_TEST_SETTINGS.algorithm],
            options={"verify_aud": False},
        )
        exp = datetime.fromtimestamp(claims["exp"], tz=UTC)
        ttl = exp - before

        assert ttl >= timedelta(days=6), f"TTL trop court : {ttl} (attendu ≥ 6 jours)"
        assert ttl <= timedelta(days=8), f"TTL trop long : {ttl} (attendu ≤ 8 jours)"

    def test_access_token_expires_in_minutes_not_days(self) -> None:
        """Access token TTL doit rester en minutes (60 min) — vérification de non-régression."""
        service = JWTService(cfg=_TEST_SETTINGS)
        before = datetime.now(UTC)

        token = service.create_access_token(subject="user-123")

        claims = jose_jwt.decode(
            token,
            _TEST_SETTINGS.secret,
            algorithms=[_TEST_SETTINGS.algorithm],
            options={"verify_aud": False},
        )
        exp = datetime.fromtimestamp(claims["exp"], tz=UTC)
        ttl = exp - before

        assert ttl >= timedelta(minutes=59), f"Access TTL trop court : {ttl}"
        assert ttl <= timedelta(minutes=61), f"Access TTL trop long : {ttl}"
