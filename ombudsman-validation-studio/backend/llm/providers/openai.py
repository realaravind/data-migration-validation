"""OpenAI LLM provider implementation."""

import httpx

from ..base import LLMConfig, LLMProvider, LLMResponse
from ..exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
)


class OpenAIProvider(LLMProvider):
    """LLM provider for OpenAI API."""

    API_BASE_URL = "https://api.openai.com/v1"

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self.config.openai_model

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "Authorization": f"Bearer {self.config.openai_api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def generate(self, prompt: str) -> str:
        """Generate a response from OpenAI."""
        response = await self.generate_with_metadata(prompt)
        return response.content

    async def generate_with_metadata(self, prompt: str) -> LLMResponse:
        """Generate a response with full metadata from OpenAI."""
        client = await self._get_client()

        payload = {
            "model": self.config.openai_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        try:
            response = await client.post(
                f"{self.API_BASE_URL}/chat/completions",
                json=payload,
            )
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"Request to OpenAI timed out after {self.config.timeout}s",
                provider=self.provider_name,
            ) from e
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                "Failed to connect to OpenAI API",
                provider=self.provider_name,
            ) from e

        # Handle HTTP errors
        if response.status_code == 401:
            raise LLMAuthenticationError(
                "Invalid OpenAI API key",
                provider=self.provider_name,
            )
        elif response.status_code == 429:
            raise LLMRateLimitError(
                "OpenAI rate limit exceeded",
                provider=self.provider_name,
            )
        elif response.status_code >= 400:
            raise LLMConnectionError(
                f"OpenAI API error: {response.status_code} - {response.text}",
                provider=self.provider_name,
            )

        try:
            data = response.json()
        except Exception as e:
            raise LLMInvalidResponseError(
                f"Failed to parse OpenAI response: {e}",
                provider=self.provider_name,
            ) from e

        # Extract content from response
        choices = data.get("choices", [])
        if not choices:
            raise LLMInvalidResponseError(
                "OpenAI returned no choices",
                provider=self.provider_name,
            )

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not content:
            raise LLMInvalidResponseError(
                "OpenAI returned empty content",
                provider=self.provider_name,
            )

        # Extract usage info
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=data.get("model", self.config.openai_model),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            finish_reason=choices[0].get("finish_reason"),
            raw_response=data,
        )

    async def is_available(self) -> bool:
        """Check if OpenAI API is available."""
        if not self.config.openai_api_key:
            return False

        try:
            client = await self._get_client()
            response = await client.get(f"{self.API_BASE_URL}/models")
            return response.status_code == 200
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
