"""
Batch Operations Data Models

Defines schemas for batch jobs, operations, and progress tracking.
"""

from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from enum import Enum


class BatchJobType(str, Enum):
    """Types of batch operations"""
    BULK_PIPELINE_EXECUTION = "bulk_pipeline_execution"
    BATCH_DATA_GENERATION = "batch_data_generation"
    MULTI_PROJECT_VALIDATION = "multi_project_validation"
    BULK_METADATA_EXTRACTION = "bulk_metadata_extraction"
    BATCH_COMPARISON = "batch_comparison"
    CUSTOM = "custom"


class BatchJobStatus(str, Enum):
    """Batch job status"""
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    PARTIAL_SUCCESS = "partial_success"


class BatchOperationStatus(str, Enum):
    """Individual operation status within a batch"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


class BatchOperation(BaseModel):
    """Individual operation within a batch job"""
    operation_id: str
    operation_type: str
    status: BatchOperationStatus = BatchOperationStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class BatchProgress(BaseModel):
    """Progress tracking for batch jobs"""
    total_operations: int
    completed_operations: int
    failed_operations: int
    skipped_operations: int
    current_operation: Optional[str] = None
    percent_complete: float = 0.0
    estimated_time_remaining_ms: Optional[int] = None


class BatchJob(BaseModel):
    """Batch job model"""
    job_id: str
    job_type: BatchJobType
    status: BatchJobStatus = BatchJobStatus.PENDING
    name: str
    description: Optional[str] = None

    # Operations
    operations: List[BatchOperation] = []

    # Progress
    progress: Optional[BatchProgress] = None

    # Execution settings
    parallel_execution: bool = False
    max_parallel: int = 5
    stop_on_error: bool = False
    retry_failed: bool = False
    max_retries: int = 3

    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Results
    total_duration_ms: Optional[int] = None
    success_count: int = 0
    failure_count: int = 0
    result_summary: Optional[Dict[str, Any]] = None

    # Metadata
    created_by: Optional[str] = None
    project_id: Optional[str] = None
    tags: List[str] = []
    metadata: Optional[Dict[str, Any]] = None


# Request models for different batch operations

class PipelineExecutionItem(BaseModel):
    """Single pipeline execution item"""
    pipeline_id: str
    pipeline_name: Optional[str] = None
    config_override: Optional[Dict[str, Any]] = None


class BatchPipelineRequest(BaseModel):
    """Request to execute multiple pipelines"""
    job_name: str
    description: Optional[str] = None
    pipelines: List[PipelineExecutionItem]
    parallel_execution: bool = False
    max_parallel: int = 5
    stop_on_error: bool = False
    project_id: Optional[str] = None
    tags: List[str] = []


class DataGenItem(BaseModel):
    """Single data generation item"""
    schema_type: str  # "Retail", "Finance", "Healthcare"
    table_name: Optional[str] = None
    row_count: int = 1000
    seed: Optional[int] = None


class BatchDataGenRequest(BaseModel):
    """Request to generate data for multiple schemas/tables"""
    job_name: str
    description: Optional[str] = None
    items: List[DataGenItem]
    parallel_execution: bool = True
    max_parallel: int = 3
    project_id: Optional[str] = None
    tags: List[str] = []


class MultiProjectValidationItem(BaseModel):
    """Single project validation item"""
    project_id: str
    pipeline_ids: List[str]


class BatchMultiProjectRequest(BaseModel):
    """Request to validate multiple projects"""
    job_name: str
    description: Optional[str] = None
    projects: List[MultiProjectValidationItem]
    parallel_execution: bool = False
    max_parallel: int = 3
    stop_on_error: bool = False
    tags: List[str] = []


class MetadataExtractionItem(BaseModel):
    """Single metadata extraction item"""
    connection_type: str  # "sqlserver" or "snowflake"
    schema_name: Optional[str] = None
    table_names: Optional[List[str]] = None  # None = all tables


class BatchMetadataRequest(BaseModel):
    """Request to extract metadata from multiple sources"""
    job_name: str
    description: Optional[str] = None
    items: List[MetadataExtractionItem]
    parallel_execution: bool = True
    max_parallel: int = 2
    project_id: Optional[str] = None
    tags: List[str] = []


# Response models

class BatchJobCreateResponse(BaseModel):
    """Response after creating a batch job"""
    job_id: str
    status: BatchJobStatus
    message: str
    total_operations: int


class BatchJobStatusResponse(BaseModel):
    """Batch job status response"""
    job: BatchJob
    current_progress: BatchProgress


class BatchJobListResponse(BaseModel):
    """List of batch jobs"""
    jobs: List[BatchJob]
    total: int
    page: int
    page_size: int


class BatchJobCancelRequest(BaseModel):
    """Request to cancel a batch job"""
    reason: Optional[str] = None
    force: bool = False


class BatchJobRetryRequest(BaseModel):
    """Request to retry failed operations"""
    operation_ids: Optional[List[str]] = None  # None = retry all failed
    max_retries: int = 3
