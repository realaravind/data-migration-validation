#!/bin/bash
set -e

echo "=== PART 5: Adding Connectivity Tests for SQL Server and Snowflake ==="

mkdir -p ombudsman/scripts

cat << 'EOF' > ombudsman/scripts/test_sqlserver.py
import pyodbc
import yaml

def main():
    cfg=yaml.safe_load(open("config/connections.yaml"))
    conn_str=cfg["sqlserver"]["conn_str"]
    try:
        conn=pyodbc.connect(conn_str, timeout=5)
        cur=conn.cursor()
        cur.execute("SELECT 1")
        print("SQL Server connection OK")
    except Exception as e:
        print("SQL Server connection FAILED:", e)

if __name__=="__main__":
    main()
EOF

cat << 'EOF' > ombudsman/scripts/test_snowflake.py
import snowflake.connector
import yaml

def main():
    cfg=yaml.safe_load(open("config/connections.yaml"))["snowflake"]
    try:
        conn=snowflake.connector.connect(
            user=cfg["user"],
            password=cfg["password"],
            account=cfg["account"],
            database=cfg["database"],
            schema=cfg["schema"],
        )
        cur=conn.cursor()
        cur.execute("SELECT 1")
        print("Snowflake connection OK")
    except Exception as e:
        print("Snowflake connection FAILED:", e)

if __name__=="__main__":
    main()
EOF

echo "PART 5 complete."