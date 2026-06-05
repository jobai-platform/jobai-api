from datetime import UTC, datetime, timedelta

import pytest

from app.domain.users.password_reset_token import PasswordResetToken


def test_generate_returns_a_non_empty_token() -> None:
    token = PasswordResetToken.generate(now=datetime(2026, 6, 5, 10, 0, tzinfo=UTC))

    assert token.value
    assert str(token) == token.value


def test_password_reset_token_expires_after_strict_thirty_minute_ttl() -> None:
    created_at = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    token = PasswordResetToken(value="reset-token", created_at=created_at)

    assert token.expires_at == created_at + timedelta(minutes=30)
    assert token.is_expired(now=created_at + timedelta(minutes=30)) is True


def test_password_reset_token_is_expired_at_t_plus_31_minutes() -> None:
    created_at = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    token = PasswordResetToken(value="reset-token", created_at=created_at)

    assert token.is_expired(now=created_at + timedelta(minutes=31)) is True


def test_password_reset_token_is_not_expired_before_ttl() -> None:
    created_at = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    token = PasswordResetToken(value="reset-token", created_at=created_at)

    assert token.is_expired(now=created_at + timedelta(minutes=29, seconds=59)) is False


def test_consume_marks_password_reset_token_as_consumed() -> None:
    token = PasswordResetToken(value="reset-token", created_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC))

    token.consume(now=datetime(2026, 6, 5, 10, 5, tzinfo=UTC))

    assert token.is_consumed is True

    assert token.consumed_at == datetime(2026, 6, 5, 10, 5, tzinfo=UTC)


def test_consume_raises_value_error_when_token_is_used_twice() -> None:
    token = PasswordResetToken(value="reset-token", created_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC))
    token.consume(now=datetime(2026, 6, 5, 10, 5, tzinfo=UTC))

    with pytest.raises(ValueError, match="Password reset token has already been consumed"):
        token.consume(now=datetime(2026, 6, 5, 10, 6, tzinfo=UTC))


def test_consume_raises_value_error_when_token_is_expired() -> None:
    created_at = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    token = PasswordResetToken(value="reset-token", created_at=created_at)

    with pytest.raises(ValueError, match="Password reset token has expired"):
        token.consume(now=created_at + timedelta(minutes=31))


def test_password_reset_token_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="Password reset token cannot be empty"):
        PasswordResetToken(value="", created_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC))


def test_password_reset_token_rejects_naive_created_at() -> None:
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        PasswordResetToken(value="reset-token", created_at=datetime(2026, 6, 5, 10, 0))
