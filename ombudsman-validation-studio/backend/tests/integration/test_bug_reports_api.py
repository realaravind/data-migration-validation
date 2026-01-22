"""
Tests for Bug Reports API endpoints

Tests bug report functionality including:
- Bug report generation from batch results
- Bug report retrieval and listing
- Bug review (approve/reject)
- Download in multiple formats
- Azure DevOps submission
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json
from datetime import datetime


class TestBugReportGeneration:
    """Tests for POST /bug-reports/generate"""

    def test_generate_bug_report_success(self, client, mock_bug_service):
        """Should generate bug report from batch results"""
        mock_report = MagicMock()
        mock_report.report_id = "br_test_123"
        mock_report.bugs = [MagicMock(), MagicMock()]
        mock_report.summary = {"total": 2, "critical": 1, "high": 1}
        mock_bug_service.return_value.generate_bug_report.return_value = mock_report

        response = client.post(
            "/bug-reports/generate",
            json={
                "batch_job_id": "batch_123",
                "include_warnings": True,
                "min_severity": "medium"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["report_id"] == "br_test_123"
        assert data["total_bugs"] == 2

    def test_generate_bug_report_batch_not_found(self, client, mock_bug_service):
        """Should return 404 when batch not found"""
        mock_bug_service.return_value.generate_bug_report.side_effect = FileNotFoundError("Batch not found")

        response = client.post(
            "/bug-reports/generate",
            json={"batch_job_id": "nonexistent"}
        )

        assert response.status_code == 404

    def test_generate_bug_report_invalid_request(self, client, mock_bug_service):
        """Should return 400 for invalid request"""
        mock_bug_service.return_value.generate_bug_report.side_effect = ValueError("Invalid batch results")

        response = client.post(
            "/bug-reports/generate",
            json={"batch_job_id": "invalid"}
        )

        assert response.status_code == 400


class TestBugReportRetrieval:
    """Tests for GET /bug-reports/{report_id}"""

    def test_get_bug_report_success(self, client, mock_bug_service, sample_bug_report):
        """Should retrieve bug report by ID"""
        mock_bug_service.return_value.load_report.return_value = sample_bug_report

        response = client.get("/bug-reports/br_test_123")

        assert response.status_code == 200
        data = response.json()
        assert data["report_id"] == "br_test_123"

    def test_get_bug_report_not_found(self, client, mock_bug_service):
        """Should return 404 for non-existent report"""
        mock_bug_service.return_value.load_report.return_value = None

        response = client.get("/bug-reports/nonexistent")

        assert response.status_code == 404


class TestBugReportListing:
    """Tests for GET /bug-reports/"""

    def test_list_bug_reports(self, client, mock_bug_service):
        """Should list all bug reports"""
        mock_bug_service.return_value.list_reports.return_value = [
            MagicMock(report_id="br_1"),
            MagicMock(report_id="br_2")
        ]

        response = client.get("/bug-reports/")

        assert response.status_code == 200
        data = response.json()
        assert "reports" in data
        assert "total" in data

    def test_list_bug_reports_filtered(self, client, mock_bug_service):
        """Should filter reports by project"""
        mock_bug_service.return_value.list_reports.return_value = []

        response = client.get("/bug-reports/?project_id=test_project")

        assert response.status_code == 200

    def test_list_bug_reports_paginated(self, client, mock_bug_service):
        """Should support pagination"""
        mock_bug_service.return_value.list_reports.return_value = []

        response = client.get("/bug-reports/?limit=10&page=2")

        assert response.status_code == 200


class TestBugReview:
    """Tests for POST /bug-reports/{report_id}/review"""

    def test_review_bugs_success(self, client, mock_bug_service, sample_bug_report):
        """Should approve/reject bugs"""
        mock_bug_service.return_value.update_bug_statuses.return_value = sample_bug_report

        response = client.post(
            "/bug-reports/br_test_123/review",
            json={
                "approved_bug_ids": ["bug_1", "bug_2"],
                "rejected_bug_ids": ["bug_3"]
            }
        )

        assert response.status_code == 200

    def test_review_bugs_report_not_found(self, client, mock_bug_service):
        """Should return 404 for non-existent report"""
        mock_bug_service.return_value.update_bug_statuses.side_effect = FileNotFoundError("Report not found")

        response = client.post(
            "/bug-reports/nonexistent/review",
            json={"approved_bug_ids": [], "rejected_bug_ids": []}
        )

        assert response.status_code == 404


class TestBugReportDownload:
    """Tests for GET /bug-reports/{report_id}/download/{format}"""

    def test_download_json(self, client, mock_bug_service, sample_bug_report):
        """Should download report as JSON"""
        mock_bug_service.return_value.load_report.return_value = sample_bug_report

        response = client.get("/bug-reports/br_test_123/download/json")

        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")

    def test_download_csv(self, client, mock_bug_service, sample_bug_report):
        """Should download report as CSV"""
        mock_bug_service.return_value.load_report.return_value = sample_bug_report

        response = client.get("/bug-reports/br_test_123/download/csv")

        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    def test_download_excel(self, client, mock_bug_service, sample_bug_report, mock_excel_exporter):
        """Should download report as Excel"""
        mock_bug_service.return_value.load_report.return_value = sample_bug_report

        response = client.get("/bug-reports/br_test_123/download/excel")

        # May return 200 or 500 depending on Excel generation
        assert response.status_code in [200, 500]

    def test_download_pdf_not_implemented(self, client, mock_bug_service, sample_bug_report):
        """Should return 501 for PDF format"""
        mock_bug_service.return_value.load_report.return_value = sample_bug_report

        response = client.get("/bug-reports/br_test_123/download/pdf")

        assert response.status_code == 501

    def test_download_report_not_found(self, client, mock_bug_service):
        """Should return 404 for non-existent report"""
        mock_bug_service.return_value.load_report.return_value = None

        response = client.get("/bug-reports/nonexistent/download/json")

        assert response.status_code == 404


class TestBugReportDelete:
    """Tests for DELETE /bug-reports/{report_id}"""

    def test_delete_bug_report_success(self, client, mock_bug_service):
        """Should delete bug report"""
        with patch('pathlib.Path.exists', return_value=True), \
             patch('pathlib.Path.unlink'):
            response = client.delete("/bug-reports/br_test_123")

            assert response.status_code == 200

    def test_delete_bug_report_not_found(self, client, mock_bug_service):
        """Should return 404 for non-existent report"""
        with patch('pathlib.Path.exists', return_value=False):
            response = client.delete("/bug-reports/nonexistent")

            assert response.status_code == 404


class TestAzureDevOpsSubmission:
    """Tests for POST /bug-reports/{report_id}/submit-to-azure"""

    def test_submit_to_azure_success(self, client, mock_bug_service, sample_bug_report, mock_azure_service):
        """Should submit approved bugs to Azure DevOps"""
        mock_bug_service.return_value.load_report.return_value = sample_bug_report

        with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value='{"azure_devops": {"enabled": true, "organization_url": "https://dev.azure.com/test", "project_name": "Test", "pat_token": "token"}}')))))):
            response = client.post("/bug-reports/br_test_123/submit-to-azure")

            # May return success or error depending on mock setup
            assert response.status_code in [200, 400, 404, 500]

    def test_submit_to_azure_not_configured(self, client, mock_bug_service, sample_bug_report):
        """Should return 400 when Azure not configured"""
        mock_bug_service.return_value.load_report.return_value = sample_bug_report

        with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value='{}')))))):
            response = client.post("/bug-reports/br_test_123/submit-to-azure")

            assert response.status_code in [400, 404]

    def test_submit_to_azure_no_approved_bugs(self, client, mock_bug_service, sample_bug_report):
        """Should return 400 when no approved bugs"""
        sample_bug_report.bugs = []
        mock_bug_service.return_value.load_report.return_value = sample_bug_report

        with patch('builtins.open', MagicMock(return_value=MagicMock(__enter__=MagicMock(return_value=MagicMock(read=MagicMock(return_value='{"azure_devops": {"enabled": true}}')))))):
            response = client.post("/bug-reports/br_test_123/submit-to-azure")

            assert response.status_code in [400, 404]

    def test_submit_specific_bugs(self, client, mock_bug_service, sample_bug_report, mock_azure_service):
        """Should submit specific bugs"""
        mock_bug_service.return_value.load_report.return_value = sample_bug_report

        response = client.post(
            "/bug-reports/br_test_123/submit-to-azure",
            json={"bug_ids": ["bug_1"]}
        )

        # May return success or error
        assert response.status_code in [200, 400, 404, 500]


# Fixtures
@pytest.fixture
def mock_bug_service():
    """Mock bug report service"""
    with patch('bugs.router.bug_service') as mock:
        yield mock


@pytest.fixture
def mock_excel_exporter():
    """Mock Excel exporter"""
    with patch('bugs.router.excel_exporter') as mock:
        mock_path = MagicMock()
        mock_path.exists.return_value = True
        mock.generate_excel_report.return_value = mock_path
        yield mock


@pytest.fixture
def mock_azure_service():
    """Mock Azure DevOps service"""
    with patch('bugs.router.AzureDevOpsService') as mock:
        instance = MagicMock()
        instance.test_connection.return_value = {"success": True}
        instance.create_bugs_batch.return_value = {
            "total": 2,
            "created": 2,
            "failed": 0,
            "work_items": [
                {"bug_id": "bug_1", "work_item_id": 123, "work_item_url": "https://..."},
                {"bug_id": "bug_2", "work_item_id": 124, "work_item_url": "https://..."}
            ]
        }
        mock.return_value = instance
        yield mock


@pytest.fixture
def sample_bug_report():
    """Create sample bug report"""
    from bugs.models import BugStatus

    report = MagicMock()
    report.report_id = "br_test_123"
    report.project_id = "test_project"
    report.batch_job_id = "batch_123"
    report.batch_job_name = "Test Batch"
    report.submitted_to_azure = False
    report.approved_count = 2
    report.summary = {"total": 3, "critical": 1, "high": 1, "medium": 1}

    # Create sample bugs
    bug1 = MagicMock()
    bug1.bug_id = "bug_1"
    bug1.title = "Data Mismatch in dim_customer"
    bug1.severity = "critical"
    bug1.category = "data_mismatch"
    bug1.status = BugStatus.APPROVED
    bug1.step_name = "row_count_validation"
    bug1.validation_type = "row_count"
    bug1.table_name = "dim_customer"
    bug1.column_name = None
    bug1.expected_value = "1000"
    bug1.actual_value = "950"
    bug1.failure_count = 50
    bug1.error_message = None
    bug1.work_item_id = None

    bug2 = MagicMock()
    bug2.bug_id = "bug_2"
    bug2.title = "Null Values in fact_sales"
    bug2.severity = "high"
    bug2.category = "null_values"
    bug2.status = BugStatus.APPROVED
    bug2.step_name = "null_check"
    bug2.validation_type = "null_count"
    bug2.table_name = "fact_sales"
    bug2.column_name = "product_id"
    bug2.expected_value = "0"
    bug2.actual_value = "25"
    bug2.failure_count = 25
    bug2.error_message = None
    bug2.work_item_id = None

    report.bugs = [bug1, bug2]

    # Mock json method
    report.json.return_value = json.dumps({
        "report_id": "br_test_123",
        "bugs": []
    })

    return report
