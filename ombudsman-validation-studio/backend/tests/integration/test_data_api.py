"""
Tests for Sample Data Generation API endpoints

Tests data generation functionality including:
- Sample data generation for SQL Server/Snowflake
- Generation status monitoring
- Schema listing
- Data clearing
- Sample workload download
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json


class TestSampleDataGeneration:
    """Tests for POST /data/generate"""

    def test_generate_sample_data_success(self, client):
        """Should start sample data generation"""
        response = client.post(
            "/data/generate",
            json={
                "num_dimensions": 3,
                "num_facts": 2,
                "rows_per_dim": 50,
                "rows_per_fact": 200,
                "broken_fk_rate": 0.05,
                "target": "both",
                "seed": 12345
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["status"] == "pending"
        assert "message" in data

    def test_generate_sqlserver_only(self, client):
        """Should generate data for SQL Server only"""
        response = client.post(
            "/data/generate",
            json={
                "num_dimensions": 2,
                "num_facts": 1,
                "rows_per_dim": 100,
                "rows_per_fact": 500,
                "target": "sqlserver",
                "seed": 42
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "sqlserver" in data["job_id"]

    def test_generate_snowflake_only(self, client):
        """Should generate data for Snowflake only"""
        response = client.post(
            "/data/generate",
            json={
                "num_dimensions": 2,
                "num_facts": 1,
                "rows_per_dim": 100,
                "rows_per_fact": 500,
                "target": "snowflake",
                "seed": 42
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "snowflake" in data["job_id"]

    def test_generate_with_defaults(self, client):
        """Should use default values"""
        response = client.post(
            "/data/generate",
            json={}
        )

        assert response.status_code == 200


class TestGenerationStatus:
    """Tests for GET /data/status/{job_id}"""

    def test_get_status_success(self, client):
        """Should return generation status"""
        # First start a generation
        gen_response = client.post(
            "/data/generate",
            json={"target": "sqlserver", "seed": 999}
        )
        job_id = gen_response.json()["job_id"]

        # Then check status
        response = client.get(f"/data/status/{job_id}")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "job_id" in data

    def test_get_status_not_found(self, client):
        """Should return 404 for non-existent job"""
        response = client.get("/data/status/nonexistent_job")

        assert response.status_code == 404


class TestSchemaListing:
    """Tests for GET /data/schemas"""

    def test_list_schemas(self, client):
        """Should list available schemas"""
        response = client.get("/data/schemas")

        assert response.status_code == 200
        data = response.json()
        assert "schemas" in data
        assert len(data["schemas"]) == 3  # Retail, Finance, Healthcare

        # Check schema structure
        for schema in data["schemas"]:
            assert "name" in schema
            assert "description" in schema
            assert "dimensions" in schema
            assert "facts" in schema

    def test_list_schemas_contains_retail(self, client):
        """Should contain Retail schema"""
        response = client.get("/data/schemas")
        data = response.json()

        schema_names = [s["name"] for s in data["schemas"]]
        assert "Retail" in schema_names

    def test_list_schemas_contains_finance(self, client):
        """Should contain Finance schema"""
        response = client.get("/data/schemas")
        data = response.json()

        schema_names = [s["name"] for s in data["schemas"]]
        assert "Finance" in schema_names

    def test_list_schemas_contains_healthcare(self, client):
        """Should contain Healthcare schema"""
        response = client.get("/data/schemas")
        data = response.json()

        schema_names = [s["name"] for s in data["schemas"]]
        assert "Healthcare" in schema_names


class TestClearSampleData:
    """Tests for DELETE /data/clear"""

    def test_clear_sample_data_success(self, client, mock_db_connection):
        """Should clear sample data tables"""
        mock_db_connection.return_value.cursor.return_value.fetchall.return_value = [
            ("dim_customer",),
            ("dim_product",),
            ("fact_sales",)
        ]

        response = client.delete("/data/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "tables_dropped" in data

    def test_clear_sample_data_no_tables(self, client, mock_db_connection):
        """Should handle no tables to clear"""
        mock_db_connection.return_value.cursor.return_value.fetchall.return_value = []

        response = client.delete("/data/clear")

        assert response.status_code == 200
        data = response.json()
        assert data["tables_dropped"] == []

    def test_clear_sample_data_connection_error(self, client, mock_db_connection):
        """Should handle connection errors"""
        import pyodbc
        mock_db_connection.side_effect = pyodbc.Error("Connection failed")

        response = client.delete("/data/clear")

        assert response.status_code == 500


class TestSampleWorkloadDownload:
    """Tests for GET /data/download-sample-workload"""

    def test_download_retail_workload(self, client, mock_workload_gen):
        """Should download Retail sample workload"""
        mock_workload_gen.return_value.generate_workload.return_value = [
            {"query_id": 1, "query_text": "SELECT * FROM dim_customer"}
        ]

        response = client.get("/data/download-sample-workload?schema=Retail")

        assert response.status_code == 200
        assert response.headers.get("content-disposition", "").contains("retail")

    def test_download_finance_workload(self, client, mock_workload_gen):
        """Should download Finance sample workload"""
        mock_workload_gen.return_value.generate_workload.return_value = [
            {"query_id": 1, "query_text": "SELECT * FROM dim_account"}
        ]

        response = client.get("/data/download-sample-workload?schema=Finance")

        assert response.status_code == 200

    def test_download_healthcare_workload(self, client, mock_workload_gen):
        """Should download Healthcare sample workload"""
        mock_workload_gen.return_value.generate_workload.return_value = [
            {"query_id": 1, "query_text": "SELECT * FROM dim_patient"}
        ]

        response = client.get("/data/download-sample-workload?schema=Healthcare")

        assert response.status_code == 200

    def test_download_invalid_schema(self, client):
        """Should reject invalid schema"""
        response = client.get("/data/download-sample-workload?schema=Invalid")

        assert response.status_code == 400
        assert "Invalid schema" in response.json()["detail"]

    def test_download_default_schema(self, client, mock_workload_gen):
        """Should use Retail as default schema"""
        mock_workload_gen.return_value.generate_workload.return_value = []

        response = client.get("/data/download-sample-workload")

        assert response.status_code == 200


class TestGenerationProgress:
    """Tests for generation progress tracking"""

    def test_progress_updates_during_generation(self, client):
        """Should track progress during generation"""
        # Start generation
        gen_response = client.post(
            "/data/generate",
            json={"target": "sqlserver", "seed": 111}
        )
        job_id = gen_response.json()["job_id"]

        # Immediately check status (should be pending or running)
        status_response = client.get(f"/data/status/{job_id}")

        assert status_response.status_code == 200
        data = status_response.json()
        assert data["status"] in ["pending", "running", "completed", "failed"]


class TestGenerationConfiguration:
    """Tests for generation configuration validation"""

    def test_max_dimensions(self, client):
        """Should handle maximum dimensions"""
        response = client.post(
            "/data/generate",
            json={
                "num_dimensions": 10,
                "num_facts": 1,
                "rows_per_dim": 10,
                "rows_per_fact": 10,
                "target": "sqlserver"
            }
        )

        assert response.status_code == 200

    def test_max_facts(self, client):
        """Should handle maximum facts"""
        response = client.post(
            "/data/generate",
            json={
                "num_dimensions": 1,
                "num_facts": 10,
                "rows_per_dim": 10,
                "rows_per_fact": 10,
                "target": "sqlserver"
            }
        )

        assert response.status_code == 200

    def test_large_row_counts(self, client):
        """Should handle large row counts"""
        response = client.post(
            "/data/generate",
            json={
                "num_dimensions": 1,
                "num_facts": 1,
                "rows_per_dim": 100000,
                "rows_per_fact": 1000000,
                "target": "sqlserver"
            }
        )

        assert response.status_code == 200

    def test_broken_fk_rate_zero(self, client):
        """Should handle zero broken FK rate"""
        response = client.post(
            "/data/generate",
            json={
                "broken_fk_rate": 0.0,
                "target": "sqlserver"
            }
        )

        assert response.status_code == 200

    def test_broken_fk_rate_high(self, client):
        """Should handle high broken FK rate"""
        response = client.post(
            "/data/generate",
            json={
                "broken_fk_rate": 0.5,
                "target": "sqlserver"
            }
        )

        assert response.status_code == 200


# Fixtures
@pytest.fixture
def mock_db_connection():
    """Mock database connection"""
    with patch('pyodbc.connect') as mock:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_conn.cursor.return_value = mock_cursor
        mock.return_value = mock_conn
        yield mock


@pytest.fixture
def mock_workload_gen():
    """Mock workload generator"""
    with patch('data.generate.workload_gen') as mock:
        yield mock
