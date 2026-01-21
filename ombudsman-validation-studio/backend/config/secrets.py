"""
Secrets Management

Secure secrets management with support for:
- AWS Secrets Manager
- Azure Key Vault
- HashiCorp Vault
- Encrypted file storage
- Environment variables (fallback)
"""

import os
import json
import base64
from typing import Dict, Any, Optional
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class SecretProvider(ABC):
    """Abstract base class for secret providers"""

    @abstractmethod
    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get a single secret value"""
        pass

    @abstractmethod
    def get_secrets(self, secret_names: list) -> Dict[str, str]:
        """Get multiple secret values"""
        pass

    @abstractmethod
    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set a secret value"""
        pass

    @abstractmethod
    def delete_secret(self, secret_name: str) -> bool:
        """Delete a secret"""
        pass

    @abstractmethod
    def list_secrets(self) -> list:
        """List all available secret names"""
        pass


class EnvironmentProvider(SecretProvider):
    """Environment variable secret provider"""

    def __init__(self, prefix: str = "SECRET_"):
        self.prefix = prefix

    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from environment variable"""
        env_name = f"{self.prefix}{secret_name.upper()}"
        return os.getenv(env_name)

    def get_secrets(self, secret_names: list) -> Dict[str, str]:
        """Get multiple secrets from environment"""
        secrets = {}
        for name in secret_names:
            value = self.get_secret(name)
            if value:
                secrets[name] = value
        return secrets

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set environment variable (runtime only)"""
        env_name = f"{self.prefix}{secret_name.upper()}"
        os.environ[env_name] = secret_value
        return True

    def delete_secret(self, secret_name: str) -> bool:
        """Delete environment variable"""
        env_name = f"{self.prefix}{secret_name.upper()}"
        if env_name in os.environ:
            del os.environ[env_name]
            return True
        return False

    def list_secrets(self) -> list:
        """List all secrets from environment"""
        return [
            key[len(self.prefix):].lower()
            for key in os.environ.keys()
            if key.startswith(self.prefix)
        ]


