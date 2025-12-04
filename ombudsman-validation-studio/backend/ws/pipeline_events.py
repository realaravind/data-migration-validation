"""
Pipeline Event Emitter

Emits real-time events during pipeline execution via WebSockets.
"""

import logging
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel

from .connection_manager import connection_manager

logger = logging.getLogger(__name__)


class EventType(str, Enum):
    """Pipeline event types"""
    # Pipeline-level events
    PIPELINE_STARTED = "pipeline_started"
    PIPELINE_RUNNING = "pipeline_running"
    PIPELINE_COMPLETED = "pipeline_completed"
    PIPELINE_FAILED = "pipeline_failed"

    # Step-level events
    STEP_STARTED = "step_started"
    STEP_PROGRESS = "step_progress"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_WARNING = "step_warning"

    # Result events
    RESULT_AVAILABLE = "result_available"
    COMPARISON_GENERATED = "comparison_generated"

    # Status events
    STATUS_UPDATE = "status_update"
    LOG_MESSAGE = "log_message"
    ERROR = "error"


class PipelineEvent(BaseModel):
    """Pipeline event model"""
    type: EventType
    run_id: str
    timestamp: str
    data: Dict[str, Any]
    step_name: Optional[str] = None
    step_order: Optional[int] = None

    class Config:
        use_enum_values = True


