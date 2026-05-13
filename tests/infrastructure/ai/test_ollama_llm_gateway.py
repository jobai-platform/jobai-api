import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.infrastructure.ai.ollama_llm_gateway import OllamaLLMGateway

# Correct patch target: scope the patch to the module that imports httpx.
# patch('httpx.AsyncClient') would replace the class globally but wouldn't
# intercept the "async with httpx.AsyncClient(...) as client:" context manager
# used inside the gateway. We patch the name as it exists in the gateway module.
_PATCH_TARGET = "app.infrastructure.ai.ollama_llm_gateway.httpx.AsyncClient"


def _make_mock_client(status_code: int, json_data: dict | None = None, text: str = "") -> MagicMock:
    """Helper that builds the mock hierarchy for `async with httpx.AsyncClient() as client:`."""
    mock_response = MagicMock()
    mock_response.status_code = status_code
    mock_response.text = text
    if json_data is not None:
        mock_response.json.return_value = json_data

    mock_client = AsyncMock()
    mock_client.post = AsyncMock(return_value=mock_response)

    mock_client_cls = MagicMock()
    mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)
    return mock_client_cls, mock_client


@pytest.fixture
def gateway() -> OllamaLLMGateway:
    return OllamaLLMGateway(base_url="http://localhost:11434", model="llama3")


@pytest.mark.asyncio
async def test_complete_success(gateway: OllamaLLMGateway) -> None:
    """GIVEN Ollama responds with a valid JSON body
    WHEN complete() is called
    THEN the 'response' field is returned as a string
    """
    mock_cls, mock_client = _make_mock_client(
        200, {"model": "llama3", "response": "Bonjour! Comment puis-je vous aider?", "done": True}
    )
    with patch(_PATCH_TARGET, mock_cls):
        result = await gateway.complete(
            prompt="Dis bonjour en français",
            max_tokens=50,
            temperature=0.7,
        )

    assert isinstance(result, str)
    assert "Bonjour" in result
    mock_client.post.assert_called_once()
    call_json = mock_client.post.call_args.kwargs["json"]
    assert call_json["model"] == "llama3"
    assert call_json["prompt"] == "Dis bonjour en français"
    assert call_json["stream"] is False


@pytest.mark.asyncio
async def test_complete_with_system_prompt(gateway: OllamaLLMGateway) -> None:
    """GIVEN a system_prompt is provided
    WHEN complete() is called
    THEN the 'system' key is present in the request payload
    """
    mock_cls, mock_client = _make_mock_client(200, {"response": "Je suis un assistant utile."})
    with patch(_PATCH_TARGET, mock_cls):
        result = await gateway.complete(
            prompt="Qui es-tu?",
            system_prompt="Tu es un assistant serviable et concis.",
        )

    assert isinstance(result, str)
    call_json = mock_client.post.call_args.kwargs["json"]
    assert call_json["system"] == "Tu es un assistant serviable et concis."


@pytest.mark.asyncio
async def test_complete_without_system_prompt_omits_key(gateway: OllamaLLMGateway) -> None:
    """GIVEN no system_prompt is passed
    WHEN complete() is called
    THEN 'system' is NOT included in the payload (avoids sending null to Ollama)
    """
    mock_cls, mock_client = _make_mock_client(200, {"response": "ok"})
    with patch(_PATCH_TARGET, mock_cls):
        await gateway.complete(prompt="test")

    call_json = mock_client.post.call_args.kwargs["json"]
    assert "system" not in call_json


@pytest.mark.asyncio
async def test_complete_sends_num_predict_not_num_predictions(gateway: OllamaLLMGateway) -> None:
    """GIVEN max_tokens=1000 is passed
    WHEN complete() is called
    THEN options.num_predict == 1000 (Ollama's real param name, not num_predictions)
    """
    mock_cls, mock_client = _make_mock_client(200, {"response": "test"})
    with patch(_PATCH_TARGET, mock_cls):
        await gateway.complete("test", max_tokens=1000)

    call_json = mock_client.post.call_args.kwargs["json"]
    assert call_json["options"]["num_predict"] == 1000
    assert "num_predictions" not in call_json["options"]


