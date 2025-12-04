# Ombudsman Error Codes Documentation

This document describes all custom error codes used in the Ombudsman Validation Studio API.

## Error Response Format

All errors follow a standard JSON format:

```json
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": {
      "key": "Additional context about the error"
    }
  }
}
```

---

## Error Categories

### Validation Errors (400 Bad Request)

| Error Code | Exception Class | Description | HTTP Status |
|------------|----------------|-------------|-------------|
| `VALIDATION_ERROR` | `ValidationError` | Generic validation error for user input issues | 400 |
| `INVALID_PIPELINE_CONFIG` | `InvalidPipelineConfigError` | Pipeline configuration is malformed or missing required fields | 400 |
| `INVALID_METADATA` | `InvalidMetadataError` | Metadata format is incorrect or incomplete | 400 |
| `INVALID_QUERY` | `InvalidQueryError` | SQL query or YAML is invalid or unsafe | 400 |
| `MISSING_PARAMETER` | `MissingParameterError` | Required parameter is missing from request | 400 |

**Example:**
```json
{
  "error": {
    "code": "INVALID_PIPELINE_CONFIG",
    "message": "Pipeline must have either 'steps' or 'custom_queries'",
    "details": {
      "pipeline_yaml": "..."
    }
  }
}
```

---

### Authentication Errors (401 Unauthorized)

| Error Code | Exception Class | Description | HTTP Status |
|------------|----------------|-------------|-------------|
| `AUTHENTICATION_ERROR` | `AuthenticationError` | Authentication required or failed | 401 |

**Example:**
```json
{
  "error": {
    "code": "AUTHENTICATION_ERROR",
    "message": "Authentication required",
    "details": {}
  }
}
```

---

### Permission Errors (403 Forbidden)

| Error Code | Exception Class | Description | HTTP Status |
|------------|----------------|-------------|-------------|
| `PERMISSION_DENIED` | `PermissionError` | User lacks permission for requested operation | 403 |

**Example:**
```json
{
  "error": {
    "code": "PERMISSION_DENIED",
    "message": "Permission denied: delete_pipeline - Only project owners can delete pipelines",
    "details": {
      "operation": "delete_pipeline"
    }
  }
}
```

---

### Not Found Errors (404 Not Found)

| Error Code | Exception Class | Description | HTTP Status |
|------------|----------------|-------------|-------------|
| `RESOURCE_NOT_FOUND` | `ResourceNotFoundError` | Generic resource not found | 404 |
| `PIPELINE_NOT_FOUND` | `PipelineNotFoundError` | Pipeline with given ID does not exist | 404 |
| `PROJECT_NOT_FOUND` | `ProjectNotFoundError` | Project with given ID does not exist | 404 |
| `TABLE_NOT_FOUND` | `TableNotFoundError` | Database table does not exist | 404 |
| `VALIDATOR_NOT_FOUND` | `ValidatorNotFoundError` | Validator function not registered | 404 |

**Example:**
```json
{
  "error": {
    "code": "PIPELINE_NOT_FOUND",
    "message": "Pipeline not found: run_20231203_143022",
    "details": {
      "resource_type": "Pipeline",
      "resource_id": "run_20231203_143022"
    }
  }
}
```

---

### Data Quality Errors (422 Unprocessable Entity)

| Error Code | Exception Class | Description | HTTP Status |
|------------|----------------|-------------|-------------|
| `DATA_QUALITY_ERROR` | `DataQualityError` | Data quality validation failed | 422 |
| `SCHEMA_MISMATCH` | `SchemaMismatchError` | Source and target schemas don't match | 422 |
| `ROW_COUNT_MISMATCH` | `RowCountMismatchError` | Source and target row counts differ | 422 |

