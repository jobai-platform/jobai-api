from __future__ import annotations
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Any, Sequence

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.functions import func

TOrm = TypeVar("TOrm")
TRead = TypeVar("TRead")
TCreate = TypeVar("TCreate")
TUpdate = TypeVar("TUpdate")


class CRUDInterface(ABC, Generic[TOrm, TRead, TCreate, TUpdate]):
    """Generic CRUD interface."""

    @abstractmethod
    async def get(self, session: AsyncSession, id_: Any) -> TRead | None: ...


    @abstractmethod
    async def list(
        self,
        session: AsyncSession,
        skip: int = 0,
        limit: int = 50,
        srt_by: str | None = None,
        ascending: bool = True,
    ) -> Sequence[TRead]: ...


    @abstractmethod
    async def count(self, session: AsyncSession) -> int: ...


    @abstractmethod
    async def create(self, session: AsyncSession, data: TCreate) -> TRead: ...


    @abstractmethod
    async def update(self, session: AsyncSession, id_: Any, data: TUpdate) -> TRead | None: ...


    @abstractmethod
    async def delete(self, session: AsyncSession, id_: Any) -> None: ...
