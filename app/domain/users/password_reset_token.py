from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets

PASSWORD_RESET_TOKEN_TTL = timedelta(minutes=30)


@dataclass(slots=True)
class PasswordResetToken:
    value: str
    signature: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    consumed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Password reset token cannot be empty")
        if not self.signature.strip():
            raise ValueError("Password reset token signature cannot be empty")
        _ensure_timezone_aware(self.created_at, field_name="created_at")
        if self.consumed_at is not None:
            _ensure_timezone_aware(self.consumed_at, field_name="consumed_at")

    @classmethod
    def generate(cls, *, signing_key: str, now: datetime | None = None) -> "PasswordResetToken":
        _ensure_signing_key(signing_key)
        created_at = now or datetime.now(UTC)
        _ensure_timezone_aware(created_at, field_name="now")
        value = secrets.token_urlsafe(32)
        return cls(
            value=value,
            signature=_sign(value=value, created_at=created_at, signing_key=signing_key),
            created_at=created_at,
        )

    @property
    def signed_value(self) -> str:
        return f"{self.value}.{self.signature}"

    @property
    def expires_at(self) -> datetime:
        return self.created_at + PASSWORD_RESET_TOKEN_TTL

    @property
    def is_consumed(self) -> bool:
        return self.consumed_at is not None

    def is_expired(self, *, now: datetime | None = None) -> bool:
        checked_at = now or datetime.now(UTC)
        _ensure_timezone_aware(checked_at, field_name="now")
        return checked_at >= self.expires_at

    def has_valid_signature(self, *, signing_key: str) -> bool:
        _ensure_signing_key(signing_key)
        expected_signature = _sign(
            value=self.value,
            created_at=self.created_at,
            signing_key=signing_key,
        )
        return hmac.compare_digest(self.signature, expected_signature)

    def consume(self, *, signing_key: str, now: datetime | None = None) -> None:
        if self.is_consumed:
            raise ValueError("Password reset token has already been consumed")
        if not self.has_valid_signature(signing_key=signing_key):
            raise ValueError("Password reset token signature is invalid")

        consumed_at = now or datetime.now(UTC)
        _ensure_timezone_aware(consumed_at, field_name="now")
        if self.is_expired(now=consumed_at):
            raise ValueError("Password reset token has expired")

        self.consumed_at = consumed_at

    def __str__(self) -> str:
        return self.signed_value


def _sign(*, value: str, created_at: datetime, signing_key: str) -> str:
    payload = f"{value}\0{created_at.isoformat()}".encode()
    return hmac.new(signing_key.encode(), payload, hashlib.sha256).hexdigest()


def _ensure_signing_key(signing_key: str) -> None:
    if not signing_key.strip():
        raise ValueError("Password reset token signing key cannot be empty")


def _ensure_timezone_aware(value: datetime, *, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