**Example:**
```json
{
  "error": {
    "code": "ROW_COUNT_MISMATCH",
    "message": "Row count mismatch for table 'dim_customer': source=1000, target=985",
    "details": {
      "validation_type": "row_count",
      "table": "dim_customer",
      "source_count": 1000,
      "target_count": 985,
      "difference": 15
    }
  }
}
```

---

### Rate Limiting Errors (429 Too Many Requests)

| Error Code | Exception Class | Description | HTTP Status |
|------------|----------------|-------------|-------------|
| `RATE_LIMIT_EXCEEDED` | `RateLimitError` | API rate limit exceeded | 429 |

**Example:**
```json
{
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "Rate limit exceeded: 100 requests per 60 seconds. Retry after 45 seconds",
    "details": {
      "limit": 100,
      "window": 60,
      "retry_after": 45
    }
  }
}
```

---

### Database Errors (500 Internal Server Error)

| Error Code | Exception Class | Description | HTTP Status |
|------------|----------------|-------------|-------------|
| `DATABASE_ERROR` | `DatabaseError` | Generic database operation error | 500 |
| `CONNECTION_ERROR` | `ConnectionError` | Database connection failed | 500 |
| `QUERY_EXECUTION_ERROR` | `QueryExecutionError` | SQL query execution failed | 500 |
| `TRANSACTION_ERROR` | `TransactionError` | Database transaction failed | 500 |

**Example:**
```json
{
  "error": {
    "code": "CONNECTION_ERROR",
    "message": "Failed to connect to sqlserver: timeout after 30 seconds",
    "details": {
      "database": "sqlserver"
    }
  }
}
```

---

### Pipeline Execution Errors (500 Internal Server Error)

| Error Code | Exception Class | Description | HTTP Status |
|------------|----------------|-------------|-------------|
| `PIPELINE_EXECUTION_ERROR` | `PipelineExecutionError` | Pipeline execution failed | 500 |
| `VALIDATOR_EXECUTION_ERROR` | `ValidatorExecutionError` | Specific validator execution failed | 500 |
| `PARAMETER_MISMATCH` | `ParameterMismatchError` | Validator parameters don't match expected signature | 500 |

**Example:**
```json
{
  "error": {
    "code": "VALIDATOR_EXECUTION_ERROR",
    "message": "Validator 'validate_record_counts' failed: Connection timeout",
    "details": {
      "validator": "validate_record_counts",
      "error": "Connection timeout",
      "config": {
        "sql_table": "dim_customer",
        "snow_table": "DIM_CUSTOMER"
      }
    }
  }
}
```

---

### Configuration Errors (500 Internal Server Error)

| Error Code | Exception Class | Description | HTTP Status |
|------------|----------------|-------------|-------------|
| `CONFIGURATION_ERROR` | `ConfigurationError` | Generic configuration error | 500 |
| `MISSING_CONFIG` | `MissingConfigError` | Required configuration is missing | 500 |
| `INVALID_CONFIG` | `InvalidConfigError` | Configuration value is invalid | 500 |

**Example:**
```json
{
  "error": {
    "code": "MISSING_CONFIG",
    "message": "Missing required configuration: SNOWFLAKE_ACCOUNT (Snowflake connection)",
    "details": {
      "config_key": "SNOWFLAKE_ACCOUNT"
    }
  }
}
```

---

### Timeout Errors (504 Gateway Timeout)

| Error Code | Exception Class | Description | HTTP Status |
|------------|----------------|-------------|-------------|
| `TIMEOUT_ERROR` | `TimeoutError` | Operation exceeded time limit | 504 |

**Example:**
```json
{
  "error": {
    "code": "TIMEOUT_ERROR",
    "message": "Operation timed out after 300 seconds: pipeline_execution",
    "details": {
      "operation": "pipeline_execution",
      "timeout": 300
    }
  }
}
```

---

## Using Custom Exceptions

### In Your Code

