"""
Batch Job Manager

Manages the lifecycle of batch jobs:
- Job creation and storage
- Job queue management
- Job execution coordination
- Progress tracking
"""

import os
import json
import uuid
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from threading import Thread, Lock

from config.paths import paths
from .models import (
    BatchJob,
    BatchJobStatus,
    BatchJobType,
    BatchOperation,
    BatchOperationStatus,
    BatchProgress
)

logger = logging.getLogger(__name__)

# Store reference to the main event loop for thread-safe WebSocket broadcasts
_main_event_loop = None


def set_main_event_loop(loop):
    """Set the main event loop for WebSocket broadcasts from background threads."""
    global _main_event_loop
    _main_event_loop = loop
    logger.info(f"Main event loop set for WebSocket broadcasts: {loop}")


def _broadcast_job_update_sync(job: 'BatchJob'):
    """Broadcast job update via WebSocket (called from sync code, potentially from background thread)."""
    try:
        from .websocket import job_update_manager

        # Create job data for broadcast
        job_data = {
            "job_id": job.job_id,
            "status": job.status.value if hasattr(job.status, 'value') else str(job.status),
            "name": job.name,
            "project_id": job.project_id,
            "progress": {
                "total_operations": job.progress.total_operations if job.progress else 0,
                "completed_operations": job.progress.completed_operations if job.progress else 0,
                "failed_operations": job.progress.failed_operations if job.progress else 0,
                "percent_complete": job.progress.percent_complete if job.progress else 0,
            } if job.progress else None,
            "success_count": job.success_count,
            "failure_count": job.failure_count,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "total_duration_ms": job.total_duration_ms,
        }

        logger.info(f"[WebSocket] Broadcasting job update: {job.job_id} status={job_data['status']} progress={job_data['progress']}")

        # Try to use the main event loop if we're in a background thread
        try:
            loop = asyncio.get_running_loop()
            # We're in an async context (main thread), schedule directly
            asyncio.create_task(job_update_manager.broadcast_job_update(job_data, job.project_id))
        except RuntimeError:
            # No running loop in this thread - use the main event loop
            if _main_event_loop and _main_event_loop.is_running():
                # Schedule coroutine in the main event loop (thread-safe)
                future = asyncio.run_coroutine_threadsafe(
                    job_update_manager.broadcast_job_update(job_data, job.project_id),
                    _main_event_loop
                )
                # Wait for it to complete (with timeout)
                try:
                    future.result(timeout=5.0)
                    logger.info(f"[WebSocket] Broadcast successful for job {job.job_id}")
                except Exception as e:
                    logger.warning(f"[WebSocket] Broadcast timed out or failed: {e}")
            else:
                logger.warning(f"[WebSocket] No main event loop available for broadcast")

    except Exception as e:
        logger.warning(f"Failed to broadcast job update: {e}")
        import traceback
        logger.warning(traceback.format_exc())


