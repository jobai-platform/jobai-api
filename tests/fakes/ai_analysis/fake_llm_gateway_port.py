class FakeLLMGatewayPort:

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
    ) -> str:
        return "Fake completion"
