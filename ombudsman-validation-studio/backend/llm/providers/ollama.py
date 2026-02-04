"""Ollama LLM provider implementation."""

import httpx

from ..base import LLMConfig, LLMProvider, LLMResponse
from ..exceptions import (
    LLMConnectionError,
    LLMInvalidResponseError,
    LLMTimeoutError,
)


class OllamaProvider(LLMProvider):
    """LLM provider for Ollama (local models)."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "ollama"

    @property
    def model_name(self) -> str:
        return self.config.ollama_model

    @property
    def base_url(self) -> str:
        return self.config.ollama_base_url.rstrip("/")

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout)
            )
        return self._client

    async def generate(self, prompt: str) -> str:
        """Generate a response from Ollama."""
        response = await self.generate_with_metadata(prompt)
        return response.content

    async def generate_with_metadata(self, prompt: str) -> LLMResponse:
        """Generate a response with full metadata from Ollama."""
        client = await self._get_client()

        payload = {
            "model": self.config.ollama_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "num_predict": self.config.max_tokens,
            },
        }

        try:
            response = await client.post(
                f"{self.base_url}/api/generate",
                json=payload,
            )
            response.raise_for_status()
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"Request to Ollama timed out after {self.config.timeout}s",
                provider=self.provider_name,
            ) from e
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Failed to connect to Ollama at {self.base_url}. "
                "Is Ollama running?",
                provider=self.provider_name,
            ) from e
        except httpx.HTTPStatusError as e:
            raise LLMConnectionError(
                f"Ollama returned error: {e.response.status_code} - "
                f"{e.response.text}",
                provider=self.provider_name,
            ) from e

        try:
            data = response.json()
        except Exception as e:
            raise LLMInvalidResponseError(
                f"Failed to parse Ollama response: {e}",
                provider=self.provider_name,
            ) from e

        content = data.get("response", "")
        if not content:
            raise LLMInvalidResponseError(
                "Ollama returned empty response",
                provider=self.provider_name,
            )

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=self.config.ollama_model,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            total_tokens=(
                (data.get("prompt_eval_count") or 0) + (data.get("eval_count") or 0)
                if data.get("prompt_eval_count") or data.get("eval_count")
                else None
            ),
            finish_reason="stop" if data.get("done") else None,
            raw_response=data,
        )

    async def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            client = await self._get_client()
            response = await client.get(f"{self.base_url}/api/tags")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
