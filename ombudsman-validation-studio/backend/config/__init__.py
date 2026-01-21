"""
Configuration and Secrets Management Module

Provides secure configuration and secrets management with:
- Environment-based configuration
- Encrypted secrets storage
- Integration with external secret managers (AWS, Azure, HashiCorp Vault)
- Configuration validation
- Hot-reload capabilities
"""

from .manager import ConfigManager, get_config
from .models import (
    DatabaseConfig,
    SecretConfig,
    ApplicationConfig,
    ConfigSource
)
from .secrets import SecretsManager, SecretProvider
from .validation import ConfigValidator

__all__ = [
    'ConfigManager',
    'get_config',
    'DatabaseConfig',
    'SecretConfig',
    'ApplicationConfig',
    'ConfigSource',
    'SecretsManager',
    'SecretProvider',
    'ConfigValidator'
]
