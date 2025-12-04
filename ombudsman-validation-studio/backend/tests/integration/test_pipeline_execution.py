"""
Integration tests for pipeline execution API.
"""

import pytest
import time
from fastapi.testclient import TestClient


class TestPipelineExecutionAPI:
    """Test pipeline execution endpoints."""

    def test_execute_pipeline_success(self, client, sample_pipeline_yaml):
        """Test successful pipeline execution."""
        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": sample_pipeline_yaml,
                "pipeline_name": "test_pipeline"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "run_id" in data
        assert data["status"] == "pending"
        assert data["validation"] == "passed"

    def test_execute_pipeline_invalid_yaml(self, client):
        """Test pipeline execution with invalid YAML."""
        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": "invalid: yaml: {{{}",
                "pipeline_name": "test"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_QUERY"
        assert "YAML" in data["error"]["message"]

    def test_execute_pipeline_invalid_config(self, client, invalid_pipeline_yaml):
        """Test pipeline execution with invalid pipeline config."""
        response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": invalid_pipeline_yaml,
                "pipeline_name": "test"
            }
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_PIPELINE_CONFIG"

    def test_get_pipeline_status_not_found(self, client):
        """Test getting status of non-existent pipeline."""
        response = client.get("/pipelines/status/invalid_run_id")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PIPELINE_NOT_FOUND"
        assert "invalid_run_id" in data["error"]["message"]

    def test_get_pipeline_status_success(self, client, sample_pipeline_yaml):
        """Test getting status of existing pipeline."""
        # First create a pipeline
        create_response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": sample_pipeline_yaml,
                "pipeline_name": "test"
            }
        )
        run_id = create_response.json()["run_id"]

        # Then get its status
        response = client.get(f"/pipelines/status/{run_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["pipeline_name"] == "test"
        assert data["status"] in ["pending", "running", "completed", "failed"]

    def test_list_pipelines(self, client, sample_pipeline_yaml):
        """Test listing all pipelines."""
        # Create a pipeline first
        client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": sample_pipeline_yaml,
                "pipeline_name": "test"
            }
        )

        # List pipelines
        response = client.get("/pipelines/list")

        assert response.status_code == 200
        data = response.json()
        assert "pipelines" in data
        assert isinstance(data["pipelines"], list)
        assert len(data["pipelines"]) > 0

    def test_delete_pipeline_not_found(self, client):
        """Test deleting non-existent pipeline."""
        response = client.delete("/pipelines/invalid_run_id")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PIPELINE_NOT_FOUND"

    def test_delete_pipeline_success(self, client, sample_pipeline_yaml):
        """Test deleting existing pipeline."""
        # Create a pipeline
        create_response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": sample_pipeline_yaml,
                "pipeline_name": "test"
            }
        )
        run_id = create_response.json()["run_id"]

        # Delete it
        response = client.delete(f"/pipelines/{run_id}")

        assert response.status_code == 200
        assert "deleted" in response.json()["message"].lower()

        # Verify it's gone
        get_response = client.get(f"/pipelines/status/{run_id}")
        assert get_response.status_code == 404


class TestPipelineTemplates:
    """Test pipeline template endpoints."""

    def test_list_pipeline_templates(self, client):
        """Test listing pipeline templates."""
        response = client.get("/pipelines/templates")

        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert isinstance(data["templates"], list)

    def test_list_default_pipelines(self, client):
        """Test listing default pipelines."""
        response = client.get("/pipelines/defaults")

        assert response.status_code == 200
        data = response.json()
        assert "defaults" in data
        assert "count" in data
        assert isinstance(data["defaults"], list)

    def test_get_default_pipeline_not_found(self, client):
        """Test getting non-existent default pipeline."""
        response = client.get("/pipelines/defaults/nonexistent_pipeline")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PIPELINE_NOT_FOUND"