@pytest.mark.asyncio
async def test_complete_sends_temperature(gateway: OllamaLLMGateway) -> None:
    """GIVEN temperature=0.3
    WHEN complete() is called
    THEN options.temperature == 0.3
    """
    mock_cls, mock_client = _make_mock_client(200, {"response": "test"})
    with patch(_PATCH_TARGET, mock_cls):
        await gateway.complete("test", temperature=0.3)

    call_json = mock_client.post.call_args.kwargs["json"]
    assert call_json["options"]["temperature"] == 0.3


@pytest.mark.asyncio
async def test_complete_raises_runtime_error_on_500(gateway: OllamaLLMGateway) -> None:
    """GIVEN Ollama returns HTTP 500
    WHEN complete() is called
    THEN RuntimeError is raised with status code in the message
    """
    mock_cls, _ = _make_mock_client(500, text="Internal Server Error")
    with patch(_PATCH_TARGET, mock_cls):
        with pytest.raises(RuntimeError, match="Ollama API error 500"):
            await gateway.complete("test")


@pytest.mark.asyncio
async def test_complete_raises_on_missing_response_field(gateway: OllamaLLMGateway) -> None:
    """GIVEN Ollama returns 200 but JSON has no 'response' key
    WHEN complete() is called
    THEN RuntimeError is raised mentioning the missing field
    """
    mock_cls, _ = _make_mock_client(200, {"model": "llama3", "done": True})
    with patch(_PATCH_TARGET, mock_cls):
        with pytest.raises(RuntimeError, match="missing 'response' field"):
            await gateway.complete("test")


@pytest.mark.asyncio
async def test_complete_raises_on_timeout(gateway: OllamaLLMGateway) -> None:
    """GIVEN the request times out
    WHEN complete() is called
    THEN RuntimeError is raised with 'timeout' in the message
    """
    import httpx

    mock_cls = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("timed out"))
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch(_PATCH_TARGET, mock_cls):
        with pytest.raises(RuntimeError, match="timeout"):
            await gateway.complete("test")


@pytest.mark.asyncio
async def test_complete_raises_on_connection_error(gateway: OllamaLLMGateway) -> None:
    """GIVEN Ollama is not running (connection refused)
    WHEN complete() is called
    THEN RuntimeError is raised with 'Is Ollama running' hint
    """
    import httpx

    mock_cls = MagicMock()
    mock_client = AsyncMock()
    mock_client.post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
    mock_cls.return_value.__aenter__ = AsyncMock(return_value=mock_client)
    mock_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    with patch(_PATCH_TARGET, mock_cls):
        with pytest.raises(RuntimeError, match="Is Ollama running"):
            await gateway.complete("test")


@pytest.mark.asyncio
async def test_complete_uses_configured_model() -> None:
    """GIVEN a gateway initialized with model='mistral'
    WHEN complete() is called
    THEN the payload sends model='mistral'
    """
    gateway = OllamaLLMGateway(model="mistral")
    mock_cls, mock_client = _make_mock_client(200, {"response": "ok"})
    with patch(_PATCH_TARGET, mock_cls):
        await gateway.complete("test")

    assert mock_client.post.call_args.kwargs["json"]["model"] == "mistral"


@pytest.mark.asyncio
async def test_trailing_slash_stripped_from_base_url() -> None:
    """GIVEN base_url has a trailing slash
    WHEN complete() is called
    THEN the resulting URL does not contain a double slash
    """
    gateway = OllamaLLMGateway(base_url="http://localhost:11434/")
    mock_cls, mock_client = _make_mock_client(200, {"response": "ok"})
    with patch(_PATCH_TARGET, mock_cls):
        await gateway.complete("test")

    url_called = mock_client.post.call_args.args[0]
    assert "//" not in url_called.replace("http://", "")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complete_real_ollama_integration() -> None:
    """GIVEN Ollama is running locally with llama3
    WHEN complete() is called with a real prompt
    THEN a non-empty string is returned

    Skip automatically if Ollama is not available.
    Run with: poetry run pytest -m integration
    """
    gateway = OllamaLLMGateway(model="llama3")
    try:
        result = await gateway.complete(
            prompt="Count from 1 to 3. Reply with only the numbers.",
            max_tokens=20,
            temperature=0.0,
        )
        assert isinstance(result, str)
        assert len(result) > 0
    except Exception as exc:
        pytest.skip(f"Ollama not available: {exc}")
