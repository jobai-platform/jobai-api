from abc import ABC, abstractmethod


class TransactionManager(ABC):
    @abstractmethod
    async def commit(self) -> None:
        raise NotImplementedError
