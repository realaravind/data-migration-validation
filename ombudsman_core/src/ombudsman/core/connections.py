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
import requests
import base64
from decimal import Decimal
from typing import Optional, Dict, Any
from contextlib import contextmanager

# Import connection pool manager
from .connection_pool import pool_manager

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


def _create_sql_connection(cfg):
    """
    Create a raw SQL Server connection (used by connection pool).

    Args:
        cfg: Configuration dictionary

    Returns:
        pyodbc.Connection: Raw SQL Server connection
    """
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
            f"Connection Timeout=60;"
        )
        return pyodbc.connect(conn_str)

    # Fallback: older env var
    env_conn_str = os.getenv("SQLSERVER_CONN_STR")
    if env_conn_str:
        return pyodbc.connect(env_conn_str)

    raise ValueError("No SQL connection config found")


@contextmanager
def get_sql_conn(cfg, use_pool=True):
    """
    Get SQL Server connection (optionally from pool).

    Args:
        cfg: Configuration dictionary
        use_pool: Whether to use connection pooling (default: True)

    Yields:
        ConnectionWrapper: Wrapped SQL Server connection

    Example:
        with get_sql_conn(cfg) as conn:
            result = conn.fetch_one("SELECT COUNT(*) FROM table")
    """
    if use_pool:
        # Get or create pool for SQL Server
        pool = pool_manager.get_or_create_pool(
            name="sqlserver",
            connection_factory=lambda: _create_sql_connection(cfg),
            min_size=2,
            max_size=10,
            max_age_seconds=3600,
            health_check_interval=300,
            connection_timeout=30
        )

        # Get connection from pool
        with pool.get_connection() as raw_conn:
            yield ConnectionWrapper(raw_conn)
    else:
        # Direct connection (no pooling)
        raw_conn = _create_sql_connection(cfg)
        try:
            yield ConnectionWrapper(raw_conn)
        finally:
            raw_conn.close()

def _get_snowflake_oauth_token(c: Dict[str, Any]) -> str:
    """
    Get OAuth access token from Snowflake using refresh token.

    Snowflake Custom OAuth flow:
    1. Security Integration created in Snowflake provides client_id/secret
    2. Refresh token is used to get access token
    3. Access token is used with authenticator="oauth"

    See: https://docs.snowflake.com/en/user-guide/oauth-custom

    Args:
        c: Snowflake config dictionary with oauth credentials

    Returns:
        str: OAuth access token

    Raises:
        ValueError: If OAuth credentials are missing or token exchange fails
    """
    # Required OAuth fields
    client_id = c.get("oauth_client_id")
    client_secret = c.get("oauth_client_secret")
    refresh_token = c.get("oauth_refresh_token")
    account = c.get("account")

    if not all([client_id, client_secret, refresh_token, account]):
        missing = []
        if not client_id: missing.append("oauth_client_id")
        if not client_secret: missing.append("oauth_client_secret")
        if not refresh_token: missing.append("oauth_refresh_token")
        if not account: missing.append("account")
        raise ValueError(f"Missing OAuth credentials: {', '.join(missing)}")

    # Build token endpoint URL
    # Format: https://<account>.snowflakecomputing.com/oauth/token-request
    token_endpoint = c.get("oauth_token_endpoint")
    if not token_endpoint:
        # Auto-construct from account
        token_endpoint = f"https://{account}.snowflakecomputing.com/oauth/token-request"

    logger.info(f"Requesting OAuth token from: {token_endpoint}")

    # Prepare request
    # Basic auth with client_id:client_secret
    auth_string = base64.b64encode(f"{client_id}:{client_secret}".encode()).decode()

    headers = {
        "Authorization": f"Basic {auth_string}",
        "Content-Type": "application/x-www-form-urlencoded"
    }

    data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
    }

    # Add redirect_uri if provided
    redirect_uri = c.get("oauth_redirect_uri")
    if redirect_uri:
        data["redirect_uri"] = redirect_uri

    try:
        response = requests.post(token_endpoint, headers=headers, data=data, timeout=30)
        response.raise_for_status()

        token_data = response.json()
        access_token = token_data.get("access_token")

        if not access_token:
            raise ValueError(f"No access_token in response: {token_data}")

        logger.info("Successfully obtained OAuth access token")
        return access_token

    except requests.exceptions.RequestException as e:
        logger.error(f"OAuth token request failed: {e}")
        if hasattr(e, 'response') and e.response is not None:
            logger.error(f"Response: {e.response.text}")
        raise ValueError(f"Failed to get OAuth token: {e}")