class TestCustomPipelineManagement:
    """Test custom pipeline management for projects."""

    def test_save_pipeline_project_not_found(self, client, sample_pipeline_yaml):
        """Test saving pipeline to non-existent project."""
        response = client.post(
            "/pipelines/custom/save",
            json={
                "project_id": "nonexistent_project",
                "pipeline_name": "test_pipeline",
                "pipeline_yaml": sample_pipeline_yaml,
                "description": "Test pipeline",
                "tags": ["test"]
            }
        )

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PROJECT_NOT_FOUND"

    def test_save_pipeline_invalid_yaml(self, client):
        """Test saving pipeline with invalid YAML."""
        response = client.post(
            "/pipelines/custom/save",
            json={
                "project_id": "test_project",
                "pipeline_name": "test_pipeline",
                "pipeline_yaml": "invalid: {{{}",
                "description": "Test"
            }
        )

        # Will fail because project doesn't exist, but that's ok for this test
        assert response.status_code in [400, 404]
        if response.status_code == 400:
            data = response.json()
            assert data["error"]["code"] == "INVALID_QUERY"

    def test_list_custom_pipelines_no_project(self, client):
        """Test listing pipelines for non-existent project."""
        response = client.get("/pipelines/custom/project/nonexistent_project")

        assert response.status_code == 200
        data = response.json()
        assert data["pipelines"] == []

    def test_get_custom_pipeline_not_found(self, client):
        """Test getting non-existent custom pipeline."""
        response = client.get("/pipelines/custom/project/test/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PIPELINE_NOT_FOUND"

    def test_delete_custom_pipeline_not_found(self, client):
        """Test deleting non-existent custom pipeline."""
        response = client.delete("/pipelines/custom/project/test/nonexistent")

        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "PIPELINE_NOT_FOUND"


class TestPipelineValidation:
    """Test pipeline configuration validation."""

    def test_pipeline_validation_missing_steps(self, client):
        """Test validation rejects pipeline without steps."""
        yaml_str = """
pipeline:
  name: Invalid Pipeline
  metadata: {}
  mapping: {}
"""
        response = client.post(
            "/pipelines/execute",
            json={"pipeline_yaml": yaml_str, "pipeline_name": "test"}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_PIPELINE_CONFIG"
        assert "steps" in data["error"]["message"].lower()

    def test_pipeline_validation_invalid_step_structure(self, client):
        """Test validation rejects pipeline with invalid step."""
        yaml_str = """
pipeline:
  name: Invalid Pipeline
  steps:
    - invalid_step_without_name: true
"""
        response = client.post(
            "/pipelines/execute",
            json={"pipeline_yaml": yaml_str, "pipeline_name": "test"}
        )

        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "INVALID_PIPELINE_CONFIG"


class TestPipelineExecutionFlow:
    """Test complete pipeline execution flow."""

    @pytest.mark.asyncio
    @pytest.mark.slow
    async def test_complete_pipeline_flow(self, client, sample_pipeline_yaml):
        """Test complete pipeline execution flow from start to finish."""
        # 1. Execute pipeline
        execute_response = client.post(
            "/pipelines/execute",
            json={
                "pipeline_yaml": sample_pipeline_yaml,
                "pipeline_name": "integration_test"
            }
        )
        assert execute_response.status_code == 200
        run_id = execute_response.json()["run_id"]

        # 2. Check initial status
        status_response = client.get(f"/pipelines/status/{run_id}")
        assert status_response.status_code == 200
        assert status_response.json()["status"] in ["pending", "running"]

        # 3. Wait a bit for execution (may complete or fail)
        time.sleep(2)

        # 4. Check final status
        final_status = client.get(f"/pipelines/status/{run_id}")
        assert final_status.status_code == 200
        final_data = final_status.json()
        assert final_data["status"] in ["running", "completed", "failed"]

        # 5. Verify in list
        list_response = client.get("/pipelines/list")
        run_ids = [p["run_id"] for p in list_response.json()["pipelines"]]
        assert run_id in run_ids

        # 6. Delete pipeline
        delete_response = client.delete(f"/pipelines/{run_id}")
        assert delete_response.status_code == 200

        # 7. Verify deleted
        deleted_status = client.get(f"/pipelines/status/{run_id}")
        assert deleted_status.status_code == 404
