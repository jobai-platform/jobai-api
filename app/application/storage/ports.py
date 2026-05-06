from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UploadedFile:
    key: str
    url: str
    size: int
    content_type: str


class StorageGateway(ABC):

    @abstractmethod
    async def upload(
        self,
        *,
        bucket: str,
        key: str,
        data: bytes,
        content_type: str,
    ) -> UploadedFile: ...

    @abstractmethod
    async def delete(self, *, bucket: str, key: str) -> None: ...
