"""Input validation tests for AI analysis use cases.

Asserts that empty/whitespace input raises BadRequestError (not bare ValueError),
aligning the use cases with the hexagonal rule that application-layer code must
raise AppError subclasses — never primitive builtins.
"""
import pytest

from app.application.ai_analysis.use_cases import (
    AnalyzeJobDescriptionUseCase,
    GenerateEmbeddingsUseCase,
)
from app.domain.ai_analysis.services.model_router import ModelRouter
from app.domain.ai_analysis.value_objects import ProviderConfig
from app.domain.common.exceptions import BadRequestError
from tests.fakes.ai_analysis.fake_embedding_port import FakeEmbeddingPort
from tests.fakes.ai_analysis.fake_llm_gateway_port import FakeLLMGatewayPort


def _router() -> ModelRouter:
    return ModelRouter(
        config=ProviderConfig(embedding_provider="ollama", llm_provider="ollama"),
        providers={
            "embedding_ollama": FakeEmbeddingPort(),
            "llm_ollama": FakeLLMGatewayPort(),
        },
    )


@pytest.mark.asyncio
async def test_generate_embeddings_raises_on_empty_text():
    use_case = GenerateEmbeddingsUseCase(router=_router())

    with pytest.raises(BadRequestError, match="Text cannot be empty"):
        await use_case.execute("")


@pytest.mark.asyncio
async def test_generate_embeddings_raises_on_whitespace_text():
    use_case = GenerateEmbeddingsUseCase(router=_router())

    with pytest.raises(BadRequestError, match="Text cannot be empty"):
        await use_case.execute("   \n\t  ")


@pytest.mark.asyncio
async def test_analyze_job_description_raises_on_empty_input():
    use_case = AnalyzeJobDescriptionUseCase(router=_router())

    with pytest.raises(BadRequestError, match="job_description cannot be empty"):
        await use_case.execute("")
