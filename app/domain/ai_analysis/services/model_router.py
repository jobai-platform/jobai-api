from app.domain.ai_analysis.ports import EmbeddingPort, LLMGatewayPort
from app.domain.ai_analysis.value_objects import ProviderConfig


class ModelRouter:
    def __init__(
        self,
        config: ProviderConfig,
        providers: dict[str, EmbeddingPort | LLMGatewayPort],
    ) -> None:
        self._config = config
        self._providers = providers

    def get_embedding_port(self) -> EmbeddingPort:
        provider_name = self._config.embedding_provider
        port = self._providers.get(f"embedding_{provider_name}")
        if port is None:
            raise ValueError(f"Embedding provider '{provider_name}' not configured")
        return port  # type: ignore[return-value]

    def get_llm_port(self) -> LLMGatewayPort:
        provider_name = self._config.llm_provider
        port = self._providers.get(f"llm_{provider_name}")
        if port is None:
            raise ValueError(f"LLM provider '{provider_name}' not configured")
        return port  # type: ignore[return-value]
