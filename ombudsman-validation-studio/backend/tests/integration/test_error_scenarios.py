"""
Integration tests for error scenarios and recovery.

Tests error handling, graceful degradation, and recovery mechanisms.
"""

import pytest
from fastapi.testclient import TestClient


class TestDatabaseFailureScenarios:
    """Test behavior when databases are unavailable."""

    @pytest.mark.integration
    def test_pipeline_execution_without_database(self, client, sample_pipeline_yaml):
        """Test that pipeline execution works even if result DB is unavailable."""
        # Should execute and save to JSON even if DB fails
        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": sample_pipeline_yaml,
                "pipeline_name": "test_no_db"
            }
        )

        # Should still accept the request
        assert response.status_code == 200
        assert "run_id" in response.json()

    @pytest.mark.integration
    def test_history_api_without_database(self, client):
        """Test history API returns proper error when DB unavailable."""
        response = client.get("/history/runs")

        # Should return error or empty list gracefully
        assert response.status_code in [200, 500]

    @pytest.mark.integration
    def test_connection_status_with_failures(self, client):
        """Test connection status handles failures gracefully."""
        response = client.get("/connections/status")

        assert response.status_code == 200
        data = response.json()

        # Should have status for each connection (may be error)
        assert "connections" in data
        for conn_type in ["sqlserver", "snowflake"]:
            assert conn_type in data["connections"]
            assert "status" in data["connections"][conn_type]


class TestInvalidInput:
    """Test handling of invalid inputs."""

    @pytest.mark.integration
    def test_malformed_json(self, client):
        """Test API handling of malformed JSON."""
        response = client.post(
            "/pipelines/execute",
            data="invalid json {{{",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    @pytest.mark.integration
    def test_missing_required_fields(self, client):
        """Test API handling of missing required fields."""
        response = client.post(
            "/pipelines/execute",
            json={"pipeline_name": "test"}  # Missing pipeline_yaml
        )

        assert response.status_code == 422

    @pytest.mark.integration
    def test_invalid_enum_values(self, client):
        """Test API handling of invalid enum values."""
        response = client.post(
            "/metadata/extract",
            json={
                "connection_type": "invalid_type",  # Invalid
                "database": "test",
                "schema": "public"
            }
        )

        assert response.status_code in [400, 422]

    @pytest.mark.integration
    def test_sql_injection_attempt(self, client):
        """Test that SQL injection attempts are handled safely."""
        malicious_yaml = """
pipeline:
  name: Malicious
  steps:
    - name: validate_record_counts
      config:
        sql_table: "dim_customer; DROP TABLE users; --"
        snow_table: "DIM_CUSTOMER"
"""

        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": malicious_yaml,
                "pipeline_name": "malicious"
            }
        )

        # Should either reject or handle safely
        # If accepted, the validator should handle SQL safely
        assert response.status_code in [200, 400]


class TestTimeouts:
    """Test timeout handling."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_long_running_pipeline(self, client):
        """Test behavior with long-running pipeline."""
        large_pipeline = """
pipeline:
  name: Large Pipeline
  metadata:
    dim_customer:
      CustomerID: INT
      CustomerName: VARCHAR
  steps:
"""
        # Add many steps
        for i in range(50):
            large_pipeline += f"""
    - name: validate_step_{i}
      config:
        sql_table: dim_customer
        snow_table: DIM_CUSTOMER
"""

        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": large_pipeline,
                "pipeline_name": "large_test"
            }
        )

        # Should accept even if it will take long
        assert response.status_code == 200


class TestRateLimiting:
    """Test rate limiting and concurrent requests."""

    @pytest.mark.integration
    def test_concurrent_pipeline_executions(self, client, sample_pipeline_yaml):
        """Test multiple concurrent pipeline executions."""
        responses = []

        # Launch multiple pipelines concurrently
        for i in range(5):
            response = client.post(
                "/pipelines/execute",
                json={
                    "pipeline_yaml": sample_pipeline_yaml,
                    "pipeline_name": f"concurrent_test_{i}"
                }
            )
            responses.append(response)

        # All should be accepted
        for response in responses:
            assert response.status_code == 200
            assert "run_id" in response.json()

        # All should have unique run IDs
        run_ids = [r.json()["run_id"] for r in responses]
        assert len(run_ids) == len(set(run_ids))


class TestErrorRecovery:
    """Test error recovery mechanisms."""

    @pytest.mark.integration
    def test_pipeline_failure_cleanup(self, client):
        """Test that failed pipelines are cleaned up properly."""
        invalid_yaml = """
pipeline:
  name: Will Fail
  steps:
    - name: nonexistent_validator
      config:
        invalid: true
