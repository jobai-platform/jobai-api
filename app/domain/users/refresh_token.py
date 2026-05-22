from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.domain.common.exceptions import ConflictError


@dataclass(slots=True)
class RefreshToken:
    """
    Domain entity representing a persisted refresh token.
    Keyed by token_hash (SHA-256 of the raw JWT string).
    """
    id: UUID
    token_hash: str
    user_id: UUID
    expires_at: datetime
    revoked_at: datetime | None = None

    @property
    def is_revoked(self) -> bool:
        return self.revoked_at is not None

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= datetime.now(UTC)

    @property
    def is_valid(self) -> bool:
        return not self.is_revoked and not self.is_expired

    def revoke(self) -> None:
        if self.is_revoked:
            raise ConflictError(
                code="token_already_revoked",
                details="Token already revoked",
            )
        self.revoked_at = datetime.now(UTC)
