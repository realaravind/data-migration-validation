"""
LLM Provider Abstraction Layer.

This module provides a unified interface for multiple LLM providers:
- Ollama (local models)
- OpenAI
- Azure OpenAI
- Anthropic Claude

Usage:
    from backend.llm import get_llm_provider

    # Get provider based on environment configuration
    provider = get_llm_provider()

    # Generate text
    response = await provider.generate("What is 2+2?")

    # Or with metadata
    response = await provider.generate_with_metadata("What is 2+2?")
    print(response.content)
    print(response.total_tokens)

Environment Variables:
    LLM_PROVIDER: Provider type (ollama, openai, azure_openai, anthropic)
    LLM_TEMPERATURE: Temperature for generation (default: 0.1)
    LLM_MAX_TOKENS: Max tokens for response (default: 2048)
    LLM_TIMEOUT: Request timeout in seconds (default: 30)

    See backend/llm/config.py for provider-specific variables.
"""

import logging
from typing import Optional

from .base import LLMConfig, LLMProvider, LLMProviderType, LLMResponse
from .config import load_llm_config, validate_config_for_provider
from .exceptions import (
    LLMAuthenticationError,
    LLMConfigurationError,
    LLMConnectionError,
    LLMInvalidResponseError,
    LLMProviderError,
    LLMRateLimitError,
    LLMTimeoutError,
)
from .providers import create_provider

logger = logging.getLogger(__name__)


def get_llm_provider(config: Optional[LLMConfig] = None) -> LLMProvider:
    """
    Factory function to get an LLM provider instance.

    Args:
        config: Optional LLM configuration. If not provided,
                configuration is loaded from environment variables.

    Returns:
        An LLM provider instance ready to use.

    Raises:
        LLMConfigurationError: If configuration is invalid or incomplete.

    Example:
        provider = get_llm_provider()
        response = await provider.generate("Hello!")
    """
    if config is None:
        config = load_llm_config()

    # Validate configuration for the selected provider
    validate_config_for_provider(config)

    logger.info(
        f"Creating LLM provider: {config.provider.value} "
        f"(model: {_get_model_name(config)})"
    )

    return create_provider(config)


def _get_model_name(config: LLMConfig) -> str:
    """Get the model name for the configured provider."""
    if config.provider == LLMProviderType.OLLAMA:
        return config.ollama_model
    elif config.provider == LLMProviderType.OPENAI:
        return config.openai_model
    elif config.provider == LLMProviderType.AZURE_OPENAI:
        return config.azure_openai_deployment or "unknown"
    elif config.provider == LLMProviderType.ANTHROPIC:
        return config.anthropic_model
    return "unknown"


__all__ = [
    # Factory
    "get_llm_provider",
    # Types
    "LLMProvider",
    "LLMConfig",
    "LLMProviderType",
    "LLMResponse",
    # Config
    "load_llm_config",
    "validate_config_for_provider",
    # Exceptions
    "LLMProviderError",
    "LLMConnectionError",
    "LLMAuthenticationError",
    "LLMRateLimitError",
    "LLMTimeoutError",
    "LLMInvalidResponseError",
    "LLMConfigurationError",
]
