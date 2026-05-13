class FakeLLMGatewayPort:
    """Simple fake that records calls and returns a configurable response."""

    def __init__(self, default_response: str = "Fake LLM response") -> None:
        self._default_response = default_response
        self._call_history: list[dict] = []

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> str:
        self._call_history.append({
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "system_prompt": system_prompt,
        })
        return f"{self._default_response} [prompt: {prompt[:50]}...]"

    def get_last_call(self) -> dict | None:
        return self._call_history[-1] if self._call_history else None

    def get_call_count(self) -> int:
        return len(self._call_history)

    def reset(self) -> None:
        self._call_history.clear()


class ConfigurableFakeLLMGateway:
    """Fake that returns different responses based on prompt content."""

    def __init__(self) -> None:
        self._responses: dict[str, str] = {}
        self._default_response = "Default fake response"

    def configure_response(self, prompt_contains: str, response: str) -> None:
        self._responses[prompt_contains] = response

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> str:
        for key, response in self._responses.items():
            if key.lower() in prompt.lower():
                return response
        return self._default_response


class FailingFakeLLMGateway:
    """Fake that always raises — use to test error handling in use cases."""

    def __init__(self, error_message: str = "Fake LLM error") -> None:
        self._error_message = error_message

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> str:
        raise RuntimeError(self._error_message)
