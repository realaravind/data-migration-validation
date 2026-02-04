"""Custom exceptions for LLM provider abstraction layer."""


class LLMProviderError(Exception):
    """Base exception for LLM provider errors."""

    def __init__(self, message: str, provider: str = None):
        self.provider = provider
        super().__init__(message)


class LLMConnectionError(LLMProviderError):
    """Raised when connection to LLM provider fails."""

    pass


class LLMAuthenticationError(LLMProviderError):
    """Raised when authentication with LLM provider fails."""

    pass


class LLMRateLimitError(LLMProviderError):
    """Raised when rate limit is exceeded."""

    pass


class LLMTimeoutError(LLMProviderError):
    """Raised when request times out."""

    pass


class LLMInvalidResponseError(LLMProviderError):
    """Raised when LLM returns an invalid or unparseable response."""

    pass


class LLMConfigurationError(LLMProviderError):
    """Raised when LLM provider is misconfigured."""

    pass
