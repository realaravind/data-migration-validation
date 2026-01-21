"""
Unit tests for Configuration Manager

Tests configuration loading, validation, and management.
"""

import pytest
import tempfile
import json
import yaml
import os
from pathlib import Path
import sys

# Add backend directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from config.manager import ConfigManager
from config.models import ApplicationConfig, DatabaseConfig, JWTConfig, SecretStr
from config.validation import ConfigValidator, validate_config
from config.secrets import SecretsManager, EnvironmentProvider


@pytest.fixture
def temp_config_dir():
    """Create temporary config directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_config_dict():
    """Sample configuration dictionary"""
    return {
        "app_name": "Test App",
        "environment": "development",
        "debug": True,
        "port": 8000,
        "sql_server": {
            "host": "localhost",
            "port": 1433,
            "database": "testdb",
            "username": "testuser",
            "password": "testpass123"
        },
        "jwt": {
            "secret_key": "test-secret-key-change-in-production",
            "algorithm": "HS256",
            "access_token_expire_minutes": 30
        }
    }


@pytest.mark.unit
class TestConfigurationModels:
    """Test configuration Pydantic models"""

    def test_database_config_creation(self):
        """Test creating database configuration"""
        db_config = DatabaseConfig(
            host="localhost",
            port=1433,
            database="testdb",
            username="user",
            password=SecretStr("pass123")
        )

        assert db_config.host == "localhost"
        assert db_config.port == 1433
        assert db_config.password.get_secret_value() == "pass123"

    def test_database_config_validation_port(self):
        """Test port validation"""
        with pytest.raises(ValueError):
            DatabaseConfig(
                host="localhost",
                port=99999,  # Invalid port
                database="testdb",
                username="user",
                password=SecretStr("pass")
            )

    def test_database_connection_string(self):
        """Test connection string generation"""
        db_config = DatabaseConfig(
            host="localhost",
            port=5432,
            database="mydb",
            username="admin",
            password=SecretStr("secret123")
        )

        # Masked password
        conn_str = db_config.get_connection_string(mask_password=True)
        assert "****" in conn_str
        assert "secret123" not in conn_str

        # Unmasked password
        conn_str = db_config.get_connection_string(mask_password=False)
        assert "secret123" in conn_str

    def test_application_config_environment_validation(self):
        """Test environment validation"""
        with pytest.raises(ValueError):
            ApplicationConfig(environment="invalid_env")

    def test_application_config_is_production(self):
        """Test production environment check"""
        config = ApplicationConfig(
            environment="production",
            jwt=JWTConfig(secret_key=SecretStr("secret"))
        )
        assert config.is_production() is True
        assert config.is_development() is False

    def test_jwt_config_algorithm_validation(self):
        """Test JWT algorithm validation"""
        with pytest.raises(ValueError):
            JWTConfig(
                secret_key=SecretStr("secret"),
                algorithm="INVALID"
            )


@pytest.mark.unit
class TestConfigManager:
    """Test ConfigManager functionality"""

    def test_load_from_dict(self, sample_config_dict):
        """Test loading configuration from dictionary"""
        # Create config file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config_dict, f)
            config_file = f.name

        try:
            manager = ConfigManager(config_file=config_file)
            config = manager.load()

            assert config.app_name == "Test App"
            assert config.environment == "development"
            assert config.debug is True
            assert config.sql_server.host == "localhost"
        finally:
            os.unlink(config_file)

    def test_load_from_yaml(self, sample_config_dict, temp_config_dir):
        """Test loading from YAML file"""
        config_file = temp_config_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(sample_config_dict, f)

        manager = ConfigManager(config_file=str(config_file))
        config = manager.load()

        assert config.app_name == "Test App"
        assert config.port == 8000

    def test_load_from_environment(self):
        """Test loading from environment variables"""
        # Set environment variables
        os.environ["APP_NAME"] = "Env Test App"
        os.environ["PORT"] = "9000"
        os.environ["DEBUG"] = "false"

        try:
            manager = ConfigManager()
            config = manager.load()

            # Environment variables should override
            assert config.port == 9000
            assert config.debug is False
        finally:
            # Cleanup
            for key in ["APP_NAME", "PORT", "DEBUG"]:
                if key in os.environ:
                    del os.environ[key]

    def test_get_config_value(self, sample_config_dict):
        """Test getting configuration values"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config_dict, f)
            config_file = f.name

        try:
            manager = ConfigManager(config_file=config_file)
            manager.load()

            # Get value by dotted path
            assert manager.get("app_name") == "Test App"
            assert manager.get("sql_server.host") == "localhost"
            assert manager.get("sql_server.port") == 1433

            # Get with default
            assert manager.get("nonexistent.key", "default") == "default"
        finally:
            os.unlink(config_file)

    def test_set_config_value(self, sample_config_dict):
        """Test setting configuration values"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config_dict, f)
            config_file = f.name

        try:
            manager = ConfigManager(config_file=config_file)
            manager.load()

            # Set value
            manager.set("debug", False)
            assert manager.get("debug") is False

            # Set nested value
            manager.set("sql_server.port", 1434)
            assert manager.get("sql_server.port") == 1434
        finally:
            os.unlink(config_file)

    def test_config_watchers(self, sample_config_dict):
        """Test configuration watchers"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config_dict, f)
            config_file = f.name

        try:
            manager = ConfigManager(config_file=config_file)
            manager.load()

            # Register watcher
            changes = []

            def watcher(key, value):
                changes.append((key, value))

            manager.watch(watcher)

            # Change value
            manager.set("debug", False)

            # Watcher should be called
            assert len(changes) == 1
            assert changes[0] == ("debug", False)
        finally:
            os.unlink(config_file)

    def test_export_configuration(self, sample_config_dict, temp_config_dir):
        """Test exporting configuration"""
        config_file = temp_config_dir / "config.json"
        with open(config_file, 'w') as f:
            json.dump(sample_config_dict, f)

        manager = ConfigManager(config_file=str(config_file))
        manager.load()

        # Export to YAML
        export_file = temp_config_dir / "export.yaml"
        manager.export(str(export_file), mask_secrets=True)

        assert export_file.exists()

        # Verify secrets are masked
        with open(export_file, 'r') as f:
            exported = yaml.safe_load(f)
            assert exported["sql_server"]["password"] == "***REDACTED***"

    def test_config_history(self, sample_config_dict):
        """Test configuration change history"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(sample_config_dict, f)
            config_file = f.name

        try:
            manager = ConfigManager(config_file=config_file)
            manager.load()

            # Make changes
            manager.set("debug", False)
            manager.set("port", 9000)

            # Check history
            history = manager.get_history()
            assert len(history) >= 2
        finally:
            os.unlink(config_file)


@pytest.mark.unit
class TestConfigValidation:
    """Test configuration validation"""

    def test_validate_production_debug_disabled(self):
        """Test production debug validation"""
        config = ApplicationConfig(
            environment="production",
            debug=True,  # Should fail validation
            jwt=JWTConfig(secret_key=SecretStr("test-secret"))
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid()
        assert any("debug" in err.lower() for err in result.errors)

    def test_validate_production_reload_disabled(self):
        """Test production reload validation"""
        config = ApplicationConfig(
            environment="production",
            reload=True,  # Should fail validation
            jwt=JWTConfig(secret_key=SecretStr("test-secret"))
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid()
        assert any("reload" in err.lower() for err in result.errors)

    def test_validate_jwt_secret_not_default(self):
        """Test JWT secret validation"""
        config = ApplicationConfig(
            environment="production",
            debug=False,
            jwt=JWTConfig(secret_key=SecretStr("default"))  # Default secret
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert not result.is_valid()
        assert any("jwt" in err.lower() for err in result.errors)

    def test_validate_jwt_secret_length(self):
        """Test JWT secret length warning"""
        config = ApplicationConfig(
            environment="development",
            jwt=JWTConfig(secret_key=SecretStr("short"))  # Too short
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert len(result.warnings) > 0

    def test_validate_port_range(self):
        """Test port range validation"""
        # This should be caught by Pydantic validation
        with pytest.raises(ValueError):
            ApplicationConfig(
                port=99999,  # Invalid port
                jwt=JWTConfig(secret_key=SecretStr("secret"))
            )

    def test_valid_development_config(self):
        """Test valid development configuration"""
        config = ApplicationConfig(
            environment="development",
            debug=True,  # OK in development
            reload=True,  # OK in development
            jwt=JWTConfig(secret_key=SecretStr("my-development-secret-key-12345"))
        )

        validator = ConfigValidator()
        result = validator.validate(config)

        assert result.is_valid()


@pytest.mark.unit
class TestSecretsManager:
    """Test secrets management"""

    def test_environment_provider_get_secret(self):
        """Test getting secret from environment"""
        os.environ["SECRET_TEST_KEY"] = "test_value"

        try:
            provider = EnvironmentProvider(prefix="SECRET_")
            value = provider.get_secret("test_key")

            assert value == "test_value"
        finally:
            del os.environ["SECRET_TEST_KEY"]

    def test_environment_provider_set_secret(self):
        """Test setting secret in environment"""
        provider = EnvironmentProvider(prefix="SECRET_")
        provider.set_secret("new_key", "new_value")

        assert os.environ["SECRET_NEW_KEY"] == "new_value"

        # Cleanup
        del os.environ["SECRET_NEW_KEY"]

    def test_environment_provider_list_secrets(self):
        """Test listing secrets from environment"""
        os.environ["SECRET_KEY1"] = "value1"
        os.environ["SECRET_KEY2"] = "value2"

        try:
            provider = EnvironmentProvider(prefix="SECRET_")
            secrets = provider.list_secrets()

            assert "key1" in secrets
            assert "key2" in secrets
        finally:
            del os.environ["SECRET_KEY1"]
            del os.environ["SECRET_KEY2"]

    def test_secrets_manager_caching(self):
        """Test secret caching"""
        os.environ["SECRET_CACHED"] = "cached_value"

        try:
            manager = SecretsManager(provider="env", cache_ttl=60)

            # First call - fetches from provider
            value1 = manager.get_secret("cached")

            # Second call - should use cache
            value2 = manager.get_secret("cached")

            assert value1 == value2 == "cached_value"

            # Clear cache
            manager.clear_cache()

            # Should fetch again
            value3 = manager.get_secret("cached")
            assert value3 == "cached_value"
        finally:
            del os.environ["SECRET_CACHED"]


@pytest.mark.unit
class TestConfigIntegration:
    """Test full configuration integration"""

    def test_complete_config_workflow(self, temp_config_dir):
        """Test complete configuration workflow"""
        # 1. Create config file
        config_data = {
            "app_name": "Integration Test",
            "environment": "development",
            "debug": True,
            "port": 8000,
            "jwt": {
                "secret_key": "integration-test-secret-key-12345",
                "algorithm": "HS256"
            }
        }

        config_file = temp_config_dir / "config.yaml"
        with open(config_file, 'w') as f:
            yaml.dump(config_data, f)

        # 2. Load configuration
        manager = ConfigManager(config_file=str(config_file))
        config = manager.load()

        assert config.app_name == "Integration Test"

        # 3. Validate configuration
        validator = ConfigValidator()
        result = validator.validate(config)

        assert result.is_valid()

        # 4. Modify configuration
        manager.set("debug", False)
        assert manager.get("debug") is False

        # 5. Export configuration
        export_file = temp_config_dir / "exported.yaml"
        manager.export(str(export_file))

        assert export_file.exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
