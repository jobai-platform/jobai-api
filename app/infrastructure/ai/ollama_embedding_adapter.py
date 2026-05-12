import httpx

from app.domain.ai_analysis.ports import EmbeddingPort


class OllamaEmbeddingAdapter:
    """Implements EmbeddingPort against the Ollama local inference API."""

    def __init__(self, base_url: str, model: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model

    async def generate_embedding(self, text: str) -> list[float]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self._base_url}/api/embeddings",
                json={"model": self._model, "prompt": text},
            )

        if response.status_code != 200:
            raise RuntimeError(
                f"Ollama API error {response.status_code}: {response.text}"
            )

        data: dict = response.json()
        return data["embedding"]


