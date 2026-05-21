"""
Tests TDD pour RefreshToken entity
Bounded Context : users-auth
Layer : domain
"""
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest

from app.domain.users.entities import RefreshToken


class TestRefreshTokenIsValid:

    def test_is_valid_when_not_revoked_and_not_expired(self) -> None:
        """A token with future expiry and no revocation is valid."""
        token = RefreshToken(
            token_hash="abc123",
            user_id=uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        assert token.is_valid is True

    def test_is_not_valid_when_revoked(self) -> None:
        """A revoked token is invalid regardless of expiry."""
        token = RefreshToken(
            token_hash="abc123",
            user_id=uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            revoked_at=datetime.now(UTC),
        )
        assert token.is_valid is False

    def test_is_not_valid_when_expired(self) -> None:
        """An expired token is invalid even if not explicitly revoked."""
        token = RefreshToken(
            token_hash="abc123",
            user_id=uuid4(),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        assert token.is_valid is False

    def test_is_revoked_false_when_revoked_at_is_none(self) -> None:
        token = RefreshToken(
            token_hash="abc123",
            user_id=uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=7),
        )
        assert token.is_revoked is False

    def test_is_revoked_true_when_revoked_at_is_set(self) -> None:
        token = RefreshToken(
            token_hash="abc123",
            user_id=uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=7),
            revoked_at=datetime.now(UTC),
        )
        assert token.is_revoked is True

    def test_is_expired_false_for_future_expiry(self) -> None:
        token = RefreshToken(
            token_hash="abc123",
            user_id=uuid4(),
            expires_at=datetime.now(UTC) + timedelta(days=1),
        )
        assert token.is_expired is False

    def test_is_expired_true_for_past_expiry(self) -> None:
        token = RefreshToken(
            token_hash="abc123",
            user_id=uuid4(),
            expires_at=datetime.now(UTC) - timedelta(seconds=1),
        )
        assert token.is_expired is True
