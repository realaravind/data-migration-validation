"""
Ombudsman Validation Studio Error Handling

This package provides comprehensive error handling for the application:
- Custom exception hierarchy (exceptions.py)
- FastAPI error handlers (handlers.py)

Usage:
    from errors import (
        OmbudsmanException,
        ValidationError,
        DatabaseError,
        register_error_handlers
    )

    # In your FastAPI app
    app = FastAPI()
    register_error_handlers(app)

    # In your code
    raise ValidationError("Invalid pipeline configuration")
"""

# Import all exceptions for easy access
from .exceptions import (
    # Base
    OmbudsmanException,

    # Validation Errors (400)
    ValidationError,
    InvalidPipelineConfigError,
    InvalidMetadataError,
    InvalidQueryError,
    MissingParameterError,

    # Not Found Errors (404)
    ResourceNotFoundError,
    PipelineNotFoundError,
    ProjectNotFoundError,
    TableNotFoundError,
    ValidatorNotFoundError,

    # Database Errors (500)
    DatabaseError,
    ConnectionError,
    QueryExecutionError,
    TransactionError,

    # Pipeline Execution Errors (500)
    PipelineExecutionError,
    ValidatorExecutionError,
    ParameterMismatchError,

    # Configuration Errors (500)
    ConfigurationError,
    MissingConfigError,
    InvalidConfigError,

    # Permission/Auth Errors
    PermissionError,
    AuthenticationError,

    # Other Errors
    TimeoutError,
    RateLimitError,
    DataQualityError,
    SchemaMismatchError,
    RowCountMismatchError,
)

# Import error handlers
from .handlers import (
    register_error_handlers,
    ombudsman_exception_handler,
    validation_error_handler,
    http_exception_handler,
    general_exception_handler,
)

__all__ = [
    # Base
    "OmbudsmanException",

    # Validation Errors
    "ValidationError",
    "InvalidPipelineConfigError",
    "InvalidMetadataError",
    "InvalidQueryError",
    "MissingParameterError",

    # Not Found Errors
    "ResourceNotFoundError",
    "PipelineNotFoundError",
    "ProjectNotFoundError",
    "TableNotFoundError",
    "ValidatorNotFoundError",

    # Database Errors
    "DatabaseError",
    "ConnectionError",
    "QueryExecutionError",
    "TransactionError",

    # Pipeline Execution Errors
    "PipelineExecutionError",
    "ValidatorExecutionError",
    "ParameterMismatchError",

    # Configuration Errors
    "ConfigurationError",
    "MissingConfigError",
    "InvalidConfigError",

    # Auth Errors
    "PermissionError",
    "AuthenticationError",

    # Other Errors
    "TimeoutError",
    "RateLimitError",
    "DataQualityError",
    "SchemaMismatchError",
    "RowCountMismatchError",

    # Handlers
    "register_error_handlers",
    "ombudsman_exception_handler",
    "validation_error_handler",
    "http_exception_handler",
    "general_exception_handler",
]
