from datetime import datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.ports import PasswordResetTokenRecord, PasswordResetTokenRepository
from app.infrastructure.persistence.models.password_reset_token import PasswordResetTokenModel


class SQLAlchemyPasswordResetTokenRepository(PasswordResetTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(
        self,
        *,
        candidate_id: UUID,
        token_hash: str,
        created_at: datetime,
    ) -> None:
        self._session.add(
            PasswordResetTokenModel(
                candidate_id=candidate_id,
                token_hash=token_hash,
                created_at=created_at,
            )
        )
        await self._session.flush()

    async def find_by_token_hash(self, token_hash: str) -> PasswordResetTokenRecord | None:
        result = await self._session.execute(
            select(PasswordResetTokenModel).where(PasswordResetTokenModel.token_hash == token_hash)
        )
        model = result.scalars().one_or_none()
        return _to_record(model) if model is not None else None

    async def consume_if_available(self, token_hash: str, *, consumed_at: datetime) -> bool:
        result = await self._session.execute(
            update(PasswordResetTokenModel)
            .where(PasswordResetTokenModel.token_hash == token_hash)
            .where(PasswordResetTokenModel.consumed_at.is_(None))
            .values(consumed_at=consumed_at)
        )
        await self._session.flush()
        return result.rowcount == 1


def _to_record(model: PasswordResetTokenModel) -> PasswordResetTokenRecord:
    return PasswordResetTokenRecord(
        candidate_id=model.candidate_id,
        token_hash=model.token_hash,
        created_at=model.created_at,
        consumed_at=model.consumed_at,
    )
