"""
Tests TDD pour JWTTokenServiceAdapter.validate_refresh_token
Bounded Context : users-auth
Layer : infrastructure
"""
from datetime import UTC, datetime, timedelta

import pytest

from app.domain.common.exceptions import UnauthorizedError
from app.infrastructure.security.jwt_service import JWTSettings, JWTService, JWTTokenServiceAdapter


@pytest.fixture
def adapter() -> JWTTokenServiceAdapter:
    settings = JWTSettings(
        secret="test-secret-key",
        algorithm="HS256",
        access_token_expire_minutes=60,
        refresh_token_expire_days=7,
    )
    return JWTTokenServiceAdapter(service=JWTService(cfg=settings))


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
