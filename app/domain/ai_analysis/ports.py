from typing import Protocol


class EmbeddingPort(Protocol):

    async def generate_embedding(self, text: str) -> list[float]: ...


class LLMGatewayPort(Protocol):

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> str: ...
