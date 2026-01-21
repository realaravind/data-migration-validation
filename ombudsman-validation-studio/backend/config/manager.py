"""
Configuration Manager

Centralized configuration management with support for:
- Multiple configuration sources
- Environment-based configs
- Hot-reload capabilities
- Configuration validation
- Change tracking
"""

import os
import json
import yaml
import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime
import logging

from .models import (
    ApplicationConfig,
    ConfigSource,
    ConfigMetadata,
    ConfigHistory,
    DatabaseConfig,
    JWTConfig,
    SecretStr
)
from .secrets import SecretsManager

logger = logging.getLogger(__name__)


class ConfigManager:
    """
    Centralized configuration manager.

    Supports loading from:
    - Environment variables
    - YAML/JSON files
    - Encrypted files
    - External secret managers (AWS, Azure, Vault)
    """

    def __init__(
        self,
        config_file: Optional[str] = None,
        environment: Optional[str] = None,
        secrets_manager: Optional[SecretsManager] = None
    ):
        """
        Initialize configuration manager.

        Args:
            config_file: Path to configuration file
            environment: Environment name (development, staging, production)
            secrets_manager: SecretsManager instance for external secrets
        """
        self.config_file = config_file
        self.environment = environment or os.getenv("ENVIRONMENT", "development")
        self.secrets_manager = secrets_manager or SecretsManager()

        self._config: Optional[ApplicationConfig] = None
        self._metadata: Optional[ConfigMetadata] = None
        self._history: List[ConfigHistory] = []
        self._watchers: List[callable] = []

    def load(self, reload: bool = False) -> ApplicationConfig:
        """
        Load configuration from all sources.

        Args:
            reload: Force reload even if config already loaded

        Returns:
            ApplicationConfig instance
        """
        if self._config and not reload:
            return self._config

        logger.info(f"Loading configuration for environment: {self.environment}")

        # Determine config sources priority
        config_data = {}

        # 1. Load from default file if exists
        default_file = self._get_default_config_file()
        if default_file and default_file.exists():
            file_data = self._load_from_file(default_file)
            config_data.update(file_data)
            logger.info(f"Loaded config from: {default_file}")

        # 2. Load from environment-specific file
        env_file = self._get_env_config_file()
        if env_file and env_file.exists():
            env_data = self._load_from_file(env_file)
            config_data.update(env_data)
            logger.info(f"Loaded env config from: {env_file}")

        # 3. Load from explicit config file
        if self.config_file:
            explicit_data = self._load_from_file(Path(self.config_file))
            config_data.update(explicit_data)
            logger.info(f"Loaded config from: {self.config_file}")

        # 4. Override with environment variables
        env_overrides = self._load_from_env()
        config_data.update(env_overrides)
        if env_overrides:
            logger.info(f"Applied {len(env_overrides)} environment variable overrides")

        # 5. Load secrets from secrets manager
        if self.secrets_manager.is_configured():
            secrets = self.secrets_manager.get_all_secrets()
            config_data = self._merge_secrets(config_data, secrets)
            logger.info("Loaded secrets from secrets manager")

        # Create config object
        try:
            self._config = ApplicationConfig(**config_data)

            # Create metadata
            self._metadata = ConfigMetadata(
                source=self._determine_source(),
                loaded_at=datetime.now(),
                file_path=str(self.config_file) if self.config_file else None,
                environment=self.environment,
                checksum=self._calculate_checksum()
            )

            logger.info("Configuration loaded successfully")
            return self._config

        except Exception as e:
            logger.error(f"Failed to load configuration: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dotted key path.

        Args:
            key: Configuration key (e.g., "database.host")
            default: Default value if key not found

        Returns:
            Configuration value
        """
        if not self._config:
            self.load()

        parts = key.split('.')
        value = self._config.dict()

        for part in parts:
            if isinstance(value, dict) and part in value:
                value = value[part]
            else:
                return default

        return value

    def set(self, key: str, value: Any, persist: bool = False) -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key (e.g., "database.host")
            value: New value
            persist: Whether to persist change to file
        """
        if not self._config:
            self.load()

        # Record change
        old_value = self.get(key)
        if old_value != value:
            self._record_change(key, old_value, value)

        # Update config
        parts = key.split('.')
        config_dict = self._config.dict()

        # Navigate to the parent dict
        current = config_dict
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]

        # Set the value
        current[parts[-1]] = value

        # Reload config object
        self._config = ApplicationConfig(**config_dict)

        # Persist if requested
        if persist and self.config_file:
            self._save_to_file(Path(self.config_file), config_dict)

        # Notify watchers
        self._notify_watchers(key, value)

    def reload(self) -> ApplicationConfig:
        """
        Reload configuration from sources.

        Returns:
            Updated ApplicationConfig
        """
        logger.info("Reloading configuration...")
        return self.load(reload=True)

    def watch(self, callback: callable) -> None:
        """
        Register a callback for configuration changes.

        Args:
            callback: Function to call when config changes
        """
        self._watchers.append(callback)

    def get_history(self, limit: int = 100) -> List[ConfigHistory]:
        """
        Get configuration change history.

        Args:
            limit: Maximum number of history items

        Returns:
            List of configuration changes
        """
        return self._history[-limit:]

    def export(self, file_path: str, mask_secrets: bool = True) -> None:
        """
        Export configuration to file.

        Args:
            file_path: Output file path
            mask_secrets: Whether to mask secret values
        """
        if not self._config:
            self.load()

        config_dict = self._config.dict()

        if mask_secrets:
            config_dict = self._mask_secrets(config_dict)

        path = Path(file_path)
        if path.suffix in ['.yaml', '.yml']:
            with open(path, 'w') as f:
                yaml.dump(config_dict, f, default_flow_style=False)
        else:
            with open(path, 'w') as f:
                json.dump(config_dict, f, indent=2)

        logger.info(f"Configuration exported to: {file_path}")

    def validate(self) -> List[str]:
        """
        Validate current configuration.

        Returns:
            List of validation errors (empty if valid)
        """
        if not self._config:
            self.load()

        errors = []

        # Check required database configs
        if self._config.enable_auth and not self._config.jwt:
            errors.append("JWT configuration required when auth is enabled")

        # Check production settings
        if self._config.is_production():
            if self._config.debug:
                errors.append("Debug mode should be disabled in production")
            if self._config.reload:
                errors.append("Auto-reload should be disabled in production")
            if self._config.jwt and self._config.jwt.secret_key.get_secret_value() == "default":
                errors.append("Default JWT secret should not be used in production")

        return errors

    # ==================== Private Methods ====================

    def _get_default_config_file(self) -> Optional[Path]:
        """Get default configuration file path"""
        possible_paths = [
            Path("config/default.yaml"),
            Path("config/default.yml"),
            Path("config/default.json"),
            Path("./config.yaml"),
            Path("./config.yml"),
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def _get_env_config_file(self) -> Optional[Path]:
        """Get environment-specific config file"""
        possible_paths = [
            Path(f"config/{self.environment}.yaml"),
            Path(f"config/{self.environment}.yml"),
            Path(f"config/{self.environment}.json"),
        ]

        for path in possible_paths:
            if path.exists():
                return path

        return None

    def _load_from_file(self, file_path: Path) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            with open(file_path, 'r') as f:
                if file_path.suffix in ['.yaml', '.yml']:
                    return yaml.safe_load(f) or {}
                else:
                    return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load config from {file_path}: {e}")
            return {}

    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        config = {}

        # Database configs
        if os.getenv("SQL_SERVER_HOST"):
            config["sql_server"] = {
                "host": os.getenv("SQL_SERVER_HOST"),
                "port": int(os.getenv("SQL_SERVER_PORT", 1433)),
                "database": os.getenv("SQL_SERVER_DATABASE", ""),
                "username": os.getenv("SQL_SERVER_USERNAME", ""),
                "password": os.getenv("SQL_SERVER_PASSWORD", ""),
                "driver": os.getenv("SQL_SERVER_DRIVER"),
            }

        if os.getenv("SNOWFLAKE_ACCOUNT"):
            config["snowflake"] = {
                "host": f"{os.getenv('SNOWFLAKE_ACCOUNT')}.snowflakecomputing.com",
                "port": int(os.getenv("SNOWFLAKE_PORT", 443)),
                "database": os.getenv("SNOWFLAKE_DATABASE", ""),
                "username": os.getenv("SNOWFLAKE_USER", ""),
                "password": os.getenv("SNOWFLAKE_PASSWORD", ""),
                "driver": "snowflake",
            }

        # JWT config
        if os.getenv("JWT_SECRET_KEY"):
            config["jwt"] = {
                "secret_key": os.getenv("JWT_SECRET_KEY"),
                "algorithm": os.getenv("JWT_ALGORITHM", "HS256"),
                "access_token_expire_minutes": int(os.getenv("JWT_ACCESS_TOKEN_EXPIRE", 30)),
                "refresh_token_expire_days": int(os.getenv("JWT_REFRESH_TOKEN_EXPIRE", 7)),
            }

        # App config
        if os.getenv("APP_NAME"):
            config["app_name"] = os.getenv("APP_NAME")
        if os.getenv("APP_VERSION"):
            config["app_version"] = os.getenv("APP_VERSION")
        if os.getenv("DEBUG"):
            config["debug"] = os.getenv("DEBUG").lower() in ["true", "1", "yes"]
        if os.getenv("HOST"):
            config["host"] = os.getenv("HOST")
        if os.getenv("PORT"):
            config["port"] = int(os.getenv("PORT"))

        return config

    def _merge_secrets(self, config: Dict[str, Any], secrets: Dict[str, Any]) -> Dict[str, Any]:
        """Merge secrets into configuration"""
        # Simple merge - override specific secret fields
        if "database_password" in secrets:
            if "sql_server" in config:
                config["sql_server"]["password"] = secrets["database_password"]

        if "jwt_secret" in secrets:
            if "jwt" not in config:
                config["jwt"] = {}
            config["jwt"]["secret_key"] = secrets["jwt_secret"]

        return config

    def _determine_source(self) -> ConfigSource:
        """Determine primary configuration source"""
        if self.secrets_manager.is_configured():
            provider = self.secrets_manager.provider
            if provider == "aws":
                return ConfigSource.AWS_SECRETS
            elif provider == "azure":
                return ConfigSource.AZURE_KEYVAULT
            elif provider == "vault":
                return ConfigSource.HASHICORP_VAULT

        if self.config_file:
            return ConfigSource.FILE

        return ConfigSource.ENV

    def _calculate_checksum(self) -> str:
        """Calculate configuration checksum"""
        if not self._config:
            return ""

        # Custom JSON encoder for datetime and SecretStr objects
        def json_encoder(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if isinstance(obj, SecretStr):
                return "***REDACTED***"
            raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

        config_str = json.dumps(self._config.dict(), sort_keys=True, default=json_encoder)
        return hashlib.sha256(config_str.encode()).hexdigest()

    def _record_change(self, key: str, old_value: Any, new_value: Any) -> None:
        """Record configuration change in history"""
        change = ConfigHistory(
            timestamp=datetime.now(),
            changes={key: {"old": old_value, "new": new_value}},
            previous_checksum=self._calculate_checksum()
        )
        self._history.append(change)

    def _save_to_file(self, file_path: Path, config_data: Dict[str, Any]) -> None:
        """Save configuration to file"""
        try:
            with open(file_path, 'w') as f:
                if file_path.suffix in ['.yaml', '.yml']:
                    yaml.dump(config_data, f, default_flow_style=False)
                else:
                    # Custom JSON encoder for datetime and SecretStr objects
                    def json_encoder(obj):
                        if isinstance(obj, datetime):
                            return obj.isoformat()
                        if isinstance(obj, SecretStr):
                            return "***REDACTED***"
                        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

                    json.dump(config_data, f, indent=2, default=json_encoder)
            logger.info(f"Configuration saved to: {file_path}")
        except Exception as e:
            logger.error(f"Failed to save config to {file_path}: {e}")

    def _mask_secrets(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mask secret values in configuration"""
        import copy
        from enum import Enum
        masked = copy.deepcopy(config)

        # Recursively mask secrets and convert special types
        def mask_dict(d: Dict[str, Any]) -> Dict[str, Any]:
            for key, value in d.items():
                if isinstance(value, dict):
                    d[key] = mask_dict(value)
                elif isinstance(value, SecretStr):
                    # Convert SecretStr to masked string
                    d[key] = "***REDACTED***"
                elif isinstance(value, datetime):
                    # Convert datetime to ISO string
                    d[key] = value.isoformat()
                elif isinstance(value, Enum):
                    # Convert Enum to its value
                    d[key] = value.value
                elif key.lower() in ['password', 'secret', 'token', 'key'] and value:
                    d[key] = "***REDACTED***"
            return d

        return mask_dict(masked)

    def _notify_watchers(self, key: str, value: Any) -> None:
        """Notify all watchers of configuration change"""
        for watcher in self._watchers:
            try:
                watcher(key, value)
            except Exception as e:
                logger.error(f"Error in config watcher: {e}")


# Global config instance
_config_manager: Optional[ConfigManager] = None


def get_config(reload: bool = False) -> ApplicationConfig:
    """
    Get global configuration instance.

    Args:
        reload: Force reload configuration

    Returns:
        ApplicationConfig instance
    """
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigManager()

    return _config_manager.load(reload=reload)


def get_manager() -> ConfigManager:
    """
    Get global ConfigManager instance.

    Returns:
        ConfigManager instance
    """
    global _config_manager

    if _config_manager is None:
        _config_manager = ConfigManager()

    return _config_manager
