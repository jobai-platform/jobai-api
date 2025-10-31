from select import select
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.interfaces.interface_AuthRepository import AuthRepositoryInterface
from app.models.usersModels import Users as UsersORM

class AuthRepository(AuthRepositoryInterface):
    """Repository for authentication-related operations."""

    async def get_user_with_password(self, session: AsyncSession, email: str) -> Optional[UsersORM]:
        """Retrieve a user by their email, including the hashed password."""
        result = await session.execute(
            select(UsersORM).where(UsersORM.email == email)
        )
        return result.scalars().one_or_none()
