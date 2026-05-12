class FakeEmbeddingPort:

    async def generate_embedding(self, text: str) -> list[float]:
        return [0.1] * 768
