from abc import abstractmethod
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from .crud_interfaces import CRUDInterface
from ..models.usersModels import Users as UsersORM
from ..schemas.UserSchemas import UserRead, UserCreate, UserUpdate


class UserRepositoryInterface(
    CRUDInterface[UsersORM, UserRead, UserCreate, UserUpdate]
):
    """Interface for user repository operations."""

    @abstractmethod
    async def get_by_email(self, session: AsyncSession, email: str) -> Optional[UserRead]: ...
