from datetime import UTC, datetime, timedelta

import pytest

from app.domain.users.password_reset_token import PasswordResetToken

SIGNING_KEY = "test-password-reset-signing-key"


def test_generate_returns_a_non_empty_token() -> None:
    token = PasswordResetToken.generate(
        signing_key=SIGNING_KEY,
        now=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )

    assert token.value
    assert token.signature
    assert token.signed_value == f"{token.value}.{token.signature}"
    assert str(token) == token.signed_value


def test_generated_password_reset_token_has_a_valid_signature() -> None:
    token = PasswordResetToken.generate(
        signing_key=SIGNING_KEY,
        now=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )

    assert token.has_valid_signature(signing_key=SIGNING_KEY) is True


def test_password_reset_token_rejects_a_different_signing_key() -> None:
    token = PasswordResetToken.generate(
        signing_key=SIGNING_KEY,
        now=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )

    assert token.has_valid_signature(signing_key="different-signing-key") is False


def test_password_reset_token_rejects_a_tampered_value() -> None:
    token = PasswordResetToken.generate(
        signing_key=SIGNING_KEY,
        now=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )
    token.value = "tampered-token"

    assert token.has_valid_signature(signing_key=SIGNING_KEY) is False


def test_password_reset_token_rejects_a_tampered_creation_time() -> None:
    token = PasswordResetToken.generate(
        signing_key=SIGNING_KEY,
        now=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )
    token.created_at += timedelta(minutes=1)

    assert token.has_valid_signature(signing_key=SIGNING_KEY) is False


def test_password_reset_token_expires_after_strict_thirty_minute_ttl() -> None:
    created_at = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    token = PasswordResetToken.generate(signing_key=SIGNING_KEY, now=created_at)

    assert token.expires_at == created_at + timedelta(minutes=30)
    assert token.is_expired(now=created_at + timedelta(minutes=30)) is True


def test_password_reset_token_is_expired_at_t_plus_31_minutes() -> None:
    created_at = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    token = PasswordResetToken.generate(signing_key=SIGNING_KEY, now=created_at)

    assert token.is_expired(now=created_at + timedelta(minutes=31)) is True


def test_password_reset_token_is_not_expired_before_ttl() -> None:
    created_at = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    token = PasswordResetToken.generate(signing_key=SIGNING_KEY, now=created_at)

    assert token.is_expired(now=created_at + timedelta(minutes=29, seconds=59)) is False


def test_consume_marks_password_reset_token_as_consumed() -> None:
    token = PasswordResetToken.generate(
        signing_key=SIGNING_KEY,
        now=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )

    token.consume(signing_key=SIGNING_KEY, now=datetime(2026, 6, 5, 10, 5, tzinfo=UTC))

    assert token.is_consumed is True

    assert token.consumed_at == datetime(2026, 6, 5, 10, 5, tzinfo=UTC)


def test_consume_raises_value_error_when_token_is_used_twice() -> None:
    token = PasswordResetToken.generate(
        signing_key=SIGNING_KEY,
        now=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )
    token.consume(signing_key=SIGNING_KEY, now=datetime(2026, 6, 5, 10, 5, tzinfo=UTC))

    with pytest.raises(ValueError, match="Password reset token has already been consumed"):
        token.consume(signing_key=SIGNING_KEY, now=datetime(2026, 6, 5, 10, 6, tzinfo=UTC))


def test_consume_raises_value_error_when_token_is_expired() -> None:
    created_at = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    token = PasswordResetToken.generate(signing_key=SIGNING_KEY, now=created_at)

    with pytest.raises(ValueError, match="Password reset token has expired"):
        token.consume(signing_key=SIGNING_KEY, now=created_at + timedelta(minutes=31))


def test_consume_raises_value_error_when_signature_is_invalid() -> None:
    token = PasswordResetToken.generate(
        signing_key=SIGNING_KEY,
        now=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
    )

    with pytest.raises(ValueError, match="Password reset token signature is invalid"):
        token.consume(
            signing_key="different-signing-key",
            now=datetime(2026, 6, 5, 10, 5, tzinfo=UTC),
        )


def test_password_reset_token_rejects_empty_value() -> None:
    with pytest.raises(ValueError, match="Password reset token cannot be empty"):
        PasswordResetToken(
            value="",
            signature="signature",
            created_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
        )


def test_password_reset_token_rejects_empty_signature() -> None:
    with pytest.raises(ValueError, match="Password reset token signature cannot be empty"):
        PasswordResetToken(
            value="reset-token",
            signature="",
            created_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
        )


def test_generate_rejects_empty_signing_key() -> None:
    with pytest.raises(ValueError, match="Password reset token signing key cannot be empty"):
        PasswordResetToken.generate(signing_key="")


def test_password_reset_token_rejects_naive_created_at() -> None:
    with pytest.raises(ValueError, match="created_at must be timezone-aware"):
        PasswordResetToken(value="reset-token", signature="signature", created_at=datetime(2026, 6, 5, 10, 0))


def test_password_reset_token_reconstructs_from_signed_value() -> None:
    created_at = datetime(2026, 6, 5, 10, 0, tzinfo=UTC)
    generated = PasswordResetToken.generate(signing_key=SIGNING_KEY, now=created_at)

    reconstructed = PasswordResetToken.from_signed_value(
        generated.signed_value,
        created_at=created_at,
    )

    assert reconstructed == generated
    assert reconstructed.has_valid_signature(signing_key=SIGNING_KEY) is True


@pytest.mark.parametrize(
    "signed_value",
    [
        "",
        "missing-signature",
        ".signature",
        "value.",
        "value.signature.extra",
    ],
)
def test_password_reset_token_rejects_malformed_signed_value(signed_value: str) -> None:
    with pytest.raises(ValueError, match="Password reset token is malformed"):
        PasswordResetToken.from_signed_value(
            signed_value,
            created_at=datetime(2026, 6, 5, 10, 0, tzinfo=UTC),
        )
