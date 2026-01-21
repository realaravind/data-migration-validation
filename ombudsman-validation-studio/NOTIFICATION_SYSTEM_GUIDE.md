# Notification System Guide

## Overview

The Ombudsman Validation Studio includes a comprehensive notification system that allows you to receive alerts about validation events through multiple channels:

- **Email (SMTP)**: Send notifications via email
- **Slack**: Post notifications to Slack channels
- **Webhook**: Send notifications to custom HTTP endpoints
- **Teams**: (Coming soon) Microsoft Teams integration

## Table of Contents

1. [Features](#features)
2. [Configuration](#configuration)
3. [Creating Notification Rules](#creating-notification-rules)
4. [API Endpoints](#api-endpoints)
5. [Frontend Interface](#frontend-interface)
6. [Examples](#examples)
7. [Troubleshooting](#troubleshooting)

## Features

### Event-Based Notifications
- **Validation Started**: Triggered when a validation pipeline starts
- **Validation Completed**: Triggered when validation completes successfully
- **Validation Failed**: Triggered when validation fails
- **Pipeline Error**: Triggered on pipeline execution errors
- **Audit Error**: Triggered on audit logging errors
- **Authentication Failure**: Triggered on auth failures
- **Data Change**: Triggered when data changes are detected
- **System Error**: Triggered on system-level errors
- **Custom**: User-defined custom events

### Priority Levels
- **Low**: Informational notifications
- **Medium**: Normal notifications (default)
- **High**: Important notifications requiring attention
- **Critical**: Urgent notifications requiring immediate action

### Multi-Channel Support
Send the same notification to multiple channels simultaneously.

### Rule-Based System
Create rules that define:
- When to send notifications (event triggers)
- Where to send them (channels)
- Who receives them (recipients)
- How often to send them (throttling)

### Throttling
Prevent notification spam by setting minimum intervals between notifications for the same event.

### History & Statistics
Track all sent notifications with detailed statistics and failure reports.

## Configuration

### Environment Variables

Copy `.env.notifications.example` to your `.env` file and configure:

```bash
# Enable/disable notifications
NOTIFICATIONS_ENABLED=true

# Rules storage location
NOTIFICATION_RULES_FILE=/data/notification_rules.json

# Email Configuration (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_FROM_NAME=Ombudsman Validation Studio
SMTP_USE_TLS=true

# Slack Configuration
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
SLACK_CHANNEL=#notifications

# Generic Webhook
WEBHOOK_URL=https://your-webhook-endpoint.com/notifications
WEBHOOK_TIMEOUT=30
```

### Email Provider Examples

#### Gmail
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password  # Use App Password, not regular password
SMTP_USE_TLS=true
```

#### Office 365
```bash
SMTP_HOST=smtp.office365.com
SMTP_PORT=587
SMTP_USERNAME=your-email@company.com
SMTP_PASSWORD=your-password
SMTP_USE_TLS=true
```

#### AWS SES
```bash
SMTP_HOST=email-smtp.us-east-1.amazonaws.com
SMTP_PORT=587
SMTP_USERNAME=your-ses-smtp-username
SMTP_PASSWORD=your-ses-smtp-password
SMTP_USE_TLS=true
```

### Slack Webhook Setup

1. Go to [Slack API: Incoming Webhooks](https://api.slack.com/messaging/webhooks)
2. Create a new app or select an existing app
3. Add "Incoming Webhooks" feature
4. Create a webhook for your desired channel
5. Copy the webhook URL to `SLACK_WEBHOOK_URL`

## Creating Notification Rules

### Via Frontend UI

1. Navigate to **Notifications** in the main menu
2. Click on the **Rules** tab
3. Click **Create Rule** button
4. Fill in the form:
   - **Name**: Descriptive name for the rule
   - **Description**: Optional description
   - **Event**: Select the trigger event
   - **Priority**: Select notification priority
   - **Channels**: Select one or more delivery channels
   - **Email Recipients**: Comma-separated email addresses (for email channel)
   - **Enabled**: Toggle to activate/deactivate the rule
5. Click **Create** to save

### Via API

```bash
curl -X POST http://localhost:8000/notifications/rules \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Validation Failure Alert",
    "description": "Alert team when validation fails",
    "event": "validation_failed",
    "channels": ["email", "slack"],
    "priority": "high",
    "email_recipients": ["team@company.com"],
    "slack_webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK",
    "enabled": true,
    "throttle_minutes": 15
  }'
```

### Rule Examples

#### Example 1: Critical Failures
```json
{
  "name": "Critical Validation Failures",
  "event": "validation_failed",
  "channels": ["email", "slack"],
  "priority": "critical",
  "email_recipients": ["oncall@company.com", "manager@company.com"],
  "throttle_minutes": 5
}
```

#### Example 2: Daily Success Summary
```json
{
  "name": "Validation Success Notifications",
  "event": "validation_completed",
  "channels": ["slack"],
  "priority": "low",
  "throttle_minutes": 60
}
```

#### Example 3: System Errors
```json
{
  "name": "System Error Alerts",
  "event": "system_error",
  "channels": ["email", "webhook"],
  "priority": "high",
  "email_recipients": ["devops@company.com"],
  "webhook_url": "https://your-incident-management.com/webhook"
}
```

## API Endpoints

### Configuration

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/notifications/config` | GET | Get current configuration |
| `/notifications/config` | PUT | Update configuration |

### Rule Management

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/notifications/rules` | GET | List all rules |
| `/notifications/rules` | POST | Create new rule |
| `/notifications/rules/{rule_id}` | PUT | Update rule |
| `/notifications/rules/{rule_id}` | DELETE | Delete rule |
| `/notifications/rules/{rule_id}/toggle` | POST | Enable/disable rule |

### Sending Notifications

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/notifications/send` | POST | Send manual notification |
| `/notifications/test` | POST | Test notification channel |

### History & Statistics

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/notifications/history` | GET | Get notification history |
| `/notifications/stats` | GET | Get notification statistics |

### Utility Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/notifications/channels` | GET | List available channels |
| `/notifications/events` | GET | List available events |
| `/notifications/priorities` | GET | List available priorities |

## Frontend Interface

### Navigation
Access the notification settings via: **http://localhost:3000/notifications**

### Tabs

#### 1. Configuration Tab
- View and edit global notification settings
- Configure SMTP, Slack, and webhook settings
- Test connection settings

#### 2. Rules Tab
- Create, edit, and delete notification rules
- Enable/disable rules with a toggle switch
- View all configured rules in a table

#### 3. History Tab
- View recent notification history
- See success/failure status
- Filter by event, channel, or priority

#### 4. Statistics Tab
- View total notifications sent
- Success/failure rates
- Breakdown by channel, event, and priority
- Recent failures list

### Testing Notifications

1. Click **Test Notification** button
2. Select a channel (Email, Slack, or Webhook)
3. Enter recipient (email address or webhook URL)
4. Click **Send Test**
5. Check for success message

## Examples

### Programmatic Usage

#### Send Custom Notification

```python
from notifications.service import notification_service
from notifications.models import NotificationEvent, NotificationPriority

notification_service.send_notification(
    event=NotificationEvent.CUSTOM,
    title="Data Processing Complete",
    message="The nightly data processing job has completed successfully.",
    priority=NotificationPriority.MEDIUM,
    context={"job_id": "nightly-2024-12-04", "records": 1000000}
)
```

#### Use Convenience Functions

```python
from notifications.service import notify_validation_completed, notify_error

# Notify validation completion
notify_validation_completed(
    pipeline_id="customer-validation",
    run_id="run-123456",
    status="success",
    duration_ms=45000
)

# Notify error
notify_error(
    title="Database Connection Failed",
    message="Unable to connect to Snowflake database",
    error_details={"host": "account.snowflakecomputing.com", "error": "timeout"}
)
```

#### Test Notification Channel

```python
from notifications.service import notification_service
from notifications.models import NotificationChannel

# Test email
success = notification_service.test_notification(
    channel=NotificationChannel.EMAIL,
    recipient="test@company.com"
)

# Test Slack
success = notification_service.test_notification(
    channel=NotificationChannel.SLACK,
    recipient="https://hooks.slack.com/services/YOUR/WEBHOOK"
)
```

### Integration with Pipeline Execution

Notifications are automatically triggered during pipeline execution:

```yaml
# In your pipeline YAML
name: customer_validation
steps:
  - name: validate_data
    type: validation
    # Notifications will automatically be sent based on rules
    # when validation starts, completes, or fails
```

## Troubleshooting

### Email Not Sending

**Problem**: Emails are not being delivered

**Solutions**:
1. Check SMTP credentials in configuration
2. Verify SMTP host and port
3. For Gmail: Use App Password instead of regular password
4. Check firewall rules for outbound SMTP traffic
5. Enable "Less secure app access" if required by provider
6. Check email notification history for error messages

### Slack Notifications Failing

**Problem**: Slack notifications not appearing

**Solutions**:
1. Verify webhook URL is correct
2. Check that the webhook is still active in Slack
3. Ensure the Slack app has permission to post to the channel
4. Test with a simple curl command:
   ```bash
   curl -X POST "YOUR_WEBHOOK_URL" \
     -H "Content-Type: application/json" \
     -d '{"text": "Test message"}'
   ```

### Webhook Timeout

**Problem**: Webhook notifications timing out

**Solutions**:
1. Increase `WEBHOOK_TIMEOUT` value
2. Check webhook endpoint is accessible
3. Verify endpoint responds within timeout period
4. Check webhook endpoint logs for errors

### Rules Not Triggering

**Problem**: Notification rules not sending notifications

**Solutions**:
1. Verify the rule is enabled (toggle switch)
2. Check event type matches the trigger
3. Review throttling settings (may be blocking notifications)
4. Check notification history for errors
5. Verify channels are properly configured

### Configuration Not Saving

**Problem**: Configuration changes don't persist

**Solutions**:
1. Check file permissions on `NOTIFICATION_RULES_FILE`
2. Ensure `/data` directory is writable
3. Check Docker volume mounts
4. Review backend logs for errors

## Best Practices

### 1. Use Appropriate Priority Levels
- **Critical**: System down, data corruption, security issues
- **High**: Validation failures, important errors
- **Medium**: Normal notifications, status updates
- **Low**: Informational messages, debug info

### 2. Set Throttling
Prevent notification spam by setting appropriate throttle intervals:
- Critical: 5-10 minutes
- High: 15-30 minutes
- Medium: 30-60 minutes
- Low: 60+ minutes

### 3. Use Multiple Channels
For critical events, send to multiple channels:
```json
{
  "event": "validation_failed",
  "channels": ["email", "slack"],
  "priority": "critical"
}
```

### 4. Test Before Production
Always test notification channels before relying on them:
1. Use the test notification feature
2. Create a test rule with low priority
3. Verify delivery to all channels
4. Check formatting and content

### 5. Monitor Notification History
Regularly review:
- Success/failure rates
- Recent failures
- Notification frequency
- Channel performance

### 6. Secure Credentials
- Never commit SMTP passwords to version control
- Use environment variables
- Rotate credentials regularly
- Use app-specific passwords when available

### 7. Group Recipients
For team notifications, consider:
- Using distribution lists instead of individual emails
- Creating dedicated Slack channels
- Setting up proper escalation paths

## Advanced Features

### Custom Conditions

Rules support custom conditions for advanced filtering:

```json
{
  "name": "High-Volume Failure Alert",
  "event": "validation_failed",
  "conditions": {
    "error_count": ">100",
    "severity": "high"
  }
}
```

### Message Templates

Customize notification messages with templates:

```json
{
  "message_template": "Validation {status} for {pipeline_id}. Duration: {duration_ms}ms. Records: {record_count}"
}
```

### Retry Configuration

Configure automatic retries for failed notifications:
- `max_retries`: Number of retry attempts (default: 3)
- `retry_delay_seconds`: Delay between retries (default: 60)

## Security Considerations

1. **SMTP Credentials**: Store in environment variables, never in code
2. **Webhook URLs**: Treat as secrets, especially for external services
3. **Email Content**: Be mindful of sensitive data in notifications
4. **Access Control**: Implement proper authentication for notification endpoints
5. **Audit Trail**: All notification events are logged in audit system

## Support

For issues or questions:
1. Check notification history and statistics for errors
2. Review backend logs for detailed error messages
3. Test individual channels to isolate problems
4. Consult this guide's troubleshooting section
5. Check the API documentation at `/docs`

## Future Enhancements

Planned features:
- Microsoft Teams integration
- SMS notifications (Twilio)
- Push notifications
- Custom notification templates
- Advanced rule conditions
- Notification scheduling
- Notification groups
- Digest notifications (batch multiple events)
