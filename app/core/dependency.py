from typing import Annotated, Any, Generator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_async_session
from app.repository.usersRepository import UserRepository
from app.services.usersService import UserService


adb_dependency = Annotated[AsyncSession, Depends(get_async_session)]


def get_user_repository() -> UserRepository:
    """FastAPI dependency that provides a UserRepository instance."""
    return UserRepository()


def get_user_service(
    repo: UserRepository = Depends(get_user_repository),
) -> UserService:
    """FastAPI dependency that provides a UserService instance."""
    return UserService(repo)
