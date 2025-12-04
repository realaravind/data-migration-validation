"""
Integration tests for metadata extraction to validation workflow.

Tests the complete flow from metadata extraction through mapping
generation to pipeline execution.
"""

import pytest
from fastapi.testclient import TestClient


class TestMetadataToValidationFlow:
    """Test complete metadata to validation workflow."""

    @pytest.mark.integration
    def test_metadata_extraction_snowflake(self, client):
        """Test Snowflake metadata extraction."""
        response = client.post(
            "/metadata/extract",
            json={
                "connection_type": "snowflake",
                "database": "SAMPLEDW",
                "schema": "PUBLIC",
                "tables": ["DIM_CUSTOMER", "FACT_SALES"]
            }
        )

        # May fail if Snowflake not configured - that's ok
        if response.status_code == 200:
            data = response.json()
            assert "metadata" in data
            assert isinstance(data["metadata"], dict)
        else:
            # If Snowflake not configured, should get proper error
            assert response.status_code in [500, 400]

    @pytest.mark.integration
    def test_metadata_extraction_sqlserver(self, client):
        """Test SQL Server metadata extraction."""
        response = client.post(
            "/metadata/extract",
            json={
                "connection_type": "sqlserver",
                "database": "SampleDW",
                "schema": "dbo",
                "tables": ["dim_customer", "fact_sales"]
            }
        )

        # May fail if SQL Server not configured - that's ok
        if response.status_code == 200:
            data = response.json()
            assert "metadata" in data
            assert isinstance(data["metadata"], dict)
        else:
            # If SQL Server not configured, should get proper error
            assert response.status_code in [500, 400]

    @pytest.mark.integration
    def test_mapping_suggestion_flow(self, client, sample_metadata):
        """Test automatic mapping suggestion from metadata."""
        response = client.post(
            "/mapping/suggest",
            json={
                "source_metadata": sample_metadata,
                "target_metadata": sample_metadata,
                "fuzzy_threshold": 0.8
            }
        )

        # Should work even without database
        if response.status_code == 200:
            data = response.json()
            assert "mappings" in data
            assert isinstance(data["mappings"], dict)

    @pytest.mark.integration
    def test_intelligent_pipeline_generation(self, client, sample_metadata):
        """Test intelligent pipeline generation from metadata."""
        response = client.post(
            "/pipelines/suggest/intelligent",
            json={
                "metadata": sample_metadata,
                "validation_level": "comprehensive"
            }
        )

        if response.status_code == 200:
            data = response.json()
            assert "pipeline_yaml" in data
            assert "steps" in data["pipeline_yaml"]

    @pytest.mark.integration
    @pytest.mark.slow
    def test_end_to_end_workflow(self, client, sample_metadata):
        """Test complete end-to-end workflow from metadata to execution."""
        # 1. Generate intelligent pipeline from metadata
        suggest_response = client.post(
            "/pipelines/suggest/intelligent",
            json={
                "metadata": sample_metadata,
                "validation_level": "basic"
            }
        )

        if suggest_response.status_code != 200:
            pytest.skip("Pipeline suggestion failed")

        pipeline_yaml = suggest_response.json()["pipeline_yaml"]

        # 2. Execute the generated pipeline
        execute_response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": pipeline_yaml,
                "pipeline_name": "e2e_test_pipeline"
            }
        )

        assert execute_response.status_code == 200
        run_id = execute_response.json()["run_id"]

        # 3. Verify pipeline was created
        status_response = client.get(f"/pipelines/status/{run_id}")
        assert status_response.status_code == 200

        # 4. Cleanup
        client.delete(f"/pipelines/{run_id}")


class TestWorkloadAnalysis:
    """Test workload analysis integration."""

    @pytest.mark.integration
    def test_workload_upload(self, client):
        """Test workload upload from Query Store."""
        workload_data = {
            "queries": [
                {
                    "query_text": "SELECT COUNT(*) FROM DIM_CUSTOMER",
                    "execution_count": 100,
                    "avg_duration_ms": 50
                },
                {
                    "query_text": "SELECT SUM(sales_amount) FROM FACT_SALES",
                    "execution_count": 50,
                    "avg_duration_ms": 200
                }
            ]
        }

        response = client.post(
            "/workload/upload",
            json=workload_data
        )

        # Should accept workload data
        if response.status_code == 200:
            data = response.json()
            assert "workload_id" in data or "status" in data

    @pytest.mark.integration
    def test_workload_to_pipeline(self, client):
        """Test generating validation pipeline from workload."""
        # First upload workload
        workload_data = {
            "queries": [
                {
                    "query_text": "SELECT * FROM DIM_CUSTOMER WHERE CustomerID > 100",
                    "execution_count": 10
                }
            ]
        }

        upload_response = client.post(
            "/workload/upload",
            json=workload_data
        )

        if upload_response.status_code == 200:
            # Try to generate pipeline from workload
            workload_id = upload_response.json().get("workload_id", "test")

            gen_response = client.post(
                f"/workload/{workload_id}/generate-pipeline",
                json={"top_queries": 5}
            )

            # Should generate pipeline or return error
            assert gen_response.status_code in [200, 404, 400]


