"""
Results History API

API endpoints for querying historical pipeline execution results from the database.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from datetime import datetime
from pydantic import BaseModel

from database import (
    ResultsRepository,
    PipelineRunHistory,
    ValidationStepDetail,
    DailyQualityTrend,
    PipelineStatus,
    Project,
    ProjectCreate,
    ProjectUpdate
)
from errors import PipelineNotFoundError, DatabaseConnectionError

router = APIRouter()


# ============================================================================
# Request/Response Models
# ============================================================================

class PipelineRunHistoryResponse(BaseModel):
    """Response model for pipeline run history"""
    runs: List[PipelineRunHistory]
    total_count: int
    page: int
    page_size: int


class ProjectListResponse(BaseModel):
    """Response model for project list"""
    projects: List[Project]
    total_count: int


# ============================================================================
# Helper Functions
# ============================================================================

def get_repository() -> ResultsRepository:
    """Get database repository instance"""
    try:
        return ResultsRepository()
    except Exception as e:
        raise DatabaseConnectionError(
            message="Failed to connect to results database",
            details={"error": str(e)}
        )


# ============================================================================
# Projects
# ============================================================================

@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(active_only: bool = True):
    """List all validation projects"""
    try:
        repo = get_repository()
        projects = repo.list_projects(active_only=active_only)
        return ProjectListResponse(
            projects=projects,
            total_count=len(projects)
        )
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.post("/projects")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    try:
        repo = get_repository()
        created_project = repo.create_project(project)
        return {
            "status": "success",
            "message": f"Project '{project.project_name}' created successfully",
            "project": created_project
        }
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project by ID"""
    try:
        repo = get_repository()
        project = repo.get_project(project_id)
        if not project:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        return project
    except DatabaseConnectionError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get project: {str(e)}")


@router.put("/projects/{project_id}")
async def update_project(project_id: str, update: ProjectUpdate):
    """Update a project"""
    try:
        repo = get_repository()
        updated_project = repo.update_project(project_id, update)
        if not updated_project:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")
        return {
            "status": "success",
            "message": f"Project '{project_id}' updated successfully",
            "project": updated_project
        }
    except DatabaseConnectionError:
        raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update project: {str(e)}")


# ============================================================================
# Pipeline Run History
# ============================================================================

@router.get("/runs", response_model=PipelineRunHistoryResponse)
async def get_pipeline_run_history(
    project_id: Optional[str] = None,
    pipeline_name: Optional[str] = None,
    status: Optional[PipelineStatus] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(100, ge=1, le=1000)
):
    """
    Get pipeline run history with filtering and pagination.

    Args:
        project_id: Filter by project ID
        pipeline_name: Filter by pipeline name
        status: Filter by execution status (pending, running, completed, failed)
        start_date: Filter runs started after this date
        end_date: Filter runs started before this date
        page: Page number (1-indexed)
        page_size: Number of results per page (max 1000)

    Returns:
        Paginated list of pipeline runs with metadata
    """
    try:
        repo = get_repository()
        offset = (page - 1) * page_size

        runs = repo.get_pipeline_run_history(
            project_id=project_id,
            pipeline_name=pipeline_name,
            status=status,
            start_date=start_date,
            end_date=end_date,
            limit=page_size,
            offset=offset
        )

        return PipelineRunHistoryResponse(
            runs=runs,
            total_count=len(runs),  # TODO: Add count query to repository
            page=page,
            page_size=page_size
        )
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline run history: {str(e)}")


@router.get("/runs/{run_id}")
async def get_pipeline_run_details(run_id: str):
    """Get detailed information about a specific pipeline run"""
    try:
        repo = get_repository()

        # Get pipeline run
        run = repo.get_pipeline_run(run_id)
        if not run:
            raise PipelineNotFoundError(pipeline_id=run_id)

        # Get validation steps
        steps = repo.get_steps_for_run(run_id)

        return {
            "run": run,
            "steps": steps,
            "summary": {
                "total_steps": run.total_steps,
                "successful_steps": run.successful_steps,
                "failed_steps": run.failed_steps,
                "warnings_count": run.warnings_count,
                "errors_count": run.errors_count,
                "duration_seconds": run.duration_seconds
            }
        }
    except PipelineNotFoundError:
        raise
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get pipeline run details: {str(e)}")


@router.get("/runs/{run_id}/steps")
async def get_run_steps(run_id: str):
    """Get all validation steps for a pipeline run"""
    try:
        repo = get_repository()

        # Verify run exists
        run = repo.get_pipeline_run(run_id)
        if not run:
            raise PipelineNotFoundError(pipeline_id=run_id)

        # Get steps
        steps = repo.get_steps_for_run(run_id)

        return {
            "run_id": run_id,
            "pipeline_name": run.pipeline_name,
            "steps": steps,
            "total_steps": len(steps)
        }
    except PipelineNotFoundError:
        raise
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get run steps: {str(e)}")


@router.get("/runs/{run_id}/steps/{step_id}/comparison")
async def get_step_comparison_details(run_id: str, step_id: int):
    """Get detailed comparison data for a validation step"""
    try:
        repo = get_repository()

        # Get step
        step = repo.get_validation_step(step_id)
        if not step or step.run_id != run_id:
            raise HTTPException(
                status_code=404,
                detail=f"Step {step_id} not found for run {run_id}"
            )

        return {
            "run_id": run_id,
            "step_id": step_id,
            "step_name": step.step_name,
            "status": step.status,
            "difference_type": step.difference_type,
            "total_rows": step.total_rows,
            "differing_rows_count": step.differing_rows_count,
            "affected_columns": step.affected_columns,
            "comparison_details": step.comparison_details,
            "match_percentage": step.match_percentage,
            "result_message": step.result_message
        }
    except HTTPException:
        raise
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get comparison details: {str(e)}")


