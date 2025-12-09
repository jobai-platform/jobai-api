from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from old.app.core.database import get_async_session
from old.app.repository.usersRepository import UserRepository
from old.app.services.usersService import UserService


adb_dependency = Annotated[AsyncSession, Depends(get_async_session)]


def get_user_repository() -> UserRepository:
    """FastAPI dependency that provides a UserRepository instance."""
    return UserRepository()


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    """FastAPI dependency that provides a UserService instance."""
    return UserService(repo)
