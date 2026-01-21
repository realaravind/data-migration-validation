"""
Notification Service

Centralized service for sending notifications through multiple channels.
"""

import os
import json
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any

from .models import (
    NotificationChannel,
    NotificationPriority,
    NotificationEvent,
    NotificationConfig,
    NotificationRule,
    NotificationHistory,
    EmailNotification,
    SlackNotification,
    WebhookNotification
)
from .providers import EmailProvider, SlackProvider, WebhookProvider


class NotificationService:
    """
    Centralized notification service.

    Handles sending notifications through multiple channels,
    applying rules, and tracking history.
    """

    _instance = None
    _config = None
    _rules = None
    _history = []
    _throttle_cache = {}  # Track recent notifications for throttling

    def __new__(cls):
        """Singleton pattern"""
        if cls._instance is None:
            cls._instance = super(NotificationService, cls).__new__(cls)
            cls._load_config()
            cls._load_rules()
        return cls._instance

    @classmethod
    def _load_config(cls):
        """Load notification configuration from environment or file"""
        cls._config = NotificationConfig(
            enabled=os.getenv("NOTIFICATIONS_ENABLED", "true").lower() == "true",
            # Email settings
            smtp_host=os.getenv("SMTP_HOST"),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME"),
            smtp_password=os.getenv("SMTP_PASSWORD"),
            smtp_use_tls=os.getenv("SMTP_USE_TLS", "true").lower() == "true",
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL"),
            smtp_from_name=os.getenv("SMTP_FROM_NAME", "Ombudsman Validation Studio"),
            # Slack settings
            default_slack_webhook=os.getenv("SLACK_WEBHOOK_URL"),
            slack_channel=os.getenv("SLACK_CHANNEL"),
            # Webhook settings
            default_webhook_url=os.getenv("WEBHOOK_URL"),
            webhook_timeout=int(os.getenv("WEBHOOK_TIMEOUT", "30"))
        )

    @classmethod
    def _load_rules(cls):
        """Load notification rules from storage"""
        rules_file = Path(os.getenv("NOTIFICATION_RULES_FILE", "./backend/data/notification_rules.json"))

        if rules_file.exists():
            try:
                with open(rules_file, 'r') as f:
                    rules_data = json.load(f)
                    cls._rules = [NotificationRule(**rule) for rule in rules_data]
            except Exception as e:
                print(f"Failed to load notification rules: {e}")
                cls._rules = []
        else:
            cls._rules = []

    @classmethod
    def _save_rules(cls):
        """Save notification rules to storage"""
        rules_file = Path(os.getenv("NOTIFICATION_RULES_FILE", "./backend/data/notification_rules.json"))
        rules_file.parent.mkdir(parents=True, exist_ok=True)

        try:
            with open(rules_file, 'w') as f:
                rules_data = [rule.model_dump() for rule in cls._rules]
                json.dump(rules_data, f, default=str, indent=2)
        except Exception as e:
            print(f"Failed to save notification rules: {e}")

    def get_config(self) -> NotificationConfig:
        """Get current notification configuration"""
        return self._config

    def update_config(self, config: NotificationConfig):
        """Update notification configuration"""
        self._config = config

    def get_rules(self) -> List[NotificationRule]:
        """Get all notification rules"""
        return self._rules

    def add_rule(self, rule: NotificationRule) -> NotificationRule:
        """Add a new notification rule"""
        if not rule.id:
            rule.id = str(uuid.uuid4())

        self._rules.append(rule)
        self._save_rules()
        return rule

    def update_rule(self, rule_id: str, updates: Dict[str, Any]) -> Optional[NotificationRule]:
        """Update an existing notification rule"""
        for rule in self._rules:
            if rule.id == rule_id:
                for key, value in updates.items():
                    if hasattr(rule, key):
                        setattr(rule, key, value)
                rule.updated_at = datetime.utcnow()
                self._save_rules()
                return rule
        return None

    def delete_rule(self, rule_id: str) -> bool:
        """Delete a notification rule"""
        initial_count = len(self._rules)
        self._rules = [r for r in self._rules if r.id != rule_id]

        if len(self._rules) < initial_count:
            self._save_rules()
            return True
        return False

    def _should_throttle(self, rule: NotificationRule, event: NotificationEvent) -> bool:
        """Check if notification should be throttled"""
        if not rule.throttle_minutes:
            return False

        cache_key = f"{rule.id}:{event}"
        last_sent = self._throttle_cache.get(cache_key)

        if last_sent:
            elapsed = (datetime.utcnow() - last_sent).total_seconds() / 60
            if elapsed < rule.throttle_minutes:
                return True

        # Update cache
        self._throttle_cache[cache_key] = datetime.utcnow()
        return False

    def _evaluate_conditions(self, rule: NotificationRule, context: Dict[str, Any]) -> bool:
        """Evaluate rule conditions against context"""
        if not rule.conditions:
            return True

        # Simple condition evaluation
        # For now, just check if all conditions match context
        for key, expected_value in rule.conditions.items():
            if context.get(key) != expected_value:
                return False

        return True

    def send_notification(
        self,
        event: NotificationEvent,
        title: str,
        message: str,
        priority: NotificationPriority = NotificationPriority.MEDIUM,
        context: Optional[Dict[str, Any]] = None,
        force_channels: Optional[List[NotificationChannel]] = None
    ) -> Dict[str, Any]:
        """
        Send notification based on event and rules.

        Args:
            event: Event type triggering the notification
            title: Notification title
            message: Notification message
            priority: Priority level
            context: Additional context for rule evaluation
            force_channels: Force specific channels (bypass rules)

        Returns:
            Dict with send results
        """
        if not self._config.enabled:
            return {"sent": False, "reason": "Notifications disabled"}

        context = context or {}
        results = {
            "sent": False,
            "channels": {},
            "errors": []
        }

        # Find matching rules or use force channels
        channels_to_use = set()

        if force_channels:
            channels_to_use = set(force_channels)
        else:
            for rule in self._rules:
                if (rule.enabled and
                    rule.event == event and
                    self._evaluate_conditions(rule, context) and
                    not self._should_throttle(rule, event)):

                    channels_to_use.update(rule.channels)

        if not channels_to_use:
            return {"sent": False, "reason": "No matching rules or channels"}

        # Send to each channel
        for channel in channels_to_use:
            try:
                if channel == NotificationChannel.EMAIL:
                    success = self._send_email(event, title, message, priority, context)
                    results["channels"]["email"] = success

                elif channel == NotificationChannel.SLACK:
                    success = self._send_slack(event, title, message, priority, context)
                    results["channels"]["slack"] = success

                elif channel == NotificationChannel.WEBHOOK:
                    success = self._send_webhook(event, title, message, priority, context)
                    results["channels"]["webhook"] = success

                if success:
                    results["sent"] = True

            except Exception as e:
                results["errors"].append(f"{channel}: {str(e)}")

        # Record history
        self._record_history(event, title, message, priority, channels_to_use, results)

        return results

    def _send_email(
        self,
        event: NotificationEvent,
        title: str,
        message: str,
        priority: NotificationPriority,
        context: Dict[str, Any]
    ) -> bool:
        """Send email notification"""
        # Find recipients from rules
        recipients = []
        for rule in self._rules:
            if rule.enabled and rule.event == event and rule.email_recipients:
                recipients.extend(rule.email_recipients)

        if not recipients:
            return False

        provider = EmailProvider(self._config)

        # Create HTML body
        html_body = f"""
        <html>
        <body>
            <h2>{title}</h2>
            <p>{message}</p>
            <hr>
            <p><strong>Event:</strong> {event}</p>
            <p><strong>Priority:</strong> {priority}</p>
            <p><strong>Time:</strong> {datetime.utcnow().isoformat()}</p>
        </body>
        </html>
        """

        return provider.send(
            to=list(set(recipients)),  # Remove duplicates
            subject=f"[{priority.upper()}] {title}",
            body=message,
            html_body=html_body
        )

    def _send_slack(
        self,
        event: NotificationEvent,
        title: str,
        message: str,
        priority: NotificationPriority,
        context: Dict[str, Any]
    ) -> bool:
        """Send Slack notification"""
        # Find webhook URL from rules or use default
        webhook_url = self._config.default_slack_webhook

        for rule in self._rules:
            if rule.enabled and rule.event == event and rule.slack_webhook_url:
                webhook_url = rule.slack_webhook_url
                break

        if not webhook_url:
            return False

        provider = SlackProvider(self._config)
        return provider.send(
            webhook_url=webhook_url,
            title=title,
            message=message,
            priority=priority,
            channel=self._config.slack_channel
        )

    def _send_webhook(
        self,
        event: NotificationEvent,
        title: str,
        message: str,
        priority: NotificationPriority,
        context: Dict[str, Any]
    ) -> bool:
        """Send webhook notification"""
        # Find webhook URL from rules or use default
        webhook_url = self._config.default_webhook_url

        for rule in self._rules:
            if rule.enabled and rule.event == event and rule.webhook_url:
                webhook_url = rule.webhook_url
                break

        if not webhook_url:
            return False

        provider = WebhookProvider(self._config)

        payload = {
            "event": event,
            "title": title,
            "message": message,
            "priority": priority,
            "timestamp": datetime.utcnow().isoformat(),
            "context": context
        }

        return provider.send(
            webhook_url=webhook_url,
            payload=payload
        )

    def _record_history(
        self,
        event: NotificationEvent,
        title: str,
        message: str,
        priority: NotificationPriority,
        channels: set,
        results: Dict[str, Any]
    ):
        """Record notification in history"""
        history_entry = NotificationHistory(
            id=str(uuid.uuid4()),
            event=event,
            channel=list(channels)[0] if channels else NotificationChannel.EMAIL,
            priority=priority,
            title=title,
            message=message,
            recipients=[],  # Would be populated from rules
            sent_at=datetime.utcnow(),
            success=results.get("sent", False),
            error_message=", ".join(results.get("errors", [])) if results.get("errors") else None
        )

        self._history.append(history_entry)

        # Keep only last 1000 entries in memory
        if len(self._history) > 1000:
            self._history = self._history[-1000:]

    def get_history(self, limit: int = 100) -> List[NotificationHistory]:
        """Get notification history"""
        return self._history[-limit:]

    def test_notification(
        self,
        channel: NotificationChannel,
        recipient: Optional[str] = None
    ) -> bool:
        """
        Send a test notification.

        Args:
            channel: Channel to test
            recipient: Optional recipient (email or webhook URL)

        Returns:
            True if test successful
        """
        if channel == NotificationChannel.EMAIL:
            if not recipient:
                return False
            provider = EmailProvider(self._config)
            return provider.send(
                to=[recipient],
                subject="Test Notification - Ombudsman",
                body="This is a test notification from Ombudsman Validation Studio.",
                html_body="<p>This is a test notification from <strong>Ombudsman Validation Studio</strong>.</p>"
            )

        elif channel == NotificationChannel.SLACK:
            webhook_url = recipient or self._config.default_slack_webhook
            if not webhook_url:
                return False
            provider = SlackProvider(self._config)
            return provider.send(
                webhook_url=webhook_url,
                title="Test Notification",
                message="This is a test notification from Ombudsman Validation Studio",
                priority="medium"
            )

        elif channel == NotificationChannel.WEBHOOK:
            if not recipient:
                return False
            provider = WebhookProvider(self._config)
            return provider.send(
                webhook_url=recipient,
                payload={
                    "test": True,
                    "message": "Test notification from Ombudsman",
                    "timestamp": datetime.utcnow().isoformat()
                }
            )

        return False


# Convenience functions for common notifications

def notify_validation_completed(pipeline_id: str, run_id: str, status: str, duration_ms: int):
    """Notify that validation completed"""
    service = NotificationService()

    event = NotificationEvent.VALIDATION_COMPLETED if status == "success" else NotificationEvent.VALIDATION_FAILED
    priority = NotificationPriority.MEDIUM if status == "success" else NotificationPriority.HIGH

    service.send_notification(
        event=event,
        title=f"Validation {status.upper()}: {pipeline_id}",
        message=f"Pipeline {pipeline_id} completed with status {status} in {duration_ms}ms",
        priority=priority,
        context={"pipeline_id": pipeline_id, "run_id": run_id, "status": status}
    )


def notify_error(title: str, message: str, error_details: Optional[Dict[str, Any]] = None):
    """Notify about system error"""
    service = NotificationService()

    service.send_notification(
        event=NotificationEvent.SYSTEM_ERROR,
        title=title,
        message=message,
        priority=NotificationPriority.HIGH,
        context=error_details or {}
    )


# Global service instance
notification_service = NotificationService()
