"""
Custom Exception Hierarchy for Ombudsman Validation Studio

This module defines a comprehensive exception hierarchy for better
error handling and user experience.
"""

from typing import Optional, Dict, Any


class OmbudsmanException(Exception):
    """
    Base exception for all Ombudsman errors.

    All custom exceptions should inherit from this class.
    """

    def __init__(
        self,
        message: str,
        error_code: str,
        status_code: int = 500,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.error_code = error_code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for API response"""
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details
            }
        }


# =============================================================================
# Validation Errors (400-series)
# =============================================================================

class ValidationError(OmbudsmanException):
    """Base class for validation errors (user input issues)"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="VALIDATION_ERROR",
            status_code=400,
            details=details
        )


class InvalidPipelineConfigError(ValidationError):
    """Raised when pipeline configuration is invalid"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.error_code = "INVALID_PIPELINE_CONFIG"


class InvalidMetadataError(ValidationError):
    """Raised when metadata format is invalid"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message, details)
        self.error_code = "INVALID_METADATA"


class InvalidQueryError(ValidationError):
    """Raised when custom query is invalid or unsafe"""

    def __init__(self, message: str, query: Optional[str] = None):
        details = {"query": query} if query else {}
        super().__init__(message, details)
        self.error_code = "INVALID_QUERY"


class MissingParameterError(ValidationError):
    """Raised when required parameter is missing"""

    def __init__(self, parameter_name: str, context: Optional[str] = None):
        message = f"Missing required parameter: {parameter_name}"
        if context:
            message += f" ({context})"
        super().__init__(message, {"parameter": parameter_name})
        self.error_code = "MISSING_PARAMETER"


# =============================================================================
# Resource Not Found Errors (404)
# =============================================================================

class ResourceNotFoundError(OmbudsmanException):
    """Base class for resource not found errors"""

    def __init__(self, resource_type: str, resource_id: str):
        message = f"{resource_type} not found: {resource_id}"
        super().__init__(
            message=message,
            error_code="RESOURCE_NOT_FOUND",
            status_code=404,
            details={"resource_type": resource_type, "resource_id": resource_id}
        )


class PipelineNotFoundError(ResourceNotFoundError):
    """Raised when pipeline is not found"""

    def __init__(self, pipeline_id: str):
        super().__init__("Pipeline", pipeline_id)
        self.error_code = "PIPELINE_NOT_FOUND"


class ProjectNotFoundError(ResourceNotFoundError):
    """Raised when project is not found"""

    def __init__(self, project_id: str):
        super().__init__("Project", project_id)
        self.error_code = "PROJECT_NOT_FOUND"


class TableNotFoundError(ResourceNotFoundError):
    """Raised when table is not found in database"""

    def __init__(self, table_name: str, schema: Optional[str] = None):
        full_name = f"{schema}.{table_name}" if schema else table_name
        super().__init__("Table", full_name)
        self.error_code = "TABLE_NOT_FOUND"
        self.details["schema"] = schema


class ValidatorNotFoundError(ResourceNotFoundError):
    """Raised when validator is not found in registry"""

    def __init__(self, validator_name: str, available_validators: Optional[list] = None):
        super().__init__("Validator", validator_name)
        self.error_code = "VALIDATOR_NOT_FOUND"
        if available_validators:
            self.details["available_validators"] = available_validators[:20]  # Limit to first 20


# =============================================================================
# Database Errors (500-series)
# =============================================================================

class DatabaseError(OmbudsmanException):
    """Base class for database-related errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATABASE_ERROR",
            status_code=500,
            details=details
        )


class ConnectionError(DatabaseError):
    """Raised when database connection fails"""

    def __init__(self, database: str, reason: Optional[str] = None):
        message = f"Failed to connect to {database}"
        if reason:
            message += f": {reason}"
        super().__init__(message, {"database": database})
        self.error_code = "CONNECTION_ERROR"


class QueryExecutionError(DatabaseError):
    """Raised when query execution fails"""

    def __init__(self, message: str, query: Optional[str] = None):
        details = {"query": query[:500] if query else None}  # Truncate long queries
        super().__init__(message, details)
        self.error_code = "QUERY_EXECUTION_ERROR"


class TransactionError(DatabaseError):
    """Raised when database transaction fails"""

    def __init__(self, message: str, operation: Optional[str] = None):
        super().__init__(message, {"operation": operation})
        self.error_code = "TRANSACTION_ERROR"


# =============================================================================
# Pipeline Execution Errors (500-series)
# =============================================================================

class PipelineExecutionError(OmbudsmanException):
    """Base class for pipeline execution errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="PIPELINE_EXECUTION_ERROR",
            status_code=500,
            details=details
        )


