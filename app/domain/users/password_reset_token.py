from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
import secrets

PASSWORD_RESET_TOKEN_TTL = timedelta(minutes=30)


@dataclass(slots=True)
class PasswordResetToken:
    value: str
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    consumed_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.value.strip():
            raise ValueError("Password reset token cannot be empty")
        _ensure_timezone_aware(self.created_at, field_name="created_at")
        if self.consumed_at is not None:
            _ensure_timezone_aware(self.consumed_at, field_name="consumed_at")

    @classmethod
    def generate(cls, *, now: datetime | None = None) -> "PasswordResetToken":
        return cls(value=secrets.token_urlsafe(32), created_at=now or datetime.now(UTC))

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

    def consume(self, *, now: datetime | None = None) -> None:
        if self.is_consumed:
            raise ValueError("Password reset token has already been consumed")

        consumed_at = now or datetime.now(UTC)
        _ensure_timezone_aware(consumed_at, field_name="now")
        if self.is_expired(now=consumed_at):
            raise ValueError("Password reset token has expired")

        self.consumed_at = consumed_at

    def __str__(self) -> str:
        return self.value


def _ensure_timezone_aware(value: datetime, *, field_name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{field_name} must be timezone-aware")
