"""Base classes for LLM provider abstraction layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class LLMProviderType(str, Enum):
    """Supported LLM provider types."""

    OLLAMA = "ollama"
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"
    ANTHROPIC = "anthropic"


@dataclass
class LLMConfig:
    """Configuration for LLM provider."""

    provider: LLMProviderType = LLMProviderType.OLLAMA
    temperature: float = 0.1
    max_tokens: int = 2048
    timeout: int = 30

    # Ollama-specific
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama2"

    # OpenAI-specific
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4o-mini"

    # Azure OpenAI-specific
    azure_openai_api_key: Optional[str] = None
    azure_openai_endpoint: Optional[str] = None
    azure_openai_deployment: Optional[str] = None
    azure_openai_api_version: str = "2024-02-15-preview"

    # Anthropic-specific
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-5-sonnet-20241022"


@dataclass
class LLMResponse:
    """Response from LLM provider with metadata."""

    content: str
    provider: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    finish_reason: Optional[str] = None
    raw_response: Optional[dict] = field(default=None, repr=False)


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, config: LLMConfig):
        self.config = config

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the name of this provider."""
        pass

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model being used."""
        pass

    @abstractmethod
    async def generate(self, prompt: str) -> str:
        """
        Generate a response from the LLM.

        Args:
            prompt: The input prompt.

        Returns:
            The generated text response.

        Raises:
            LLMProviderError: If generation fails.
        """
        pass

    @abstractmethod
    async def generate_with_metadata(self, prompt: str) -> LLMResponse:
        """
        Generate a response with full metadata.

        Args:
            prompt: The input prompt.

        Returns:
            LLMResponse with content and metadata.

        Raises:
            LLMProviderError: If generation fails.
        """
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        """
        Check if the provider is available and configured correctly.

        Returns:
            True if provider is available, False otherwise.
        """
        pass

    async def close(self) -> None:
        """
        Clean up any resources held by the provider.

        Override in subclasses if cleanup is needed.
        """
        pass

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