def _create_snowflake_connection(cfg, retries=3, retry_delay=2):
    """
    Create a raw Snowflake connection with retry logic (used by connection pool).

    Supports three authentication methods:
    1. OAuth: Set oauth_client_id, oauth_client_secret, oauth_refresh_token
    2. Token (PAT): Set 'token' in config (uses OAuth authenticator)
    3. Password: Set 'password' in config (traditional auth)

    Args:
        cfg: Configuration dictionary with snowflake credentials
        retries: Number of connection attempts (default: 3)
        retry_delay: Seconds to wait between retries (default: 2)

    Returns:
        snowflake.connector.Connection: Raw Snowflake connection

    Raises:
        ValueError: If configuration is missing
        snowflake.connector.Error: If connection fails after retries
    """
    if cfg is None:
        raise ValueError("Snowflake configuration is required")

    c = cfg.get("snowflake")
    if not c:
        raise ValueError("No Snowflake configuration found in cfg")

    # Check authentication method: OAuth > Token > Password
    has_oauth = bool(c.get("oauth_client_id") and c.get("oauth_refresh_token"))
    has_token = bool(c.get("token"))
    has_password = bool(c.get("password"))

    if not has_oauth and not has_token and not has_password:
        raise ValueError("Snowflake authentication required: set OAuth credentials, 'token', or 'password'")

    # Validate required fields
    required_fields = ["user", "account", "warehouse", "database", "schema"]
    missing_fields = [field for field in required_fields if not c.get(field)]
    if missing_fields:
        raise ValueError(f"Missing required Snowflake config fields: {', '.join(missing_fields)}")

    # Build connection parameters
    connection_params = {
        "user": c["user"],
        "account": c["account"],
        "warehouse": c["warehouse"],
        "database": c["database"],
        "schema": c["schema"],
        "client_session_keep_alive": True,  # Keep session alive
        "network_timeout": 60,  # Network timeout in seconds
        "login_timeout": 30,  # Login timeout in seconds
    }

    # Set authentication method (priority: OAuth > Token > Password)
    if has_oauth:
        # Full OAuth flow with refresh token
        logger.info("Using Snowflake OAuth authentication")
        access_token = _get_snowflake_oauth_token(c)
        connection_params["token"] = access_token
        connection_params["authenticator"] = "oauth"
    elif has_token:
        # Direct token (pre-obtained OAuth access token)
        logger.info("Using Snowflake token authentication (OAuth)")
        connection_params["token"] = c["token"]
        connection_params["authenticator"] = "oauth"
    else:
        # Traditional password authentication
        connection_params["password"] = c["password"]
        logger.info("Using Snowflake password authentication")

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
            return raw_conn

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


@contextmanager
def get_snow_conn(cfg=None, use_pool=True, retries=3, retry_delay=2):
    """
    Get Snowflake connection (optionally from pool) with retry logic.

    Args:
        cfg: Configuration dictionary with snowflake credentials
        use_pool: Whether to use connection pooling (default: True)
        retries: Number of connection attempts (default: 3)
        retry_delay: Seconds to wait between retries (default: 2)

    Yields:
        ConnectionWrapper: Wrapped Snowflake connection

    Raises:
        ValueError: If configuration is missing
        snowflake.connector.Error: If connection fails after retries

    Example:
        with get_snow_conn(cfg) as conn:
            result = conn.fetch_one("SELECT CURRENT_VERSION()")
    """
    if use_pool:
        # Get or create pool for Snowflake
        pool = pool_manager.get_or_create_pool(
            name="snowflake",
            connection_factory=lambda: _create_snowflake_connection(cfg, retries, retry_delay),
            min_size=2,
            max_size=10,
            max_age_seconds=3600,
            health_check_interval=300,
            connection_timeout=30
        )

        # Get connection from pool
        with pool.get_connection() as raw_conn:
            yield ConnectionWrapper(raw_conn)
    else:
        # Direct connection (no pooling)
        raw_conn = _create_snowflake_connection(cfg, retries, retry_delay)
        try:
            yield ConnectionWrapper(raw_conn)
        finally:
            raw_conn.close()


def test_snowflake_connection(cfg=None):
    """
    Test Snowflake connection and return status information.

    Args:
        cfg: Configuration dictionary with snowflake credentials

    Returns:
        dict: Connection status with details
    """
    try:
        with get_snow_conn(cfg, retries=1) as conn:
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
