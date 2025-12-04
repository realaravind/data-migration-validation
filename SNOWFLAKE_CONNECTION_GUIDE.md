# Snowflake Connection Setup Guide

This guide explains how to configure and use Real Snowflake connections in the Ombudsman Validation Studio.

## Prerequisites

1. **Snowflake Account**
   - Active Snowflake account
   - Account URL (e.g., `abc12345.us-east-1`)
   - Username and password

2. **Warehouse and Database**
   - Created warehouse (e.g., `COMPUTE_WH`)
   - Target database (e.g., `SAMPLEDW`)
   - Schema (e.g., `PUBLIC`)

3. **Python Package**
   - `snowflake-connector-python` (already in requirements.txt)

## Configuration

### Environment Variables

Create a `.env` file in the project root with your Snowflake credentials:

```bash
# Snowflake Connection
SNOWFLAKE_USER=your_username
SNOWFLAKE_PASSWORD=your_password
SNOWFLAKE_ACCOUNT=abc12345.us-east-1
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_DATABASE=SAMPLEDW
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_ROLE=ACCOUNTADMIN  # Optional
```

### Finding Your Snowflake Account

Your Snowflake account identifier can be found in:
1. **URL**: https://**abc12345.us-east-1**.snowflakecomputing.com
2. **Account**: `abc12345.us-east-1`

### Required Permissions

The Snowflake user needs:
- `USAGE` on warehouse
- `USAGE` on database
- `USAGE` on schema
- `SELECT` on tables to validate
- `CREATE TABLE` if generating sample data

## Connection Features

### 1. Retry Logic

The connection automatically retries on failure:
```python
conn = get_snow_conn(cfg, retries=3, retry_delay=2)
```

- **Retries**: 3 attempts by default
- **Delay**: 2 seconds between attempts
- **Logging**: All attempts logged

### 2. Connection Pooling

Connections use:
- `client_session_keep_alive=True` - Keeps session alive
- `network_timeout=60` - 60 second network timeout
- `login_timeout=30` - 30 second login timeout

### 3. Health Checks

Test connection anytime:
```python
from ombudsman.core.connections import test_snowflake_connection

result = test_snowflake_connection(cfg)
print(result)
```

Returns:
```json
{
  "status": "success",
  "message": "Snowflake connection successful",
  "details": {
    "version": "7.33.0",
    "warehouse": "COMPUTE_WH",
    "database": "SAMPLEDW",
    "schema": "PUBLIC",
    "user": "YOUR_USER",
    "role": "ACCOUNTADMIN"
  }
}
```

## Usage Examples

### In Python Code

```python
from ombudsman.core.connections import get_snow_conn

# Build configuration
cfg = {
    "snowflake": {
        "user": "your_username",
        "password": "your_password",
        "account": "abc12345.us-east-1",
        "warehouse": "COMPUTE_WH",
        "database": "SAMPLEDW",
        "schema": "PUBLIC"
    }
}

# Get connection
conn = get_snow_conn(cfg)

# Execute query
cursor = conn.cursor()
cursor.execute("SELECT COUNT(*) FROM DIM_CUSTOMER")
count = cursor.fetchone()[0]
cursor.close()

# Close connection
conn.close()
```

### Via API

```bash
# Test connection
curl -X POST http://localhost:8000/connections/snowflake \
  -H "Content-Type: application/json" \
  -d '{
    "use_env": true
  }'

# Or with credentials
curl -X POST http://localhost:8000/connections/snowflake \
  -H "Content-Type: application/json" \
  -d '{
    "use_env": false,
    "username": "your_user",
    "password": "your_password",
    "host": "abc12345.us-east-1",
    "database": "SAMPLEDW"
  }'
```

### Check All Connections

```bash
curl http://localhost:8000/connections/status
```

Returns status for both SQL Server and Snowflake:
```json
{
  "connections": {
    "sqlserver": {
      "configured": true,
      "status": "success",
      "host": "sqlserver",
      "port": "1433",
      "database": "SampleDW"
    },
    "snowflake": {
      "configured": true,
      "status": "success",
      "account": "abc12345.us-east-1",
      "database": "SAMPLEDW",
      "schema": "PUBLIC"
    }
  }
}
```

## Troubleshooting

### Connection Timeout

**Problem**: Connection times out

**Solutions**:
1. Check firewall/network access to Snowflake
2. Verify account URL is correct
3. Increase timeout in config:
```python
connection_params = {
    "network_timeout": 120,  # Increase to 120 seconds
    "login_timeout": 60
}
```

### Authentication Failed

**Problem**: "Incorrect username or password"

**Solutions**:
1. Verify credentials in `.env` file
2. Check for special characters (escape if needed)
3. Try logging in via Snowflake web UI first
4. Verify user is not locked

### Warehouse Suspended

**Problem**: "Warehouse 'COMPUTE_WH' cannot be used"

**Solutions**:
1. Resume warehouse in Snowflake UI
2. Use auto-resume warehouse
3. Check warehouse exists:
```sql
SHOW WAREHOUSES;
```

### Database Not Found

**Problem**: "Database 'SAMPLEDW' does not exist"

