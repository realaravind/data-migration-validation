"""
Audit Log API Router

Endpoints for querying, viewing, and exporting audit logs.
"""

from fastapi import APIRouter, HTTPException, Response
from typing import List
from datetime import datetime, timedelta

from .models import (
    AuditLog,
    AuditLogFilter,
    AuditLogSummary,
    AuditLogExport,
    AuditLevel,
    AuditCategory
)
from .storage import AuditLogStorage
from .audit_logger import audit_logger

router = APIRouter(prefix="/audit", tags=["Audit Logs"])
storage = AuditLogStorage()


@router.post("/logs/query", response_model=List[AuditLog])
async def query_audit_logs(filters: AuditLogFilter):
    """
    Query audit logs with filters.

    Returns paginated list of audit logs matching the filter criteria.
    """
    try:
        logs = storage.query_logs(filters)
        return logs
    except Exception as e:
        audit_logger.log_error(
            error_message=str(e),
            action="query_audit_logs_failed"
        )
        raise HTTPException(status_code=500, detail=f"Failed to query audit logs: {str(e)}")


@router.get("/logs/summary", response_model=AuditLogSummary)
async def get_audit_summary(
    start_date: datetime = None,
    end_date: datetime = None
):
    """
    Get summary statistics for audit logs.

    Returns aggregated statistics including:
    - Total log count
    - Counts by level and category
    - Most active users
    - Recent errors
    - Common actions
    """
    try:
        # Default to last 30 days if not specified
        if not start_date:
            start_date = datetime.utcnow() - timedelta(days=30)
        if not end_date:
            end_date = datetime.utcnow()

        filters = AuditLogFilter(
            start_date=start_date,
            end_date=end_date
        )

        summary = storage.get_summary(filters)
        return summary
    except Exception as e:
        audit_logger.log_error(
            error_message=str(e),
            action="get_audit_summary_failed"
        )
        raise HTTPException(status_code=500, detail=f"Failed to get audit summary: {str(e)}")


@router.post("/logs/export")
async def export_audit_logs(export_config: AuditLogExport):
    """
    Export audit logs to CSV or JSON format.

    Returns the exported data as a downloadable file.
    """
    try:
        # Export logs
        data = storage.export_logs(
            filters=export_config.filters,
            format=export_config.format
        )

        # Set appropriate content type and filename
        if export_config.format == "json":
            media_type = "application/json"
            filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
        elif export_config.format == "csv":
            media_type = "text/csv"
            filename = f"audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
        else:
            raise ValueError(f"Unsupported format: {export_config.format}")

        # Log export
        audit_logger.log_export(
            export_type="audit_logs",
            format=export_config.format,
            record_count=len(data.split('\n')) if export_config.format == "csv" else data.count('{'),
            user_id="system",  # TODO: Get from auth
            details={"filters": export_config.filters.model_dump()}
        )

        return Response(
            content=data,
            media_type=media_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
    except Exception as e:
        audit_logger.log_error(
            error_message=str(e),
            action="export_audit_logs_failed"
        )
        raise HTTPException(status_code=500, detail=f"Failed to export audit logs: {str(e)}")


@router.get("/logs/recent", response_model=List[AuditLog])
async def get_recent_logs(limit: int = 100, level: AuditLevel = None):
    """
    Get recent audit logs.

    Quick access to most recent logs, optionally filtered by level.
    """
    try:
        filters = AuditLogFilter(
            start_date=datetime.utcnow() - timedelta(days=7),
            level=level,
            limit=limit,
            sort_by="timestamp",
            sort_order="desc"
        )

        logs = storage.query_logs(filters)
        return logs
    except Exception as e:
        audit_logger.log_error(
            error_message=str(e),
            action="get_recent_logs_failed"
        )
        raise HTTPException(status_code=500, detail=f"Failed to get recent logs: {str(e)}")


@router.get("/logs/errors", response_model=List[AuditLog])
async def get_error_logs(limit: int = 50):
    """
    Get recent error and critical logs.

    Returns most recent errors for troubleshooting.
    """
    try:
        # Query ERROR and CRITICAL logs
        filters_error = AuditLogFilter(
            start_date=datetime.utcnow() - timedelta(days=7),
            level=AuditLevel.ERROR,
            limit=limit // 2,
            sort_by="timestamp",
            sort_order="desc"
        )

        filters_critical = AuditLogFilter(
            start_date=datetime.utcnow() - timedelta(days=7),
            level=AuditLevel.CRITICAL,
            limit=limit // 2,
            sort_by="timestamp",
            sort_order="desc"
        )

        errors = storage.query_logs(filters_error)
        critical = storage.query_logs(filters_critical)

        # Combine and sort
        all_errors = errors + critical
        all_errors.sort(key=lambda x: x.timestamp, reverse=True)

        return all_errors[:limit]
    except Exception as e:
        audit_logger.log_error(
            error_message=str(e),
            action="get_error_logs_failed"
        )
        raise HTTPException(status_code=500, detail=f"Failed to get error logs: {str(e)}")


@router.get("/logs/user/{user_id}", response_model=List[AuditLog])
async def get_user_logs(user_id: str, limit: int = 100):
    """
    Get audit logs for a specific user.

    Returns all actions performed by the specified user.
    """
    try:
        filters = AuditLogFilter(
            user_id=user_id,
            start_date=datetime.utcnow() - timedelta(days=30),
            limit=limit,
            sort_by="timestamp",
            sort_order="desc"
        )

        logs = storage.query_logs(filters)
        return logs
    except Exception as e:
        audit_logger.log_error(
            error_message=str(e),
            action="get_user_logs_failed"
        )
        raise HTTPException(status_code=500, detail=f"Failed to get user logs: {str(e)}")


@router.get("/logs/resource/{resource_type}/{resource_id}", response_model=List[AuditLog])
async def get_resource_logs(resource_type: str, resource_id: str, limit: int = 100):
    """
    Get audit logs for a specific resource.

    Returns all actions performed on the specified resource.
    """
    try:
        filters = AuditLogFilter(
            resource_type=resource_type,
            resource_id=resource_id,
            start_date=datetime.utcnow() - timedelta(days=90),
            limit=limit,
            sort_by="timestamp",
            sort_order="desc"
        )

        logs = storage.query_logs(filters)
        return logs
    except Exception as e:
        audit_logger.log_error(
            error_message=str(e),
            action="get_resource_logs_failed"
        )
        raise HTTPException(status_code=500, detail=f"Failed to get resource logs: {str(e)}")


@router.delete("/logs/cleanup")
async def cleanup_old_logs(days_to_keep: int = 90):
    """
    Delete audit logs older than specified days.

    Use this endpoint to clean up old audit logs and free disk space.
    """
    try:
        storage.cleanup_old_logs(days_to_keep)

        audit_logger.log_system_event(
            action="audit_logs_cleanup",
            details={"days_to_keep": days_to_keep}
        )

        return {
            "status": "success",
            "message": f"Deleted audit logs older than {days_to_keep} days"
        }
    except Exception as e:
        audit_logger.log_error(
            error_message=str(e),
            action="cleanup_old_logs_failed"
        )
        raise HTTPException(status_code=500, detail=f"Failed to cleanup logs: {str(e)}")


@router.get("/categories", response_model=List[str])
async def get_audit_categories():
    """Get list of all audit categories"""
    return [category.value for category in AuditCategory]


@router.get("/levels", response_model=List[str])
async def get_audit_levels():
    """Get list of all audit levels"""
    return [level.value for level in AuditLevel]
