import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.infrastructure.ai.ollama_embedding_adapter import OllamaEmbeddingAdapter


@pytest.fixture
def adapter() -> OllamaEmbeddingAdapter:
    return OllamaEmbeddingAdapter(
        base_url="http://localhost:11434",
        model="nomic-embed-text",
    )


@pytest.mark.asyncio
async def test_generate_embedding_success(adapter: OllamaEmbeddingAdapter) -> None:
    """GIVEN Ollama API responds successfully
    WHEN generating an embedding
    THEN a 768-dimensional float vector is returned
    """
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"embedding": [0.1] * 768}

    with patch("app.infrastructure.ai.ollama_embedding_adapter.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        result = await adapter.generate_embedding("hello world")

    assert len(result) == 768
    assert all(isinstance(x, float) for x in result)
    mock_client.post.assert_called_once()


@pytest.mark.asyncio
async def test_generate_embedding_handles_api_error(adapter: OllamaEmbeddingAdapter) -> None:
    """GIVEN Ollama API returns a 500 error
    WHEN generating an embedding
    THEN RuntimeError is raised with a clear message
    """
    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.text = "Internal Server Error"

    with patch("app.infrastructure.ai.ollama_embedding_adapter.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        with pytest.raises(RuntimeError, match="Ollama API error"):
            await adapter.generate_embedding("test")
