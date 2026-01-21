# Notification System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                     Notification System                          │
└─────────────────────────────────────────────────────────────────┘

┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│   Frontend   │────▶│   Backend    │────▶│   Providers  │
│   (React)    │     │   (FastAPI)  │     │   (SMTP/etc) │
└──────────────┘     └──────────────┘     └──────────────┘
      │                     │                     │
      │                     │                     │
      ▼                     ▼                     ▼
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ User Actions │     │    Rules     │     │ Email Server │
│   - Create   │     │   Engine     │     │ Slack API    │
│   - Edit     │     │   - Match    │     │ Webhooks     │
│   - Test     │     │   - Throttle │     └──────────────┘
│   - View     │     │   - Send     │
└──────────────┘     └──────────────┘
```

## Component Architecture

### Frontend Layer (`/frontend/src/pages/NotificationSettings.tsx`)

```
┌────────────────────────────────────────────────────┐
│          NotificationSettings Component            │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────┐  │
│  │Configuration│  │    Rules    │  │ History  │  │
│  │    Tab      │  │     Tab     │  │   Tab    │  │
│  └─────────────┘  └─────────────┘  └──────────┘  │
│                                                    │
│  ┌──────────────────────────────────────────────┐ │
│  │          Statistics Tab                       │ │
│  └──────────────────────────────────────────────┘ │
│                                                    │
│  Features:                                         │
│  - CRUD operations on rules                        │
│  - Configuration management                        │
│  - Real-time testing                               │
│  - History visualization                           │
│  - Analytics & statistics                          │
└────────────────────────────────────────────────────┘
```

### Backend Layer (`/backend/notifications/`)

```
┌────────────────────────────────────────────────────┐
│              Backend Architecture                   │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────┐                                 │
│  │   router.py  │ ◄── 14 REST API Endpoints       │
│  └──────┬───────┘                                 │
│         │                                          │
│         ▼                                          │
│  ┌──────────────┐                                 │
│  │  service.py  │ ◄── Notification Service        │
│  │              │     - Rule engine                │
│  │  (Singleton) │     - Throttling                 │
│  │              │     - History tracking           │
│  └──────┬───────┘                                 │
│         │                                          │
│         ▼                                          │
│  ┌──────────────┐                                 │
│  │ providers.py │ ◄── Channel Providers           │
│  │              │     - EmailProvider              │
│  │              │     - SlackProvider              │
│  │              │     - WebhookProvider            │
│  └──────┬───────┘                                 │
│         │                                          │
│         ▼                                          │
│  ┌──────────────┐                                 │
│  │  models.py   │ ◄── Data Models                 │
│  │              │     - Pydantic schemas           │
│  │              │     - Enums                      │
│  │              │     - Validation                 │
│  └──────────────┘                                 │
└────────────────────────────────────────────────────┘
```

## Data Flow

### 1. Creating a Notification Rule

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│  User    │      │ Frontend │      │ Backend  │      │  Storage │
│  (UI)    │      │ (React)  │      │ (Router) │      │  (JSON)  │
└────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                 │                 │
     │ Click Create    │                 │                 │
     │────────────────▶│                 │                 │
     │                 │                 │                 │
     │ Fill Form       │                 │                 │
     │────────────────▶│                 │                 │
     │                 │                 │                 │
     │ Submit          │                 │                 │
     │────────────────▶│                 │                 │
     │                 │ POST /rules     │                 │
     │                 │────────────────▶│                 │
     │                 │                 │ Validate        │
     │                 │                 │─────────┐       │
     │                 │                 │         │       │
     │                 │                 │◀────────┘       │
     │                 │                 │ Save Rule       │
     │                 │                 │────────────────▶│
     │                 │                 │                 │
     │                 │                 │◀────────────────│
     │                 │◀────────────────│                 │
     │◀────────────────│                 │                 │
     │ Success         │                 │                 │
```

### 2. Sending a Notification

