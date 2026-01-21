"""
Notification Data Models

Defines schemas for notifications, rules, and configurations.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, EmailStr
from enum import Enum


class NotificationChannel(str, Enum):
    """Notification delivery channels"""
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    TEAMS = "teams"  # Future


class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class NotificationEvent(str, Enum):
    """Events that can trigger notifications"""
    VALIDATION_STARTED = "validation_started"
    VALIDATION_COMPLETED = "validation_completed"
    VALIDATION_FAILED = "validation_failed"
    PIPELINE_ERROR = "pipeline_error"
    AUDIT_ERROR = "audit_error"
    AUTHENTICATION_FAILURE = "authentication_failure"
    DATA_CHANGE = "data_change"
    SYSTEM_ERROR = "system_error"
    CUSTOM = "custom"


# Base notification models

class NotificationBase(BaseModel):
    """Base notification model"""
    channel: NotificationChannel
    priority: NotificationPriority = NotificationPriority.MEDIUM
    event: NotificationEvent
    title: str
    message: str
    metadata: Optional[Dict[str, Any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class EmailNotification(NotificationBase):
    """Email notification"""
    channel: NotificationChannel = NotificationChannel.EMAIL
    to: List[EmailStr]
    cc: Optional[List[EmailStr]] = None
    bcc: Optional[List[EmailStr]] = None
    subject: str
    html_body: Optional[str] = None
    attachments: Optional[List[str]] = None


class SlackNotification(NotificationBase):
    """Slack notification"""
    channel: NotificationChannel = NotificationChannel.SLACK
    webhook_url: str
    slack_channel: Optional[str] = None  # Override default channel
    username: Optional[str] = "Ombudsman Bot"
    icon_emoji: Optional[str] = ":robot_face:"
    blocks: Optional[List[Dict[str, Any]]] = None  # Slack Block Kit


class WebhookNotification(NotificationBase):
    """Generic webhook notification"""
    channel: NotificationChannel = NotificationChannel.WEBHOOK
    webhook_url: str
    method: str = "POST"
    headers: Optional[Dict[str, str]] = None
    payload: Dict[str, Any]


# Notification rules and configuration

class NotificationRule(BaseModel):
    """Notification rule configuration"""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    enabled: bool = True
    event: NotificationEvent
    channels: List[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.MEDIUM

    # Conditions
    conditions: Optional[Dict[str, Any]] = None  # JSON conditions

    # Throttling
    throttle_minutes: Optional[int] = None  # Prevent duplicate alerts

    # Recipients
    email_recipients: Optional[List[EmailStr]] = None
    slack_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None

    # Template
    message_template: Optional[str] = None

    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


class NotificationConfig(BaseModel):
    """Global notification configuration"""
    enabled: bool = True

    # Email settings
    smtp_host: Optional[str] = None
    smtp_port: int = 587
    smtp_username: Optional[str] = None
    smtp_password: Optional[str] = None
    smtp_use_tls: bool = True
    smtp_from_email: Optional[EmailStr] = None
    smtp_from_name: str = "Ombudsman Validation Studio"

    # Slack settings
    default_slack_webhook: Optional[str] = None
    slack_channel: Optional[str] = None

    # Webhook settings
    default_webhook_url: Optional[str] = None
    webhook_timeout: int = 30

    # Rate limiting
    max_notifications_per_hour: int = 100

    # Retry settings
    max_retries: int = 3
    retry_delay_seconds: int = 60


class NotificationHistory(BaseModel):
    """Record of sent notifications"""
    id: str
    rule_id: Optional[str] = None
    channel: NotificationChannel
    event: NotificationEvent
    priority: NotificationPriority
    title: str
    message: str
    recipients: List[str]
    sent_at: datetime
    success: bool
    error_message: Optional[str] = None
    retry_count: int = 0
    metadata: Optional[Dict[str, Any]] = None


class NotificationStats(BaseModel):
    """Notification statistics"""
    total_sent: int
    successful: int
    failed: int
    by_channel: Dict[str, int]
    by_event: Dict[str, int]
    by_priority: Dict[str, int]
    recent_failures: List[NotificationHistory]


# API request/response models

class NotificationRuleCreate(BaseModel):
    """Create notification rule"""
    name: str
    description: Optional[str] = None
    event: NotificationEvent
    channels: List[NotificationChannel]
    priority: NotificationPriority = NotificationPriority.MEDIUM
    conditions: Optional[Dict[str, Any]] = None
    throttle_minutes: Optional[int] = None
    email_recipients: Optional[List[EmailStr]] = None
    slack_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    message_template: Optional[str] = None


class NotificationRuleUpdate(BaseModel):
    """Update notification rule"""
    name: Optional[str] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None
    channels: Optional[List[NotificationChannel]] = None
    priority: Optional[NotificationPriority] = None
    conditions: Optional[Dict[str, Any]] = None
    throttle_minutes: Optional[int] = None
    email_recipients: Optional[List[EmailStr]] = None
    slack_webhook_url: Optional[str] = None
    webhook_url: Optional[str] = None
    message_template: Optional[str] = None


class NotificationTest(BaseModel):
    """Test notification request"""
    channel: NotificationChannel
    title: str = "Test Notification"
    message: str = "This is a test notification from Ombudsman Validation Studio"
    recipient: Optional[str] = None  # Email or channel name
    webhook_url: Optional[str] = None


class NotificationSendRequest(BaseModel):
    """Manual notification send request"""
    event: NotificationEvent = NotificationEvent.CUSTOM
    priority: NotificationPriority = NotificationPriority.MEDIUM
    title: str
    message: str
    channels: List[NotificationChannel]
    recipients: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None