class AWSSecretsProvider(SecretProvider):
    """AWS Secrets Manager provider"""

    def __init__(self, region: str = "us-east-1"):
        self.region = region
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize AWS Secrets Manager client"""
        try:
            import boto3
            self.client = boto3.client('secretsmanager', region_name=self.region)
            logger.info(f"Initialized AWS Secrets Manager client for region: {self.region}")
        except ImportError:
            logger.warning("boto3 not installed. AWS Secrets Manager unavailable.")
        except Exception as e:
            logger.error(f"Failed to initialize AWS Secrets Manager: {e}")

    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from AWS Secrets Manager"""
        if not self.client:
            return None

        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            if 'SecretString' in response:
                return response['SecretString']
            else:
                # Binary secret
                return base64.b64decode(response['SecretBinary']).decode('utf-8')
        except Exception as e:
            logger.error(f"Failed to get secret '{secret_name}' from AWS: {e}")
            return None

    def get_secrets(self, secret_names: list) -> Dict[str, str]:
        """Get multiple secrets from AWS"""
        secrets = {}
        for name in secret_names:
            value = self.get_secret(name)
            if value:
                secrets[name] = value
        return secrets

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Create or update secret in AWS"""
        if not self.client:
            return False

        try:
            # Try to update existing secret
            self.client.put_secret_value(
                SecretId=secret_name,
                SecretString=secret_value
            )
            logger.info(f"Updated secret: {secret_name}")
            return True
        except self.client.exceptions.ResourceNotFoundException:
            # Create new secret
            try:
                self.client.create_secret(
                    Name=secret_name,
                    SecretString=secret_value
                )
                logger.info(f"Created secret: {secret_name}")
                return True
            except Exception as e:
                logger.error(f"Failed to create secret '{secret_name}': {e}")
                return False
        except Exception as e:
            logger.error(f"Failed to set secret '{secret_name}': {e}")
            return False

    def delete_secret(self, secret_name: str) -> bool:
        """Delete secret from AWS"""
        if not self.client:
            return False

        try:
            self.client.delete_secret(
                SecretId=secret_name,
                ForceDeleteWithoutRecovery=True
            )
            logger.info(f"Deleted secret: {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret '{secret_name}': {e}")
            return False

    def list_secrets(self) -> list:
        """List all secrets in AWS Secrets Manager"""
        if not self.client:
            return []

        try:
            secrets = []
            paginator = self.client.get_paginator('list_secrets')
            for page in paginator.paginate():
                secrets.extend([s['Name'] for s in page['SecretList']])
            return secrets
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []


class AzureKeyVaultProvider(SecretProvider):
    """Azure Key Vault provider"""

    def __init__(self, vault_url: str):
        self.vault_url = vault_url
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Azure Key Vault client"""
        try:
            from azure.identity import DefaultAzureCredential
            from azure.keyvault.secrets import SecretClient

            credential = DefaultAzureCredential()
            self.client = SecretClient(vault_url=self.vault_url, credential=credential)
            logger.info(f"Initialized Azure Key Vault client for: {self.vault_url}")
        except ImportError:
            logger.warning("azure-identity or azure-keyvault-secrets not installed.")
        except Exception as e:
            logger.error(f"Failed to initialize Azure Key Vault: {e}")

    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from Azure Key Vault"""
        if not self.client:
            return None

        try:
            secret = self.client.get_secret(secret_name)
            return secret.value
        except Exception as e:
            logger.error(f"Failed to get secret '{secret_name}' from Azure: {e}")
            return None

    def get_secrets(self, secret_names: list) -> Dict[str, str]:
        """Get multiple secrets from Azure"""
        secrets = {}
        for name in secret_names:
            value = self.get_secret(name)
            if value:
                secrets[name] = value
        return secrets

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set secret in Azure Key Vault"""
        if not self.client:
            return False

        try:
            self.client.set_secret(secret_name, secret_value)
            logger.info(f"Set secret: {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to set secret '{secret_name}': {e}")
            return False

    def delete_secret(self, secret_name: str) -> bool:
        """Delete secret from Azure Key Vault"""
        if not self.client:
            return False

        try:
            poller = self.client.begin_delete_secret(secret_name)
            poller.wait()
            logger.info(f"Deleted secret: {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret '{secret_name}': {e}")
            return False

    def list_secrets(self) -> list:
        """List all secrets in Azure Key Vault"""
        if not self.client:
            return []

        try:
            return [secret.name for secret in self.client.list_properties_of_secrets()]
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []


class HashiCorpVaultProvider(SecretProvider):
    """HashiCorp Vault provider"""

    def __init__(self, vault_url: str, token: str, mount_point: str = "secret"):
        self.vault_url = vault_url
        self.token = token
        self.mount_point = mount_point
        self.client = None
        self._initialize_client()

    def _initialize_client(self):
        """Initialize Vault client"""
        try:
            import hvac
            self.client = hvac.Client(url=self.vault_url, token=self.token)
            if not self.client.is_authenticated():
                logger.error("Failed to authenticate with HashiCorp Vault")
                self.client = None
            else:
                logger.info(f"Initialized HashiCorp Vault client for: {self.vault_url}")
        except ImportError:
            logger.warning("hvac not installed. HashiCorp Vault unavailable.")
        except Exception as e:
            logger.error(f"Failed to initialize HashiCorp Vault: {e}")

    def get_secret(self, secret_name: str) -> Optional[str]:
        """Get secret from Vault"""
        if not self.client:
            return None

        try:
            secret = self.client.secrets.kv.v2.read_secret_version(
                path=secret_name,
                mount_point=self.mount_point
            )
            return secret['data']['data'].get('value')
        except Exception as e:
            logger.error(f"Failed to get secret '{secret_name}' from Vault: {e}")
            return None

    def get_secrets(self, secret_names: list) -> Dict[str, str]:
        """Get multiple secrets from Vault"""
        secrets = {}
        for name in secret_names:
            value = self.get_secret(name)
            if value:
                secrets[name] = value
        return secrets

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """Set secret in Vault"""
        if not self.client:
            return False

        try:
            self.client.secrets.kv.v2.create_or_update_secret(
                path=secret_name,
                secret={'value': secret_value},
                mount_point=self.mount_point
            )
            logger.info(f"Set secret: {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to set secret '{secret_name}': {e}")
            return False

    def delete_secret(self, secret_name: str) -> bool:
        """Delete secret from Vault"""
        if not self.client:
            return False

        try:
            self.client.secrets.kv.v2.delete_metadata_and_all_versions(
                path=secret_name,
                mount_point=self.mount_point
            )
            logger.info(f"Deleted secret: {secret_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to delete secret '{secret_name}': {e}")
            return False

    def list_secrets(self) -> list:
        """List all secrets in Vault"""
        if not self.client:
            return []

        try:
            response = self.client.secrets.kv.v2.list_secrets(
                path='',
                mount_point=self.mount_point
            )
            return response['data']['keys']
        except Exception as e:
            logger.error(f"Failed to list secrets: {e}")
            return []