```
┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Event   │   │  Service │   │  Rules   │   │ Provider │   │ External │
│ Trigger  │   │  Layer   │   │  Engine  │   │  (SMTP)  │   │  Server  │
└────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘   └────┬─────┘
     │              │              │              │              │
     │ validation_  │              │              │              │
     │ completed    │              │              │              │
     │─────────────▶│              │              │              │
     │              │ Find Rules   │              │              │
     │              │─────────────▶│              │              │
     │              │              │ Match Event  │              │
     │              │              │──────┐       │              │
     │              │              │      │       │              │
     │              │              │◀─────┘       │              │
     │              │◀─────────────│              │              │
     │              │ Check        │              │              │
     │              │ Throttle     │              │              │
     │              │──────┐       │              │              │
     │              │      │       │              │              │
     │              │◀─────┘       │              │              │
     │              │ Send Email   │              │              │
     │              │─────────────────────────────▶│              │
     │              │              │              │ Connect SMTP │
     │              │              │              │─────────────▶│
     │              │              │              │              │
     │              │              │              │◀─────────────│
     │              │◀─────────────────────────────│              │
     │              │ Record       │              │              │
     │              │ History      │              │              │
     │              │──────┐       │              │              │
     │              │      │       │              │              │
     │              │◀─────┘       │              │              │
```

### 3. Testing a Notification

```
┌──────────┐      ┌──────────┐      ┌──────────┐      ┌──────────┐
│  User    │      │ Frontend │      │ Backend  │      │ Provider │
└────┬─────┘      └────┬─────┘      └────┬─────┘      └────┬─────┘
     │                 │                 │                 │
     │ Click Test      │                 │                 │
     │────────────────▶│                 │                 │
     │                 │                 │                 │
     │ Select Channel  │                 │                 │
     │────────────────▶│                 │                 │
     │                 │                 │                 │
     │ Enter Recipient │                 │                 │
     │────────────────▶│                 │                 │
     │                 │ POST /test      │                 │
     │                 │────────────────▶│                 │
     │                 │                 │ Send Test       │
     │                 │                 │────────────────▶│
     │                 │                 │                 │
     │                 │                 │◀────────────────│
     │                 │◀────────────────│                 │
     │◀────────────────│                 │                 │
     │ Success/Fail    │                 │                 │
```

## API Endpoints

### Configuration Management
```
GET    /notifications/config          → Get configuration
PUT    /notifications/config          → Update configuration
```

### Rule Management
```
GET    /notifications/rules           → List all rules
POST   /notifications/rules           → Create new rule
PUT    /notifications/rules/{id}      → Update rule
DELETE /notifications/rules/{id}      → Delete rule
POST   /notifications/rules/{id}/toggle → Enable/disable rule
```

### Notification Operations
```
POST   /notifications/send            → Send manual notification
POST   /notifications/test            → Test channel
```

### Analytics
```
GET    /notifications/history         → Get history
GET    /notifications/stats           → Get statistics
```

### Utility
```
GET    /notifications/channels        → List available channels
GET    /notifications/events          → List available events
GET    /notifications/priorities      → List priority levels
```

## Data Models

### Core Models

```typescript
// NotificationConfig
{
  enabled: boolean
  smtp_host?: string
  smtp_port: number
  smtp_username?: string
  smtp_password?: string
  smtp_from_email?: string
  default_slack_webhook?: string
  default_webhook_url?: string
  max_notifications_per_hour: number
  ...
}

// NotificationRule
{
  id?: string
  name: string
  description?: string
  enabled: boolean
  event: string
  channels: string[]
  priority: string
  email_recipients?: string[]
  slack_webhook_url?: string
  webhook_url?: string
  throttle_minutes?: number
  ...
}

// NotificationHistory
{
  id: string
  rule_id?: string
  channel: string
  event: string
  priority: string
  title: string
  message: string
  sent_at: string
  success: boolean
  error_message?: string
  ...
}
```

## Storage

