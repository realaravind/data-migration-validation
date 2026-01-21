"""
Notification System Module

Provides multi-channel notification capabilities:
- Email notifications via SMTP
- Slack notifications via webhooks
- Generic webhooks for custom integrations
- Configurable notification rules
- Template-based messages

Usage:
    from notifications import NotificationService

    service = NotificationService()
    service.send_email(
        to="user@example.com",
        subject="Validation Failed",
        body="Pipeline ABC failed with errors"
    )
"""

from .service import NotificationService
from .models import (
    NotificationChannel,
    NotificationPriority,
    NotificationRule,
    NotificationConfig,
    EmailNotification,
    SlackNotification,
    WebhookNotification
)
from .providers import EmailProvider, SlackProvider, WebhookProvider

__all__ = [
    "NotificationService",
    "NotificationChannel",
    "NotificationPriority",
    "NotificationRule",
    "NotificationConfig",
    "EmailNotification",
    "SlackNotification",
    "WebhookNotification",
    "EmailProvider",
    "SlackProvider",
    "WebhookProvider",
]