@router.get("/runs/{run_id}/logs")
async def get_execution_logs(
    run_id: str,
    step_id: Optional[int] = None,
    log_level: Optional[str] = None,
    limit: int = Query(1000, ge=1, le=10000)
):
    """Get execution logs for a pipeline run"""
    try:
        repo = get_repository()

        # Verify run exists
        run = repo.get_pipeline_run(run_id)
        if not run:
            raise PipelineNotFoundError(pipeline_id=run_id)

        # Parse log level
        from database import LogLevel
        level = None
        if log_level:
            try:
                level = LogLevel(log_level.upper())
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid log level: {log_level}. Must be one of: DEBUG, INFO, WARNING, ERROR"
                )

        # Get logs
        logs = repo.get_execution_logs(
            run_id=run_id,
            step_id=step_id,
            log_level=level,
            limit=limit
        )

        return {
            "run_id": run_id,
            "step_id": step_id,
            "log_level": log_level,
            "logs": logs,
            "total_logs": len(logs)
        }
    except PipelineNotFoundError:
        raise
    except HTTPException:
        raise
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get execution logs: {str(e)}")


# ============================================================================
# Metrics and Analytics
# ============================================================================

@router.get("/metrics/daily-trend")
async def get_daily_quality_trend(
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
):
    """Get daily data quality trend"""
    try:
        repo = get_repository()
        trends = repo.get_daily_quality_trend(
            start_date=start_date,
            end_date=end_date
        )

        return {
            "trends": trends,
            "total_days": len(trends)
        }
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get daily quality trend: {str(e)}")


@router.get("/metrics/summary")
async def get_metrics_summary(
    project_id: Optional[str] = None,
    days: int = Query(30, ge=1, le=365)
):
    """Get summary metrics for the last N days"""
    try:
        repo = get_repository()

        # Calculate date range
        from datetime import timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get runs in date range
        runs = repo.get_pipeline_run_history(
            project_id=project_id,
            start_date=start_date,
            end_date=end_date,
            limit=10000
        )

        # Calculate summary
        total_runs = len(runs)
        successful_runs = sum(1 for r in runs if r.status == PipelineStatus.COMPLETED and r.failed_steps == 0)
        failed_runs = sum(1 for r in runs if r.status == PipelineStatus.FAILED)
        completed_with_errors = sum(1 for r in runs if r.status == PipelineStatus.COMPLETED and r.failed_steps > 0)

        total_steps = sum(r.total_steps for r in runs)
        total_successful_steps = sum(r.successful_steps for r in runs)
        total_failed_steps = sum(r.failed_steps for r in runs)

        avg_duration = sum(r.duration_seconds for r in runs if r.duration_seconds) / max(total_runs, 1)

        return {
            "period": {
                "start_date": start_date.isoformat(),
                "end_date": end_date.isoformat(),
                "days": days
            },
            "runs": {
                "total": total_runs,
                "successful": successful_runs,
                "failed": failed_runs,
                "completed_with_errors": completed_with_errors,
                "success_rate": (successful_runs / max(total_runs, 1)) * 100
            },
            "steps": {
                "total": total_steps,
                "successful": total_successful_steps,
                "failed": total_failed_steps,
                "success_rate": (total_successful_steps / max(total_steps, 1)) * 100
            },
            "performance": {
                "avg_duration_seconds": round(avg_duration, 2),
                "avg_duration_minutes": round(avg_duration / 60, 2)
            }
        }
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get metrics summary: {str(e)}")


# ============================================================================
# Comparison Utilities
# ============================================================================

@router.get("/runs/compare")
async def compare_pipeline_runs(
    run_id_1: str = Query(..., description="First run ID"),
    run_id_2: str = Query(..., description="Second run ID")
):
    """Compare two pipeline runs side by side"""
    try:
        repo = get_repository()

        # Get both runs
        run1 = repo.get_pipeline_run(run_id_1)
        run2 = repo.get_pipeline_run(run_id_2)

        if not run1:
            raise PipelineNotFoundError(pipeline_id=run_id_1)
        if not run2:
            raise PipelineNotFoundError(pipeline_id=run_id_2)

        # Get steps for both runs
        steps1 = repo.get_steps_for_run(run_id_1)
        steps2 = repo.get_steps_for_run(run_id_2)

        return {
            "run_1": {
                "run": run1,
                "steps": steps1
            },
            "run_2": {
                "run": run2,
                "steps": steps2
            },
            "comparison": {
                "duration_diff_seconds": (run2.duration_seconds or 0) - (run1.duration_seconds or 0),
                "steps_diff": len(steps2) - len(steps1),
                "success_rate_diff": (
                    (run2.successful_steps / max(run2.total_steps, 1)) -
                    (run1.successful_steps / max(run1.total_steps, 1))
                ) * 100 if run1.total_steps and run2.total_steps else 0
            }
        }
    except PipelineNotFoundError:
        raise
    except DatabaseConnectionError:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to compare runs: {str(e)}")
