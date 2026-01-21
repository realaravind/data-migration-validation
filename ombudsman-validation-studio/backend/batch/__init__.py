"""
Batch Operations Module

Provides batch execution capabilities for:
- Bulk pipeline execution
- Batch data generation
- Multi-project operations
- Progress tracking
"""

from .models import (
    BatchJob,
    BatchJobStatus,
    BatchJobType,
    BatchPipelineRequest,
    BatchDataGenRequest,
    BatchOperation
)

from .job_manager import BatchJobManager
from .executor import BatchExecutor

__all__ = [
    "BatchJob",
    "BatchJobStatus",
    "BatchJobType",
    "BatchPipelineRequest",
    "BatchDataGenRequest",
    "BatchOperation",
    "BatchJobManager",
    "BatchExecutor"
]