```python
from errors import InvalidPipelineConfigError, PipelineNotFoundError

# Raise a validation error
if not pipeline_def.get("steps"):
    raise InvalidPipelineConfigError(
        message="Pipeline must have 'steps' field",
        details={"pipeline": pipeline_def}
    )

# Raise a not found error
if run_id not in pipeline_runs:
    raise PipelineNotFoundError(pipeline_id=run_id)
```

### Error Handlers

Error handlers are automatically registered in `main.py`:

```python
from errors import register_error_handlers

app = FastAPI()
register_error_handlers(app)
```

This registers handlers for:
- `OmbudsmanException` → Returns structured error with proper status code
- `RequestValidationError` → Pydantic validation errors
- `StarletteHTTPException` → Standard HTTP exceptions
- `Exception` → Catch-all for unhandled exceptions

---

## Best Practices

### 1. Use Specific Exceptions

```python
# Good
raise PipelineNotFoundError(pipeline_id=run_id)

# Bad
raise HTTPException(status_code=404, detail="Pipeline not found")
```

### 2. Include Helpful Details

```python
raise ValidatorExecutionError(
    validator_name="validate_record_counts",
    error_message=str(e),
    step_config={
        "sql_table": "dim_customer",
        "snow_table": "DIM_CUSTOMER"
    }
)
```

### 3. Re-raise Custom Exceptions

```python
try:
    # operation
except PipelineNotFoundError:
    raise  # Re-raise custom exceptions as-is
except Exception as e:
    raise PipelineExecutionError(...)  # Wrap unexpected errors
```

### 4. Don't Leak Internal Details

```python
# Good (in production)
raise DatabaseError(
    message="Database query failed",
    details={"query": query[:100]}  # Truncate
)

# Bad (leaks internals)
raise Exception(f"Failed: {full_stack_trace}")
```

---

## Testing Error Responses

### Using curl

```bash
# Test pipeline not found
curl http://localhost:8000/pipelines/status/invalid_id

# Response:
{
  "error": {
    "code": "PIPELINE_NOT_FOUND",
    "message": "Pipeline not found: invalid_id",
    "details": {
      "resource_type": "Pipeline",
      "resource_id": "invalid_id"
    }
  }
}
```

### Using Python requests

```python
import requests

response = requests.post(
    "http://localhost:8000/pipelines/execute",
    json={"pipeline_yaml": "invalid yaml {{{"}
)

print(response.status_code)  # 400
print(response.json())
# {
#   "error": {
#     "code": "INVALID_QUERY",
#     "message": "Invalid YAML syntax: ...",
#     "details": {"query": "invalid yaml {{{"}
#   }
# }
```

---

## Error Code Quick Reference

| HTTP | Error Code | Common Cause |
|------|-----------|--------------|
| 400 | `VALIDATION_ERROR` | Bad request data |
| 400 | `INVALID_PIPELINE_CONFIG` | Malformed pipeline YAML |
| 400 | `INVALID_QUERY` | Invalid SQL or YAML syntax |
| 400 | `MISSING_PARAMETER` | Required parameter missing |
| 401 | `AUTHENTICATION_ERROR` | Not authenticated |
| 403 | `PERMISSION_DENIED` | Not authorized |
| 404 | `PIPELINE_NOT_FOUND` | Pipeline doesn't exist |
| 404 | `PROJECT_NOT_FOUND` | Project doesn't exist |
| 404 | `VALIDATOR_NOT_FOUND` | Validator not registered |
| 422 | `SCHEMA_MISMATCH` | Source/target schemas differ |
| 422 | `ROW_COUNT_MISMATCH` | Source/target counts differ |
| 429 | `RATE_LIMIT_EXCEEDED` | Too many requests |
| 500 | `DATABASE_ERROR` | Database operation failed |
| 500 | `PIPELINE_EXECUTION_ERROR` | Pipeline failed |
| 500 | `CONFIGURATION_ERROR` | Invalid configuration |
| 504 | `TIMEOUT_ERROR` | Operation timed out |