```
/data/
  └── notification_rules.json    ← Persistent rule storage
      [
        {
          "id": "uuid-1",
          "name": "Validation Failures",
          "event": "validation_failed",
          "channels": ["email", "slack"],
          ...
        }
      ]
```

## Environment Configuration

```
Environment Variables → Docker Compose → Backend Service
                                            │
                                            ├─→ NotificationConfig
                                            ├─→ EmailProvider
                                            ├─→ SlackProvider
                                            └─→ WebhookProvider
```

## Security Model

```
┌─────────────────────────────────────┐
│      Security Considerations        │
├─────────────────────────────────────┤
│                                     │
│ 1. Credentials                      │
│    - Stored in env vars             │
│    - Masked in API responses        │
│    - Never logged                   │
│                                     │
│ 2. API Security                     │
│    - Input validation (Pydantic)    │
│    - HTTP status codes              │
│    - Error handling                 │
│                                     │
│ 3. Audit Trail                      │
│    - All sends logged               │
│    - Success/failure tracked        │
│    - Full history maintained        │
│                                     │
│ 4. Rate Limiting                    │
│    - Configurable max/hour          │
│    - Per-rule throttling            │
│    - Retry mechanisms               │
└─────────────────────────────────────┘
```

## Extensibility

### Adding New Channel

```python
# 1. Add to models.py
class NotificationChannel(str, Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
    TEAMS = "teams"  # NEW!

# 2. Create provider in providers.py
class TeamsProvider:
    def send(self, ...):
        # Implementation

# 3. Update service.py
def _send_teams(self, ...):
    provider = TeamsProvider(self._config)
    return provider.send(...)

# 4. Update router.py description
def get_channel_description(channel):
    descriptions = {
        NotificationChannel.TEAMS: "Send to Microsoft Teams"
    }
```

### Adding New Event

```python
# 1. Add to models.py
class NotificationEvent(str, Enum):
    VALIDATION_STARTED = "validation_started"
    # ... existing events
    DATA_QUALITY_ALERT = "data_quality_alert"  # NEW!

# 2. Use in your code
from notifications.service import notification_service

notification_service.send_notification(
    event=NotificationEvent.DATA_QUALITY_ALERT,
    title="Data Quality Issue Detected",
    message="Null values exceed threshold",
    priority=NotificationPriority.HIGH
)
```

## Performance Considerations

```
Optimization Strategies:

1. Rule Matching
   - Rules stored in memory
   - O(n) lookup per event
   - Minimal overhead

2. Throttling
   - In-memory cache
   - Automatic cleanup
   - Prevents spam

3. Async Sending (Future)
   - Queue-based sending
   - Non-blocking operations
   - Retry mechanisms

4. History Management
   - Rotating log files
   - Configurable retention
   - Pagination support
```

## Integration Points

```
┌─────────────────────────────────────────────────┐
│         System Integrations                     │
├─────────────────────────────────────────────────┤
│                                                 │
│  Pipeline Execution                             │
│  ├─→ validation_started                         │
│  ├─→ validation_completed                       │
│  └─→ validation_failed                          │
│                                                 │
│  Audit System                                   │
│  ├─→ audit_error                                │
│  └─→ authentication_failure                     │
│                                                 │
│  Custom Integrations                            │
│  ├─→ data_change                                │
│  ├─→ system_error                               │
│  └─→ custom events                              │
└─────────────────────────────────────────────────┘
```

## Monitoring & Observability

```
Metrics Available:

1. Success Rates
   - Total sent
   - Successful deliveries
   - Failed deliveries
   - Success percentage

2. Channel Performance
   - Per-channel counts
   - Per-channel failures
   - Response times

3. Event Analytics
   - Most frequent events
   - Event trends
   - Event priorities

4. Rule Effectiveness
   - Rule trigger counts
   - Rule success rates
   - Throttling stats
```

This architecture provides a robust, scalable, and maintainable notification system for the Ombudsman Validation Studio.
