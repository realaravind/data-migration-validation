# Notifications Quick Start Guide

## 5-Minute Setup

### Step 1: Configure Email (Optional but Recommended)

Edit your `.env` file or set environment variables:

```bash
# For Gmail
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
```

**Gmail Setup**:
1. Go to Google Account Settings
2. Enable 2-Factor Authentication
3. Generate an App Password
4. Use the App Password (not your regular password)

### Step 2: Start the Application

```bash
cd ombudsman-validation-studio
docker-compose up
```

### Step 3: Access Notification Settings

Open your browser: `http://localhost:3000/notifications`

### Step 4: Create Your First Rule

1. Click on the **Rules** tab
2. Click **Create Rule** button
3. Fill in:
   - **Name**: `My First Notification`
   - **Event**: Select `validation_completed`
   - **Channels**: Select `email`
   - **Priority**: Select `medium`
   - **Email Recipients**: Enter your email
   - **Enabled**: Keep checked
4. Click **Create**

### Step 5: Test It!

1. Click **Test Notification** button (top right)
2. Select `email` as channel
3. Enter your email address
4. Click **Send Test**
5. Check your inbox!

## Common Use Cases

### Use Case 1: Get Notified When Validations Fail

```json
{
  "name": "Validation Failures",
  "event": "validation_failed",
  "channels": ["email"],
  "priority": "high",
  "email_recipients": ["your-email@company.com"]
}
```

### Use Case 2: Slack Notifications

1. Get Slack webhook URL from: https://api.slack.com/messaging/webhooks
2. Add to your `.env`:
   ```bash
   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
   ```
3. Create rule:
   ```json
   {
     "name": "Slack Alerts",
     "event": "validation_completed",
     "channels": ["slack"],
     "priority": "medium"
   }
   ```

### Use Case 3: Multi-Channel Critical Alerts

```json
{
  "name": "Critical Issues",
  "event": "system_error",
  "channels": ["email", "slack"],
  "priority": "critical",
  "email_recipients": ["team@company.com"],
  "throttle_minutes": 5
}
```

## Troubleshooting

### Email Not Working?

**Quick Checks**:
1. Are credentials correct in `.env`?
2. Using App Password for Gmail?
3. Check firewall for port 587
4. Look at History tab for error messages

**Test Command**:
```bash
curl -X POST http://localhost:8000/notifications/test \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "email",
    "recipient": "your-email@company.com"
  }'
```

### Slack Not Working?

**Quick Checks**:
1. Is webhook URL correct?
2. Is webhook active in Slack?
3. Does app have permission to post?

**Test Command**:
```bash
curl -X POST http://localhost:8000/notifications/test \
  -H "Content-Type: application/json" \
  -d '{
    "channel": "slack",
    "webhook_url": "YOUR_WEBHOOK_URL"
  }'
```

## Next Steps

- Read the full guide: `NOTIFICATION_SYSTEM_GUIDE.md`
- View API docs: `http://localhost:8000/docs`
- Check Statistics tab for analytics
- Create rules for different events

## Quick Reference

### API Endpoints
- List rules: `GET /notifications/rules`
- Create rule: `POST /notifications/rules`
- Send notification: `POST /notifications/send`
- View history: `GET /notifications/history`
- View stats: `GET /notifications/stats`

### Available Events
- `validation_started`
- `validation_completed`
- `validation_failed`
- `pipeline_error`
- `system_error`
- `audit_error`
- `authentication_failure`
- `data_change`
- `custom`

### Priority Levels
- `low` - Informational
- `medium` - Normal (default)
- `high` - Important
- `critical` - Urgent

### Channels
- `email` - SMTP Email
- `slack` - Slack Webhooks
- `webhook` - Generic HTTP
- `teams` - Coming Soon

## Support

- Documentation: `NOTIFICATION_SYSTEM_GUIDE.md`
- API Docs: http://localhost:8000/docs
- Logs: Check Docker logs for errors

Enjoy your notifications!
