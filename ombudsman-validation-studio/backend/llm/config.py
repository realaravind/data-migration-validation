"""Configuration loading for LLM providers from environment variables."""

import os
from typing import Optional

from .base import LLMConfig, LLMProviderType
from .exceptions import LLMConfigurationError


def load_llm_config() -> LLMConfig:
    """
    Load LLM configuration from environment variables.

    Environment Variables:
        LLM_PROVIDER: Provider type (ollama, openai, azure_openai, anthropic)
        LLM_TEMPERATURE: Temperature for generation (default: 0.1)
        LLM_MAX_TOKENS: Max tokens for response (default: 2048)
        LLM_TIMEOUT: Request timeout in seconds (default: 30)

        # Ollama
        OLLAMA_BASE_URL: Ollama server URL (default: http://localhost:11434)
        OLLAMA_MODEL: Model name (default: llama2)

        # OpenAI
        OPENAI_API_KEY: API key for OpenAI
        OPENAI_MODEL: Model name (default: gpt-4o-mini)

        # Azure OpenAI
        AZURE_OPENAI_API_KEY: API key for Azure OpenAI
        AZURE_OPENAI_ENDPOINT: Azure OpenAI endpoint URL
        AZURE_OPENAI_DEPLOYMENT: Deployment name
        AZURE_OPENAI_API_VERSION: API version (default: 2024-02-15-preview)

        # Anthropic
        ANTHROPIC_API_KEY: API key for Anthropic
        ANTHROPIC_MODEL: Model name (default: claude-3-5-sonnet-20241022)

    Returns:
        LLMConfig with values from environment.
    """
    # Parse provider type
    provider_str = os.getenv("LLM_PROVIDER", "ollama").lower()
    try:
        provider = LLMProviderType(provider_str)
    except ValueError:
        valid_providers = [p.value for p in LLMProviderType]
        raise LLMConfigurationError(
            f"Invalid LLM_PROVIDER '{provider_str}'. "
            f"Valid options: {', '.join(valid_providers)}"
        )

    # Parse common settings
    temperature = float(os.getenv("LLM_TEMPERATURE", "0.1"))
    max_tokens = int(os.getenv("LLM_MAX_TOKENS", "2048"))
    timeout = int(os.getenv("LLM_TIMEOUT", "30"))

    return LLMConfig(
        provider=provider,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
        # Ollama
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "llama2"),
        # OpenAI
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        openai_model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
        # Azure OpenAI
        azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
        azure_openai_deployment=os.getenv("AZURE_OPENAI_DEPLOYMENT"),
        azure_openai_api_version=os.getenv(
            "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
        ),
        # Anthropic
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-20241022"),
    )


def validate_config_for_provider(config: LLMConfig) -> None:
    """
    Validate that required configuration is present for the selected provider.

    Args:
        config: The LLM configuration to validate.

    Raises:
        LLMConfigurationError: If required configuration is missing.
    """
    if config.provider == LLMProviderType.OPENAI:
        if not config.openai_api_key:
            raise LLMConfigurationError(
                "OPENAI_API_KEY environment variable is required for OpenAI provider",
                provider="openai",
            )

    elif config.provider == LLMProviderType.AZURE_OPENAI:
        missing = []
        if not config.azure_openai_api_key:
            missing.append("AZURE_OPENAI_API_KEY")
        if not config.azure_openai_endpoint:
            missing.append("AZURE_OPENAI_ENDPOINT")
        if not config.azure_openai_deployment:
            missing.append("AZURE_OPENAI_DEPLOYMENT")
        if missing:
            raise LLMConfigurationError(
                f"Missing required environment variables for Azure OpenAI: "
                f"{', '.join(missing)}",
                provider="azure_openai",
            )

    elif config.provider == LLMProviderType.ANTHROPIC:
        if not config.anthropic_api_key:
            raise LLMConfigurationError(
                "ANTHROPIC_API_KEY environment variable is required for Anthropic provider",
                provider="anthropic",
            )

    # Ollama doesn't require API keys, just connectivity
