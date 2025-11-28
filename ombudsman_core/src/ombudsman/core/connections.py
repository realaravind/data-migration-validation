'''
Centralized SQL + Snowflake creation.

'''

# src/ombudsman/core/connections.py

import pyodbc
import snowflake.connector

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
        return pyodbc.connect(conn_str)

    # Fallback: older env var
    env_conn_str = os.getenv("SQLSERVER_CONN_STR")
    if env_conn_str:
        return pyodbc.connect(env_conn_str)

    raise ValueError("No SQL connection config found")

def get_snow_conn(cfg=None):
    c = cfg.get("snowflake")
    return snowflake.connector.connect(
        user=c["user"],
        password=c["password"],
        account=c["account"],
        warehouse=c["warehouse"],
        database=c["database"],
        schema=c["schema"]
    )
    