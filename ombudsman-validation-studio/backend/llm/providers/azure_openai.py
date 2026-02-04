"""Azure OpenAI LLM provider implementation."""

import httpx

from ..base import LLMConfig, LLMProvider, LLMResponse
from ..exceptions import (
    LLMAuthenticationError,
    LLMConnectionError,
    LLMInvalidResponseError,
    LLMRateLimitError,
    LLMTimeoutError,
)


class AzureOpenAIProvider(LLMProvider):
    """LLM provider for Azure OpenAI Service."""

    def __init__(self, config: LLMConfig):
        super().__init__(config)
        self._client: httpx.AsyncClient | None = None

    @property
    def provider_name(self) -> str:
        return "azure_openai"

    @property
    def model_name(self) -> str:
        return self.config.azure_openai_deployment

    @property
    def _api_url(self) -> str:
        """Build the Azure OpenAI API URL."""
        endpoint = self.config.azure_openai_endpoint.rstrip("/")
        deployment = self.config.azure_openai_deployment
        api_version = self.config.azure_openai_api_version
        return (
            f"{endpoint}/openai/deployments/{deployment}"
            f"/chat/completions?api-version={api_version}"
        )

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.config.timeout),
                headers={
                    "api-key": self.config.azure_openai_api_key,
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def generate(self, prompt: str) -> str:
        """Generate a response from Azure OpenAI."""
        response = await self.generate_with_metadata(prompt)
        return response.content

    async def generate_with_metadata(self, prompt: str) -> LLMResponse:
        """Generate a response with full metadata from Azure OpenAI."""
        client = await self._get_client()

        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.temperature,
            "max_tokens": self.config.max_tokens,
        }

        try:
            response = await client.post(
                self._api_url,
                json=payload,
            )
        except httpx.TimeoutException as e:
            raise LLMTimeoutError(
                f"Request to Azure OpenAI timed out after {self.config.timeout}s",
                provider=self.provider_name,
            ) from e
        except httpx.ConnectError as e:
            raise LLMConnectionError(
                f"Failed to connect to Azure OpenAI at "
                f"{self.config.azure_openai_endpoint}",
                provider=self.provider_name,
            ) from e

        # Handle HTTP errors
        if response.status_code == 401:
            raise LLMAuthenticationError(
                "Invalid Azure OpenAI API key",
                provider=self.provider_name,
            )
        elif response.status_code == 429:
            raise LLMRateLimitError(
                "Azure OpenAI rate limit exceeded",
                provider=self.provider_name,
            )
        elif response.status_code == 404:
            raise LLMConnectionError(
                f"Azure OpenAI deployment '{self.config.azure_openai_deployment}' "
                "not found. Check your deployment name and endpoint.",
                provider=self.provider_name,
            )
        elif response.status_code >= 400:
            raise LLMConnectionError(
                f"Azure OpenAI API error: {response.status_code} - {response.text}",
                provider=self.provider_name,
            )

        try:
            data = response.json()
        except Exception as e:
            raise LLMInvalidResponseError(
                f"Failed to parse Azure OpenAI response: {e}",
                provider=self.provider_name,
            ) from e

        # Extract content from response (same format as OpenAI)
        choices = data.get("choices", [])
        if not choices:
            raise LLMInvalidResponseError(
                "Azure OpenAI returned no choices",
                provider=self.provider_name,
            )

        message = choices[0].get("message", {})
        content = message.get("content", "")
        if not content:
            raise LLMInvalidResponseError(
                "Azure OpenAI returned empty content",
                provider=self.provider_name,
            )

        # Extract usage info
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            provider=self.provider_name,
            model=data.get("model", self.config.azure_openai_deployment),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            total_tokens=usage.get("total_tokens"),
            finish_reason=choices[0].get("finish_reason"),
            raw_response=data,
        )

    async def is_available(self) -> bool:
        """Check if Azure OpenAI is available."""
        if not all([
            self.config.azure_openai_api_key,
            self.config.azure_openai_endpoint,
            self.config.azure_openai_deployment,
        ]):
            return False

        # Try a simple request to verify connectivity
        try:
            client = await self._get_client()
            # Azure OpenAI doesn't have a simple health endpoint,
            # so we check if we can reach the endpoint
            endpoint = self.config.azure_openai_endpoint.rstrip("/")
            response = await client.get(f"{endpoint}/openai/models?api-version=2024-02-15-preview")
            # 401 means endpoint is reachable but auth may be wrong
            # 200 means everything works
            return response.status_code in (200, 401)
        except Exception:
            return False

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None
