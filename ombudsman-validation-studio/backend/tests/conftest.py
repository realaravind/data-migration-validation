"""
Pytest configuration and shared fixtures.
"""

import pytest
import sys
import os
from pathlib import Path

# Add backend directory to path
backend_dir = Path(__file__).parent.parent
sys.path.insert(0, str(backend_dir))


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    try:
        from fastapi.testclient import TestClient
        from main import app
        return TestClient(app)
    except ImportError as e:
        pytest.skip(f"Cannot import app dependencies: {e}")


@pytest.fixture
def sample_pipeline_yaml():
    """Sample valid pipeline YAML for testing."""
    return """
pipeline:
  name: Test Pipeline
  metadata:
    dim_customer:
      CustomerID: INT
      CustomerName: VARCHAR
      Email: VARCHAR
  mapping:
    dim_customer: DIM_CUSTOMER
  steps:
    - name: validate_record_counts
      config:
        sql_table: dim_customer
        snow_table: DIM_CUSTOMER
"""


@pytest.fixture
def invalid_pipeline_yaml():
    """Invalid pipeline YAML (missing steps)."""
    return """
pipeline:
  name: Invalid Pipeline
  metadata: {}
  mapping: {}
"""


@pytest.fixture
def sample_metadata():
    """Sample table metadata."""
    return {
        "dim_customer": {
            "CustomerID": "INT",
            "CustomerName": "VARCHAR(100)",
            "Email": "VARCHAR(255)",
            "CreatedDate": "DATETIME"
        },
        "fact_sales": {
            "SaleID": "INT",
            "CustomerID": "INT",
            "Amount": "DECIMAL(10,2)",
            "SaleDate": "DATE"
        }
    }


@pytest.fixture
def sample_run_id():
    """Sample pipeline run ID."""
    return "run_20231203_120000"


@pytest.fixture
def mock_auth_user():
    """Mock authenticated user for protected endpoints."""
    from unittest.mock import patch, MagicMock

    with patch('auth.dependencies.require_user_or_admin') as mock:
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock_user.email = "test@example.com"
        mock_user.role = "admin"
        mock.return_value = mock_user
        yield mock_user


@pytest.fixture
def mock_optional_auth():
    """Mock optional authentication."""
    from unittest.mock import patch, MagicMock

    with patch('auth.dependencies.optional_authentication') as mock:
        mock_user = MagicMock()
        mock_user.username = "testuser"
        mock.return_value = mock_user
        yield mock_user


@pytest.fixture
def temp_project_dir(tmp_path):
    """Create temporary project directory structure."""
    project_dir = tmp_path / "test_project"
    project_dir.mkdir()
    config_dir = project_dir / "config"
    config_dir.mkdir()
    pipelines_dir = project_dir / "pipelines"
    pipelines_dir.mkdir()

    # Create minimal project.json
    import json
    with open(project_dir / "project.json", "w") as f:
        json.dump({
            "name": "Test Project",
            "description": "Test project for unit tests",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "sql_database": "TestDB",
            "sql_schemas": ["dbo"],
            "snowflake_database": "TESTDB",
            "snowflake_schemas": ["PUBLIC"],
            "schema_mappings": {"dbo": "PUBLIC"},
            "project_id": "test_project"
        }, f)

    return project_dir


@pytest.fixture
def sample_validation_result():
    """Sample validation result data."""
    return {
        "run_id": "run_20240101_120000",
        "pipeline_name": "test_pipeline",
        "status": "completed",
        "started_at": "2024-01-01T12:00:00",
        "completed_at": "2024-01-01T12:01:00",
        "duration_ms": 60000,
        "steps": [
            {
                "name": "row_count_validation",
                "status": "passed",
                "sql_result": 1000,
                "snow_result": 1000,
                "match": True
            },
            {
                "name": "null_check",
                "status": "failed",
                "sql_result": 0,
                "snow_result": 5,
                "match": False,
                "error": "Null values found in Snowflake"
            }
        ],
        "summary": {
            "total_steps": 2,
            "passed": 1,
            "failed": 1,
            "pass_rate": 50.0
        }
    }


@pytest.fixture
def sample_batch_job_data():
    """Sample batch job data."""
    return {
        "job_id": "batch_test_123",
        "job_name": "Test Batch Job",
        "job_type": "bulk_pipeline_execution",
        "status": "queued",
        "created_at": "2024-01-01T00:00:00",
        "pipelines": [
            {"pipeline_id": "dim_customer_validation"},
            {"pipeline_id": "fact_sales_validation"}
        ],
        "parallel_execution": True,
        "max_parallel": 3
    }


@pytest.fixture
def sample_workload_data():
    """Sample workload data."""
    return {
        "workload_id": "wl_test_123",
        "project_id": "test_project",
        "upload_date": "2024-01-01T00:00:00",
        "query_count": 10,
        "total_executions": 1000,
        "queries": [
            {
                "query_id": 1,
                "query_text": "SELECT * FROM dim_customer WHERE customer_id = @p1",
                "execution_count": 500,
                "avg_duration_ms": 50
            },
            {
                "query_id": 2,
                "query_text": "SELECT SUM(amount) FROM fact_sales GROUP BY product_id",
                "execution_count": 300,
                "avg_duration_ms": 200
            }
        ],
        "table_usage": {
            "dim_customer": 500,
            "fact_sales": 300
        }
    }


@pytest.fixture
def mock_db_connections():
    """Mock database connections for testing."""
    from unittest.mock import patch, MagicMock

    sql_conn = MagicMock()
    snow_conn = MagicMock()

    with patch('pyodbc.connect', return_value=sql_conn) as sql_mock, \
         patch('snowflake.connector.connect', return_value=snow_conn) as snow_mock:
        yield {
            "sql": sql_conn,
            "snowflake": snow_conn,
            "sql_mock": sql_mock,
            "snow_mock": snow_mock
        }


@pytest.fixture(autouse=True)
def setup_test_environment(monkeypatch, tmp_path):
    """Set up test environment variables."""
    # Set data directory to temp path for isolation
    monkeypatch.setenv("DATA_DIR", str(tmp_path / "data"))
    monkeypatch.setenv("PROJECTS_DIR", str(tmp_path / "projects"))
    monkeypatch.setenv("RESULTS_DIR", str(tmp_path / "results"))

    # Create directories
    (tmp_path / "data").mkdir(exist_ok=True)
    (tmp_path / "projects").mkdir(exist_ok=True)
    (tmp_path / "results").mkdir(exist_ok=True)

    # Mock database credentials
    monkeypatch.setenv("MSSQL_HOST", "localhost")
    monkeypatch.setenv("MSSQL_PORT", "1433")
    monkeypatch.setenv("MSSQL_USER", "testuser")
    monkeypatch.setenv("MSSQL_PASSWORD", "testpass")
    monkeypatch.setenv("MSSQL_DATABASE", "testdb")

    monkeypatch.setenv("SNOWFLAKE_USER", "testuser")
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "testpass")
    monkeypatch.setenv("SNOWFLAKE_ACCOUNT", "testaccount")
    monkeypatch.setenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    monkeypatch.setenv("SNOWFLAKE_DATABASE", "TESTDB")
    monkeypatch.setenv("SNOWFLAKE_SCHEMA", "PUBLIC")
