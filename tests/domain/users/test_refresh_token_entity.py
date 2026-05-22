"""
Tests TDD pour RefreshToken entity
Bounded Context : users-auth
Layer : domain
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.common.exceptions import ConflictError
from app.domain.users.refresh_token import RefreshToken


def _make_token(
    *,
    expires_at: datetime | None = None,
    revoked_at: datetime | None = None,
) -> RefreshToken:
    return RefreshToken(
        id=uuid4(),
        token_hash="abc123",
        user_id=uuid4(),
        expires_at=expires_at or datetime.now(UTC) + timedelta(days=7),
        revoked_at=revoked_at,
    )


class TestRefreshTokenIsValid:

    def test_is_valid_when_not_revoked_and_not_expired(self) -> None:
        """A token with future expiry and no revocation is valid."""
        assert _make_token().is_valid is True

    def test_is_not_valid_when_revoked(self) -> None:
        """A revoked token is invalid regardless of expiry."""
        token = _make_token(revoked_at=datetime.now(UTC))
        assert token.is_valid is False

    def test_is_not_valid_when_expired(self) -> None:
        """An expired token is invalid even if not explicitly revoked."""
        token = _make_token(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        assert token.is_valid is False

    def test_is_revoked_false_when_revoked_at_is_none(self) -> None:
        assert _make_token().is_revoked is False

    def test_is_revoked_true_when_revoked_at_is_set(self) -> None:
        token = _make_token(revoked_at=datetime.now(UTC))
        assert token.is_revoked is True

    def test_is_expired_false_for_future_expiry(self) -> None:
        token = _make_token(expires_at=datetime.now(UTC) + timedelta(days=1))
        assert token.is_expired is False

    def test_is_expired_true_for_past_expiry(self) -> None:
        token = _make_token(expires_at=datetime.now(UTC) - timedelta(seconds=1))
        assert token.is_expired is True


class TestRefreshTokenRevoke:

    def test_revoke_sets_revoked_at(self) -> None:
        """Calling revoke() on a valid token sets revoked_at to a UTC datetime."""
        token = _make_token()
        before = datetime.now(UTC)
        token.revoke()
        assert token.revoked_at is not None
        assert token.revoked_at >= before

    def test_revoke_makes_token_invalid(self) -> None:
        """A revoked token is no longer valid even if not yet expired."""
        token = _make_token()
        token.revoke()
        assert token.is_valid is False

    def test_revoke_raises_if_already_revoked(self) -> None:
        """Calling revoke() twice signals a replay attack — domain invariant."""
        token = _make_token(revoked_at=datetime.now(UTC))
        with pytest.raises(ConflictError) as exc_info:
            token.revoke()
        assert exc_info.value.code == "token_already_revoked"
