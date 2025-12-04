'''
Centralized SQL + Snowflake connection management.

Provides:
- Connection pooling
- Retry logic
- Health checks
- Consistent interface via ConnectionWrapper
'''

# src/ombudsman/core/connections.py

import pyodbc
import snowflake.connector
from snowflake.connector import DictCursor
import os
import time
import logging
from decimal import Decimal
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class ConnectionWrapper:
    """Wrapper to provide consistent interface for DB connections"""

    def __init__(self, conn):
        self._conn = conn

    def fetch_one(self, query):
        """Execute query and return first result"""
        cursor = self._conn.cursor()
        cursor.execute(query)
        result = cursor.fetchone()
        cursor.close()
        # Return first column if result exists
        return result[0] if result else None

    def fetch_many(self, query):
        """Execute query and return all results"""
        cursor = self._conn.cursor()
        cursor.execute(query)
        results = cursor.fetchall()
        cursor.close()
        return results

    def fetch_dicts(self, query):
        """Execute query and return results as list of dictionaries"""
        cursor = self._conn.cursor()
        cursor.execute(query)
        # Lowercase column names for consistent access across databases
        columns = [column[0].lower() for column in cursor.description]
        results = []
        for row in cursor.fetchall():
            # Convert Decimal values to float for JSON serialization
            converted_row = []
            for value in row:
                if isinstance(value, Decimal):
                    converted_row.append(float(value))
                else:
                    converted_row.append(value)
            results.append(dict(zip(columns, converted_row)))
        cursor.close()
        return results

    def cursor(self):
        """Get raw cursor for direct access"""
        return self._conn.cursor()

    def commit(self):
        """Commit transaction"""
        return self._conn.commit()

    def close(self):
        """Close connection"""
        return self._conn.close()

    @property
    def database(self):
        """Get database name (for Snowflake)"""
        return getattr(self._conn, 'database', None)

    @property
    def schema(self):
        """Get schema name (for Snowflake)"""
        return getattr(self._conn, 'schema', None)


def get_sql_conn(cfg):
    sql_cfg = cfg["connections"]["sql"]

    # New structured config
    if all(k in sql_cfg for k in ["host", "port", "user", "password", "database"]):
        conn_str = (
            f"DRIVER={{ODBC Driver 18 for SQL Server}};"
            f"SERVER={sql_cfg['host']},{sql_cfg['port']};"
            f"DATABASE={sql_cfg['database']};"
            f"UID={sql_cfg['user']};"
            f"PWD={sql_cfg['password']};"
            f"TrustServerCertificate=yes;"
        )
        raw_conn = pyodbc.connect(conn_str)
        return ConnectionWrapper(raw_conn)

    # Fallback: older env var
    env_conn_str = os.getenv("SQLSERVER_CONN_STR")
    if env_conn_str:
        raw_conn = pyodbc.connect(env_conn_str)
        return ConnectionWrapper(raw_conn)

    raise ValueError("No SQL connection config found")

def get_snow_conn(cfg=None, retries=3, retry_delay=2):
    """
    Get Snowflake connection with retry logic.

    Args:
        cfg: Configuration dictionary with snowflake credentials
        retries: Number of connection attempts (default: 3)
        retry_delay: Seconds to wait between retries (default: 2)

    Returns:
        ConnectionWrapper: Wrapped Snowflake connection

    Raises:
        ValueError: If configuration is missing
        snowflake.connector.Error: If connection fails after retries
    """
    if cfg is None:
        raise ValueError("Snowflake configuration is required")

    c = cfg.get("snowflake")
    if not c:
        raise ValueError("No Snowflake configuration found in cfg")

    # Validate required fields
    required_fields = ["user", "password", "account", "warehouse", "database", "schema"]
    missing_fields = [field for field in required_fields if not c.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required Snowflake config fields: {', '.join(missing_fields)}")

    # Build connection parameters
    connection_params = {
        "user": c["user"],
        "password": c["password"],
        "account": c["account"],
        "warehouse": c["warehouse"],
        "database": c["database"],
        "schema": c["schema"],
        "client_session_keep_alive": True,  # Keep session alive
        "network_timeout": 60,  # Network timeout in seconds
        "login_timeout": 30,  # Login timeout in seconds
    }

    # Add optional parameters
    if c.get("role"):
        connection_params["role"] = c["role"]

    # Retry logic
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            logger.info(f"Attempting Snowflake connection (attempt {attempt}/{retries})...")
            raw_conn = snowflake.connector.connect(**connection_params)

            # Test connection with a simple query
            cursor = raw_conn.cursor()
            cursor.execute("SELECT CURRENT_VERSION()")
            version = cursor.fetchone()[0]
            cursor.close()

            logger.info(f"Successfully connected to Snowflake (version: {version})")
            return ConnectionWrapper(raw_conn)

        except snowflake.connector.Error as e:
            last_error = e
            logger.warning(f"Snowflake connection attempt {attempt} failed: {str(e)}")

            if attempt < retries:
                logger.info(f"Retrying in {retry_delay} seconds...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to connect to Snowflake after {retries} attempts")
                raise

        except Exception as e:
            last_error = e
            logger.error(f"Unexpected error during Snowflake connection: {str(e)}")
            raise

    # This should never be reached due to raise in loop, but just in case
    raise last_error if last_error else Exception("Unknown error during Snowflake connection")


def test_snowflake_connection(cfg=None):
    """
    Test Snowflake connection and return status information.

    Args:
        cfg: Configuration dictionary with snowflake credentials

    Returns:
        dict: Connection status with details
    """
    try:
        conn = get_snow_conn(cfg, retries=1)
        cursor = conn.cursor()

        # Get connection info
        cursor.execute("SELECT CURRENT_VERSION()")
        version = cursor.fetchone()[0]

        cursor.execute("SELECT CURRENT_WAREHOUSE()")
        warehouse = cursor.fetchone()[0]

        cursor.execute("SELECT CURRENT_DATABASE()")
        database = cursor.fetchone()[0]

        cursor.execute("SELECT CURRENT_SCHEMA()")
        schema = cursor.fetchone()[0]

        cursor.execute("SELECT CURRENT_USER()")
        user = cursor.fetchone()[0]

        cursor.execute("SELECT CURRENT_ROLE()")
        role = cursor.fetchone()[0]

        cursor.close()
        conn.close()

        return {
            "status": "success",
            "message": "Snowflake connection successful",
            "details": {
                "version": version,
                "warehouse": warehouse,
                "database": database,
                "schema": schema,
                "user": user,
                "role": role
            }
        }

    except Exception as e:
        return {
            "status": "error",
            "message": f"Snowflake connection failed: {str(e)}",
            "details": {
                "error_type": type(e).__name__,
                "error_message": str(e)
            }
        }