class ValidatorExecutionError(PipelineExecutionError):
    """Raised when validator execution fails"""

    def __init__(
        self,
        validator_name: str,
        error_message: str,
        step_config: Optional[Dict[str, Any]] = None
    ):
        message = f"Validator '{validator_name}' failed: {error_message}"
        details = {
            "validator": validator_name,
            "error": error_message,
            "config": step_config
        }
        super().__init__(message, details)
        self.error_code = "VALIDATOR_EXECUTION_ERROR"


class ParameterMismatchError(PipelineExecutionError):
    """Raised when validator parameters don't match expected signature"""

    def __init__(
        self,
        validator_name: str,
        expected_params: list,
        provided_params: list
    ):
        message = f"Parameter mismatch for validator '{validator_name}'"
        details = {
            "validator": validator_name,
            "expected_parameters": expected_params,
            "provided_parameters": provided_params
        }
        super().__init__(message, details)
        self.error_code = "PARAMETER_MISMATCH"


# =============================================================================
# Configuration Errors (500-series)
# =============================================================================

class ConfigurationError(OmbudsmanException):
    """Base class for configuration errors"""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="CONFIGURATION_ERROR",
            status_code=500,
            details=details
        )


class MissingConfigError(ConfigurationError):
    """Raised when required configuration is missing"""

    def __init__(self, config_key: str, context: Optional[str] = None):
        message = f"Missing required configuration: {config_key}"
        if context:
            message += f" ({context})"
        super().__init__(message, {"config_key": config_key})
        self.error_code = "MISSING_CONFIG"


class InvalidConfigError(ConfigurationError):
    """Raised when configuration value is invalid"""

    def __init__(self, config_key: str, expected: str, actual: Any):
        message = f"Invalid configuration for '{config_key}': expected {expected}, got {type(actual).__name__}"
        super().__init__(
            message,
            {"config_key": config_key, "expected": expected, "actual": str(actual)}
        )
        self.error_code = "INVALID_CONFIG"


# =============================================================================
# Permission/Authorization Errors (403)
# =============================================================================

class PermissionError(OmbudsmanException):
    """Raised when user lacks permission for operation"""

    def __init__(self, operation: str, reason: Optional[str] = None):
        message = f"Permission denied: {operation}"
        if reason:
            message += f" - {reason}"
        super().__init__(
            message=message,
            error_code="PERMISSION_DENIED",
            status_code=403,
            details={"operation": operation}
        )


class AuthenticationError(OmbudsmanException):
    """Raised when authentication fails"""

    def __init__(self, message: str = "Authentication required"):
        super().__init__(
            message=message,
            error_code="AUTHENTICATION_ERROR",
            status_code=401
        )


# =============================================================================
# Timeout Errors (504)
# =============================================================================

class TimeoutError(OmbudsmanException):
    """Raised when operation times out"""

    def __init__(self, operation: str, timeout_seconds: int):
        message = f"Operation timed out after {timeout_seconds} seconds: {operation}"
        super().__init__(
            message=message,
            error_code="TIMEOUT_ERROR",
            status_code=504,
            details={"operation": operation, "timeout": timeout_seconds}
        )


# =============================================================================
# Rate Limiting Errors (429)
# =============================================================================

class RateLimitError(OmbudsmanException):
    """Raised when rate limit is exceeded"""

    def __init__(self, limit: int, window_seconds: int, retry_after: Optional[int] = None):
        message = f"Rate limit exceeded: {limit} requests per {window_seconds} seconds"
        if retry_after:
            message += f". Retry after {retry_after} seconds"
        super().__init__(
            message=message,
            error_code="RATE_LIMIT_EXCEEDED",
            status_code=429,
            details={
                "limit": limit,
                "window": window_seconds,
                "retry_after": retry_after
            }
        )


# =============================================================================
# Data Quality Errors
# =============================================================================

class DataQualityError(OmbudsmanException):
    """Raised when data quality validation fails"""

    def __init__(self, message: str, validation_type: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(
            message=message,
            error_code="DATA_QUALITY_ERROR",
            status_code=422,  # Unprocessable Entity
            details={
                "validation_type": validation_type,
                **(details or {})
            }
        )


class SchemaMismatchError(DataQualityError):
    """Raised when schemas don't match between source and target"""

    def __init__(self, table: str, mismatches: list):
        message = f"Schema mismatch for table '{table}'"
        super().__init__(
            message,
            validation_type="schema",
            details={"table": table, "mismatches": mismatches}
        )
        self.error_code = "SCHEMA_MISMATCH"


class RowCountMismatchError(DataQualityError):
    """Raised when row counts don't match"""

    def __init__(self, table: str, source_count: int, target_count: int):
        message = f"Row count mismatch for table '{table}': source={source_count}, target={target_count}"
        super().__init__(
            message,
            validation_type="row_count",
            details={
                "table": table,
                "source_count": source_count,
                "target_count": target_count,
                "difference": abs(source_count - target_count)
            }
        )
        self.error_code = "ROW_COUNT_MISMATCH"
