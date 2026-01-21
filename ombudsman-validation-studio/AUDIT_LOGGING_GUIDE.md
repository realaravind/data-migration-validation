# Ombudsman Validation Studio - Audit Logging Guide

**Version:** 1.0
**Date:** December 4, 2025
**Status:** ✅ Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Features](#features)
3. [Architecture](#architecture)
4. [Using the Audit Log Viewer](#using-the-audit-log-viewer)
5. [API Endpoints](#api-endpoints)
6. [Audit Categories](#audit-categories)
7. [Programmatic Usage](#programmatic-usage)
8. [Best Practices](#best-practices)
9. [Troubleshooting](#troubleshooting)

---

## Overview

The Audit Logging system provides comprehensive tracking of all system activities including:

- **User Actions** - Login, logout, API calls
- **Data Changes** - Create, update, delete operations
- **Validation Execution** - Pipeline runs and results
- **Configuration Changes** - Settings modifications
- **System Events** - Errors, warnings, and system operations
- **Database Operations** - Query execution and connections

### Key Benefits

✅ **Compliance** - Meet regulatory requirements (SOX, GDPR, HIPAA)
✅ **Security** - Track unauthorized access attempts
✅ **Debugging** - Trace issues through complete audit trail
✅ **Performance** - Monitor response times and slow operations
✅ **Accountability** - Know who did what and when

---

## Features

### 1. Automatic API Request Logging

Every API request is automatically logged with:
- Request method and path
- Response status code
- Duration (milliseconds)
- User information (if authenticated)
- Client IP address and user agent
- Request ID for correlation

### 2. Audit Categories

10 distinct categories for organized tracking:

| Category | Description | Examples |
|----------|-------------|----------|
| **authentication** | Login/logout events | User login, token refresh |
| **authorization** | Permission checks | Access denied, role checks |
| **api_request** | API calls | GET /features, POST /pipelines |
| **data_change** | Data modifications | Create pipeline, update config |
| **validation** | Pipeline execution | Run validation, view results |
| **configuration** | Config changes | Update settings, change mappings |
| **system** | System events | Startup, shutdown, errors |
| **database** | DB operations | Query execution, connection tests |
| **file_operation** | File actions | Upload, download, delete |
| **export** | Data exports | CSV export, JSON export |

### 3. Severity Levels

5 levels for filtering and alerting:

- **DEBUG** - Detailed diagnostic information
- **INFO** - General informational messages
- **WARNING** - Warning messages for potential issues
- **ERROR** - Error messages for serious problems
- **CRITICAL** - Critical errors requiring immediate attention

### 4. Advanced Filtering

Filter logs by:
- Date range (start/end date)
- Severity level
- Category
- User ID or username
- Action keywords
- Resource type and ID
- IP address
- Free-text search

### 5. Export Capabilities

Export audit logs to:
- **CSV** - For Excel and analysis tools
- **JSON** - For programmatic processing
- Filtered exports with custom date ranges

### 6. Summary Statistics

View aggregated metrics:
- Total log count
- Breakdown by level
- Breakdown by category
- Most active users
- Most common actions
- Recent errors

---

## Architecture

### Components

```
┌─────────────────────────────────────────────┐
│          FastAPI Application                 │
│                                              │
│  ┌──────────────────────────────────┐      │
│  │   AuditMiddleware                 │      │
│  │   - Intercepts all requests       │      │
│  │   - Logs automatically            │      │
│  └──────────────┬───────────────────┘      │
│                 │                            │
│  ┌──────────────▼───────────────────┐      │
│  │   AuditLogger Service             │      │
│  │   - Centralized logging           │      │
│  │   - Convenience methods           │      │
│  └──────────────┬───────────────────┘      │
│                 │                            │
│  ┌──────────────▼───────────────────┐      │
│  │   AuditLogStorage                 │      │
│  │   - JSONL file storage            │      │
│  │   - Daily rotation                │      │
│  │   - Query and filter              │      │
│  └──────────────┬───────────────────┘      │
│                 │                            │
└─────────────────┼────────────────────────────┘
                 │
                 ▼
         ┌──────────────┐
         │  Data Files  │
         │  (JSONL)     │
         └──────────────┘
```

### Storage Format

Audit logs are stored as **JSONL** (JSON Lines) files:
- One log entry per line
- One file per day: `audit_YYYYMMDD.jsonl`
- Efficient for append operations
- Easy to parse and analyze

**Example Log Entry:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-04T08:54:18.779102",
  "level": "info",
  "category": "api_request",
  "action": "GET /features",
  "user_id": "user123",
  "username": "john.doe",
  "ip_address": "192.168.1.100",
  "user_agent": "Mozilla/5.0...",
  "resource_type": null,
  "resource_id": null,
  "details": {"query_params": {}},
  "request_id": "req-abc-123",
  "session_id": "session-xyz",
  "duration_ms": 25,
  "status_code": 200,
  "error_message": null
}
```

---

## Using the Audit Log Viewer

### Accessing the UI

**URL:** http://localhost:3000/audit-logs

### Main Features

#### 1. Summary Cards

At the top of the page, view real-time statistics:
- **Total Logs** - Count of all audit entries
- **Recent Errors** - Number of errors in selected period
- **By Level** - Distribution across severity levels
- **By Category** - Most active categories

#### 2. Filter Panel

Collapsible filter panel with multiple criteria:

**Date Range:**
- Start date/time picker
- End date/time picker
- Default: Last 7 days

**Level Filter:**
- Dropdown with all severity levels
- Filter to specific severity

**Category Filter:**
- Dropdown with all audit categories
- Focus on specific activity types

**Search:**
- Free-text search across action, details, error messages
- Case-insensitive matching

**User Filter:**
- Filter by username
- Track specific user activity

**Actions:**
- **Apply Filters** - Execute filtered query
- **Reset** - Clear all filters

#### 3. Audit Logs Table

Sortable table with key information:

| Column | Description |
|--------|-------------|
| Timestamp | When the event occurred |
| Level | Severity level (colored chip) |
| Category | Event category |
| Action | What action was performed |
| User | Username (if authenticated) |
| IP Address | Client IP address |
| Status | HTTP status code (if applicable) |
| Duration | How long the operation took |

**Table Features:**
- Click any row to see full details
- Sort by any column
- Pagination controls at bottom
- Configurable rows per page (10, 25, 50, 100)

#### 4. Detail Dialog

Click any log entry to see complete information:
- All log fields displayed
- JSON details pretty-printed
- Copy button for Request ID
- Close button to return to table

#### 5. Export Functions

**Export to CSV:**
- Click "Export CSV" button
- Downloads filtered results as CSV file
- Filename includes timestamp

**Export to JSON:**
- Click "Export JSON" button
- Downloads filtered results as JSON file
- Includes all log details

#### 6. Refresh

Click the **Refresh** button to reload the latest logs and statistics.

---

## API Endpoints

### Base URL

```
http://localhost:8000/audit
```

### Endpoints Reference

#### 1. Get Recent Logs

```http
GET /audit/logs/recent?limit=100&level=error
```

**Query Parameters:**
- `limit` (int): Max number of logs to return (default: 100)
- `level` (string): Filter by severity level

**Response:** Array of AuditLog objects

**Example:**
```bash
curl "http://localhost:8000/audit/logs/recent?limit=10"
```

---

#### 2. Query Logs with Filters

```http
POST /audit/logs/query
Content-Type: application/json
```

**Request Body:**
```json
{
  "start_date": "2025-12-01T00:00:00",
  "end_date": "2025-12-04T23:59:59",
  "level": "error",
  "category": "validation",
  "search": "pipeline",
  "limit": 50,
  "offset": 0,
  "sort_by": "timestamp",
  "sort_order": "desc"
}
```

**Response:** Array of filtered AuditLog objects

**Example:**
```bash
curl -X POST http://localhost:8000/audit/logs/query \
  -H "Content-Type: application/json" \
  -d '{"level": "error", "limit": 20}'
```

---

#### 3. Get Summary Statistics

```http
GET /audit/logs/summary?start_date=2025-12-01&end_date=2025-12-04
```

**Query Parameters:**
- `start_date` (datetime): Start of date range
- `end_date` (datetime): End of date range

**Response:**
```json
{
  "total_logs": 1250,
  "by_level": {
    "info": 1000,
    "warning": 200,
    "error": 50
  },
  "by_category": {
    "api_request": 800,
    "validation": 300,
    "authentication": 100
  },
  "by_user": {
    "john.doe": 500,
    "jane.smith": 400
  },
  "recent_errors": [...],
  "most_active_users": [...],
  "most_common_actions": [...]
}
```

---

#### 4. Export Logs

```http
POST /audit/logs/export
Content-Type: application/json
```

**Request Body:**
```json
{
  "format": "csv",
  "filters": {
    "start_date": "2025-12-01T00:00:00",
    "end_date": "2025-12-04T23:59:59",
    "level": "error"
  },
  "include_details": true
}
```

**Response:** File download (CSV or JSON)

**Example:**
```bash
curl -X POST http://localhost:8000/audit/logs/export \
  -H "Content-Type: application/json" \
  -d '{"format": "csv", "filters": {"limit": 100}}' \
  -o audit_logs.csv
```

---

#### 5. Get Error Logs

```http
GET /audit/logs/errors?limit=50
```

Returns recent ERROR and CRITICAL level logs.

---

#### 6. Get User Logs

```http
GET /audit/logs/user/{user_id}?limit=100
```

Returns all logs for a specific user.

---

#### 7. Get Resource Logs

```http
GET /audit/logs/resource/{resource_type}/{resource_id}?limit=100
```

Returns all logs related to a specific resource.

**Example:**
```bash
curl "http://localhost:8000/audit/logs/resource/pipeline/pipeline_abc"
```

---

#### 8. Get Categories

```http
GET /audit/categories
```

Returns list of all audit categories.

---

#### 9. Get Levels

```http
GET /audit/levels
```

Returns list of all severity levels.

---

#### 10. Cleanup Old Logs

```http
DELETE /audit/logs/cleanup?days_to_keep=90
```

Deletes audit logs older than specified days.

---

## Audit Categories

### Detailed Category Descriptions

#### 1. Authentication (`authentication`)

**Tracked Events:**
- User login attempts (success/failure)
- User logout
- Token generation and refresh
- Password changes
- Multi-factor authentication

**Example:**
```python
audit_logger.log_authentication(
    user_id="user123",
    action="login_success",
    username="john.doe",
    ip_address="192.168.1.100"
)
```

---

#### 2. Authorization (`authorization`)

**Tracked Events:**
- Permission checks
- Access denied events
- Role-based access control decisions
- Resource access attempts

**Example:**
```python
audit_logger.log_authorization(
    user_id="user123",
    action="access_denied",
    resource_type="pipeline",
    resource_id="sensitive_pipeline",
    allowed=False
)
```

---

#### 3. API Request (`api_request`)

**Tracked Events:**
- All HTTP requests (automatically by middleware)
- Request method and path
- Response status and duration

**Automatic Logging:**
```
Every API call is logged automatically:
GET /features -> logged
POST /pipelines/execute -> logged
DELETE /data/clear -> logged
```

---

#### 4. Data Change (`data_change`)

**Tracked Events:**
- Create operations
- Update operations
- Delete operations
- Before/after values

**Example:**
```python
audit_logger.log_data_change(
    resource_type="pipeline",
    resource_id="pipeline_abc",
    operation="update",
    user_id="user123",
    before={"name": "Old Name"},
    after={"name": "New Name"}
)
```

---

#### 5. Validation (`validation`)

**Tracked Events:**
- Pipeline execution start
- Pipeline execution completion
- Validation failures
- Result generation

**Example:**
```python
audit_logger.log_validation_execution(
    pipeline_id="pipeline_abc",
    run_id="run_xyz",
    status="completed",
    duration_ms=5000,
    user_id="user123"
)
```

---

#### 6. Configuration (`configuration`)

**Tracked Events:**
- Settings changes
- Configuration updates
- Mapping modifications
- System preferences

**Example:**
```python
audit_logger.log_configuration_change(
    config_type="mapping",
    config_id="mapping_123",
    operation="update",
    user_id="user123",
    before={...},
    after={...}
)
```

---

#### 7. System (`system`)

**Tracked Events:**
- Application startup/shutdown
- System errors
- Background jobs
- Scheduled tasks

**Example:**
```python
audit_logger.log_system_event(
    action="application_startup",
    level=AuditLevel.INFO,
    details={"version": "2.0.0"}
)
```

---

#### 8. Database (`database`)

**Tracked Events:**
- Query execution
- Connection tests
- Schema changes
- Data migrations

**Example:**
```python
audit_logger.log_database_operation(
    database="sqlserver",
    operation="query_execute",
    table="Customers",
    duration_ms=250
)
```

---

#### 9. File Operation (`file_operation`)

**Tracked Events:**
- File uploads
- File downloads
- File deletions
- File modifications

**Example:**
```python
audit_logger.log_file_operation(
    operation="upload",
    file_path="/data/pipelines/pipeline.yaml",
    file_type="yaml",
    user_id="user123"
)
```

---

#### 10. Export (`export`)

**Tracked Events:**
- Data exports (CSV, JSON, Excel)
- Report generation
- Audit log exports

**Example:**
```python
audit_logger.log_export(
    export_type="audit_logs",
    format="csv",
    record_count=1000,
    user_id="user123"
)
```

---

## Programmatic Usage

### Using the Audit Logger in Code

#### Import the Logger

```python
from audit.audit_logger import audit_logger, AuditLevel, AuditCategory
```

#### Basic Usage

```python
# Simple log entry
audit_logger.log(
    category=AuditCategory.API_REQUEST,
    action="custom_action",
    level=AuditLevel.INFO,
    user_id="user123"
)
```

#### Convenience Methods

**Log Authentication:**
```python
audit_logger.log_authentication(
    user_id="user123",
    action="login_success",
    username="john.doe",
    ip_address=request.client.host,
    success=True
)
```

**Log Data Change:**
```python
audit_logger.log_data_change(
    resource_type="pipeline",
    resource_id="pipeline_123",
    operation="create",
    user_id="user123",
    after={"name": "New Pipeline"}
)
```

**Log Error:**
```python
audit_logger.log_error(
    error_message="Failed to connect to database",
    action="database_connection_failed",
    user_id="user123",
    details={"error_code": "CONN_TIMEOUT"}
)
```

**Log Validation:**
```python
audit_logger.log_validation_execution(
    pipeline_id="pipeline_123",
    run_id="run_xyz",
    status="completed",
    duration_ms=5000,
    user_id="user123",
    details={"steps_completed": 10, "errors": 0}
)
```

### Querying Logs Programmatically

```python
from audit.storage import AuditLogStorage
from audit.models import AuditLogFilter, AuditLevel

storage = AuditLogStorage()

# Query with filters
filters = AuditLogFilter(
    level=AuditLevel.ERROR,
    category="validation",
    limit=50
)

logs = storage.query_logs(filters)

# Get summary
summary = storage.get_summary(filters)

# Export logs
csv_data = storage.export_logs(filters, format="csv")
```

---

## Best Practices

### 1. What to Log

**DO Log:**
- Authentication events (login, logout)
- Authorization failures
- Data modifications (create, update, delete)
- Configuration changes
- Security-related events
- Errors and exceptions
- Long-running operations

**DON'T Log:**
- Passwords or credentials
- Sensitive personal information (unless required)
- Excessive DEBUG information in production
- Health check endpoints (excluded by default)

### 2. Log Levels

Use appropriate severity levels:

- **DEBUG** - Development and troubleshooting
- **INFO** - Normal operations (default)
- **WARNING** - Potential issues, degraded performance
- **ERROR** - Errors that need attention
- **CRITICAL** - System failures, data loss

### 3. Performance Considerations

**Storage:**
- Logs rotate daily automatically
- Configure retention period (default: 90 days)
- Monitor disk space usage

**Query Performance:**
- Use date ranges for queries
- Limit result sets appropriately
- Consider archiving old logs

### 4. Compliance

**For Regulatory Compliance:**
- Enable audit logging for all environments
- Set appropriate retention periods
- Regularly review audit logs
- Export logs for archival
- Restrict access to audit log viewer
- Monitor for suspicious activity

### 5. Alerting

Set up alerts for:
- High error rates
- Failed authentication attempts
- Unauthorized access attempts
- System errors
- Long-running operations

---

## Troubleshooting

### Common Issues

#### 1. Logs Not Appearing

**Check:**
```bash
# Verify audit middleware is active
docker logs ombudsman-validation-studio-studio-backend-1 | grep "audit"

# Check log files exist
ls -la backend/data/audit_logs/

# Verify endpoint
curl http://localhost:8000/audit/logs/recent?limit=5
```

**Solution:**
- Ensure backend is restarted after adding audit logging
- Check AUDIT_LOG_DIR environment variable
- Verify write permissions on data directory

---

#### 2. UI Not Showing Logs

**Check:**
```bash
# Test API directly
curl http://localhost:8000/audit/logs/recent

# Check browser console for errors
```

**Solution:**
- Verify backend is running
- Check CORS configuration
- Clear browser cache
- Check network tab in dev tools

---

#### 3. Performance Issues

**Symptoms:**
- Slow API responses
- High disk usage
- Memory issues

**Solutions:**
- Run cleanup: `curl -X DELETE "http://localhost:8000/audit/logs/cleanup?days_to_keep=30"`
- Reduce retention period
- Archive old logs to external storage
- Use more specific date ranges in queries

---

#### 4. Disk Space

**Check Disk Usage:**
```bash
du -sh backend/data/audit_logs/
ls -lh backend/data/audit_logs/
```

**Cleanup Old Logs:**
```bash
# Via API
curl -X DELETE "http://localhost:8000/audit/logs/cleanup?days_to_keep=30"

# Manual cleanup
find backend/data/audit_logs -name "audit_*.jsonl" -mtime +30 -delete
```

---

## Configuration

### Environment Variables

```bash
# Audit log storage directory
AUDIT_LOG_DIR="/data/audit_logs"

# Retention period (days)
AUDIT_RETENTION_DAYS=90

# Log level for audit events
AUDIT_LOG_LEVEL="INFO"
```

### Docker Configuration

In `docker-compose.yml`:
```yaml
environment:
  AUDIT_LOG_DIR: "/data/audit_logs"
volumes:
  - ./backend/data:/data
```

---

## Security Considerations

### 1. Access Control

- Restrict access to audit log viewer to administrators
- Use authentication for audit API endpoints
- Consider read-only access for most users

### 2. Data Protection

- Audit logs may contain sensitive information
- Encrypt logs at rest (if required)
- Secure log export/download process
- Control who can delete logs

### 3. Audit the Auditors

- Log access to audit logs themselves
- Monitor export activities
- Track cleanup operations

---

## Compliance Checklist

### SOX Compliance
- [ ] All financial data access logged
- [ ] User actions traceable
- [ ] Logs retained for required period
- [ ] Regular audit log reviews performed
- [ ] Unauthorized access attempts logged

### GDPR Compliance
- [ ] Personal data access logged
- [ ] Data deletion logged
- [ ] Export requests logged
- [ ] Consent changes logged
- [ ] Data breach detection enabled

### HIPAA Compliance
- [ ] PHI access logged
- [ ] Authentication events logged
- [ ] Authorization failures logged
- [ ] Logs encrypted
- [ ] Audit trail complete and unalterable

---

## Support

### Getting Help

**View Logs:**
```bash
# Backend logs
docker-compose logs -f studio-backend | grep audit

# Check audit log files
cat backend/data/audit_logs/audit_$(date +%Y%m%d).jsonl
```

**Test Endpoints:**
```bash
# Health check
curl http://localhost:8000/health

# Recent logs
curl http://localhost:8000/audit/logs/recent?limit=5

# Summary
curl http://localhost:8000/audit/logs/summary
```

**Access UI:**
- Open http://localhost:3000/audit-logs
- Check browser console for errors

---

## Summary

The Audit Logging system is now fully operational with:

✅ **Automatic Logging** - All API requests tracked
✅ **10 Categories** - Comprehensive event coverage
✅ **5 Severity Levels** - Appropriate filtering
✅ **Advanced Filtering** - Query by multiple criteria
✅ **Export Capabilities** - CSV and JSON formats
✅ **Rich UI** - Complete audit log viewer
✅ **9 API Endpoints** - Programmatic access
✅ **Compliance Ready** - Meet regulatory requirements

**Access the System:**
- **UI:** http://localhost:3000/audit-logs
- **API:** http://localhost:8000/audit/*
- **Docs:** http://localhost:8000/docs (search for "audit")

---

**Audit Logging Guide Version:** 1.0
**Date:** December 4, 2025
**Status:** ✅ Production Ready
