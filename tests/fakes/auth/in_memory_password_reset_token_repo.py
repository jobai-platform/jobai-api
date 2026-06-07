from datetime import datetime
from uuid import UUID

from app.application.auth.ports import PasswordResetTokenRecord, PasswordResetTokenRepository


class InMemoryPasswordResetTokenRepository(PasswordResetTokenRepository):
    def __init__(self) -> None:
        self._records: dict[str, PasswordResetTokenRecord] = {}
        self.allow_consume = True

    async def save(
        self,
        *,
        candidate_id: UUID,
        token_hash: str,
        created_at: datetime,
    ) -> None:
        self._records[token_hash] = PasswordResetTokenRecord(
            candidate_id=candidate_id,
            token_hash=token_hash,
            created_at=created_at,
        )

    async def find_by_token_hash(self, token_hash: str) -> PasswordResetTokenRecord | None:
        return self._records.get(token_hash)

    async def consume_if_available(self, token_hash: str, *, consumed_at: datetime) -> bool:
        record = self._records.get(token_hash)
        if record is None or record.consumed_at is not None or not self.allow_consume:
            return False
        self._records[token_hash] = PasswordResetTokenRecord(
            candidate_id=record.candidate_id,
            token_hash=record.token_hash,
            created_at=record.created_at,
            consumed_at=consumed_at,
        )
        return True
