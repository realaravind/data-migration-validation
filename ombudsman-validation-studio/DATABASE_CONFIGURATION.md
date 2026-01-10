# Database Configuration Guide

This guide explains how to configure SQL Server and Snowflake connections for the Ombudsman Validation Studio.

## Table of Contents
- [Configuration File Location](#configuration-file-location)
- [SQL Server Configuration](#sql-server-configuration)
  - [Local SQL Server](#local-sql-server)
  - [Azure SQL Database](#azure-sql-database)
  - [SQL Server on VM/Remote Server](#sql-server-on-vmremote-server)
- [Snowflake Configuration](#snowflake-configuration)
  - [Production Snowflake Account](#production-snowflake-account)
  - [Snowflake Emulator (Testing)](#snowflake-emulator-testing)
- [Testing Connections](#testing-connections)
- [Troubleshooting](#troubleshooting)

---

## Configuration File Location

All database connections are configured in the `.env` file located at:

```
ombudsman_core/.env
```

After modifying this file, you must restart the backend container for changes to take effect:

```bash
cd ombudsman-validation-studio
docker-compose restart studio-backend
```

---

## SQL Server Configuration

The system supports three SQL Server connection scenarios:

### Local SQL Server

For SQL Server running in a Docker container or on localhost:

```bash
# SQL Server structured config (Local)
MSSQL_HOST=sqlserver                    # or 'localhost'
MSSQL_PORT=1433
MSSQL_DATABASE=SampleDW
MSSQL_USER=sa
MSSQL_PASSWORD=YourStrong!Passw0rd

# Connection string (backward compatibility)
SQLSERVER_CONN_STR=DRIVER={ODBC Driver 18 for SQL Server};SERVER=sqlserver,1433;DATABASE=SampleDW;UID=sa;PWD=YourStrong!Passw0rd;TrustServerCertificate=yes;
```

**Notes:**
- Use `TrustServerCertificate=yes` for local development (self-signed certificates)
- Use `sqlserver` as hostname if SQL Server is in docker-compose network
- Use `localhost` or `host.docker.internal` if accessing from host machine

---

### Azure SQL Database

For cloud-hosted Azure SQL Database:

```bash
# SQL Server structured config (Azure SQL Database)
MSSQL_HOST=your-server.database.windows.net
MSSQL_PORT=1433
MSSQL_DATABASE=snowmigratedev01
MSSQL_USER=sqladmin
MSSQL_PASSWORD=YourAzurePassword

# Connection string (backward compatibility)
SQLSERVER_CONN_STR=DRIVER={ODBC Driver 18 for SQL Server};SERVER=your-server.database.windows.net,1433;DATABASE=snowmigratedev01;UID=sqladmin;PWD=YourAzurePassword;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
```

**Key Differences from Local:**
- `Encrypt=yes` - Required for Azure SQL
- `TrustServerCertificate=no` - Validates Azure's SSL certificate
- `Connection Timeout=30` - Allows time for cloud connection establishment

**Getting Your Azure SQL Connection Details:**

1. Go to Azure Portal → SQL databases → Your database
2. Click "Connection strings"
3. Select "ADO.NET" tab
4. Copy the connection string components:
   - **Server**: `tcp:server-name.database.windows.net,1433`
   - **Database**: Initial Catalog value
   - **User**: User ID value
   - **Password**: (you set this when creating the SQL user)

**Authentication Options:**

- **SQL Authentication** (Recommended): Use username/password as shown above
- **Azure AD**: Not currently supported from Docker containers

---

### SQL Server on VM/Remote Server

For SQL Server on a virtual machine or remote server:

```bash
# SQL Server structured config (Remote)
MSSQL_HOST=10.0.1.50                    # IP address or hostname
MSSQL_PORT=1433
MSSQL_DATABASE=ProductionDW
MSSQL_USER=dbuser
MSSQL_PASSWORD=SecurePassword123

# Connection string
SQLSERVER_CONN_STR=DRIVER={ODBC Driver 18 for SQL Server};SERVER=10.0.1.50,1433;DATABASE=ProductionDW;UID=dbuser;PWD=SecurePassword123;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;
```

**Firewall Requirements:**
- Ensure port 1433 is open on the remote server
- Add your Docker host IP to SQL Server allowed connections
- Check Windows Firewall and SQL Server Configuration Manager settings

---

## Snowflake Configuration

The system supports both production Snowflake accounts and a local emulator for testing.

### Production Snowflake Account

For real Snowflake cloud account:

```bash
# Snowflake (Real Account)
SNOWFLAKE_ACCOUNT=ABC12345.us-east-1    # Your Snowflake account identifier
SNOWFLAKE_USER=YourUsername
SNOWFLAKE_PASSWORD=YourPassword
SNOWFLAKE_DATABASE=PRODUCTION_DB
SNOWFLAKE_SCHEMA=PUBLIC
SNOWFLAKE_WAREHOUSE=COMPUTE_WH
SNOWFLAKE_ROLE=ACCOUNTADMIN             # or appropriate role
```

**Getting Your Snowflake Connection Details:**

1. **Account Identifier**:
   - Format: `<orgname>-<account_name>` (e.g., `ACME-PROD123`)
   - Or legacy format: `<account_locator>.<region>` (e.g., `ABC12345.us-east-1`)
   - Find in: Snowflake Web UI → Account dropdown → Copy account identifier

2. **Username/Password**: Your Snowflake user credentials

3. **Database/Schema**: The database and schema you want to validate

4. **Warehouse**: Virtual warehouse to use for queries (e.g., `COMPUTE_WH`)

5. **Role**:
   - `ACCOUNTADMIN` - Full access (use for setup)
   - `SYSADMIN` - Can create databases/warehouses
   - Custom role with appropriate permissions

**Required Permissions:**

Your Snowflake user needs:
```sql
-- Minimum required grants
GRANT USAGE ON WAREHOUSE <warehouse_name> TO ROLE <your_role>;
GRANT USAGE ON DATABASE <database_name> TO ROLE <your_role>;
GRANT USAGE ON SCHEMA <database>.<schema> TO ROLE <your_role>;
GRANT SELECT ON ALL TABLES IN SCHEMA <database>.<schema> TO ROLE <your_role>;
GRANT SELECT ON ALL VIEWS IN SCHEMA <database>.<schema> TO ROLE <your_role>;

-- For metadata extraction
GRANT USAGE ON DATABASE INFORMATION_SCHEMA TO ROLE <your_role>;
```

---

### Snowflake Emulator (Testing)

For local development without cloud costs:

```bash
# Snowflake emulator (legacy variables)
SNOW_HOST=snowflake-emulator
SNOW_PORT=8080
SNOW_USER=admin
SNOW_PASSWORD=dummy
SNOW_DATABASE=DEMO_DB
SNOW_SCHEMA=PUBLIC
```

**Notes:**
- The emulator is for testing only, not production validation
- Limited SQL functionality compared to real Snowflake
- Runs as a Docker container in docker-compose

---

## Testing Connections

After updating the `.env` file, test your connections:

### Option 1: Connection Testing UI

1. Navigate to: `http://localhost:3001`
2. Click "Connection Testing" from the dashboard
3. Test both SQL Server and Snowflake connections
4. View detailed connection status and error messages

### Option 2: Backend Container Test

Test SQL Server connection:
```bash
docker exec ombudsman-validation-studio-studio-backend-1 python3 -c "
import pyodbc
conn = pyodbc.connect('DRIVER={ODBC Driver 18 for SQL Server};SERVER=your-server,1433;DATABASE=your-db;UID=user;PWD=password;Encrypt=yes;TrustServerCertificate=no;')
print('Connected:', conn)
cursor = conn.cursor()
cursor.execute('SELECT DB_NAME()')
print('Database:', cursor.fetchone()[0])
"
```

Test Snowflake connection:
```bash
docker exec ombudsman-validation-studio-studio-backend-1 python3 -c "
import snowflake.connector
conn = snowflake.connector.connect(
    account='your-account',
    user='your-user',
    password='your-password',
    database='your-db',
    schema='your-schema',
    warehouse='your-warehouse'
)
print('Connected:', conn)
cursor = conn.cursor()
cursor.execute('SELECT CURRENT_DATABASE()')
print('Database:', cursor.fetchone()[0])
"
```

### Option 3: Backend Health Check

```bash
curl http://localhost:8000/health
```

---

## Troubleshooting

### SQL Server Issues

**Problem: "Login failed for user"**
- **Solution**: Verify username and password are correct
- Check SQL Server authentication mode (must allow SQL Auth, not just Windows)
- Ensure user has appropriate database permissions

**Problem: "SSL Provider: The certificate chain was issued by an authority that is not trusted"**
- **Solution**: Set `TrustServerCertificate=yes` for local servers
- For Azure SQL, keep `TrustServerCertificate=no` and ensure Encrypt=yes

**Problem: "Cannot open database requested by the login"**
- **Solution**: Verify database name is correct
- Ensure user has access to the database: `USE master; EXEC sp_grantdbaccess 'username'`

**Problem: Connection timeout**
- **Solution**: Check firewall rules
- Verify SQL Server is listening on TCP/IP (use SQL Server Configuration Manager)
- Test connectivity: `telnet server-name 1433`

### Snowflake Issues

**Problem: "Incorrect username or password was specified"**
- **Solution**: Verify credentials in Snowflake Web UI first
- Check for special characters that need escaping in .env file

**Problem: "Account name is not valid"**
- **Solution**: Use correct account identifier format
- Try both `orgname-account` and `locator.region` formats
- Remove `https://` and `.snowflakecomputing.com` if present

**Problem: "Insufficient privileges to operate on database"**
- **Solution**: Grant appropriate permissions (see Required Permissions above)
- Ask Snowflake admin to grant role with database access

**Problem: "Object does not exist, or operation cannot be performed"**
- **Solution**: Verify database/schema names are correct (case-sensitive!)
- Ensure warehouse is running and accessible

### General Issues

**Problem: Changes to .env file not taking effect**
- **Solution**: Restart backend container: `docker-compose restart studio-backend`
- Or rebuild if you changed requirements: `docker-compose build studio-backend`

**Problem: "Unable to connect to database" in UI**
- **Solution**: Check backend logs: `docker logs ombudsman-validation-studio-studio-backend-1`
- Verify .env file has no syntax errors (no quotes around values, no spaces around =)

---

## Example Configurations

### Complete Azure SQL + Snowflake Production Setup

```bash
# --- SQL Server (Azure SQL Database) ---
MSSQL_HOST=prodserver.database.windows.net
MSSQL_PORT=1433
MSSQL_DATABASE=DataWarehouse
MSSQL_USER=ombudsman_user
MSSQL_PASSWORD=Str0ng!P@ssw0rd

SQLSERVER_CONN_STR=DRIVER={ODBC Driver 18 for SQL Server};SERVER=prodserver.database.windows.net,1433;DATABASE=DataWarehouse;UID=ombudsman_user;PWD=Str0ng!P@ssw0rd;Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;

# --- Snowflake (Production) ---
SNOWFLAKE_ACCOUNT=ACMEORG-PROD001
SNOWFLAKE_USER=validation_service
SNOWFLAKE_PASSWORD=Sn0wfl@ke123
SNOWFLAKE_DATABASE=DW_PROD
SNOWFLAKE_SCHEMA=FACT
SNOWFLAKE_WAREHOUSE=VALIDATION_WH
SNOWFLAKE_ROLE=DATA_VALIDATOR
```

### Local Development Setup

```bash
# --- SQL Server (Local Docker) ---
MSSQL_HOST=sqlserver
MSSQL_PORT=1433
MSSQL_DATABASE=SampleDW
MSSQL_USER=sa
MSSQL_PASSWORD=DevPassword123!

SQLSERVER_CONN_STR=DRIVER={ODBC Driver 18 for SQL Server};SERVER=sqlserver,1433;DATABASE=SampleDW;UID=sa;PWD=DevPassword123!;TrustServerCertificate=yes;

# --- Snowflake Emulator (Local) ---
SNOW_HOST=snowflake-emulator
SNOW_PORT=8080
SNOW_USER=admin
SNOW_PASSWORD=dummy
SNOW_DATABASE=DEMO_DB
SNOW_SCHEMA=PUBLIC
```

---

## Additional Resources

- [SQL Server Connection Strings Reference](https://www.connectionstrings.com/sql-server/)
- [Snowflake Connection Parameters](https://docs.snowflake.com/en/user-guide/python-connector-api.html#connect)
- [Azure SQL Database Documentation](https://docs.microsoft.com/en-us/azure/azure-sql/)
- [ODBC Driver 18 for SQL Server](https://docs.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server)

---

## Security Best Practices

1. **Never commit .env files to git** - Add to `.gitignore`
2. **Use strong passwords** - Minimum 12 characters with mixed case, numbers, symbols
3. **Rotate credentials regularly** - Change passwords every 90 days
4. **Use least privilege** - Grant only necessary database permissions
5. **Enable MFA** - Use multi-factor authentication for Snowflake accounts
6. **Audit access** - Review connection logs regularly
7. **Encrypt in transit** - Always use `Encrypt=yes` for production
8. **Secure storage** - Consider using Azure Key Vault or similar for credentials

---

For additional help, check the Connection Testing page in the UI or contact your database administrator.
