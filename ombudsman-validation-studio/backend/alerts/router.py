"""API endpoints for alerts and notifications."""

from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from .service import alert_service, AlertSeverity, AlertCategory

router = APIRouter()


class AlertResponse(BaseModel):
    """Response model for a single alert."""
    id: str
    timestamp: str
    severity: str
    category: str
    title: str
    message: str
    source: str
    details: Optional[dict] = None
    suggestions: List[dict] = []
    read: bool = False


class AlertsListResponse(BaseModel):
    """Response model for alerts list."""
    alerts: List[dict]
    total: int
    unread_count: int


class AlertCountResponse(BaseModel):
    """Response for alert count."""
    unread_count: int
    total: int


@router.get("/", response_model=AlertsListResponse)
async def get_alerts(
    unread_only: bool = Query(False, description="Only return unread alerts"),
    severity: Optional[str] = Query(None, description="Filter by severity"),
    category: Optional[str] = Query(None, description="Filter by category"),
    limit: int = Query(50, ge=1, le=100, description="Max alerts to return")
):
    """Get all alerts with optional filtering."""
    sev = AlertSeverity(severity) if severity else None
    cat = AlertCategory(category) if category else None

    alerts = alert_service.get_alerts(
        unread_only=unread_only,
        severity=sev,
        category=cat,
        limit=limit
    )

    return AlertsListResponse(
        alerts=[a.to_dict() for a in alerts],
        total=len(alert_service._alerts),
        unread_count=alert_service.get_unread_count()
    )


@router.get("/count", response_model=AlertCountResponse)
async def get_alert_count():
    """Get count of alerts (for badge display)."""
    return AlertCountResponse(
        unread_count=alert_service.get_unread_count(),
        total=len(alert_service._alerts)
    )


@router.post("/{alert_id}/read")
async def mark_alert_read(alert_id: str):
    """Mark a specific alert as read."""
    if alert_service.mark_read(alert_id):
        return {"status": "success", "message": f"Alert {alert_id} marked as read"}
    raise HTTPException(status_code=404, detail="Alert not found")


@router.post("/read-all")
async def mark_all_alerts_read():
    """Mark all alerts as read."""
    count = alert_service.mark_all_read()
    return {"status": "success", "message": f"Marked {count} alerts as read"}


@router.delete("/{alert_id}")
async def delete_alert(alert_id: str):
    """Delete a specific alert."""
    if alert_service.delete_alert(alert_id):
        return {"status": "success", "message": f"Alert {alert_id} deleted"}
    raise HTTPException(status_code=404, detail="Alert not found")


@router.delete("/")
async def clear_all_alerts():
    """Clear all alerts."""
    count = alert_service.clear_alerts()
    return {"status": "success", "message": f"Cleared {count} alerts"}


# Test endpoint to add sample alerts (for development)
@router.post("/test")
async def add_test_alert(
    message: str = Query(..., description="Error message"),
    source: str = Query("test", description="Source of error")
):
    """Add a test alert (for development/testing)."""
    alert = alert_service.add_alert(message=message, source=source)
    return {"status": "success", "alert": alert.to_dict()}
