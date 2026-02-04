"""Anthropic Claude LLM provider implementation."""

import httpx

from ..base import LLMConfig, LLMProvider, LLMResponse
from ..exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
)


class AnthropicProvider(LLMProvider):
    """LLM provider for Anthropic Claude API."""

    API_BASE_URL = "https://api.anthropic.com/v1"
    API_VERSION = "2023-06-01"

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "anthropic"

    @property
    def model_name(self) -> str:
        return self.config.anthropic_model

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "x-api-key": self.config.anthropic_api_key,
                    "anthropic-version": self.API_VERSION,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def generate(self, prompt: str) -> str:
        """Generate a response from Anthropic Claude."""
        response = await self.generate_with_metadata(prompt)
        return response.content

    async def generate_with_metadata(self, prompt: str) -> LLMResponse:
        """Generate a response with full metadata from Anthropic Claude."""
        client = await self._get_client()

        payload = {
            "model": self.config.anthropic_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature,
        }

        try:
            response = await client.post(
                f"{self.API_BASE_URL}/messages",
                json=payload,
            )
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"Request to Anthropic timed out after {self.config.timeout}s",
                provider=self.provider_name,
            ) from e
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                "Failed to connect to Anthropic API",
                provider=self.provider_name,
            ) from e

        # Handle HTTP errors
        if response.status_code == 401:
            raise LLMAuthenticationError(
                "Invalid Anthropic API key",
                provider=self.provider_name,
            )
        elif response.status_code == 429:
            raise LLMRateLimitError(
                "Anthropic rate limit exceeded",
                provider=self.provider_name,
            )
        elif response.status_code >= 400:
            raise LLMConnectionError(
                f"Anthropic API error: {response.status_code} - {response.text}",
                provider=self.provider_name,
            )

        try:
            data = response.json()
        except Exception as e:
            raise LLMInvalidResponseError(
                f"Failed to parse Anthropic response: {e}",
                provider=self.provider_name,
            ) from e

        # Extract content from response
        # Anthropic returns content as a list of content blocks
        content_blocks = data.get("content", [])
        if not content_blocks:
            raise LLMInvalidResponseError(
                "Anthropic returned no content",
                provider=self.provider_name,
            )

        # Extract text from content blocks
        text_parts = []
        for block in content_blocks:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))

        content = "".join(text_parts)
        if not content:
            raise LLMInvalidResponseError(
                "Anthropic returned empty content",
                provider=self.provider_name,
            )

        # Extract usage info
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=data.get("model", self.config.anthropic_model),
            prompt_tokens=usage.get("input_tokens"),
            completion_tokens=usage.get("output_tokens"),
            total_tokens=(
                (usage.get("input_tokens") or 0) + (usage.get("output_tokens") or 0)
                if usage.get("input_tokens") or usage.get("output_tokens")
                else None
            ),
            finish_reason=data.get("stop_reason"),
            raw_response=data,
        )

    async def is_available(self) -> bool:
        """Check if Anthropic API is available."""
        if not self.config.anthropic_api_key:
            return False

        # Anthropic doesn't have a simple health check endpoint
        # We assume it's available if API key is configured
        # A real check would require making a request
        return True

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
