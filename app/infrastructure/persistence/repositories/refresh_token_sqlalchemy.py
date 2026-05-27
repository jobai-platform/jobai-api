from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.auth.ports import RefreshTokenRepository
from app.domain.users.refresh_token import RefreshToken
from app.infrastructure.persistence.models.refresh_token import RefreshTokenModel


class SQLAlchemyRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save(self, token: RefreshToken) -> None:
        self._session.add(
            RefreshTokenModel(
                jti=token.token_hash,  # jti column still required (NOT NULL) — use hash as fallback
                token_hash=token.token_hash,
                user_id=token.user_id,
                expires_at=token.expires_at,
                revoked_at=token.revoked_at,
            )
        )
        await self._session.commit()

    async def find_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        result = await self._session.execute(
            select(RefreshTokenModel).where(RefreshTokenModel.token_hash == token_hash)
        )
        model = result.scalars().one_or_none()
        return _to_domain(model) if model is not None else None

    async def revoke(self, token_hash: str) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.token_hash == token_hash)
            .where(RefreshTokenModel.revoked_at.is_(None))
            .values(revoked_at=datetime.now(UTC))
        )
        await self._session.commit()


def _to_domain(model: RefreshTokenModel) -> RefreshToken:
    return RefreshToken(
        id=model.id,
        token_hash=model.token_hash,
        user_id=model.user_id,
        expires_at=model.expires_at,
        revoked_at=model.revoked_at,
    )