**Solutions**:
1. Create database:
```sql
CREATE DATABASE SAMPLEDW;
```
2. Verify user has access:
```sql
SHOW DATABASES;
```

### Permission Denied

**Problem**: "Insufficient privileges to operate on..."

**Solutions**:
1. Grant necessary permissions:
```sql
GRANT USAGE ON WAREHOUSE COMPUTE_WH TO ROLE YOUR_ROLE;
GRANT USAGE ON DATABASE SAMPLEDW TO ROLE YOUR_ROLE;
GRANT USAGE ON SCHEMA PUBLIC TO ROLE YOUR_ROLE;
GRANT SELECT ON ALL TABLES IN SCHEMA PUBLIC TO ROLE YOUR_ROLE;
```

## Best Practices

### 1. Use Environment Variables

✅ **Good**:
```python
cfg = {
    "snowflake": {
        "user": os.getenv('SNOWFLAKE_USER'),
        "password": os.getenv('SNOWFLAKE_PASSWORD'),
        ...
    }
}
```

❌ **Bad**:
```python
cfg = {
    "snowflake": {
        "user": "hardcoded_user",
        "password": "hardcoded_password",  # NEVER do this!
        ...
    }
}
```

### 2. Close Connections

Always close connections when done:
```python
try:
    conn = get_snow_conn(cfg)
    # Use connection
finally:
    conn.close()
```

Or use context manager pattern (if implemented):
```python
with get_snow_conn(cfg) as conn:
    # Use connection
    pass
# Auto-closed
```

### 3. Handle Errors Gracefully

```python
from ombudsman.core.connections import get_snow_conn
import snowflake.connector

try:
    conn = get_snow_conn(cfg)
except snowflake.connector.Error as e:
    logger.error(f"Snowflake connection failed: {e}")
    # Handle specific error
except ValueError as e:
    logger.error(f"Configuration error: {e}")
    # Handle config issues
```

### 4. Use Connection Pooling

For multiple queries, reuse the connection:
```python
conn = get_snow_conn(cfg)
try:
    # Query 1
    cursor1 = conn.cursor()
    cursor1.execute("SELECT...")
    cursor1.close()

    # Query 2
    cursor2 = conn.cursor()
    cursor2.execute("SELECT...")
    cursor2.close()
finally:
    conn.close()
```

### 5. Monitor Connection Health

Periodically test connections:
```python
result = test_snowflake_connection(cfg)
if result["status"] != "success":
    logger.warning(f"Snowflake connection unhealthy: {result['message']}")
    # Reconnect or alert
```

## Security

### Secrets Management

**Development**:
- Use `.env` file (add to `.gitignore`)
- Never commit credentials

**Production**:
- Use environment variables
- Use secrets manager (AWS Secrets Manager, Azure Key Vault, etc.)
- Rotate credentials regularly

### Network Security

- Use private link/PrivateConnect if available
- Whitelist IP addresses in Snowflake
- Use VPN for remote access
- Enable MFA for Snowflake accounts

### Credential Rotation

```bash
# 1. Update password in Snowflake
ALTER USER your_username SET PASSWORD='new_password';

# 2. Update .env file
SNOWFLAKE_PASSWORD=new_password

# 3. Restart application
docker-compose restart
```

## Performance Tips

### 1. Use Appropriate Warehouse Size

```sql
-- Small queries
ALTER WAREHOUSE COMPUTE_WH SET WAREHOUSE_SIZE = 'XSMALL';

-- Large data validations
ALTER WAREHOUSE COMPUTE_WH SET WAREHOUSE_SIZE = 'LARGE';
```

### 2. Enable Query Result Caching

Snowflake automatically caches results for 24 hours. Rerun identical queries for faster results.

### 3. Use Query Tags

```python
cursor.execute("ALTER SESSION SET QUERY_TAG = 'ombudsman_validation'")
```

This helps track queries in Snowflake query history.

### 4. Batch Operations

Instead of many small queries, batch when possible:
```python
# Good - batch insert
cursor.executemany("INSERT INTO...", rows)

# Bad - individual inserts
for row in rows:
    cursor.execute("INSERT INTO...", row)
```

## Monitoring

### Query History

View queries in Snowflake UI:
1. Go to **History** tab
2. Filter by user/query tag
3. Check execution time and errors

### Connection Logs

Application logs include:
- Connection attempts
- Retry attempts
- Connection success/failure
- Query execution

```bash
# View logs
docker-compose logs -f backend | grep -i snowflake
```

## Additional Resources

- [Snowflake Python Connector Docs](https://docs.snowflake.com/en/user-guide/python-connector)
- [Connection Parameters](https://docs.snowflake.com/en/user-guide/python-connector-api.html#connect)
- [Error Codes](https://docs.snowflake.com/en/user-guide/python-connector-api.html#module-snowflake.connector.errors)
- [Best Practices](https://docs.snowflake.com/en/user-guide/python-connector-best-practices)

## Support

If you encounter issues:
1. Check this guide's troubleshooting section
2. Review application logs
3. Test connection via Snowflake web UI
4. Contact Snowflake support for account issues
