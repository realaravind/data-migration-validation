"""
Database Package for Results Persistence

Provides database models and repository for storing pipeline execution results.
"""

from .models import (
    # Enums
    PipelineStatus,
    StepStatus,
    LogLevel,

    # Models
    Project,
    PipelineRun,
    ValidationStep,
    ExecutionLog,
    DataQualityMetrics,

    # Request/Response Models
    ProjectCreate,
    ProjectUpdate,
    PipelineRunCreate,
    PipelineRunUpdate,
    ValidationStepCreate,
    ValidationStepUpdate,
    PipelineRunHistory,
    ValidationStepDetail,
    DailyQualityTrend,
)

from .repository import ResultsRepository

__all__ = [
    # Enums
    "PipelineStatus",
    "StepStatus",
    "LogLevel",

    # Models
    "Project",
    "PipelineRun",
    "ValidationStep",
    "ExecutionLog",
    "DataQualityMetrics",

    # Request/Response Models
    "ProjectCreate",
    "ProjectUpdate",
    "PipelineRunCreate",
    "PipelineRunUpdate",
    "ValidationStepCreate",
    "ValidationStepUpdate",
    "PipelineRunHistory",
    "ValidationStepDetail",
    "DailyQualityTrend",

    # Repository
    "ResultsRepository",
]
