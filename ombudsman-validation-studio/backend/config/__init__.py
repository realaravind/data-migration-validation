"""
Configuration and Secrets Management Module

Provides secure configuration and secrets management with:
- Environment-based configuration
- Encrypted secrets storage
- Integration with external secret managers (AWS, Azure, HashiCorp Vault)
- Configuration validation
- Hot-reload capabilities
- Centralized path management
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
from .paths import paths, init_paths, get_projects_dir, get_core_config_dir, get_data_dir

__all__ = [
    'ConfigManager',
    'get_config',
    'DatabaseConfig',
    'SecretConfig',
    'ApplicationConfig',
    'ConfigSource',
    'SecretsManager',
    'SecretProvider',
    'ConfigValidator',
    'paths',
    'init_paths',
    'get_projects_dir',
    'get_core_config_dir',
    'get_data_dir'
]
