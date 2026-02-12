from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict
import logging

from alerts.service import alert_service

logger = logging.getLogger(__name__)
router = APIRouter()

class ConnectionTestRequest(BaseModel):
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    use_env: bool = True  # Use environment variables if True


@router.post("/sqlserver")
async def test_sqlserver_connection(request: ConnectionTestRequest):
    """Test SQL Server connection"""
    try:
        import pyodbc
        import os

        if request.use_env:
            # Use environment variables
            conn_str = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={os.getenv('MSSQL_HOST', 'sqlserver')},{os.getenv('MSSQL_PORT', '1433')};"
                f"DATABASE={os.getenv('MSSQL_DATABASE', 'master')};"
                f"UID={os.getenv('MSSQL_USER', 'sa')};"
                f"PWD={os.getenv('MSSQL_PASSWORD', '')};"
                f"TrustServerCertificate=yes;"
            )
        else:
            # Use provided credentials
            conn_str = (
                f"DRIVER={{ODBC Driver 18 for SQL Server}};"
                f"SERVER={request.host},{request.port};"
                f"DATABASE={request.database};"
                f"UID={request.username};"
                f"PWD={request.password};"
                f"TrustServerCertificate=yes;"
            )

        # Test connection
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        version = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": "SQL Server connection successful",
            "server_version": version,
            "connection_string": conn_str.replace(request.password or os.getenv('MSSQL_PASSWORD', ''), '***') if not request.use_env else "Using environment variables"
        }

    except pyodbc.Error as e:
        error_msg = f"SQL Server connection failed: {str(e)}"
        logger.error(error_msg)
        alert_service.add_alert(
            message=error_msg,
            source="connections/sqlserver",
            details={"error_type": "pyodbc.Error", "sql_state": getattr(e, 'args', [None])[0] if e.args else None}
        )
        return {
            "status": "error",
            "message": error_msg
        }
    except Exception as e:
        error_msg = f"SQL Server connection failed: {str(e)}"
        logger.error(error_msg)
        alert_service.add_alert(
            message=error_msg,
            source="connections/sqlserver",
            details={"error_type": type(e).__name__}
        )
        return {
            "status": "error",
            "message": error_msg
        }


