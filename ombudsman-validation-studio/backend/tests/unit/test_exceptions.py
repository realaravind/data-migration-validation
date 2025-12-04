"""
Unit tests for custom exception hierarchy.
"""

import pytest
from errors import (
    OmbudsmanException,
    ValidationError,
    InvalidPipelineConfigError,
    InvalidMetadataError,
    InvalidQueryError,
    MissingParameterError,
    ResourceNotFoundError,
    PipelineNotFoundError,
    ProjectNotFoundError,
    TableNotFoundError,
    ValidatorNotFoundError,
    DatabaseError,
    ConnectionError,
    QueryExecutionError,
    TransactionError,
    PipelineExecutionError,
    ValidatorExecutionError,
    ParameterMismatchError,
    ConfigurationError,
    MissingConfigError,
    InvalidConfigError,
    PermissionError,
    AuthenticationError,
    TimeoutError,
    RateLimitError,
    DataQualityError,
    SchemaMismatchError,
    RowCountMismatchError,
)


class TestOmbudsmanException:
    """Test base OmbudsmanException class."""

    def test_basic_exception(self):
        """Test basic exception creation."""
        exc = OmbudsmanException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=500
        )
        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.status_code == 500
        assert exc.details == {}

    def test_exception_with_details(self):
        """Test exception with details."""
        exc = OmbudsmanException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=500,
            details={"key": "value"}
        )
        assert exc.details == {"key": "value"}

    def test_to_dict(self):
        """Test to_dict method."""
        exc = OmbudsmanException(
            message="Test error",
            error_code="TEST_ERROR",
            status_code=500,
            details={"key": "value"}
        )
        result = exc.to_dict()
        assert result == {
            "error": {
                "code": "TEST_ERROR",
                "message": "Test error",
                "details": {"key": "value"}
            }
        }


class TestValidationErrors:
    """Test validation error classes (400)."""

    def test_validation_error(self):
        """Test ValidationError."""
        exc = ValidationError("Invalid input")
        assert exc.status_code == 400
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.message == "Invalid input"

    def test_invalid_pipeline_config_error(self):
        """Test InvalidPipelineConfigError."""
        exc = InvalidPipelineConfigError(
            message="Missing steps",
            details={"pipeline": "test"}
        )
        assert exc.status_code == 400
        assert exc.error_code == "INVALID_PIPELINE_CONFIG"
        assert exc.message == "Missing steps"
        assert exc.details == {"pipeline": "test"}

    def test_invalid_metadata_error(self):
        """Test InvalidMetadataError."""
        exc = InvalidMetadataError("Bad metadata format")
        assert exc.status_code == 400
        assert exc.error_code == "INVALID_METADATA"

    def test_invalid_query_error(self):
        """Test InvalidQueryError."""
        exc = InvalidQueryError(
            message="SQL syntax error",
            query="SELECT * FROM"
        )
        assert exc.status_code == 400
        assert exc.error_code == "INVALID_QUERY"
        assert exc.details["query"] == "SELECT * FROM"

    def test_missing_parameter_error(self):
        """Test MissingParameterError."""
        exc = MissingParameterError("table_name", "validation context")
        assert exc.status_code == 400
        assert exc.error_code == "MISSING_PARAMETER"
        assert "table_name" in exc.message
        assert exc.details["parameter"] == "table_name"


class TestNotFoundErrors:
    """Test not found error classes (404)."""

    def test_resource_not_found_error(self):
        """Test ResourceNotFoundError."""
        exc = ResourceNotFoundError("Pipeline", "run_123")
        assert exc.status_code == 404
        assert exc.error_code == "RESOURCE_NOT_FOUND"
        assert "Pipeline" in exc.message
        assert "run_123" in exc.message

    def test_pipeline_not_found_error(self):
        """Test PipelineNotFoundError."""
        exc = PipelineNotFoundError("run_123")
        assert exc.status_code == 404
        assert exc.error_code == "PIPELINE_NOT_FOUND"
        assert exc.details["resource_type"] == "Pipeline"
        assert exc.details["resource_id"] == "run_123"

    def test_project_not_found_error(self):
        """Test ProjectNotFoundError."""
        exc = ProjectNotFoundError("project_abc")
        assert exc.status_code == 404
        assert exc.error_code == "PROJECT_NOT_FOUND"

    def test_table_not_found_error(self):
        """Test TableNotFoundError."""
        exc = TableNotFoundError("customers", "dbo")
        assert exc.status_code == 404
        assert exc.error_code == "TABLE_NOT_FOUND"
        assert "dbo.customers" in exc.message
        assert exc.details["schema"] == "dbo"

    def test_validator_not_found_error(self):
        """Test ValidatorNotFoundError."""
        exc = ValidatorNotFoundError(
            "validate_xyz",
            available_validators=["validate_a", "validate_b"]
        )
        assert exc.status_code == 404
        assert exc.error_code == "VALIDATOR_NOT_FOUND"
        assert exc.details["available_validators"] == ["validate_a", "validate_b"]


