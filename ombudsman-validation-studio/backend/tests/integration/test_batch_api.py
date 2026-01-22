"""
Tests for Batch Operations API endpoints

Tests batch job management including:
- Bulk pipeline execution
- Batch data generation
- Multi-project validation
- Job control (cancel, retry, delete)
- Job monitoring and statistics
- Report generation
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, AsyncMock
import json
from datetime import datetime


class TestBulkPipelineExecution:
    """Tests for POST /batch/pipelines/bulk-execute"""

    def test_bulk_execute_success(self, client, mock_batch_executor):
        """Should create batch job for multiple pipelines"""
        response = client.post(
            "/batch/pipelines/bulk-execute",
            json={
                "job_name": "Test Batch Job",
                "pipelines": [
                    {"pipeline_id": "dim_customer_validation"},
                    {"pipeline_id": "fact_sales_validation"}
                ],
                "parallel_execution": True,
                "max_parallel": 3,
                "stop_on_error": False,
                "project_id": "test_project"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["total_operations"] == 2
        assert "status" in data

    def test_bulk_execute_with_config_override(self, client, mock_batch_executor):
        """Should accept config overrides per pipeline"""
        response = client.post(
            "/batch/pipelines/bulk-execute",
            json={
                "job_name": "Config Override Test",
                "pipelines": [
                    {
                        "pipeline_id": "dim_validation",
                        "config_override": {"timeout": 300}
                    }
                ],
                "parallel_execution": False
            }
        )

        assert response.status_code == 200

    def test_bulk_execute_empty_pipelines(self, client):
        """Should handle empty pipeline list"""
        response = client.post(
            "/batch/pipelines/bulk-execute",
            json={
                "job_name": "Empty Test",
                "pipelines": []
            }
        )

        assert response.status_code == 200
        assert response.json()["total_operations"] == 0


class TestBulkDataGeneration:
    """Tests for POST /batch/data/bulk-generate"""

    def test_bulk_generate_success(self, client, mock_batch_executor):
        """Should create batch job for data generation"""
        response = client.post(
            "/batch/data/bulk-generate",
            json={
                "job_name": "Generate Test Data",
                "items": [
                    {"schema_type": "Retail", "row_count": 10000},
                    {"schema_type": "Finance", "row_count": 5000}
                ],
                "parallel_execution": True,
                "max_parallel": 2
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "job_id" in data
        assert data["total_operations"] == 2

    def test_bulk_generate_with_seed(self, client, mock_batch_executor):
        """Should accept seed for reproducible data"""
        response = client.post(
            "/batch/data/bulk-generate",
            json={
                "job_name": "Seeded Data",
                "items": [
                    {"schema_type": "Retail", "row_count": 1000, "seed": 42}
                ]
            }
        )

        assert response.status_code == 200


class TestMultiProjectValidation:
    """Tests for POST /batch/projects/multi-validate"""

    def test_multi_project_validate_success(self, client, mock_batch_executor):
        """Should create batch job for multi-project validation"""
        response = client.post(
            "/batch/projects/multi-validate",
            json={
                "job_name": "Weekly Multi-Project Validation",
                "projects": [
                    {
                        "project_id": "retail_migration",
                        "pipeline_ids": ["dim_validation", "fact_validation"]
                    },
                    {
                        "project_id": "finance_migration",
                        "pipeline_ids": ["general_ledger_validation"]
                    }
                ],
                "parallel_execution": False,
                "stop_on_error": False
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_operations"] == 2


class TestBulkMetadataExtraction:
    """Tests for POST /batch/metadata/bulk-extract"""

    def test_bulk_extract_success(self, client, mock_batch_executor):
        """Should create batch job for metadata extraction"""
        response = client.post(
            "/batch/metadata/bulk-extract",
            json={
                "job_name": "Extract All Metadata",
                "items": [
                    {"connection_type": "sqlserver", "schema_name": "dbo"},
                    {"connection_type": "snowflake", "schema_name": "PUBLIC"}
                ],
                "parallel_execution": True,
                "max_parallel": 2
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["total_operations"] == 2


class TestJobListing:
    """Tests for GET /batch/jobs"""

    def test_list_jobs(self, client, mock_job_manager):
        """Should list all batch jobs"""
        response = client.get("/batch/jobs")

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert "page" in data

    def test_list_jobs_with_status_filter(self, client, mock_job_manager):
        """Should filter jobs by status"""
        response = client.get("/batch/jobs?status=running")

        assert response.status_code == 200

    def test_list_jobs_with_type_filter(self, client, mock_job_manager):
        """Should filter jobs by type"""
        response = client.get("/batch/jobs?job_type=bulk_pipeline_execution")

        assert response.status_code == 200

    def test_list_jobs_with_project_filter(self, client, mock_job_manager):
        """Should filter jobs by project"""
        response = client.get("/batch/jobs?project_id=test_project")

        assert response.status_code == 200

    def test_list_jobs_pagination(self, client, mock_job_manager):
        """Should support pagination"""
        response = client.get("/batch/jobs?limit=10&offset=20")

        assert response.status_code == 200


class TestJobDetails:
    """Tests for GET /batch/jobs/{job_id}"""

    def test_get_job_success(self, client, mock_job_manager, sample_job):
        """Should return job details"""
        mock_job_manager.return_value.get_job.return_value = sample_job

        response = client.get(f"/batch/jobs/{sample_job.job_id}")

        assert response.status_code == 200
        data = response.json()
        assert "job" in data
        assert data["job"]["job_id"] == sample_job.job_id

    def test_get_job_not_found(self, client, mock_job_manager):
        """Should return 404 for non-existent job"""
        mock_job_manager.return_value.get_job.return_value = None

        response = client.get("/batch/jobs/non_existent_job")

        assert response.status_code == 404


class TestJobCancel:
    """Tests for POST /batch/jobs/{job_id}/cancel"""

    def test_cancel_job_success(self, client, mock_job_manager, sample_job):
        """Should cancel running job"""
        sample_job.status = "running"
        mock_job_manager.return_value.get_job.return_value = sample_job
        mock_job_manager.return_value.cancel_job.return_value = True

        response = client.post(
            f"/batch/jobs/{sample_job.job_id}/cancel",
            json={"reason": "User cancelled"}
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_cancel_completed_job(self, client, mock_job_manager, sample_job):
        """Should warn when cancelling completed job"""
        sample_job.status = MagicMock()
        sample_job.status.value = "completed"
        mock_job_manager.return_value.get_job.return_value = sample_job

        response = client.post(f"/batch/jobs/{sample_job.job_id}/cancel")

        assert response.status_code == 200
        assert response.json()["status"] == "warning"


class TestJobRetry:
    """Tests for POST /batch/jobs/{job_id}/retry"""

    def test_retry_failed_operations(self, client, mock_job_manager, mock_batch_executor, sample_job_with_failures):
        """Should retry failed operations"""
        mock_job_manager.return_value.get_job.return_value = sample_job_with_failures

        response = client.post(f"/batch/jobs/{sample_job_with_failures.job_id}/retry")

        assert response.status_code == 200
        assert "retrying_operations" in response.json()

    def test_retry_specific_operations(self, client, mock_job_manager, mock_batch_executor, sample_job_with_failures):
        """Should retry specific operations"""
        mock_job_manager.return_value.get_job.return_value = sample_job_with_failures

        response = client.post(
            f"/batch/jobs/{sample_job_with_failures.job_id}/retry",
            json={"operation_ids": ["pipeline_0_dim_validation"]}
        )

        assert response.status_code == 200

    def test_retry_no_failed_operations(self, client, mock_job_manager, sample_job):
        """Should handle no failed operations"""
        sample_job.operations = []
        mock_job_manager.return_value.get_job.return_value = sample_job

        response = client.post(f"/batch/jobs/{sample_job.job_id}/retry")

        assert response.status_code == 200
        assert response.json()["status"] == "info"


class TestJobDelete:
    """Tests for DELETE /batch/jobs/{job_id}"""

    def test_delete_job_success(self, client, mock_job_manager, sample_job):
        """Should delete completed job"""
        sample_job.status = MagicMock()
        sample_job.status.value = "completed"
        mock_job_manager.return_value.get_job.return_value = sample_job
        mock_job_manager.return_value.delete_job.return_value = True

        response = client.delete(f"/batch/jobs/{sample_job.job_id}")

        assert response.status_code == 200

    def test_delete_running_job(self, client, mock_job_manager, sample_job):
        """Should prevent deleting running job"""
        from batch.models import BatchJobStatus
        sample_job.status = BatchJobStatus.RUNNING
        mock_job_manager.return_value.get_job.return_value = sample_job

        response = client.delete(f"/batch/jobs/{sample_job.job_id}")

        assert response.status_code == 400
        assert "running" in response.json()["detail"].lower()


class TestJobProgress:
    """Tests for GET /batch/jobs/{job_id}/progress"""

    def test_get_progress(self, client, mock_job_manager, sample_job):
        """Should return job progress"""
        mock_job_manager.return_value.get_job.return_value = sample_job

        response = client.get(f"/batch/jobs/{sample_job.job_id}/progress")

        assert response.status_code == 200
        data = response.json()
        assert "progress" in data
        assert "job_status" in data


class TestJobOperations:
    """Tests for GET /batch/jobs/{job_id}/operations"""

    def test_get_operations(self, client, mock_job_manager, sample_job):
        """Should return job operations"""
        mock_job_manager.return_value.get_job.return_value = sample_job

        response = client.get(f"/batch/jobs/{sample_job.job_id}/operations")

        assert response.status_code == 200
        data = response.json()
        assert "operations" in data
        assert "total_operations" in data


class TestBatchStatistics:
    """Tests for GET /batch/statistics"""

    def test_get_statistics(self, client, mock_job_manager):
        """Should return batch statistics"""
        mock_job_manager.return_value.get_statistics.return_value = {
            "total_jobs": 100,
            "jobs_by_status": {"completed": 80, "failed": 10, "running": 10},
            "jobs_by_type": {"bulk_pipeline_execution": 60, "batch_data_generation": 40}
        }

        response = client.get("/batch/statistics")

        assert response.status_code == 200
        data = response.json()
        assert "statistics" in data


class TestBatchReport:
    """Tests for GET /batch/jobs/{job_id}/report"""

    def test_generate_report(self, client, mock_job_manager, mock_report_generator, sample_completed_job):
        """Should generate consolidated report"""
        mock_job_manager.return_value.get_job.return_value = sample_completed_job

        response = client.get(f"/batch/jobs/{sample_completed_job.job_id}/report")

        assert response.status_code == 200
        data = response.json()
        assert "report" in data

    def test_report_no_completed_runs(self, client, mock_job_manager, sample_job):
        """Should handle job with no completed runs"""
        sample_job.operations = []
        mock_job_manager.return_value.get_job.return_value = sample_job

        response = client.get(f"/batch/jobs/{sample_job.job_id}/report")

        assert response.status_code == 400


# Fixtures
@pytest.fixture
def mock_batch_executor():
    """Mock batch executor"""
    with patch('batch.router.batch_executor') as mock:
        mock.execute_job_async = MagicMock()
        yield mock


@pytest.fixture
def mock_job_manager():
    """Mock batch job manager"""
    with patch('batch.router.batch_job_manager') as mock:
        mock.list_jobs.return_value = []
        yield mock


@pytest.fixture
def mock_report_generator():
    """Mock report generator"""
    with patch('batch.router.report_generator') as mock:
        mock.generate_batch_report.return_value = {
            "summary": {"total": 10, "passed": 8, "failed": 2}
        }
        yield mock


@pytest.fixture
def sample_job():
    """Create sample batch job"""
    from batch.models import BatchJob, BatchJobStatus, BatchJobType

    job = MagicMock()
    job.job_id = "test_job_123"
    job.name = "Test Batch Job"
    job.status = BatchJobStatus.QUEUED
    job.job_type = BatchJobType.BULK_PIPELINE_EXECUTION
    job.operations = []
    job.progress = MagicMock()
    job.progress.model_dump.return_value = {"completed": 0, "total": 5, "percentage": 0}
    job.started_at = None
    job.completed_at = None
    job.total_duration_ms = 0
    return job


@pytest.fixture
def sample_job_with_failures(sample_job):
    """Create sample job with failed operations"""
    from batch.models import BatchOperation, BatchOperationStatus

    failed_op = MagicMock()
    failed_op.operation_id = "pipeline_0_dim_validation"
    failed_op.status = BatchOperationStatus.FAILED
    failed_op.error = "Connection timeout"
    failed_op.started_at = None
    failed_op.completed_at = None

    sample_job.operations = [failed_op]
    sample_job.status = MagicMock()
    sample_job.status.value = "failed"
    return sample_job


@pytest.fixture
def sample_completed_job(sample_job):
    """Create sample completed job"""
    from batch.models import BatchOperation, BatchOperationStatus

    completed_op = MagicMock()
    completed_op.operation_id = "pipeline_0_test"
    completed_op.status = BatchOperationStatus.COMPLETED
    completed_op.result = {"run_id": "run_123", "status": "passed"}
    completed_op.started_at = datetime.utcnow()
    completed_op.completed_at = datetime.utcnow()
    completed_op.duration_ms = 1000
    completed_op.error = None
    completed_op.metadata = {}
    completed_op.operation_type = "pipeline_execution"

    sample_job.operations = [completed_op]
    sample_job.status = MagicMock()
    sample_job.status.value = "completed"
    return sample_job