class PipelineEventEmitter:
    """
    Emits real-time events during pipeline execution.

    Usage:
        emitter = PipelineEventEmitter(run_id="run_123")
        await emitter.pipeline_started(pipeline_name="My Pipeline")
        await emitter.step_started(step_name="validate_schema", step_order=1)
        await emitter.step_completed(step_name="validate_schema", result={"status": "passed"})
    """

    def __init__(self, run_id: str):
        """
        Initialize event emitter for a pipeline run.

        Args:
            run_id: Pipeline run identifier
        """
        self.run_id = run_id
        self.enabled = True  # Can be disabled for testing

    async def emit(
        self,
        event_type: EventType,
        data: Dict[str, Any],
        step_name: Optional[str] = None,
        step_order: Optional[int] = None
    ):
        """
        Emit an event to all subscribers.

        Args:
            event_type: Type of event
            data: Event data
            step_name: Optional step name for step-level events
            step_order: Optional step order number
        """
        if not self.enabled:
            return

        event = PipelineEvent(
            type=event_type,
            run_id=self.run_id,
            timestamp=datetime.now().isoformat(),
            data=data,
            step_name=step_name,
            step_order=step_order
        )

        try:
            await connection_manager.broadcast_to_run(
                self.run_id,
                event.dict()
            )
            logger.debug(f"Emitted event {event_type} for run {self.run_id}")
        except Exception as e:
            logger.error(f"Failed to emit event {event_type} for run {self.run_id}: {e}")

    # ========================================================================
    # Pipeline-level events
    # ========================================================================

    async def pipeline_started(
        self,
        pipeline_name: str,
        total_steps: int = 0,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Emit pipeline started event.

        Args:
            pipeline_name: Name of the pipeline
            total_steps: Total number of steps
            config: Optional pipeline configuration
        """
        await self.emit(
            EventType.PIPELINE_STARTED,
            {
                "run_id": self.run_id,
                "pipeline_name": pipeline_name,
                "total_steps": total_steps,
                "status": "running",
                "config": config
            }
        )

    async def pipeline_completed(
        self,
        pipeline_name: str,
        duration_seconds: int,
        total_steps: int,
        successful_steps: int,
        failed_steps: int,
        warnings_count: int = 0
    ):
        """
        Emit pipeline completed event.

        Args:
            pipeline_name: Name of the pipeline
            duration_seconds: Total execution time
            total_steps: Total number of steps
            successful_steps: Number of successful steps
            failed_steps: Number of failed steps
            warnings_count: Number of warnings
        """
        await self.emit(
            EventType.PIPELINE_COMPLETED,
            {
                "run_id": self.run_id,
                "pipeline_name": pipeline_name,
                "status": "completed",
                "duration_seconds": duration_seconds,
                "summary": {
                    "total_steps": total_steps,
                    "successful_steps": successful_steps,
                    "failed_steps": failed_steps,
                    "warnings_count": warnings_count,
                    "success_rate": (successful_steps / max(total_steps, 1)) * 100
                }
            }
        )

    async def pipeline_failed(
        self,
        pipeline_name: str,
        error_message: str,
        duration_seconds: Optional[int] = None
    ):
        """
        Emit pipeline failed event.

        Args:
            pipeline_name: Name of the pipeline
            error_message: Error description
            duration_seconds: Execution time before failure
        """
        await self.emit(
            EventType.PIPELINE_FAILED,
            {
                "run_id": self.run_id,
                "pipeline_name": pipeline_name,
                "status": "failed",
                "error_message": error_message,
                "duration_seconds": duration_seconds
            }
        )

    # ========================================================================
    # Step-level events
    # ========================================================================

    async def step_started(
        self,
        step_name: str,
        step_order: int,
        validator_type: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Emit step started event.

        Args:
            step_name: Name of the validation step
            step_order: Step sequence number (0-indexed)
            validator_type: Type of validator
            config: Step configuration
        """
        await self.emit(
            EventType.STEP_STARTED,
            {
                "step_name": step_name,
                "status": "running",
                "validator_type": validator_type,
                "config": config
            },
            step_name=step_name,
            step_order=step_order
        )

    async def step_progress(
        self,
        step_name: str,
        step_order: int,
        progress_percentage: float,
        message: Optional[str] = None
    ):
        """
        Emit step progress event.

        Args:
            step_name: Name of the validation step
            step_order: Step sequence number
            progress_percentage: Progress percentage (0-100)
            message: Optional progress message
        """
        await self.emit(
            EventType.STEP_PROGRESS,
            {
                "step_name": step_name,
                "progress_percentage": min(100, max(0, progress_percentage)),
                "message": message
            },
            step_name=step_name,
            step_order=step_order
        )

    async def step_completed(
        self,
        step_name: str,
        step_order: int,
        status: str,
        result: Optional[Dict[str, Any]] = None,
        duration_ms: Optional[int] = None
    ):
        """
        Emit step completed event.

        Args:
            step_name: Name of the validation step
            step_order: Step sequence number
            status: Step status (passed, failed, warning)
            result: Step result data
            duration_ms: Execution time in milliseconds
        """
        await self.emit(
            EventType.STEP_COMPLETED,
            {
                "step_name": step_name,
                "status": status,
                "result": result,
                "duration_ms": duration_ms
            },
            step_name=step_name,
            step_order=step_order
        )

    async def step_failed(
        self,
        step_name: str,
        step_order: int,
        error_message: str,
        duration_ms: Optional[int] = None
    ):
        """
        Emit step failed event.

        Args:
            step_name: Name of the validation step
            step_order: Step sequence number
            error_message: Error description
            duration_ms: Execution time before failure
        """
        await self.emit(
            EventType.STEP_FAILED,
            {
                "step_name": step_name,
                "status": "failed",
                "error_message": error_message,
                "duration_ms": duration_ms
            },
            step_name=step_name,
            step_order=step_order
        )

    async def step_warning(
        self,
        step_name: str,
        step_order: int,
        warning_message: str
    ):
        """
        Emit step warning event.

        Args:
            step_name: Name of the validation step
            step_order: Step sequence number
            warning_message: Warning description
        """
        await self.emit(
            EventType.STEP_WARNING,
            {
                "step_name": step_name,
                "status": "warning",
                "message": warning_message
            },
            step_name=step_name,
            step_order=step_order
        )

    # ========================================================================
    # Result events
    # ========================================================================

    async def result_available(
        self,
        step_name: str,
        step_order: int,
        result_summary: Dict[str, Any]
    ):
        """
        Emit result available event.

        Args:
            step_name: Name of the validation step
            step_order: Step sequence number
            result_summary: Summary of validation results
        """
        await self.emit(
            EventType.RESULT_AVAILABLE,
            {
                "step_name": step_name,
                "result_summary": result_summary
            },
            step_name=step_name,
            step_order=step_order
        )

    async def comparison_generated(
        self,
        step_name: str,
        step_order: int,
        comparison_type: str,
        total_rows: int,
        differing_rows: int,
        match_percentage: float
    ):
        """
        Emit comparison generated event.

        Args:
            step_name: Name of the validation step
            step_order: Step sequence number
            comparison_type: Type of comparison
            total_rows: Total rows compared
            differing_rows: Number of differing rows
            match_percentage: Percentage of matching rows
        """
        await self.emit(
            EventType.COMPARISON_GENERATED,
            {
                "step_name": step_name,
                "comparison_type": comparison_type,
                "total_rows": total_rows,
                "differing_rows": differing_rows,
                "match_percentage": match_percentage
            },
            step_name=step_name,
            step_order=step_order
        )

    # ========================================================================
    # Status and logging events
    # ========================================================================

    async def status_update(
        self,
        status: str,
        message: str,
        step_name: Optional[str] = None
    ):
        """
        Emit general status update.

        Args:
            status: Status value
            message: Status message
            step_name: Optional step name
        """
        await self.emit(
            EventType.STATUS_UPDATE,
            {
                "status": status,
                "message": message
            },
            step_name=step_name
        )

    async def log_message(
        self,
        level: str,
        message: str,
        step_name: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Emit log message.

        Args:
            level: Log level (DEBUG, INFO, WARNING, ERROR)
            message: Log message
            step_name: Optional step name
            context: Optional additional context
        """
        await self.emit(
            EventType.LOG_MESSAGE,
            {
                "level": level,
                "message": message,
                "context": context
            },
            step_name=step_name
        )

    async def error(
        self,
        error_message: str,
        error_type: Optional[str] = None,
        step_name: Optional[str] = None
    ):
        """
        Emit error event.

        Args:
            error_message: Error description
            error_type: Type/class of error
            step_name: Optional step name
        """
        await self.emit(
            EventType.ERROR,
            {
                "error_message": error_message,
                "error_type": error_type
            },
            step_name=step_name
        )
