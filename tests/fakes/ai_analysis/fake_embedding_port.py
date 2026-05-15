from app.domain.ai_analysis.ports import EmbeddingPort


class FakeEmbeddingPort(EmbeddingPort):

    async def generate_embedding(self, text: str) -> list[float]:
        return [0.1] * 768
