from app.domain.ai_analysis.services.model_router import ModelRouter


class GenerateEmbeddingsUseCase:
    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    async def execute(self, text: str) -> list[float]:
        if not text or not text.strip():
            raise ValueError("Text cannot be empty")
        port = self._router.get_embedding_port()
        return await port.generate_embedding(text)


class GenerateLLMCompletionUseCase:
    def __init__(self, router: ModelRouter) -> None:
        self._router = router

    async def execute(self, prompt: str, **kwargs: object) -> str:
        port = self._router.get_llm_port()
        return await port.complete(prompt, **kwargs)
