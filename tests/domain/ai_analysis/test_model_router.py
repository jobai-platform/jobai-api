import pytest
from app.domain.ai_analysis.services.model_router import ModelRouter
from app.domain.ai_analysis.value_objects import ProviderConfig
from tests.fakes.ai_analysis.fake_embedding_port import FakeEmbeddingPort
from tests.fakes.ai_analysis.fake_llm_gateway_port import FakeLLMGatewayPort


@pytest.fixture
def router() -> ModelRouter:
    config = ProviderConfig(
        embedding_provider="fake",
        llm_provider="fake",
    )
    providers = {
        "embedding_fake": FakeEmbeddingPort(),
        "llm_fake": FakeLLMGatewayPort(),
    }
    return ModelRouter(config, providers)


def test_router_returns_embedding_port(router: ModelRouter) -> None:
    """GIVEN a configured router
    WHEN requesting the embedding port
    THEN a port with generate_embedding is returned
    """
    port = router.get_embedding_port()
    assert port is not None
    assert hasattr(port, "generate_embedding")


@pytest.mark.asyncio
async def test_router_can_generate_embedding(router: ModelRouter) -> None:
    """GIVEN a router with a fake embedding provider
    WHEN generating an embedding
    THEN a valid 768-dimensional float vector is returned
    """
    port = router.get_embedding_port()
    embedding = await port.generate_embedding("test text")
    assert isinstance(embedding, list)
    assert len(embedding) == 768
    assert all(isinstance(x, float) for x in embedding)


def test_router_raises_when_embedding_provider_missing() -> None:
    """GIVEN a router with no providers registered
    WHEN requesting the embedding port
    THEN ValueError is raised
    """
    config = ProviderConfig(embedding_provider="missing", llm_provider="fake")
    router = ModelRouter(config, providers={})
    with pytest.raises(ValueError, match="Embedding provider 'missing' not configured"):
        router.get_embedding_port()


def test_router_raises_when_llm_provider_missing() -> None:
    """GIVEN a router with no providers registered
    WHEN requesting the LLM port
    THEN ValueError is raised
    """
    config = ProviderConfig(embedding_provider="fake", llm_provider="missing")
    router = ModelRouter(config, providers={})
    with pytest.raises(ValueError, match="LLM provider 'missing' not configured"):
        router.get_llm_port()
