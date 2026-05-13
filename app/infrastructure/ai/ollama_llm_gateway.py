import json
import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OllamaLLMGateway:
    """Implements LLMGatewayPort against the Ollama local inference API."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama3",
        timeout: float = 120.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout

    async def complete(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> str:
        url = f"{self._base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {
                # Ollama's actual param name is "num_predict", not "num_predictions"
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=payload)

                if response.status_code != 200:
                    logger.error("Ollama API error %s: %s", response.status_code, response.text)
                    raise RuntimeError(f"Ollama API error {response.status_code}: {response.text}")

                data: dict[str, Any] = response.json()
                if "response" not in data:
                    logger.error("Ollama API response missing 'response' field: %s", data)
                    raise RuntimeError(f"Ollama API response missing 'response' field: {data}")

                return data["response"]

        except RuntimeError:
            raise
        except httpx.TimeoutException as exc:
            logger.error("Ollama API timeout after %s seconds: %s", self._timeout, exc)
            raise RuntimeError(f"Ollama API timeout after {self._timeout} seconds") from exc
        except httpx.RequestError as exc:
            logger.error(
                "Ollama API request failed: %s. Is Ollama running at %s?", exc, self._base_url
            )
            raise RuntimeError(
                f"Ollama API request failed: {exc}. Is Ollama running at {self._base_url}?"
            ) from exc

    async def complete_stream(
        self,
        prompt: str,
        max_tokens: int = 500,
        temperature: float = 0.7,
        system_prompt: str | None = None,
    ) -> str:
        """Returns the full completion by accumulating streamed tokens.

        Ollama sends one JSON object per line: {"response": "token", "done": bool}.
        We parse each line and concatenate the "response" fields.
        """
        url = f"{self._base_url}/api/generate"
        payload: dict[str, Any] = {
            "model": self._model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }
        if system_prompt:
            payload["system"] = system_prompt

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                async with client.stream("POST", url, json=payload) as response:
                    if response.status_code != 200:
                        error_detail = await response.aread()
                        logger.error("Ollama stream error %s: %s", response.status_code, error_detail)
                        raise RuntimeError(f"Ollama API error {response.status_code}: {error_detail}")

                    result = ""
                    async for line in response.iter_lines():
                        if line:
                            # iter_lines() yields str — no .decode() needed
                            chunk: dict[str, Any] = json.loads(line)
                            result += chunk.get("response", "")

                    return result

        except RuntimeError:
            raise
        except httpx.TimeoutException as exc:
            logger.error("Ollama stream timeout after %s seconds: %s", self._timeout, exc)
            raise RuntimeError(f"Ollama API timeout after {self._timeout} seconds") from exc
        except httpx.RequestError as exc:
            logger.error(
                "Ollama stream request failed: %s. Is Ollama running at %s?", exc, self._base_url
            )
            raise RuntimeError(
                f"Ollama API request failed: {exc}. Is Ollama running at {self._base_url}?"
            ) from exc
