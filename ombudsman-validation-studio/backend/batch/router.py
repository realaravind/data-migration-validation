"""
Batch Operations API Router

Provides REST API endpoints for batch job management, execution, and monitoring.
"""

from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect
from typing import List, Optional
from datetime import datetime

from .models import (
    BatchPipelineRequest,
    BatchDataGenRequest,
    BatchMultiProjectRequest,
    BatchMetadataRequest,
    BatchJob,
    BatchJobStatus,
    BatchJobType,
    BatchOperation,
    BatchOperationStatus,
    BatchJobCreateResponse,
    BatchJobStatusResponse,
    BatchJobListResponse,
    BatchJobCancelRequest,
    BatchJobRetryRequest,
    PipelineExecutionItem,
    DataGenItem,
    MetadataExtractionItem,
    MultiProjectValidationItem
)
from .job_manager import batch_job_manager
from .executor import batch_executor
from .websocket import job_update_manager


router = APIRouter()


# WebSocket endpoint for real-time job updates
@router.websocket("/ws/{project_id}")
async def websocket_job_updates(websocket: WebSocket, project_id: str):
    """WebSocket endpoint for real-time job updates for a specific project."""
    await job_update_manager.connect(websocket, project_id)
    try:
        while True:
            # Keep connection alive, handle any client messages
            data = await websocket.receive_text()
            # Client can send ping/pong for keepalive
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        job_update_manager.disconnect(websocket, project_id)


@router.websocket("/ws")
async def websocket_global_updates(websocket: WebSocket):
    """WebSocket endpoint for real-time job updates (all projects)."""
    await job_update_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        job_update_manager.disconnect(websocket)


# Job Creation Endpoints

