# Ombudsman Validation Studio - Test Suite

This directory contains all tests for the Ombudsman Validation Studio backend API.

## Test Structure

```
tests/
├── unit/                           # Unit tests (fast, no external dependencies)
│   ├── test_exceptions.py         # Custom exception hierarchy tests
│   └── test_error_handlers.py     # Error handler middleware tests
├── integration/                    # Integration tests (slower, may need database)
│   └── test_pipeline_execution.py # Pipeline execution API tests
├── conftest.py                    # Shared fixtures and configuration
└── README.md                      # This file
```

## Running Tests

### Install Dependencies

```bash
pip install -r requirements.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# Slow tests
pytest -m slow
```

### Run Specific Test Files

```bash
# Test exceptions
pytest tests/unit/test_exceptions.py

# Test error handlers
pytest tests/unit/test_error_handlers.py

# Test pipeline execution
pytest tests/integration/test_pipeline_execution.py
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/unit/test_exceptions.py::TestValidationErrors

# Run a specific test function
pytest tests/unit/test_exceptions.py::TestValidationErrors::test_validation_error
```

### Run with Coverage Report

```bash
# Terminal coverage report
pytest --cov=. --cov-report=term-missing

# HTML coverage report (opens in browser)
pytest --cov=. --cov-report=html
open htmlcov/index.html
```

### Run with Verbose Output

```bash
pytest -v
```

### Run Tests in Parallel (faster)

```bash
pip install pytest-xdist
pytest -n auto
```

## Test Coverage

Current coverage targets:
- **Minimum:** 50% (enforced by pytest.ini)
- **Target:** 70%
- **Ideal:** 85%+

Check coverage with:
```bash
pytest --cov=. --cov-report=term-missing
```

## Writing Tests

### Unit Tests

Unit tests should:
- Be fast (< 1 second each)
- Have no external dependencies (databases, APIs, etc.)
- Test a single function or class in isolation
- Use mocks for dependencies

Example:
```python
@pytest.mark.unit
def test_exception_creation():
    exc = PipelineNotFoundError("run_123")
    assert exc.status_code == 404
    assert "run_123" in exc.message
```

### Integration Tests

Integration tests should:
- Test multiple components working together
- May use databases or external services
- Test API endpoints end-to-end
- Be marked with `@pytest.mark.integration`

Example:
```python
@pytest.mark.integration
def test_pipeline_execution(client):
    response = client.post("/pipelines/execute", json={...})
    assert response.status_code == 200
```

### Using Fixtures

Fixtures are defined in `conftest.py` and available to all tests:

```python
def test_with_client(client):
    """client fixture is automatically injected"""
    response = client.get("/health")
    assert response.status_code == 200

def test_with_sample_data(sample_pipeline_yaml):
    """sample_pipeline_yaml fixture provides test data"""
    assert "pipeline:" in sample_pipeline_yaml
```

## Common Test Patterns

### Testing API Endpoints

```python
def test_endpoint(client):
    response = client.post("/api/endpoint", json={"key": "value"})
    assert response.status_code == 200
    data = response.json()
    assert data["expected_field"] == "expected_value"
```

### Testing Exceptions

```python
def test_exception():
    exc = CustomException("message", details={"key": "value"})
    assert exc.message == "message"
    assert exc.details["key"] == "value"

    result = exc.to_dict()
    assert result["error"]["code"] == "EXPECTED_CODE"
```

### Testing Error Handlers

```python
def test_error_handler(client):
    response = client.get("/endpoint/that/raises/error")
    assert response.status_code == 400
    data = response.json()
    assert "error" in data
    assert data["error"]["code"] == "ERROR_CODE"
```

## Debugging Tests

### Run with print statements

```bash
pytest -s
```

### Run with debugger (pdb)

```python
def test_something():
    import pdb; pdb.set_trace()
    # Test code here
```

### Show local variables on failure

```bash
pytest -l
```

### Stop at first failure

```bash
pytest -x
```

## Continuous Integration

Tests are run automatically on:
- Every commit
- Every pull request
- Before deployment

CI requirements:
- All tests must pass
- Coverage must be ≥ 50%
- No test should take > 30 seconds

## Test Markers

Available markers (defined in pytest.ini):
- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.slow` - Slow tests (> 5 seconds)
- `@pytest.mark.asyncio` - Async tests

## Troubleshooting

### Import Errors

If you get import errors, make sure you're running pytest from the `backend/` directory:
```bash
cd ombudsman-validation-studio/backend
pytest
```

### Database Connection Errors

Integration tests may require database connections. Make sure:
1. Environment variables are set (`.env` file)
2. Database is running
3. Or skip integration tests: `pytest -m "not integration"`

### Async Test Errors

Make sure `pytest-asyncio` is installed:
```bash
pip install pytest-asyncio
```

## Best Practices

1. **Keep tests simple** - One assertion per test when possible
2. **Use descriptive names** - `test_pipeline_execution_fails_with_invalid_yaml`
3. **Arrange-Act-Assert** - Setup, execute, verify pattern
4. **Don't test implementation details** - Test behavior, not internals
5. **Use fixtures** - Reuse setup code with fixtures
6. **Clean up after tests** - Delete created resources
7. **Mock external services** - Don't depend on external APIs
8. **Test edge cases** - Empty inputs, null values, large data
9. **Test error conditions** - Not just happy paths
10. **Keep tests fast** - Unit tests should be < 1 second

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Coverage.py](https://coverage.readthedocs.io/)
