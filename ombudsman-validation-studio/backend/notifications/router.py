"""
Notification API Router

Provides REST API endpoints for notification configuration, rules, and sending.
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from datetime import datetime

from .models import (
    NotificationConfig,
    NotificationRule,
    NotificationRuleCreate,
    NotificationRuleUpdate,
    NotificationTest,
    NotificationSendRequest,
    NotificationHistory,
    NotificationStats,
    NotificationChannel,
    NotificationEvent,
    NotificationPriority
)
from .service import notification_service


router = APIRouter()


# Configuration Endpoints

@router.get("/config")
def get_notification_config():
    """
    Get current notification configuration.

    Returns the global notification settings including SMTP, Slack, and webhook configuration.
    """
    try:
        config = notification_service.get_config()

        # Mask sensitive information
        config_dict = config.model_dump()
        if config_dict.get("smtp_password"):
            config_dict["smtp_password"] = "***MASKED***"

        return {
            "status": "success",
            "config": config_dict
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config")
def update_notification_config(config: NotificationConfig):
    """
    Update notification configuration.

    Updates global notification settings. Note: This updates runtime configuration only.
    For persistent changes, update environment variables.
    """
    try:
        notification_service.update_config(config)

        return {
            "status": "success",
            "message": "Configuration updated successfully",
            "config": config.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Rule Management Endpoints

@router.get("/rules", response_model=List[NotificationRule])
def get_notification_rules(
    enabled: Optional[bool] = Query(None, description="Filter by enabled status"),
    event: Optional[NotificationEvent] = Query(None, description="Filter by event type")
):
    """
    Get all notification rules.

    Optional filters:
    - enabled: Filter by enabled/disabled rules
    - event: Filter by specific event type
    """
    try:
        rules = notification_service.get_rules()

        # Apply filters
        if enabled is not None:
            rules = [r for r in rules if r.enabled == enabled]

        if event is not None:
            rules = [r for r in rules if r.event == event]

        return rules
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules")
def create_notification_rule(rule_create: NotificationRuleCreate):
    """
    Create a new notification rule.

    Creates a rule that defines when and how notifications should be sent.
    """
    try:
        # Convert to NotificationRule
        rule = NotificationRule(**rule_create.model_dump())

        # Add rule
        created_rule = notification_service.add_rule(rule)

        return {
            "status": "success",
            "message": "Notification rule created successfully",
            "rule": created_rule.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/rules/{rule_id}")
def update_notification_rule(rule_id: str, rule_update: NotificationRuleUpdate):
    """
    Update an existing notification rule.

    Updates only the fields provided in the request.
    """
    try:
        # Filter out None values
        updates = {k: v for k, v in rule_update.model_dump().items() if v is not None}

        updated_rule = notification_service.update_rule(rule_id, updates)

        if not updated_rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        return {
            "status": "success",
            "message": "Notification rule updated successfully",
            "rule": updated_rule.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/rules/{rule_id}")
def delete_notification_rule(rule_id: str):
    """
    Delete a notification rule.

    Permanently removes the rule from the system.
    """
    try:
        success = notification_service.delete_rule(rule_id)

        if not success:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        return {
            "status": "success",
            "message": "Notification rule deleted successfully"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rules/{rule_id}/toggle")
def toggle_notification_rule(rule_id: str):
    """
    Toggle a notification rule on/off.

    Enables a disabled rule or disables an enabled rule.
    """
    try:
        rules = notification_service.get_rules()
        rule = next((r for r in rules if r.id == rule_id), None)

        if not rule:
            raise HTTPException(status_code=404, detail=f"Rule {rule_id} not found")

        # Toggle enabled status
        new_status = not rule.enabled
        updated_rule = notification_service.update_rule(rule_id, {"enabled": new_status})

        return {
            "status": "success",
            "message": f"Rule {'enabled' if new_status else 'disabled'} successfully",
            "rule": updated_rule.model_dump()
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Sending Notifications

@router.post("/send")
def send_notification(request: NotificationSendRequest):
    """
    Send a manual notification.

    Sends a notification through specified channels, bypassing rules.
    """
    try:
        result = notification_service.send_notification(
            event=request.event,
            title=request.title,
            message=request.message,
            priority=request.priority,
            context=request.metadata or {},
            force_channels=request.channels
        )

        if not result.get("sent"):
            return {
                "status": "warning",
                "message": "Notification not sent",
                "reason": result.get("reason", "Unknown"),
                "details": result
            }

        return {
            "status": "success",
            "message": "Notification sent successfully",
            "details": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/test")
def test_notification(test: NotificationTest):
    """
    Test a notification channel.

    Sends a test notification to verify channel configuration.
    """
    try:
        success = notification_service.test_notification(
            channel=test.channel,
            recipient=test.recipient or test.webhook_url
        )

        if not success:
            return {
                "status": "error",
                "message": f"Test notification failed for channel: {test.channel}",
                "channel": test.channel
            }

        return {
            "status": "success",
            "message": f"Test notification sent successfully to {test.channel}",
            "channel": test.channel
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# History and Statistics

@router.get("/history")
def get_notification_history(
    limit: int = Query(100, description="Maximum number of records to return", ge=1, le=1000)
):
    """
    Get notification history.

    Returns a list of recently sent notifications.
    """
    try:
        history = notification_service.get_history(limit=limit)

        return {
            "status": "success",
            "count": len(history),
            "history": [h.model_dump() for h in history]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
def get_notification_stats():
    """
    Get notification statistics.

    Returns aggregated statistics about sent notifications.
    """
    try:
        history = notification_service.get_history(limit=1000)

        # Calculate statistics
        total_sent = len(history)
        successful = sum(1 for h in history if h.success)
        failed = sum(1 for h in history if not h.success)

        by_channel = {}
        by_event = {}
        by_priority = {}

        for entry in history:
            # By channel
            channel_key = entry.channel.value if hasattr(entry.channel, 'value') else str(entry.channel)
            by_channel[channel_key] = by_channel.get(channel_key, 0) + 1

            # By event
            event_key = entry.event.value if hasattr(entry.event, 'value') else str(entry.event)
            by_event[event_key] = by_event.get(event_key, 0) + 1

            # By priority
            priority_key = entry.priority.value if hasattr(entry.priority, 'value') else str(entry.priority)
            by_priority[priority_key] = by_priority.get(priority_key, 0) + 1

        # Recent failures
        recent_failures = [h for h in history[-50:] if not h.success]

        stats = NotificationStats(
            total_sent=total_sent,
            successful=successful,
            failed=failed,
            by_channel=by_channel,
            by_event=by_event,
            by_priority=by_priority,
            recent_failures=recent_failures
        )

        return {
            "status": "success",
            "stats": stats.model_dump()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Utility Endpoints

@router.get("/channels")
def get_available_channels():
    """
    Get list of available notification channels.
    """
    return {
        "channels": [
            {
                "value": channel.value,
                "label": channel.value.title(),
                "description": get_channel_description(channel)
            }
            for channel in NotificationChannel
        ]
    }


@router.get("/events")
def get_available_events():
    """
    Get list of available notification events.
    """
    return {
        "events": [
            {
                "value": event.value,
                "label": event.value.replace("_", " ").title(),
                "description": get_event_description(event)
            }
            for event in NotificationEvent
        ]
    }


@router.get("/priorities")
def get_available_priorities():
    """
    Get list of available priority levels.
    """
    return {
        "priorities": [
            {
                "value": priority.value,
                "label": priority.value.title(),
                "description": get_priority_description(priority)
            }
            for priority in NotificationPriority
        ]
    }


# Helper functions

def get_channel_description(channel: NotificationChannel) -> str:
    """Get description for a notification channel"""
    descriptions = {
        NotificationChannel.EMAIL: "Send notifications via email",
        NotificationChannel.SLACK: "Send notifications to Slack workspace",
        NotificationChannel.WEBHOOK: "Send notifications to custom webhook",
        NotificationChannel.TEAMS: "Send notifications to Microsoft Teams (coming soon)"
    }
    return descriptions.get(channel, "")


def get_event_description(event: NotificationEvent) -> str:
    """Get description for a notification event"""
    descriptions = {
        NotificationEvent.VALIDATION_STARTED: "Triggered when a validation pipeline starts",
        NotificationEvent.VALIDATION_COMPLETED: "Triggered when a validation completes successfully",
        NotificationEvent.VALIDATION_FAILED: "Triggered when a validation fails",
        NotificationEvent.PIPELINE_ERROR: "Triggered when a pipeline encounters an error",
        NotificationEvent.AUDIT_ERROR: "Triggered on audit logging errors",
        NotificationEvent.AUTHENTICATION_FAILURE: "Triggered on authentication failures",
        NotificationEvent.DATA_CHANGE: "Triggered when data changes are detected",
        NotificationEvent.SYSTEM_ERROR: "Triggered on system-level errors",
        NotificationEvent.CUSTOM: "Custom user-defined event"
    }
    return descriptions.get(event, "")


def get_priority_description(priority: NotificationPriority) -> str:
    """Get description for a priority level"""
    descriptions = {
        NotificationPriority.LOW: "Low priority - informational only",
        NotificationPriority.MEDIUM: "Medium priority - normal notifications",
        NotificationPriority.HIGH: "High priority - requires attention",
        NotificationPriority.CRITICAL: "Critical priority - immediate action required"
    }
    return descriptions.get(priority, "")