@router.post("/snowflake")
async def test_snowflake_connection(request: ConnectionTestRequest):
    """Test Snowflake connection (supports OAuth, token, and password auth)"""
    try:
        import os
        from ombudsman.core.connections import test_snowflake_connection as test_snow_conn

        # Build config from environment or request
        if request.use_env:
            # Check for OAuth, then token, then password
            oauth_client_id = os.getenv('SNOWFLAKE_OAUTH_CLIENT_ID', '')
            oauth_client_secret = os.getenv('SNOWFLAKE_OAUTH_CLIENT_SECRET', '')
            oauth_refresh_token = os.getenv('SNOWFLAKE_OAUTH_REFRESH_TOKEN', '')
            token = os.getenv('SNOWFLAKE_TOKEN', '')
            password = os.getenv('SNOWFLAKE_PASSWORD', '')

            cfg = {
                "snowflake": {
                    "user": os.getenv('SNOWFLAKE_USER', ''),
                    "account": os.getenv('SNOWFLAKE_ACCOUNT', ''),
                    "warehouse": os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                    "database": os.getenv('SNOWFLAKE_DATABASE', ''),
                    "schema": os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
                    "role": os.getenv('SNOWFLAKE_ROLE', '')
                }
            }
            # Add auth method (OAuth > token > password)
            if oauth_client_id and oauth_refresh_token:
                cfg["snowflake"]["oauth_client_id"] = oauth_client_id
                cfg["snowflake"]["oauth_client_secret"] = oauth_client_secret
                cfg["snowflake"]["oauth_refresh_token"] = oauth_refresh_token
                # Optional OAuth settings
                oauth_redirect_uri = os.getenv('SNOWFLAKE_OAUTH_REDIRECT_URI', '')
                oauth_token_endpoint = os.getenv('SNOWFLAKE_OAUTH_TOKEN_ENDPOINT', '')
                if oauth_redirect_uri:
                    cfg["snowflake"]["oauth_redirect_uri"] = oauth_redirect_uri
                if oauth_token_endpoint:
                    cfg["snowflake"]["oauth_token_endpoint"] = oauth_token_endpoint
            elif token:
                cfg["snowflake"]["token"] = token
            else:
                cfg["snowflake"]["password"] = password
        else:
            cfg = {
                "snowflake": {
                    "user": request.username,
                    "password": request.password,
                    "account": request.host,  # account is stored in host field
                    "warehouse": os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                    "database": request.database,
                    "schema": "PUBLIC"
                }
            }

        # Test connection using core function
        result = test_snow_conn(cfg)

        # Create alert if connection failed (even without exception)
        if result.get("status") == "error":
            error_msg = result.get("message", "Snowflake connection failed")
            logger.warning(f"Snowflake connection error: {error_msg}")
            alert_service.add_alert(
                message=error_msg,
                source="connections/snowflake",
                details=result.get("details")
            )

        return result

    except Exception as e:
        error_msg = f"Snowflake connection failed: {str(e)}"
        logger.error(error_msg)
        alert_service.add_alert(
            message=error_msg,
            source="connections/snowflake",
            details={"error_type": type(e).__name__}
        )
        return {
            "status": "error",
            "message": error_msg,
            "details": {
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        }


@router.get("/status")
async def get_all_connection_status():
    """Get status of all configured connections"""
    import os

    connections = {
        "sqlserver": {
            "configured": bool(os.getenv('MSSQL_HOST')),
            "host": os.getenv('MSSQL_HOST', 'Not configured'),
            "port": os.getenv('MSSQL_PORT', 'Not configured'),
            "database": os.getenv('MSSQL_DATABASE', 'Not configured')
        },
        "snowflake": {
            "configured": bool(os.getenv('SNOWFLAKE_ACCOUNT')),
            "account": os.getenv('SNOWFLAKE_ACCOUNT', 'Not configured'),
            "database": os.getenv('SNOWFLAKE_DATABASE', 'Not configured'),
            "schema": os.getenv('SNOWFLAKE_SCHEMA', 'Not configured')
        }
    }

    # Test SQL Server
    try:
        sql_test = await test_sqlserver_connection(ConnectionTestRequest(use_env=True))
        connections["sqlserver"]["status"] = sql_test["status"]
        connections["sqlserver"]["message"] = sql_test["message"]
    except Exception as e:
        connections["sqlserver"]["status"] = "error"
        connections["sqlserver"]["message"] = str(e)

    # Test Snowflake
    try:
        snow_test = await test_snowflake_connection(ConnectionTestRequest(use_env=True))
        connections["snowflake"]["status"] = snow_test["status"]
        connections["snowflake"]["message"] = snow_test["message"]
    except Exception as e:
        connections["snowflake"]["status"] = "error"
        connections["snowflake"]["message"] = str(e)

    return {"connections": connections}


@router.get("/databases/sqlserver")
async def list_sqlserver_databases():
    """List all databases available in SQL Server"""
    try:
        import pyodbc
        import os

        # Use environment variables to connect to SQL Server
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={os.getenv('MSSQL_HOST', 'sqlserver')},{os.getenv('MSSQL_PORT', '1433')};"
            f"DATABASE=master;"  # Connect to master to list all databases
            f"UID={os.getenv('MSSQL_USER', 'sa')};"
            f"PWD={os.getenv('MSSQL_PASSWORD', '')};"
            f"TrustServerCertificate=yes;"
        )

        # Query to list all user databases (excluding system databases if desired)
        conn = pyodbc.connect(conn_str, timeout=5)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT name
            FROM sys.databases
            WHERE name NOT IN ('master', 'tempdb', 'model', 'msdb')
            ORDER BY name
        """)

        databases = [row[0] for row in cursor.fetchall()]
        cursor.close()
        conn.close()

        return {
            "status": "success",
            "databases": databases,
            "count": len(databases)
        }

    except Exception as e:
        error_msg = f"Failed to list SQL Server databases: {str(e)}"
        logger.error(error_msg)
        alert_service.add_alert(
            message=error_msg,
            source="connections/databases/sqlserver",
            details={"error_type": type(e).__name__}
        )
        return {
            "status": "error",
            "message": error_msg,
            "databases": []
        }


@router.get("/databases/snowflake")
async def list_snowflake_databases():
    """List all databases available in Snowflake (supports OAuth, token, and password auth)"""
    try:
        import os
        from ombudsman.core.connections import get_snow_conn

        # Build config using same pattern as test connection
        oauth_client_id = os.getenv('SNOWFLAKE_OAUTH_CLIENT_ID', '')
        oauth_client_secret = os.getenv('SNOWFLAKE_OAUTH_CLIENT_SECRET', '')
        oauth_refresh_token = os.getenv('SNOWFLAKE_OAUTH_REFRESH_TOKEN', '')
        token = os.getenv('SNOWFLAKE_TOKEN', '')
        password = os.getenv('SNOWFLAKE_PASSWORD', '')

        cfg = {
            "snowflake": {
                "user": os.getenv('SNOWFLAKE_USER', ''),
                "account": os.getenv('SNOWFLAKE_ACCOUNT', ''),
                "warehouse": os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                "database": os.getenv('SNOWFLAKE_DATABASE', ''),
                "schema": os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
                "role": os.getenv('SNOWFLAKE_ROLE', '')
            }
        }

        # Add auth method (OAuth > token > password)
        if oauth_client_id and oauth_refresh_token:
            cfg["snowflake"]["oauth_client_id"] = oauth_client_id
            cfg["snowflake"]["oauth_client_secret"] = oauth_client_secret
            cfg["snowflake"]["oauth_refresh_token"] = oauth_refresh_token
        elif token:
            cfg["snowflake"]["token"] = token
        else:
            cfg["snowflake"]["password"] = password

        # Connect and list databases
        with get_snow_conn(cfg) as conn:
            cursor = conn.cursor()
            cursor.execute("SHOW DATABASES")
            databases = [row[1] for row in cursor.fetchall()]
            cursor.close()

        return {
            "status": "success",
            "databases": databases,
            "count": len(databases)
        }

    except Exception as e:
        error_msg = f"Failed to list Snowflake databases: {str(e)}"
        logger.error(error_msg)
        alert_service.add_alert(
            message=error_msg,
            source="connections/databases/snowflake",
            details={"error_type": type(e).__name__}
        )
        return {
            "status": "error",
            "message": error_msg,
            "databases": []
        }
