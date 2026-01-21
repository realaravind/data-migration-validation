"""
Configuration Validation

Validates configuration for security, completeness, and correctness.
"""

import re
from typing import List, Dict, Any, Optional
from .models import ApplicationConfig, DatabaseConfig
import logging

logger = logging.getLogger(__name__)


class ValidationRule:
    """Single validation rule"""

    def __init__(self, name: str, severity: str, check: callable, message: str):
        """
        Initialize validation rule.

        Args:
            name: Rule name
            severity: error, warning, or info
            check: Function that returns True if validation passes
            message: Error message if validation fails
        """
        self.name = name
        self.severity = severity
        self.check = check
        self.message = message


class ValidationResult:
    """Validation result"""

    def __init__(self):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.info: List[str] = []

    def add_error(self, message: str):
        """Add error message"""
        self.errors.append(message)

    def add_warning(self, message: str):
        """Add warning message"""
        self.warnings.append(message)

    def add_info(self, message: str):
        """Add info message"""
        self.info.append(message)

    def is_valid(self) -> bool:
        """Check if configuration is valid (no errors)"""
        return len(self.errors) == 0

    def summary(self) -> str:
        """Get validation summary"""
        return (
            f"Errors: {len(self.errors)}, "
            f"Warnings: {len(self.warnings)}, "
            f"Info: {len(self.info)}"
        )


class ConfigValidator:
    """
    Configuration validator with built-in rules.

    Validates:
    - Security settings
    - Required fields
    - Value ranges
    - Format correctness
    - Production readiness
    """

    def __init__(self):
        self.rules: List[ValidationRule] = []
        self._register_default_rules()

    def validate(self, config: ApplicationConfig) -> ValidationResult:
        """
        Validate configuration.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with errors, warnings, and info
        """
        result = ValidationResult()

        for rule in self.rules:
            try:
                if not rule.check(config):
                    if rule.severity == "error":
                        result.add_error(f"{rule.name}: {rule.message}")
                    elif rule.severity == "warning":
                        result.add_warning(f"{rule.name}: {rule.message}")
                    else:
                        result.add_info(f"{rule.name}: {rule.message}")
            except Exception as e:
                logger.error(f"Error running validation rule '{rule.name}': {e}")
                result.add_error(f"{rule.name}: Validation check failed - {str(e)}")

        return result

    def add_rule(self, rule: ValidationRule):
        """Add custom validation rule"""
        self.rules.append(rule)

    def _register_default_rules(self):
        """Register default validation rules"""

        # Production environment rules
        self.add_rule(ValidationRule(
            name="debug_disabled_in_production",
            severity="error",
            check=lambda c: not (c.is_production() and c.debug),
            message="Debug mode must be disabled in production"
        ))

        self.add_rule(ValidationRule(
            name="reload_disabled_in_production",
            severity="error",
            check=lambda c: not (c.is_production() and c.reload),
            message="Auto-reload must be disabled in production"
        ))

        # JWT security rules
        self.add_rule(ValidationRule(
            name="jwt_secret_not_default",
            severity="error",
            check=lambda c: not (
                c.is_production() and
                c.jwt and
                c.jwt.secret_key.get_secret_value() in ["default", "changeme", "secret"]
            ),
            message="JWT secret must not be a default value in production"
        ))

        self.add_rule(ValidationRule(
            name="jwt_secret_length",
            severity="warning",
            check=lambda c: not c.jwt or len(c.jwt.secret_key.get_secret_value()) >= 32,
            message="JWT secret should be at least 32 characters long"
        ))

        # Database configuration rules
        self.add_rule(ValidationRule(
            name="database_password_not_empty",
            severity="error",
            check=lambda c: self._check_database_passwords(c),
            message="Database passwords must not be empty"
        ))

        self.add_rule(ValidationRule(
            name="database_ssl_in_production",
            severity="warning",
            check=lambda c: not c.is_production() or self._check_database_ssl(c),
            message="Database SSL should be enabled in production"
        ))

        # CORS rules
        self.add_rule(ValidationRule(
            name="cors_not_wildcard_in_production",
            severity="warning",
            check=lambda c: not (c.is_production() and "*" in c.cors.allow_origins),
            message="CORS should not allow all origins (*) in production"
        ))

        # Logging rules
        self.add_rule(ValidationRule(
            name="log_level_appropriate",
            severity="info",
            check=lambda c: c.logging.level != "DEBUG" if c.is_production() else True,
            message="Consider using INFO or WARNING level in production"
        ))

        # Port rules
        self.add_rule(ValidationRule(
            name="port_in_valid_range",
            severity="error",
            check=lambda c: 1 <= c.port <= 65535,
            message="Port must be between 1 and 65535"
        ))

        # Worker rules
        self.add_rule(ValidationRule(
            name="sufficient_workers",
            severity="warning",
            check=lambda c: not c.is_production() or c.workers > 1,
            message="Consider using multiple workers in production"
        ))

        # Feature flags
        self.add_rule(ValidationRule(
            name="auth_enabled_in_production",
            severity="warning",
            check=lambda c: not c.is_production() or c.enable_auth,
            message="Authentication should be enabled in production"
        ))

        # Rate limiting
        self.add_rule(ValidationRule(
            name="rate_limit_reasonable",
            severity="info",
            check=lambda c: c.rate_limit_per_minute <= 1000,
            message="Rate limit seems very high, consider lowering it"
        ))

    def _check_database_passwords(self, config: ApplicationConfig) -> bool:
        """Check that database passwords are set"""
        databases = [config.sql_server, config.snowflake, config.postgres]
        for db in databases:
            if db and not db.password.get_secret_value():
                return False
        return True

    def _check_database_ssl(self, config: ApplicationConfig) -> bool:
        """Check that database SSL is enabled"""
        databases = [config.sql_server, config.snowflake, config.postgres]
        for db in databases:
            if db and not db.ssl_enabled:
                return False
        return True


# Global validator instance
_validator = ConfigValidator()


def validate_config(config: ApplicationConfig) -> ValidationResult:
    """
    Validate configuration using default validator.

    Args:
        config: Configuration to validate

    Returns:
        ValidationResult
    """
    return _validator.validate(config)


def get_validator() -> ConfigValidator:
    """Get global validator instance"""
    return _validator
