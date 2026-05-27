from datetime import UTC, datetime

from app.application.auth.ports import RefreshTokenRepository
from app.domain.users.refresh_token import RefreshToken


class InMemoryRefreshTokenRepository(RefreshTokenRepository):
    def __init__(self) -> None:
        self._store: dict[str, RefreshToken] = {}

    async def save(self, token: RefreshToken) -> None:
        self._store[token.token_hash] = token

    async def find_by_token_hash(self, token_hash: str) -> RefreshToken | None:
        return self._store.get(token_hash)

    async def revoke(self, token_hash: str) -> None:
        token = self._store.get(token_hash)
        if token is not None and token.revoked_at is None:
            token.revoked_at = datetime.now(UTC)