class SecretsManager:
    """
    Unified secrets manager supporting multiple providers.

    Supports:
    - AWS Secrets Manager
    - Azure Key Vault
    - HashiCorp Vault
    - Environment variables (fallback)
    """

    def __init__(self, provider: str = "env", **kwargs):
        """
        Initialize secrets manager.

        Args:
            provider: Provider type (env, aws, azure, vault)
            **kwargs: Provider-specific configuration
        """
        self.provider = provider
        self.cache: Dict[str, tuple] = {}  # (value, expiry)
        self.cache_ttl = kwargs.get('cache_ttl', 300)  # 5 minutes default

        # Initialize provider
        if provider == "env":
            self._provider = EnvironmentProvider(
                prefix=kwargs.get('prefix', 'SECRET_')
            )
        elif provider == "aws":
            self._provider = AWSSecretsProvider(
                region=kwargs.get('region', 'us-east-1')
            )
        elif provider == "azure":
            vault_url = kwargs.get('vault_url')
            if not vault_url:
                raise ValueError("vault_url required for Azure Key Vault")
            self._provider = AzureKeyVaultProvider(vault_url=vault_url)
        elif provider == "vault":
            vault_url = kwargs.get('vault_url')
            token = kwargs.get('token')
            if not vault_url or not token:
                raise ValueError("vault_url and token required for HashiCorp Vault")
            self._provider = HashiCorpVaultProvider(
                vault_url=vault_url,
                token=token,
                mount_point=kwargs.get('mount_point', 'secret')
            )
        else:
            raise ValueError(f"Unknown provider: {provider}")

        logger.info(f"Initialized SecretsManager with provider: {provider}")

    def get_secret(self, secret_name: str, use_cache: bool = True) -> Optional[str]:
        """
        Get a secret value.

        Args:
            secret_name: Secret name/key
            use_cache: Whether to use cached value

        Returns:
            Secret value or None
        """
        # Check cache
        if use_cache and secret_name in self.cache:
            value, expiry = self.cache[secret_name]
            if datetime.now() < expiry:
                return value

        # Get from provider
        value = self._provider.get_secret(secret_name)

        # Cache the value
        if value and use_cache:
            expiry = datetime.now() + timedelta(seconds=self.cache_ttl)
            self.cache[secret_name] = (value, expiry)

        return value

    def get_all_secrets(self, use_cache: bool = True) -> Dict[str, str]:
        """
        Get all available secrets.

        Args:
            use_cache: Whether to use cached values

        Returns:
            Dictionary of secret names and values
        """
        secret_names = self._provider.list_secrets()
        return self._provider.get_secrets(secret_names)

    def set_secret(self, secret_name: str, secret_value: str) -> bool:
        """
        Set a secret value.

        Args:
            secret_name: Secret name/key
            secret_value: Secret value

        Returns:
            True if successful
        """
        # Clear cache
        if secret_name in self.cache:
            del self.cache[secret_name]

        return self._provider.set_secret(secret_name, secret_value)

    def delete_secret(self, secret_name: str) -> bool:
        """
        Delete a secret.

        Args:
            secret_name: Secret name/key

        Returns:
            True if successful
        """
        # Clear cache
        if secret_name in self.cache:
            del self.cache[secret_name]

        return self._provider.delete_secret(secret_name)

    def list_secrets(self) -> list:
        """
        List all available secret names.

        Returns:
            List of secret names
        """
        return self._provider.list_secrets()

    def clear_cache(self) -> None:
        """Clear the secret cache"""
        self.cache.clear()
        logger.info("Secret cache cleared")

    def is_configured(self) -> bool:
        """Check if secrets manager is properly configured"""
        return self._provider is not None
