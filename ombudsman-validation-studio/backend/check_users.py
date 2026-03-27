#!/usr/bin/env python3
"""
Check Users Table - Direct database query
Run: python3 check_users.py
"""

import os
import sys

# Check which backend
AUTH_BACKEND = os.getenv("AUTH_BACKEND", "sqlite").lower()

print("=" * 60)
print(f"AUTH_BACKEND: {AUTH_BACKEND}")
print("=" * 60)

if AUTH_BACKEND == "sqlserver":
    # SQL Server connection
    import pyodbc

    server = os.getenv("AUTH_DB_SERVER", os.getenv("MSSQL_HOST", "localhost"))
    database = os.getenv("AUTH_DB_NAME", "ovs_studio")
    username = os.getenv("AUTH_DB_USER", os.getenv("MSSQL_USER", ""))
    password = os.getenv("AUTH_DB_PASSWORD", os.getenv("MSSQL_PASSWORD", ""))
    port = os.getenv("MSSQL_PORT", "1433")

    print(f"\nConnecting to SQL Server...")
    print(f"  Server: {server}:{port}")
    print(f"  Database: {database}")
    print(f"  User: {username}")
    print(f"  Password: {'*' * len(password) if password else '(empty)'}")

    try:
        conn_str = f"DRIVER={{ODBC Driver 18 for SQL Server}};SERVER={server},{port};DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes;"
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        print("\nSUCCESS: Connected to SQL Server")

        # Check if users table exists
        print("\n[1] CHECKING TABLES")
        print("-" * 40)
        cursor.execute("""
            SELECT TABLE_NAME
            FROM INFORMATION_SCHEMA.TABLES
            WHERE TABLE_TYPE = 'BASE TABLE'
            ORDER BY TABLE_NAME
        """)
        tables = cursor.fetchall()
        print(f"Found {len(tables)} tables:")
        for t in tables:
            print(f"  - {t[0]}")

        # Query users table
        print("\n[2] USERS TABLE")
        print("-" * 40)
        try:
            cursor.execute("SELECT * FROM users")
            columns = [column[0] for column in cursor.description]
            print(f"Columns: {columns}")

            rows = cursor.fetchall()
            print(f"\nFound {len(rows)} users:")
            for row in rows:
                print("-" * 40)
                for i, col in enumerate(columns):
                    value = row[i]
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"  {col}: {value}")
        except Exception as e:
            print(f"ERROR querying users table: {e}")
            print("\nTrying to create tables...")

        conn.close()

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

else:
    # SQLite connection
    import sqlite3

    # Find SQLite database
    data_dir = os.getenv("OMBUDSMAN_DATA_DIR", "/DataDisk1/ombudsman/data")
    db_path = os.path.join(data_dir, "auth", "auth.db")

    print(f"\nSQLite database path: {db_path}")
    print(f"Database exists: {os.path.exists(db_path)}")

    if not os.path.exists(db_path):
        print("\nERROR: Database file not found!")
        print("The auth database hasn't been created yet.")
        sys.exit(1)

    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        print("\nSUCCESS: Connected to SQLite")

        # Check tables
        print("\n[1] CHECKING TABLES")
        print("-" * 40)
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = cursor.fetchall()
        print(f"Found {len(tables)} tables:")
        for t in tables:
            print(f"  - {t[0]}")

        # Query users table
        print("\n[2] USERS TABLE")
        print("-" * 40)
        try:
            cursor.execute("SELECT * FROM users")
            columns = [description[0] for description in cursor.description]
            print(f"Columns: {columns}")

            rows = cursor.fetchall()
            print(f"\nFound {len(rows)} users:")
            for row in rows:
                print("-" * 40)
                for i, col in enumerate(columns):
                    value = row[i]
                    # Truncate long values
                    if isinstance(value, str) and len(value) > 50:
                        value = value[:50] + "..."
                    print(f"  {col}: {value}")
        except Exception as e:
            print(f"ERROR querying users table: {e}")

        conn.close()

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

print("\n" + "=" * 60)
print("DONE")
print("=" * 60)
