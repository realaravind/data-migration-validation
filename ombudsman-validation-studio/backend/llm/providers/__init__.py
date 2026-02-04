"""LLM provider implementations and registry."""

from typing import Type

from ..base import LLMConfig, LLMProvider, LLMProviderType
from .anthropic import AnthropicProvider
from .azure_openai import AzureOpenAIProvider
from .ollama import OllamaProvider
from .openai import OpenAIProvider

# Provider registry maps provider types to their implementations
PROVIDER_REGISTRY: dict[LLMProviderType, Type[LLMProvider]] = {
    LLMProviderType.OLLAMA: OllamaProvider,
    LLMProviderType.OPENAI: OpenAIProvider,
    LLMProviderType.AZURE_OPENAI: AzureOpenAIProvider,
    LLMProviderType.ANTHROPIC: AnthropicProvider,
}


def create_provider(config: LLMConfig) -> LLMProvider:
    """
    Create an LLM provider instance based on configuration.

    Args:
        config: LLM configuration specifying which provider to use.

    Returns:
        An instance of the appropriate LLM provider.

    Raises:
        ValueError: If the provider type is not supported.
    """
    provider_class = PROVIDER_REGISTRY.get(config.provider)
    if provider_class is None:
        valid_providers = [p.value for p in LLMProviderType]
        raise ValueError(
            f"Unsupported provider type: {config.provider}. "
            f"Valid options: {', '.join(valid_providers)}"
        )

    return provider_class(config)


__all__ = [
    "PROVIDER_REGISTRY",
    "create_provider",
    "OllamaProvider",
    "OpenAIProvider",
    "AzureOpenAIProvider",
    "AnthropicProvider",
]
