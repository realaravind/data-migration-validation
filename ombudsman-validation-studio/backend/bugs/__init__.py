"""
Bug Reporting and Azure DevOps Integration Module

Provides functionality for:
- Generating bug reports from batch validation results
- Reviewing and approving bugs
- Submitting bugs to Azure DevOps
- Managing Azure DevOps configuration
"""

from .models import (
    Bug,
    BugReport,
    BugReportSummary,
    BugSeverity,
    BugStatus,
    ValidationCategory,
    AzureDevOpsConfig,
    AzureDevOpsWorkItemType,
    GenerateBugReportRequest,
    BugReviewRequest,
    SubmitToAzureDevOpsRequest,
    TestAzureDevOpsConnectionRequest,
    AzureDevOpsConnectionTestResponse,
    BugReportGenerateResponse,
    BugReportDownloadFormat,
    AzureDevOpsSubmissionResponse,
    BugReportListResponse
)
from .bug_report_service import BugReportService
from .router import router

__all__ = [
    "Bug",
    "BugReport",
    "BugReportSummary",
    "BugSeverity",
    "BugStatus",
    "ValidationCategory",
    "AzureDevOpsConfig",
    "AzureDevOpsWorkItemType",
    "GenerateBugReportRequest",
    "BugReviewRequest",
    "SubmitToAzureDevOpsRequest",
    "TestAzureDevOpsConnectionRequest",
    "AzureDevOpsConnectionTestResponse",
    "BugReportGenerateResponse",
    "BugReportDownloadFormat",
    "AzureDevOpsSubmissionResponse",
    "BugReportListResponse",
    "BugReportService",
    "router"
]
