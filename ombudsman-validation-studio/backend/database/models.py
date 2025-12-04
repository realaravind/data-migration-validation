"""
Database Models for Results Persistence

Pydantic models representing the database schema for pipeline execution results.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class PipelineStatus(str, Enum):
    """Pipeline execution status"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class StepStatus(str, Enum):
    """Validation step status"""
    PASSED = "passed"
    FAILED = "failed"
    WARNING = "warning"
    SKIPPED = "skipped"


class LogLevel(str, Enum):
    """Log level"""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


# ============================================================================
# Database Models
# ============================================================================

class Project(BaseModel):
    """Validation project/workspace"""
    project_id: str
    project_name: str
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    created_by: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: bool = True

    class Config:
        from_attributes = True


class PipelineRun(BaseModel):
    """Pipeline execution record"""
    run_id: str
    project_id: Optional[str] = None
    pipeline_name: str
    status: PipelineStatus
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    pipeline_config: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    total_steps: int = 0
    successful_steps: int = 0
    failed_steps: int = 0
    warnings_count: int = 0
    errors_count: int = 0
    executed_by: Optional[str] = None

    class Config:
        from_attributes = True


class ValidationStep(BaseModel):
    """Individual validation step result"""
    step_id: Optional[int] = None  # Auto-generated
    run_id: str
    step_name: str
    step_order: Optional[int] = None
    validator_type: Optional[str] = None
    status: StepStatus
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    duration_milliseconds: Optional[int] = None

    # Results
    result_message: Optional[str] = None
    difference_type: Optional[str] = None
    total_rows: Optional[int] = None
    differing_rows_count: Optional[int] = None
    affected_columns: Optional[List[str]] = None
    comparison_details: Optional[Dict[str, Any]] = None

    # Metrics
    sql_row_count: Optional[int] = None
    snowflake_row_count: Optional[int] = None
    match_percentage: Optional[float] = None

    # Configuration
    step_config: Optional[Dict[str, Any]] = None

    # Error details
    error_message: Optional[str] = None
    error_stack_trace: Optional[str] = None

    class Config:
        from_attributes = True


class ExecutionLog(BaseModel):
    """Execution log entry"""
    log_id: Optional[int] = None  # Auto-generated
    run_id: str
    step_id: Optional[int] = None
    log_level: LogLevel
    message: str
    timestamp: datetime = Field(default_factory=datetime.now)
    context: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True


class DataQualityMetrics(BaseModel):
    """Aggregate data quality metrics"""
    metric_id: Optional[int] = None  # Auto-generated
    run_id: str
    metric_date: datetime = Field(default_factory=lambda: datetime.now().date())

    # Overall metrics
    total_tables_validated: Optional[int] = None
    total_rows_compared: Optional[int] = None
    total_mismatches: Optional[int] = None
    overall_match_percentage: Optional[float] = None

    # Category breakdowns
    schema_validations: Optional[int] = None
    data_validations: Optional[int] = None
    business_rule_validations: Optional[int] = None

    # Error categories
    critical_errors: Optional[int] = None
    warnings: Optional[int] = None
    info_messages: Optional[int] = None

    # Performance metrics
    total_execution_time_seconds: Optional[int] = None
    avg_step_execution_time_ms: Optional[int] = None

    # Computed scores
    data_quality_score: Optional[float] = None
    completeness_score: Optional[float] = None
    consistency_score: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        from_attributes = True


# ============================================================================
# Request/Response Models
# ============================================================================

class ProjectCreate(BaseModel):
    """Request model for creating a project"""
    project_id: str
    project_name: str
    description: Optional[str] = None
    created_by: Optional[str] = None
    tags: Optional[List[str]] = None


class ProjectUpdate(BaseModel):
    """Request model for updating a project"""
    project_name: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[List[str]] = None
    is_active: Optional[bool] = None


class PipelineRunCreate(BaseModel):
    """Request model for creating a pipeline run"""
    run_id: str
    project_id: Optional[str] = None
    pipeline_name: str
    pipeline_config: Optional[Dict[str, Any]] = None
    executed_by: Optional[str] = None


class PipelineRunUpdate(BaseModel):
    """Request model for updating a pipeline run"""
    status: Optional[PipelineStatus] = None
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    error_message: Optional[str] = None
    total_steps: Optional[int] = None
    successful_steps: Optional[int] = None
    failed_steps: Optional[int] = None
    warnings_count: Optional[int] = None
    errors_count: Optional[int] = None


class ValidationStepCreate(BaseModel):
    """Request model for creating a validation step"""
    run_id: str
    step_name: str
    step_order: Optional[int] = None
    validator_type: Optional[str] = None
    step_config: Optional[Dict[str, Any]] = None


class ValidationStepUpdate(BaseModel):
    """Request model for updating a validation step"""
    status: Optional[StepStatus] = None
    completed_at: Optional[datetime] = None
    duration_milliseconds: Optional[int] = None
    result_message: Optional[str] = None
    difference_type: Optional[str] = None
    total_rows: Optional[int] = None
    differing_rows_count: Optional[int] = None
    affected_columns: Optional[List[str]] = None
    comparison_details: Optional[Dict[str, Any]] = None
    sql_row_count: Optional[int] = None
    snowflake_row_count: Optional[int] = None
    match_percentage: Optional[float] = None
    error_message: Optional[str] = None
    error_stack_trace: Optional[str] = None


class PipelineRunHistory(BaseModel):
    """Response model for pipeline run history"""
    run_id: str
    project_id: Optional[str] = None
    project_name: Optional[str] = None
    pipeline_name: str
    status: PipelineStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_seconds: Optional[int] = None
    total_steps: int
    successful_steps: int
    failed_steps: int
    errors_count: int
    warnings_count: int
    result_status: str  # success, completed_with_errors, failed, pending, running

    class Config:
        from_attributes = True


class ValidationStepDetail(BaseModel):
    """Response model for validation step details"""
    step_id: int
    run_id: str
    pipeline_name: str
    project_id: Optional[str] = None
    step_name: str
    step_order: Optional[int] = None
    validator_type: Optional[str] = None
    status: StepStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_milliseconds: Optional[int] = None
    difference_type: Optional[str] = None
    total_rows: Optional[int] = None
    differing_rows_count: Optional[int] = None
    match_percentage: Optional[float] = None
    result_message: Optional[str] = None
    run_started_at: datetime

    class Config:
        from_attributes = True


class DailyQualityTrend(BaseModel):
    """Response model for daily quality trend"""
    metric_date: datetime
    total_runs: int
    avg_quality_score: Optional[float] = None
    total_mismatches: Optional[int] = None
    avg_match_percentage: Optional[float] = None
    total_critical_errors: Optional[int] = None
    total_warnings: Optional[int] = None

    class Config:
        from_attributes = True