class TestDatabaseErrors:
    """Test database error classes (500)."""

    def test_database_error(self):
        """Test DatabaseError."""
        exc = DatabaseError("Query failed")
        assert exc.status_code == 500
        assert exc.error_code == "DATABASE_ERROR"

    def test_connection_error(self):
        """Test ConnectionError."""
        exc = ConnectionError("sqlserver", "timeout")
        assert exc.status_code == 500
        assert exc.error_code == "CONNECTION_ERROR"
        assert "sqlserver" in exc.message
        assert "timeout" in exc.message

    def test_query_execution_error(self):
        """Test QueryExecutionError."""
        query = "SELECT * FROM very_long_table_name" * 100
        exc = QueryExecutionError("Syntax error", query)
        assert exc.status_code == 500
        assert exc.error_code == "QUERY_EXECUTION_ERROR"
        # Check query is truncated to 500 chars
        assert len(exc.details["query"]) <= 500

    def test_transaction_error(self):
        """Test TransactionError."""
        exc = TransactionError("Rollback failed", "commit")
        assert exc.status_code == 500
        assert exc.error_code == "TRANSACTION_ERROR"
        assert exc.details["operation"] == "commit"


class TestPipelineErrors:
    """Test pipeline execution error classes (500)."""

    def test_pipeline_execution_error(self):
        """Test PipelineExecutionError."""
        exc = PipelineExecutionError("Pipeline failed")
        assert exc.status_code == 500
        assert exc.error_code == "PIPELINE_EXECUTION_ERROR"

    def test_validator_execution_error(self):
        """Test ValidatorExecutionError."""
        exc = ValidatorExecutionError(
            validator_name="validate_counts",
            error_message="Connection timeout",
            step_config={"table": "customers"}
        )
        assert exc.status_code == 500
        assert exc.error_code == "VALIDATOR_EXECUTION_ERROR"
        assert exc.details["validator"] == "validate_counts"
        assert exc.details["error"] == "Connection timeout"
        assert exc.details["config"] == {"table": "customers"}

    def test_parameter_mismatch_error(self):
        """Test ParameterMismatchError."""
        exc = ParameterMismatchError(
            validator_name="validate_test",
            expected_params=["table", "column"],
            provided_params=["table"]
        )
        assert exc.status_code == 500
        assert exc.error_code == "PARAMETER_MISMATCH"
        assert exc.details["expected_parameters"] == ["table", "column"]
        assert exc.details["provided_parameters"] == ["table"]


class TestConfigurationErrors:
    """Test configuration error classes (500)."""

    def test_configuration_error(self):
        """Test ConfigurationError."""
        exc = ConfigurationError("Invalid config")
        assert exc.status_code == 500
        assert exc.error_code == "CONFIGURATION_ERROR"

    def test_missing_config_error(self):
        """Test MissingConfigError."""
        exc = MissingConfigError("DATABASE_URL", "connection setup")
        assert exc.status_code == 500
        assert exc.error_code == "MISSING_CONFIG"
        assert "DATABASE_URL" in exc.message
        assert exc.details["config_key"] == "DATABASE_URL"

    def test_invalid_config_error(self):
        """Test InvalidConfigError."""
        exc = InvalidConfigError("port", "integer", "abc")
        assert exc.status_code == 500
        assert exc.error_code == "INVALID_CONFIG"
        assert "port" in exc.message
        assert exc.details["expected"] == "integer"


class TestAuthErrors:
    """Test authentication and permission error classes."""

    def test_authentication_error(self):
        """Test AuthenticationError."""
        exc = AuthenticationError()
        assert exc.status_code == 401
        assert exc.error_code == "AUTHENTICATION_ERROR"
        assert exc.message == "Authentication required"

    def test_authentication_error_custom_message(self):
        """Test AuthenticationError with custom message."""
        exc = AuthenticationError("Invalid token")
        assert exc.message == "Invalid token"

    def test_permission_error(self):
        """Test PermissionError."""
        exc = PermissionError("delete_pipeline", "Only admins can delete")
        assert exc.status_code == 403
        assert exc.error_code == "PERMISSION_DENIED"
        assert "delete_pipeline" in exc.message
        assert "Only admins can delete" in exc.message


class TestOtherErrors:
    """Test other error classes."""

    def test_timeout_error(self):
        """Test TimeoutError."""
        exc = TimeoutError("long_query", 300)
        assert exc.status_code == 504
        assert exc.error_code == "TIMEOUT_ERROR"
        assert "300 seconds" in exc.message
        assert exc.details["timeout"] == 300

    def test_rate_limit_error(self):
        """Test RateLimitError."""
        exc = RateLimitError(100, 60, 45)
        assert exc.status_code == 429
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert "100 requests" in exc.message
        assert "60 seconds" in exc.message
        assert exc.details["retry_after"] == 45

    def test_data_quality_error(self):
        """Test DataQualityError."""
        exc = DataQualityError(
            message="Data validation failed",
            validation_type="schema",
            details={"table": "customers"}
        )
        assert exc.status_code == 422
        assert exc.error_code == "DATA_QUALITY_ERROR"
        assert exc.details["validation_type"] == "schema"
        assert exc.details["table"] == "customers"

    def test_schema_mismatch_error(self):
        """Test SchemaMismatchError."""
        exc = SchemaMismatchError(
            table="customers",
            mismatches=["column_type_mismatch"]
        )
        assert exc.status_code == 422
        assert exc.error_code == "SCHEMA_MISMATCH"
        assert exc.details["table"] == "customers"
        assert exc.details["mismatches"] == ["column_type_mismatch"]

    def test_row_count_mismatch_error(self):
        """Test RowCountMismatchError."""
        exc = RowCountMismatchError("customers", 1000, 985)
        assert exc.status_code == 422
        assert exc.error_code == "ROW_COUNT_MISMATCH"
        assert exc.details["source_count"] == 1000
        assert exc.details["target_count"] == 985
        assert exc.details["difference"] == 15
