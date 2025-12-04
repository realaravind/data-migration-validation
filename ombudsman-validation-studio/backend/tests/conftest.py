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
