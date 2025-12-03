'''
Centralized SQL + Snowflake creation.

'''

# src/ombudsman/core/connections.py

import pyodbc
import snowflake.connector
import os
from decimal import Decimal


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

def get_snow_conn(cfg=None):
    c = cfg.get("snowflake")
    raw_conn = snowflake.connector.connect(
        user=c["user"],
        password=c["password"],
        account=c["account"],
        warehouse=c["warehouse"],
        database=c["database"],
        schema=c["schema"]
    )
    return ConnectionWrapper(raw_conn)
    