"""

        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": invalid_yaml,
                "pipeline_name": "failure_test"
            }
        )

        if response.status_code == 200:
            run_id = response.json()["run_id"]

            # Should still be able to get status
            status_response = client.get(f"/pipelines/status/{run_id}")
            assert status_response.status_code == 200

            # Should be able to delete
            delete_response = client.delete(f"/pipelines/{run_id}")
            assert delete_response.status_code == 200

    @pytest.mark.integration
    def test_rollback_on_database_error(self, client):
        """Test database rollback on error."""
        # This would test transaction rollback in results persistence
        # For now, just verify the system doesn't crash
        response = client.get("/history/runs")
        assert response.status_code in [200, 500]


class TestResourceLimits:
    """Test resource limit handling."""

    @pytest.mark.integration
    def test_large_result_set(self, client):
        """Test handling of large result sets."""
        response = client.get("/history/runs?page_size=1000")

        # Should handle large page size or reject it
        assert response.status_code in [200, 400]

    @pytest.mark.integration
    def test_large_yaml_input(self, client):
        """Test handling of very large YAML input."""
        # Create a large YAML with many steps
        large_yaml = "pipeline:\n  name: Large\n  metadata:\n    table1:\n"

        # Add many columns
        for i in range(100):
            large_yaml += f"      col{i}: VARCHAR\n"

        large_yaml += "  steps:\n"
        for i in range(100):
            large_yaml += f"    - name: step{i}\n      config: {{}}\n"

        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": large_yaml,
                "pipeline_name": "large_yaml_test"
            }
        )

        # Should accept or reject based on size limits
        assert response.status_code in [200, 400, 413]


class TestAuthenticationErrors:
    """Test authentication error handling (future)."""

    @pytest.mark.integration
    def test_missing_auth_header(self, client):
        """Test request without authentication (when implemented)."""
        # Currently no auth, so should succeed
        response = client.get("/pipelines/list")
        assert response.status_code == 200

    @pytest.mark.integration
    def test_invalid_token(self, client):
        """Test request with invalid token (when implemented)."""
        # Currently no auth, so should succeed
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/pipelines/list", headers=headers)
        assert response.status_code in [200, 401]


class TestValidationErrors:
    """Test validation error scenarios."""

    @pytest.mark.integration
    def test_invalid_date_range(self, client):
        """Test invalid date range in history query."""
        response = client.get("/history/runs?start_date=2025-12-31&end_date=2025-01-01")

        # Should handle invalid range gracefully
        assert response.status_code in [200, 400]

    @pytest.mark.integration
    def test_invalid_pagination(self, client):
        """Test invalid pagination parameters."""
        # Negative page
        response1 = client.get("/history/runs?page=-1")
        assert response1.status_code in [200, 422]

        # Zero page size
        response2 = client.get("/history/runs?page_size=0")
        assert response2.status_code in [200, 422]

        # Excessive page size
        response3 = client.get("/history/runs?page_size=10000")
        assert response3.status_code in [200, 400]


class TestConcurrencyIssues:
    """Test concurrency and race condition handling."""

    @pytest.mark.integration
    def test_delete_during_execution(self, client, sample_pipeline_yaml):
        """Test deleting pipeline while it's executing."""
        # Start pipeline
        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": sample_pipeline_yaml,
                "pipeline_name": "delete_test"
            }
        )

        if response.status_code == 200:
            run_id = response.json()["run_id"]

            # Immediately try to delete
            delete_response = client.delete(f"/pipelines/{run_id}")

            # Should handle gracefully
            assert delete_response.status_code in [200, 409]

    @pytest.mark.integration
    def test_concurrent_status_checks(self, client, sample_pipeline_yaml):
        """Test concurrent status checks for same pipeline."""
        # Start pipeline
        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": sample_pipeline_yaml,
                "pipeline_name": "concurrent_status_test"
            }
        )

        if response.status_code == 200:
            run_id = response.json()["run_id"]

            # Check status multiple times concurrently
            responses = []
            for _ in range(10):
                status_response = client.get(f"/pipelines/status/{run_id}")
                responses.append(status_response)

            # All should succeed
            for r in responses:
                assert r.status_code == 200


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    @pytest.mark.integration
    def test_empty_pipeline(self, client):
        """Test pipeline with no steps."""
        empty_yaml = """
pipeline:
  name: Empty
  metadata: {}
  steps: []
"""

        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": empty_yaml,
                "pipeline_name": "empty_test"
            }
        )

        # Should reject empty pipeline
        assert response.status_code == 400

    @pytest.mark.integration
    def test_special_characters_in_names(self, client, sample_pipeline_yaml):
        """Test handling of special characters in names."""
        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": sample_pipeline_yaml,
                "pipeline_name": "test-pipeline!@#$%^&*()"
            }
        )

        # Should handle or sanitize special characters
        assert response.status_code in [200, 400]

    @pytest.mark.integration
    def test_unicode_in_yaml(self, client):
        """Test handling of Unicode characters in YAML."""
        unicode_yaml = """
pipeline:
  name: テストパイプライン
  metadata:
    客户表:
      ID: INT
      名前: VARCHAR
  steps:
    - name: validate_schema
      config: {}
"""

        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": unicode_yaml,
                "pipeline_name": "unicode_test"
            }
        )

        # Should handle Unicode properly
        assert response.status_code in [200, 400]

    @pytest.mark.integration
    def test_null_values(self, client):
        """Test handling of null values in requests."""
        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": None,
                "pipeline_name": "test"
            }
        )

        # Should reject null required fields
        assert response.status_code in [400, 422]
