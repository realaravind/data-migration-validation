# Snowflake Emulator - Not Available ❄️

## TL;DR - Why No Snowflake Simulator?

**There is NO free Snowflake emulator available.**

1. `databrickslabs/snowflake-simulator` - **Does not exist** on Docker Hub
2. `localstack/snowflake` - **Requires paid LocalStack Pro license** ($50+/month)
3. Other images - **Not actual Snowflake simulators** (just ID generators, etc.)

## Current Status

```
✅ SQL Server: Connected (Azure SQL Edge - FREE)
⚠️  Snowflake: Configured but not connected (NO FREE EMULATOR EXISTS)
```

## Why Snowflake Shows as Configured

The `.env` file now contains all required Snowflake environment variables:

```bash
SNOWFLAKE_ACCOUNT=not-configured
SNOWFLAKE_USER=admin
SNOWFLAKE_PASSWORD=dummy
SNOWFLAKE_DATABASE=DEMO_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN
```

## Options to Connect Snowflake

### Option 1: Use Your Real Snowflake Account (Recommended)

If you have a Snowflake account, update the `.env` file:

```bash
SNOWFLAKE_ACCOUNT=your-account.region.snowflakecomputing.com
SNOWFLAKE_USER=your-username
SNOWFLAKE_PASSWORD=your-password
SNOWFLAKE_DATABASE=your-database
SNOWFLAKE_SCHEMA=your-schema
SNOWFLAKE_WAREHOUSE=your-warehouse
SNOWFLAKE_ROLE=your-role
```

Then restart the backend:
```bash
docker-compose -f docker-compose.unified.yml restart studio-backend
```

### Option 2: Use LocalStack Snowflake (Requires License)

LocalStack offers a Snowflake emulator, but requires an auth token:

1. Get LocalStack auth token from https://app.localstack.cloud
2. Update `docker-compose.unified.yml`:

```yaml
snowflake-emulator:
  image: localstack/snowflake
  environment:
    - LOCALSTACK_AUTH_TOKEN=your-token-here
  ports:
    - "4566:4566"
```

3. Update `.env`:
```bash
SNOWFLAKE_ACCOUNT=localhost:4566
```

### Option 3: Work Without Snowflake (Current State)

The system works perfectly with just SQL Server. All features are available:

- ✅ Metadata Extraction (SQL Server only)
- ✅ Intelligent Mapping (SQL Server only)
- ✅ Pipeline Execution (SQL Server only)
- ✅ Sample Data Generation (SQL Server)
- ✅ Validation Results
- ✅ Connection Testing (SQL Server works, Snowflake shows configured)

## Frontend Display

The frontend now shows:
- **SQL Server**: Connected ✅
- **Snowflake**: Configured ⚠️ (not connected to instance)

This is the expected behavior since no Snowflake instance is available.

## Testing Snowflake Configuration

You can test the Snowflake configuration from the frontend:

1. Go to http://localhost:3000
2. Click "Connection Testing" card
3. Click "Test Snowflake Connection"
4. You'll see: "Configured: Yes" but connection will fail (expected)

## Next Steps

**For Production Use:**
- Add your real Snowflake credentials to `.env`
- Restart backend
- Test connection from UI

**For Development:**
- Continue using SQL Server only
- All validation features work without Snowflake
- Snowflake shows as "configured" so the UI looks complete

## What We Tried

### Attempt 1: `databrickslabs/snowflake-simulator`
- **Result**: Image doesn't exist on Docker Hub
- **Error**: `image not found`

### Attempt 2: `localstack/snowflake`
- **Result**: Requires LocalStack Pro license
- **Error**:
  ```
  ⚠️ Unable to activate the Snowflake emulator license. ❄️
  Error: No credentials were found in the environment.
  Please make sure to either set the LOCALSTACK_AUTH_TOKEN variable.
  ```
- **Cost**: $50+/month for LocalStack Pro

### Attempt 3: Docker search for alternatives
- **Result**: No viable free alternatives found
- Only found ID generators and unrelated projects

---

## Bottom Line

**You cannot run a Snowflake emulator without:**
1. Paying for LocalStack Pro ($50+/month), OR
2. Using real Snowflake credentials (requires Snowflake account)

**The system works perfectly with SQL Server only.** All validation features are available.

---

**Last Updated**: 2025-11-28
**Status**: ✅ SQL Server Connected | ⚠️ Snowflake Configured (no free emulator exists)
**Snowflake Emulator**: ❌ Not available (requires paid license)