@router.post("/pipelines/bulk-execute", response_model=BatchJobCreateResponse)
def bulk_execute_pipelines(request: BatchPipelineRequest):
    """
    Execute multiple pipelines in bulk.

    Creates a batch job that executes the specified pipelines either
    sequentially or in parallel based on the configuration.

    Example:
    ```json
    {
      "job_name": "Daily Validation Suite",
      "pipelines": [
        {"pipeline_id": "dim_customer_validation"},
        {"pipeline_id": "fact_sales_validation"}
      ],
      "parallel_execution": true,
      "max_parallel": 3,
      "stop_on_error": false,
      "project_id": "retail_migration"
    }
    ```
    """
    try:
        import yaml
        from config.paths import paths

        # Create operations for each pipeline (expand batch files)
        operations = []
        op_idx = 0

        for pipeline_item in request.pipelines:
            pipeline_id = pipeline_item.pipeline_id.replace(".yaml", "").replace(".yml", "")

            # Check if this is a batch file by reading it
            pipeline_path = paths.results_dir / "pipelines" / f"{pipeline_id}.yaml"
            is_batch_file = False
            nested_pipelines = []

            if pipeline_path.exists():
                try:
                    with open(pipeline_path) as f:
                        parsed_yaml = yaml.safe_load(f)
                    if parsed_yaml and "batch" in parsed_yaml and "batch" not in parsed_yaml.get("pipeline", {}):
                        is_batch_file = True
                        batch_def = parsed_yaml["batch"]
                        nested_pipelines = batch_def.get("pipelines", [])
                except Exception:
                    pass  # If we can't parse, treat as regular pipeline

            if is_batch_file and nested_pipelines:
                # Expand batch file into individual pipeline operations
                for nested_item in nested_pipelines:
                    nested_file = nested_item.get("file", "")
                    nested_id = nested_file.replace(".yaml", "").replace(".yml", "")
                    if nested_id:
                        operation = BatchOperation(
                            operation_id=f"pipeline_{op_idx}_{nested_id}",
                            operation_type="pipeline_execution",
                            status=BatchOperationStatus.PENDING,
                            metadata={
                                "pipeline_id": nested_id,
                                "pipeline_name": nested_id,
                                "config_override": pipeline_item.config_override or {},
                                "from_batch": pipeline_id  # Track source batch file
                            }
                        )
                        operations.append(operation)
                        op_idx += 1
            else:
                # Regular pipeline
                operation = BatchOperation(
                    operation_id=f"pipeline_{op_idx}_{pipeline_id}",
                    operation_type="pipeline_execution",
                    status=BatchOperationStatus.PENDING,
                    metadata={
                        "pipeline_id": pipeline_id,
                        "pipeline_name": pipeline_item.pipeline_name or pipeline_id,
                        "config_override": pipeline_item.config_override or {}
                    }
                )
                operations.append(operation)
                op_idx += 1

        # Create batch job
        job = batch_job_manager.create_job(
            job_type=BatchJobType.BULK_PIPELINE_EXECUTION,
            name=request.job_name,
            operations=operations,
            description=request.description,
            parallel_execution=request.parallel_execution,
            max_parallel=request.max_parallel,
            stop_on_error=request.stop_on_error,
            project_id=request.project_id,
            tags=request.tags
        )

        # Start execution asynchronously
        batch_executor.execute_job_async(job.job_id)

        return BatchJobCreateResponse(
            job_id=job.job_id,
            status=job.status,
            message=f"Batch pipeline execution job created with {len(operations)} pipelines",
            total_operations=len(operations)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/data/bulk-generate", response_model=BatchJobCreateResponse)
def bulk_generate_data(request: BatchDataGenRequest):
    """
    Generate sample data for multiple schemas/tables in bulk.

    Creates a batch job that generates test data for the specified
    schemas and tables.

    Example:
    ```json
    {
      "job_name": "Generate Test Data",
      "items": [
        {"schema_type": "Retail", "row_count": 10000},
        {"schema_type": "Finance", "row_count": 5000}
      ],
      "parallel_execution": true,
      "max_parallel": 2
    }
    ```
    """
    try:
        # Create operations for each data generation item
        operations = []
        for idx, item in enumerate(request.items):
            operation = BatchOperation(
                operation_id=f"datagen_{idx}_{item.schema_type}",
                operation_type="data_generation",
                status=BatchOperationStatus.PENDING,
                metadata={
                    "schema_type": item.schema_type,
                    "table_name": item.table_name,
                    "row_count": item.row_count,
                    "seed": item.seed
                }
            )
            operations.append(operation)

        # Create batch job
        job = batch_job_manager.create_job(
            job_type=BatchJobType.BATCH_DATA_GENERATION,
            name=request.job_name,
            operations=operations,
            description=request.description,
            parallel_execution=request.parallel_execution,
            max_parallel=request.max_parallel,
            project_id=request.project_id,
            tags=request.tags
        )

        # Start execution asynchronously
        batch_executor.execute_job_async(job.job_id)

        return BatchJobCreateResponse(
            job_id=job.job_id,
            status=job.status,
            message=f"Batch data generation job created with {len(operations)} items",
            total_operations=len(operations)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/projects/multi-validate", response_model=BatchJobCreateResponse)
def multi_project_validate(request: BatchMultiProjectRequest):
    """
    Validate multiple projects in bulk.

    Creates a batch job that runs validation pipelines across
    multiple projects.

    Example:
    ```json
    {
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
      "parallel_execution": false,
      "stop_on_error": false
    }
    ```
    """
    try:
        # Create operations for each project
        operations = []
        for idx, project in enumerate(request.projects):
            operation = BatchOperation(
                operation_id=f"project_{idx}_{project.project_id}",
                operation_type="project_validation",
                status=BatchOperationStatus.PENDING,
                metadata={
                    "project_id": project.project_id,
                    "pipeline_ids": project.pipeline_ids
                }
            )
            operations.append(operation)

        # Create batch job
        job = batch_job_manager.create_job(
            job_type=BatchJobType.MULTI_PROJECT_VALIDATION,
            name=request.job_name,
            operations=operations,
            description=request.description,
            parallel_execution=request.parallel_execution,
            max_parallel=request.max_parallel,
            stop_on_error=request.stop_on_error,
            tags=request.tags
        )

        # Start execution asynchronously
        batch_executor.execute_job_async(job.job_id)

        return BatchJobCreateResponse(
            job_id=job.job_id,
            status=job.status,
            message=f"Multi-project validation job created with {len(operations)} projects",
            total_operations=len(operations)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/metadata/bulk-extract", response_model=BatchJobCreateResponse)
def bulk_extract_metadata(request: BatchMetadataRequest):
    """
    Extract metadata from multiple sources in bulk.

    Creates a batch job that extracts table and column metadata
    from multiple database connections.

    Example:
    ```json
    {
      "job_name": "Extract All Metadata",
      "items": [
        {"connection_type": "sqlserver", "schema_name": "dbo"},
        {"connection_type": "snowflake", "schema_name": "PUBLIC"}
      ],
      "parallel_execution": true,
      "max_parallel": 2
    }
    ```
    """
    try:
        # Create operations for each metadata extraction
        operations = []
        for idx, item in enumerate(request.items):
            operation = BatchOperation(
                operation_id=f"metadata_{idx}_{item.connection_type}_{item.schema_name or 'all'}",
                operation_type="metadata_extraction",
                status=BatchOperationStatus.PENDING,
                metadata={
                    "connection_type": item.connection_type,
                    "schema_name": item.schema_name,
                    "table_names": item.table_names
                }
            )
            operations.append(operation)

        # Create batch job
        job = batch_job_manager.create_job(
            job_type=BatchJobType.BULK_METADATA_EXTRACTION,
            name=request.job_name,
            operations=operations,
            description=request.description,
            parallel_execution=request.parallel_execution,
            max_parallel=request.max_parallel,
            project_id=request.project_id,
            tags=request.tags
        )

        # Start execution asynchronously
        batch_executor.execute_job_async(job.job_id)

        return BatchJobCreateResponse(
            job_id=job.job_id,
            status=job.status,
            message=f"Bulk metadata extraction job created with {len(operations)} sources",
            total_operations=len(operations)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Job Control Endpoints

@router.get("/jobs", response_model=BatchJobListResponse)
def list_batch_jobs(
    status: Optional[BatchJobStatus] = Query(None, description="Filter by job status"),
    job_type: Optional[BatchJobType] = Query(None, description="Filter by job type"),
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    limit: int = Query(100, description="Maximum number of jobs to return", ge=1, le=500),
    offset: int = Query(0, description="Offset for pagination", ge=0)
):
    """
    List batch jobs with optional filtering.

    Returns a paginated list of batch jobs matching the specified criteria.

    Query parameters:
    - status: Filter by job status (pending, running, completed, etc.)
    - job_type: Filter by job type (bulk_pipeline_execution, etc.)
    - project_id: Filter by associated project
    - limit: Number of results per page (default: 100, max: 500)
    - offset: Pagination offset (default: 0)
    """
    try:
        # Get jobs and total count in single call
        jobs, total = batch_job_manager.list_jobs(
            status=status,
            job_type=job_type,
            project_id=project_id,
            limit=limit,
            offset=offset,
            return_total=True
        )

        return BatchJobListResponse(
            jobs=jobs,
            total=total,
            page=offset // limit + 1 if limit > 0 else 1,
            page_size=limit
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}", response_model=BatchJobStatusResponse)
def get_batch_job(job_id: str):
    """
    Get detailed information about a specific batch job.

    Returns the complete job status including all operations
    and current progress.
    """
    try:
        job = batch_job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return BatchJobStatusResponse(
            job=job,
            current_progress=job.progress
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/cancel")
def cancel_batch_job(job_id: str, request: BatchJobCancelRequest = BatchJobCancelRequest()):
    """
    Cancel a running or queued batch job.

    Stops the execution of the job and marks all pending/running
    operations as skipped.

    Request body (optional):
    ```json
    {
      "reason": "User cancelled - testing purposes",
      "force": false
    }
    ```
    """
    try:
        job = batch_job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        if job.status in [BatchJobStatus.COMPLETED, BatchJobStatus.FAILED, BatchJobStatus.CANCELLED]:
            return {
                "status": "warning",
                "message": f"Job is already in {job.status.value} state",
                "job_id": job_id,
                "current_status": job.status.value
            }

        success = batch_job_manager.cancel_job(job_id, reason=request.reason)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to cancel job")

        return {
            "status": "success",
            "message": "Batch job cancelled successfully",
            "job_id": job_id,
            "reason": request.reason
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/jobs/{job_id}/retry")
def retry_failed_operations(job_id: str, request: BatchJobRetryRequest = BatchJobRetryRequest()):
    """
    Retry failed operations in a batch job.

    Re-executes operations that failed during the initial run.

    Request body (optional):
    ```json
    {
      "operation_ids": ["pipeline_0_dim_validation"],  // null = retry all failed
      "max_retries": 3
    }
    ```
    """
    try:
        job = batch_job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Get failed operations
        failed_ops = [op for op in job.operations if op.status == BatchOperationStatus.FAILED]

        if request.operation_ids:
            # Retry specific operations
            failed_ops = [op for op in failed_ops if op.operation_id in request.operation_ids]

        if not failed_ops:
            return {
                "status": "info",
                "message": "No failed operations to retry",
                "job_id": job_id
            }

        # Reset failed operations to pending
        for op in failed_ops:
            op.status = BatchOperationStatus.PENDING
            op.error = None
            op.started_at = None
            op.completed_at = None

        # Update job status back to running if it was failed/partial
        if job.status in [BatchJobStatus.FAILED, BatchJobStatus.PARTIAL_SUCCESS]:
            job.status = BatchJobStatus.QUEUED

        batch_job_manager.update_job(job)

        # Re-execute the job
        batch_executor.execute_job_async(job.job_id)

        return {
            "status": "success",
            "message": f"Retrying {len(failed_ops)} failed operations",
            "job_id": job_id,
            "retrying_operations": len(failed_ops)
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/jobs/{job_id}")
def delete_batch_job(job_id: str):
    """
    Delete a batch job.

    Permanently removes the job from the system.
    Only jobs that are not currently running can be deleted.
    """
    try:
        job = batch_job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        if job.status == BatchJobStatus.RUNNING:
            raise HTTPException(
                status_code=400,
                detail="Cannot delete a running job. Cancel it first."
            )

        success = batch_job_manager.delete_job(job_id)

        if not success:
            raise HTTPException(status_code=500, detail="Failed to delete job")

        return {
            "status": "success",
            "message": "Batch job deleted successfully",
            "job_id": job_id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Monitoring Endpoints

@router.get("/jobs/{job_id}/progress")
def get_job_progress(job_id: str):
    """
    Get real-time progress for a batch job.

    Returns current progress metrics including completion percentage,
    operation counts, and estimated time remaining.
    """
    try:
        job = batch_job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return {
            "status": "success",
            "job_id": job_id,
            "job_status": job.status.value,
            "progress": job.progress.model_dump() if job.progress else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "duration_ms": job.total_duration_ms
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/jobs/{job_id}/operations")
def get_job_operations(job_id: str):
    """
    Get detailed status of all operations in a batch job.

    Returns a list of all operations with their current status,
    results, and any errors.
    """
    try:
        job = batch_job_manager.get_job(job_id)

        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        return {
            "status": "success",
            "job_id": job_id,
            "total_operations": len(job.operations),
            "operations": [
                {
                    "operation_id": op.operation_id,
                    "operation_type": op.operation_type,
                    "status": op.status.value,
                    "started_at": op.started_at.isoformat() if op.started_at else None,
                    "completed_at": op.completed_at.isoformat() if op.completed_at else None,
                    "duration_ms": op.duration_ms,
                    "result": op.result,
                    "error": op.error,
                    "metadata": op.metadata
                }
                for op in job.operations
            ]
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/statistics")
def get_batch_statistics():
    """
    Get aggregate statistics about batch operations.

    Returns overall metrics including:
    - Total jobs by status
    - Jobs by type
    - Active job count
    - Recent job history
    """
    try:
        stats = batch_job_manager.get_statistics()

        return {
            "status": "success",
            "statistics": stats,
            "timestamp": datetime.utcnow().isoformat()
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Report Generation Endpoints

@router.get("/jobs/{job_id}/report")
def generate_consolidated_report(job_id: str):
    """
    Generate a consolidated report for a completed batch job.

    This endpoint generates a comprehensive report including:
    - Executive summary with overall pass/fail metrics
    - Aggregate data quality metrics across all pipelines
    - Per-table validation summaries
    - Failure analysis grouped by category
    - Data quality scores by dimension
    - Debugging SQL queries for each failure
    - Detailed pipeline-by-pipeline breakdown

    Args:
        job_id: The batch job ID

    Returns:
        Comprehensive consolidated report
    """
    try:
        from .report_generator import report_generator

        # Get the job
        job = batch_job_manager.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} not found")

        # Extract run_ids from completed AND failed operations (so we can show failure reports)
        run_ids = []
        for operation in job.operations:
            # Include both completed and failed operations that have results
            if operation.status in [BatchOperationStatus.COMPLETED, BatchOperationStatus.FAILED] and operation.result:
                # Check if this is a batch execution result with nested pipeline results
                if "results" in operation.result and isinstance(operation.result["results"], list):
                    # Extract run_ids from nested results (batch execution)
                    for nested_result in operation.result["results"]:
                        nested_run_id = nested_result.get("run_id")
                        if nested_run_id:
                            run_ids.append(nested_run_id)
                else:
                    # Regular pipeline execution - single run_id
                    run_id = operation.result.get("run_id")
                    if run_id:
                        run_ids.append(run_id)

        if not run_ids:
            raise HTTPException(
                status_code=400,
                detail="No completed pipeline runs found for this job. Report cannot be generated."
            )

        # Generate consolidated report
        report = report_generator.generate_batch_report(job_id, run_ids)

        return {
            "status": "success",
            "job_id": job_id,
            "job_name": job.name,
            "report": report
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating report: {str(e)}")