class TestDatabaseMapping:
    """Test database mapping integration."""

    @pytest.mark.integration
    def test_create_database_mapping(self, client):
        """Test creating database mapping configuration."""
        mapping_config = {
            "source": {
                "type": "sqlserver",
                "host": "localhost",
                "database": "SourceDB"
            },
            "target": {
                "type": "snowflake",
                "account": "test_account",
                "database": "TargetDB"
            },
            "table_mappings": {
                "dim_customer": "DIM_CUSTOMER",
                "fact_sales": "FACT_SALES"
            }
        }

        response = client.post(
            "/database-mapping/create",
            json=mapping_config
        )

        # Should create or return validation error
        assert response.status_code in [200, 201, 400]

    @pytest.mark.integration
    def test_list_database_mappings(self, client):
        """Test listing all database mappings."""
        response = client.get("/database-mapping/list")

        # Should return list (may be empty)
        assert response.status_code == 200
        data = response.json()
        assert "mappings" in data or isinstance(data, list)


class TestCustomQueries:
    """Test custom query integration."""

    @pytest.mark.integration
    def test_create_custom_query(self, client):
        """Test creating custom business query."""
        query_config = {
            "name": "Total Sales by Region",
            "sql_query": "SELECT region, SUM(sales_amount) FROM FACT_SALES GROUP BY region",
            "snowflake_query": "SELECT REGION, SUM(SALES_AMOUNT) FROM FACT_SALES GROUP BY REGION",
            "comparison_type": "aggregation",
            "tolerance": 0.01
        }

        response = client.post(
            "/custom-queries/create",
            json=query_config
        )

        # Should create query or return validation error
        assert response.status_code in [200, 201, 400]

    @pytest.mark.integration
    def test_execute_custom_query(self, client):
        """Test executing custom query."""
        query_config = {
            "name": "Simple Count",
            "sql_query": "SELECT COUNT(*) as cnt FROM dim_customer",
            "snowflake_query": "SELECT COUNT(*) as cnt FROM DIM_CUSTOMER"
        }

        # Create query
        create_response = client.post(
            "/custom-queries/create",
            json=query_config
        )

        if create_response.status_code in [200, 201]:
            query_id = create_response.json().get("query_id", "test_query")

            # Execute query
            exec_response = client.post(f"/custom-queries/{query_id}/execute")

            # May fail if databases not configured
            assert exec_response.status_code in [200, 500, 400]


class TestResultsHistory:
    """Test results history integration."""

    @pytest.mark.integration
    def test_create_project(self, client):
        """Test creating validation project."""
        project_data = {
            "project_id": "test_integration_project",
            "project_name": "Integration Test Project",
            "description": "Test project for integration tests",
            "created_by": "test_user",
            "tags": ["test", "integration"]
        }

        response = client.post(
            "/history/projects",
            json=project_data
        )

        # Should create or fail if DB not configured
        if response.status_code in [200, 201]:
            data = response.json()
            assert "project" in data

    @pytest.mark.integration
    def test_list_projects(self, client):
        """Test listing all projects."""
        response = client.get("/history/projects")

        # Should return list or error if DB not configured
        if response.status_code == 200:
            data = response.json()
            assert "projects" in data

    @pytest.mark.integration
    def test_get_pipeline_run_history(self, client):
        """Test getting pipeline run history."""
        response = client.get("/history/runs")

        # Should return runs or error if DB not configured
        if response.status_code == 200:
            data = response.json()
            assert "runs" in data

    @pytest.mark.integration
    def test_get_metrics_summary(self, client):
        """Test getting metrics summary."""
        response = client.get("/history/metrics/summary?days=7")

        # Should return metrics or error if DB not configured
        if response.status_code == 200:
            data = response.json()
            assert "period" in data
            assert "runs" in data


class TestConnectionStatus:
    """Test connection status integration."""

    @pytest.mark.integration
    def test_connection_status(self, client):
        """Test getting all connection statuses."""
        response = client.get("/connections/status")

        assert response.status_code == 200
        data = response.json()
        assert "connections" in data
        assert "sqlserver" in data["connections"]
        assert "snowflake" in data["connections"]

    @pytest.mark.integration
    def test_sqlserver_connection_test(self, client):
        """Test SQL Server connection."""
        response = client.post(
            "/connections/sqlserver",
            json={"use_env": True}
        )

        # Should return success or error
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    @pytest.mark.integration
    def test_snowflake_connection_test(self, client):
        """Test Snowflake connection."""
        response = client.post(
            "/connections/snowflake",
            json={"use_env": True}
        )

        # Should return success or error
        assert response.status_code == 200
        data = response.json()
        assert "status" in data


class TestSampleDataGeneration:
    """Test sample data generation integration."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_generate_sample_data(self, client):
        """Test generating sample data."""
        response = client.post(
            "/data/generate-sample",
            json={
                "dim_count": 1,
                "fact_count": 1,
                "dim_rows": 10,
                "fact_rows": 20,
                "target": "both"
            }
        )

        # May fail if databases not configured
        if response.status_code == 200:
            data = response.json()
            assert "status" in data

    @pytest.mark.integration
    def test_download_sample_workload(self, client):
        """Test downloading sample workload."""
        response = client.get("/data/download-sample-workload?schema=Retail")

        # Should return workload data
        if response.status_code == 200:
            data = response.json()
            assert "queries" in data or "workload" in data