class BatchJobManager:
    """
    Singleton manager for batch jobs.

    Handles job storage, queue management, and coordination.
    """

    _instance = None
    _lock = Lock()
    _jobs: Dict[str, BatchJob] = {}
    _job_storage_dir = None

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(BatchJobManager, cls).__new__(cls)
                    cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        """Initialize the job manager"""
        # Set storage directory from centralized config
        self._job_storage_dir = paths.batch_jobs_dir
        self._job_storage_dir.mkdir(parents=True, exist_ok=True)

        # Load existing jobs from storage
        self._load_jobs()

    def _load_jobs(self):
        """Load existing jobs from storage"""
        try:
            for job_file in self._job_storage_dir.glob("*.json"):
                with open(job_file, 'r') as f:
                    job_data = json.load(f)
                    job = BatchJob(**job_data)
                    self._jobs[job.job_id] = job

            print(f"Loaded {len(self._jobs)} batch jobs from storage")
        except Exception as e:
            print(f"Error loading batch jobs: {e}")

    def _save_job(self, job: BatchJob):
        """Save job to storage"""
        try:
            job_file = self._job_storage_dir / f"{job.job_id}.json"
            with open(job_file, 'w') as f:
                json.dump(job.model_dump(), f, default=str, indent=2)
        except Exception as e:
            print(f"Error saving batch job {job.job_id}: {e}")

    def create_job(
        self,
        job_type: BatchJobType,
        name: str,
        operations: List[BatchOperation],
        description: Optional[str] = None,
        parallel_execution: bool = False,
        max_parallel: int = 5,
        stop_on_error: bool = False,
        project_id: Optional[str] = None,
        tags: List[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> BatchJob:
        """
        Create a new batch job.

        Args:
            job_type: Type of batch operation
            name: Job name
            operations: List of operations to execute
            description: Optional description
            parallel_execution: Execute operations in parallel
            max_parallel: Max parallel operations
            stop_on_error: Stop batch on first error
            project_id: Associated project ID
            tags: Job tags
            metadata: Additional metadata

        Returns:
            Created batch job
        """
        job_id = str(uuid.uuid4())

        # Calculate initial progress
        progress = BatchProgress(
            total_operations=len(operations),
            completed_operations=0,
            failed_operations=0,
            skipped_operations=0,
            percent_complete=0.0
        )

        job = BatchJob(
            job_id=job_id,
            job_type=job_type,
            status=BatchJobStatus.PENDING,
            name=name,
            description=description,
            operations=operations,
            progress=progress,
            parallel_execution=parallel_execution,
            max_parallel=max_parallel,
            stop_on_error=stop_on_error,
            project_id=project_id,
            tags=tags or [],
            metadata=metadata
        )

        # Store job
        with self._lock:
            self._jobs[job_id] = job
            self._save_job(job)

        # Broadcast new job via WebSocket
        _broadcast_job_update_sync(job)

        return job

    def get_job(self, job_id: str) -> Optional[BatchJob]:
        """Get job by ID"""
        return self._jobs.get(job_id)

    def update_job(self, job: BatchJob):
        """Update job state"""
        with self._lock:
            self._jobs[job.job_id] = job
            self._save_job(job)

    def update_job_status(self, job_id: str, status: BatchJobStatus, broadcast: bool = True):
        """Update job status and optionally broadcast via WebSocket"""
        job = self.get_job(job_id)
        if job:
            job.status = status

            if status == BatchJobStatus.RUNNING and not job.started_at:
                job.started_at = datetime.utcnow()
                # Initialize progress when job starts
                if not job.progress:
                    job.progress = BatchProgress(
                        total_operations=len(job.operations),
                        completed_operations=0,
                        failed_operations=0,
                        skipped_operations=0,
                        current_operation=None,
                        percent_complete=0.0
                    )
            elif status in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED, BatchJobStatus.CANCELLED]:
                job.completed_at = datetime.utcnow()
                if job.started_at:
                    duration = (job.completed_at - job.started_at).total_seconds() * 1000
                    job.total_duration_ms = int(duration)

            self.update_job(job)

            # Broadcast update via WebSocket
            if broadcast:
                _broadcast_job_update_sync(job)

    def update_operation_status(
        self,
        job_id: str,
        operation_id: str,
        status: BatchOperationStatus,
        result: Optional[Dict[str, Any]] = None,
        error: Optional[str] = None,
        broadcast: bool = True
    ):
        """Update individual operation status and optionally broadcast via WebSocket"""
        job = self.get_job(job_id)
        if not job:
            return

        # Find and update operation
        for op in job.operations:
            if op.operation_id == operation_id:
                op.status = status

                if status == BatchOperationStatus.RUNNING:
                    op.started_at = datetime.utcnow()
                elif status in [BatchOperationStatus.COMPLETED, BatchOperationStatus.FAILED, BatchOperationStatus.SKIPPED]:
                    op.completed_at = datetime.utcnow()
                    if op.started_at:
                        duration = (op.completed_at - op.started_at).total_seconds() * 1000
                        op.duration_ms = int(duration)

                if result:
                    op.result = result
                if error:
                    op.error = error

                break

        # Update progress
        self._update_progress(job)
        self.update_job(job)

        # Broadcast progress update via WebSocket
        if broadcast:
            _broadcast_job_update_sync(job)

    def _update_progress(self, job: BatchJob):
        """Update job progress based on operation statuses"""
        total = len(job.operations)
        completed = sum(1 for op in job.operations if op.status == BatchOperationStatus.COMPLETED)
        failed = sum(1 for op in job.operations if op.status == BatchOperationStatus.FAILED)
        skipped = sum(1 for op in job.operations if op.status == BatchOperationStatus.SKIPPED)

        # Find current running operation
        current_op = next(
            (op.operation_id for op in job.operations if op.status == BatchOperationStatus.RUNNING),
            None
        )

        # Calculate percent complete
        finished = completed + failed + skipped
        percent = (finished / total * 100) if total > 0 else 0

        print(f"[JOB MANAGER] Progress update for {job.job_id}: {finished}/{total} = {percent:.1f}% (completed={completed}, failed={failed})")

        # Estimate time remaining
        estimated_remaining = None
        if job.started_at and completed > 0:
            elapsed = (datetime.utcnow() - job.started_at).total_seconds() * 1000
            avg_time_per_op = elapsed / completed
            remaining_ops = total - finished
            estimated_remaining = int(avg_time_per_op * remaining_ops)

        job.progress = BatchProgress(
            total_operations=total,
            completed_operations=completed,
            failed_operations=failed,
            skipped_operations=skipped,
            current_operation=current_op,
            percent_complete=round(percent, 2),
            estimated_time_remaining_ms=estimated_remaining
        )

        # Update success/failure counts
        job.success_count = completed
        job.failure_count = failed

    def list_jobs(
        self,
        status: Optional[BatchJobStatus] = None,
        job_type: Optional[BatchJobType] = None,
        project_id: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
        return_total: bool = False
    ) -> List[BatchJob]:
        """
        List batch jobs with filtering.

        Args:
            status: Filter by status
            job_type: Filter by type
            project_id: Filter by project
            limit: Max results
            offset: Offset for pagination
            return_total: If True, returns tuple (jobs, total_count)

        Returns:
            List of matching jobs, or tuple (jobs, total) if return_total=True
        """
        jobs = list(self._jobs.values())

        # Apply filters
        if status:
            jobs = [j for j in jobs if j.status == status]
        if job_type:
            jobs = [j for j in jobs if j.job_type == job_type]
        if project_id:
            jobs = [j for j in jobs if j.project_id == project_id]

        # Sort by created_at descending
        jobs.sort(key=lambda j: j.created_at, reverse=True)

        total = len(jobs)

        # Pagination
        paginated = jobs[offset:offset + limit]

        if return_total:
            return paginated, total
        return paginated

    def cancel_job(self, job_id: str, reason: Optional[str] = None) -> bool:
        """
        Cancel a batch job.

        Args:
            job_id: Job to cancel
            reason: Cancellation reason

        Returns:
            True if cancelled successfully
        """
        job = self.get_job(job_id)
        if not job:
            return False

        if job.status in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED, BatchJobStatus.CANCELLED]:
            return False  # Already finished

        # Update status
        self.update_job_status(job_id, BatchJobStatus.CANCELLED)

        # Mark pending/running operations as skipped
        for op in job.operations:
            if op.status in [BatchOperationStatus.PENDING, BatchOperationStatus.RUNNING]:
                op.status = BatchOperationStatus.SKIPPED
                if reason:
                    op.error = f"Cancelled: {reason}"

        self.update_job(job)
        return True

    def delete_job(self, job_id: str) -> bool:
        """Delete a batch job"""
        if job_id not in self._jobs:
            return False

        # Remove from memory
        with self._lock:
            del self._jobs[job_id]

        # Remove from storage
        try:
            job_file = self._job_storage_dir / f"{job_id}.json"
            if job_file.exists():
                job_file.unlink()
        except Exception as e:
            print(f"Error deleting batch job file {job_id}: {e}")

        return True

    def get_statistics(self) -> Dict[str, Any]:
        """Get batch job statistics"""
        total_jobs = len(self._jobs)

        status_counts = {}
        for status in BatchJobStatus:
            count = sum(1 for j in self._jobs.values() if j.status == status)
            status_counts[status.value] = count

        type_counts = {}
        for job_type in BatchJobType:
            count = sum(1 for j in self._jobs.values() if j.job_type == job_type)
            type_counts[job_type.value] = count

        # Recent activity
        recent_jobs = sorted(
            self._jobs.values(),
            key=lambda j: j.created_at,
            reverse=True
        )[:10]

        return {
            "total_jobs": total_jobs,
            "status_distribution": status_counts,
            "type_distribution": type_counts,
            "active_jobs": status_counts.get(BatchJobStatus.RUNNING.value, 0),
            "recent_jobs": [
                {
                    "job_id": j.job_id,
                    "name": j.name,
                    "status": j.status,
                    "created_at": j.created_at.isoformat()
                }
                for j in recent_jobs
            ]
        }


# Global instance
batch_job_manager = BatchJobManager()
