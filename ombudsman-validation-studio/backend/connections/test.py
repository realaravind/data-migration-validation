from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict

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

    except Exception as e:
        return {
            "status": "error",
            "message": f"SQL Server connection failed: {str(e)}"
        }


@router.post("/snowflake")
async def test_snowflake_connection(request: ConnectionTestRequest):
    """Test Snowflake connection"""
    try:
        import os
        import sys
        sys.path.insert(0, "/core/src")
        from ombudsman.core.connections import test_snowflake_connection as test_snow_conn

        # Build config from environment or request
        if request.use_env:
            cfg = {
                "snowflake": {
                    "user": os.getenv('SNOWFLAKE_USER', ''),
                    "password": os.getenv('SNOWFLAKE_PASSWORD', ''),
                    "account": os.getenv('SNOWFLAKE_ACCOUNT', ''),
                    "warehouse": os.getenv('SNOWFLAKE_WAREHOUSE', 'COMPUTE_WH'),
                    "database": os.getenv('SNOWFLAKE_DATABASE', ''),
                    "schema": os.getenv('SNOWFLAKE_SCHEMA', 'PUBLIC'),
                    "role": os.getenv('SNOWFLAKE_ROLE', '')
                }
            }
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

        return result

    except Exception as e:
        return {
            "status": "error",
            "message": f"Snowflake connection failed: {str(e)}",
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
