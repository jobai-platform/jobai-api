from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.persistence.models.refresh_token import RefreshTokenModel


class SQLAlchemyRefreshTokenRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def is_revoked(self, jti: str) -> bool:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.jti == jti)
        )
        token = result.scalars().one_or_none()
        if token is None:
            return True
        return token.revoked_at is not None or token.expires_at <= datetime.now(UTC)

    async def revoke(self, jti: str) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.jti == jti)
            .where(RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.commit()

    async def persist(self, *, jti: str, user_id: UUID, expires_at: datetime) -> None:
        self._session.add(
            RefreshTokenModel(
                jti=jti,
                user_id=user_id,
                expires_at=expires_at,
            )
        )
        await self._session.commit()
