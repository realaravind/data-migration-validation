"""
Bug Reporting and Azure DevOps Integration Data Models

Defines schemas for bug reports, bugs, Azure DevOps configuration, and related operations.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, HttpUrl
from enum import Enum


class BugSeverity(str, Enum):
    """Bug severity levels"""
    CRITICAL = "critical"  # Data corruption, system crash
    HIGH = "high"          # Major functional failure
    MEDIUM = "medium"      # Moderate impact on functionality
    LOW = "low"            # Minor issues, cosmetic
    INFO = "info"          # Informational, not a bug


class BugStatus(str, Enum):
    """Bug status"""
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    CREATED_IN_AZURE = "created_in_azure"
    FAILED_TO_CREATE = "failed_to_create"


class ValidationCategory(str, Enum):
    """Validation failure categories"""
    SCHEMA = "schema"
    DATA_QUALITY = "data_quality"
    REFERENTIAL_INTEGRITY = "referential_integrity"
    DIMENSION = "dimension"
    FACT = "fact"
    METRIC = "metric"
    TIMESERIES = "timeseries"
    CUSTOM = "custom"


class Bug(BaseModel):
    """Individual bug/validation failure"""
    bug_id: str
    title: str
    description: str
    severity: BugSeverity
    category: ValidationCategory
    status: BugStatus = BugStatus.PENDING_REVIEW

    # Source information
    batch_job_id: str
    run_id: Optional[str] = None
    step_name: str
    validation_type: str

    # Failure details
    table_name: Optional[str] = None
    column_name: Optional[str] = None
    error_message: Optional[str] = None
    expected_value: Optional[str] = None
    actual_value: Optional[str] = None
    row_count: Optional[int] = None
    failure_count: Optional[int] = None
    failure_percentage: Optional[float] = None
    sample_data: Optional[List[Dict[str, Any]]] = None

    # Azure DevOps mapping
    work_item_id: Optional[int] = None
    work_item_url: Optional[str] = None
    azure_devops_response: Optional[Dict[str, Any]] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    reviewed_at: Optional[datetime] = None
    created_in_azure_at: Optional[datetime] = None

    # Metadata
    tags: List[str] = []
    metadata: Optional[Dict[str, Any]] = None


class BugReportSummary(BaseModel):
    """Summary statistics for bug report"""
    total_bugs: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0

    # By category
    schema_failures: int = 0
    data_quality_failures: int = 0
    referential_integrity_failures: int = 0
    dimension_failures: int = 0
    fact_failures: int = 0
    metric_failures: int = 0
    timeseries_failures: int = 0
    custom_failures: int = 0

    # By status
    pending_review: int = 0
    approved: int = 0
    rejected: int = 0
    created_in_azure: int = 0
    failed_to_create: int = 0


class BugReport(BaseModel):
    """Bug report generated from batch execution results"""
    report_id: str
    batch_job_id: str
    batch_job_name: str
    project_id: str
    project_name: str

    # Report metadata
    title: str
    description: Optional[str] = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    generated_by: Optional[str] = None

    # Bugs
    bugs: List[Bug] = []
    summary: BugReportSummary = Field(default_factory=BugReportSummary)

    # Grouping strategies
    group_by: Optional[str] = None  # "severity", "category", "table", "step"
    grouped_bugs: Optional[Dict[str, List[Bug]]] = None

    # Export settings
    include_sample_data: bool = True
    max_samples_per_bug: int = 5

    # Status
    approved_count: int = 0
    submitted_to_azure: bool = False
    azure_submission_timestamp: Optional[datetime] = None

    # Metadata
    tags: List[str] = []
    metadata: Optional[Dict[str, Any]] = None


# Azure DevOps Configuration


class AzureDevOpsWorkItemType(str, Enum):
    """Azure DevOps work item types"""
    BUG = "Bug"
    TASK = "Task"
    USER_STORY = "User Story"
    ISSUE = "Issue"


class AzureDevOpsConfig(BaseModel):
    """Azure DevOps configuration for a project"""
    config_id: str
    project_id: str

    # Connection settings
    organization_url: HttpUrl  # e.g., https://dev.azure.com/myorg
    project_name: str          # Azure DevOps project name
    pat_token: str             # Personal Access Token (encrypted)

    # Work item settings
    work_item_type: AzureDevOpsWorkItemType = AzureDevOpsWorkItemType.BUG
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None
    assigned_to: Optional[str] = None  # Email of default assignee

    # Field mappings (custom fields)
    custom_field_mappings: Optional[Dict[str, str]] = None

    # Auto-tagging
    auto_tags: List[str] = ["ombudsman", "data-validation"]
    tag_prefix: Optional[str] = "OVS-"  # Tag prefix for all bugs

    # Connection status
    is_active: bool = True
    last_tested_at: Optional[datetime] = None
    last_test_status: Optional[str] = None
    last_test_message: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: Optional[str] = None


# Request/Response Models


class GenerateBugReportRequest(BaseModel):
    """Request to generate bug report from batch results"""
    batch_job_id: str
    title: Optional[str] = None
    description: Optional[str] = None
    group_by: Optional[str] = "severity"  # "severity", "category", "table", "step"
    include_sample_data: bool = True
    max_samples_per_bug: int = 5
    severity_threshold: Optional[BugSeverity] = None  # Only include bugs >= this severity


class BugReviewRequest(BaseModel):
    """Request to review and approve/reject bugs"""
    report_id: str
    approved_bug_ids: List[str] = []
    rejected_bug_ids: List[str] = []
    rejection_reasons: Optional[Dict[str, str]] = None  # bug_id -> reason


class SubmitToAzureDevOpsRequest(BaseModel):
    """Request to submit approved bugs to Azure DevOps"""
    report_id: str
    bug_ids: Optional[List[str]] = None  # None = all approved bugs
    work_item_type: Optional[AzureDevOpsWorkItemType] = None
    assigned_to: Optional[str] = None
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None
    additional_tags: List[str] = []


class TestAzureDevOpsConnectionRequest(BaseModel):
    """Request to test Azure DevOps connection"""
    organization_url: HttpUrl
    project_name: str
    pat_token: str


class AzureDevOpsConnectionTestResponse(BaseModel):
    """Response from Azure DevOps connection test"""
    success: bool
    message: str
    organization_name: Optional[str] = None
    project_id: Optional[str] = None
    test_timestamp: datetime = Field(default_factory=datetime.utcnow)
    error_details: Optional[str] = None


class BugReportGenerateResponse(BaseModel):
    """Response after generating bug report"""
    report_id: str
    total_bugs: int
    summary: BugReportSummary
    message: str


class BugReportDownloadFormat(str, Enum):
    """Bug report download formats"""
    PDF = "pdf"
    JSON = "json"
    EXCEL = "excel"
    CSV = "csv"


class AzureDevOpsSubmissionResponse(BaseModel):
    """Response after submitting bugs to Azure DevOps"""
    report_id: str
    submitted_count: int
    failed_count: int
    work_item_ids: List[int] = []
    errors: Optional[Dict[str, str]] = None  # bug_id -> error message
    message: str


class BugReportListResponse(BaseModel):
    """List of bug reports"""
    reports: List[BugReport]
    total: int
    page: int
    page_size: int
