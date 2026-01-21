"""
Setup SQL Server authentication database and tables.

Run this script to create the ovs_studio database and all required tables.

IMPORTANT: This script requires environment variables to be set:
- AUTH_DB_SERVER (e.g., "sqlserver,1433" or "myserver.database.windows.net,1433")
- AUTH_DB_USER (e.g., "sa" or "sqladmin")
- AUTH_DB_PASSWORD
- AUTH_DB_NAME (optional, defaults to "ovs_studio")
"""

import pyodbc
import sys
import os

# Get configuration from environment variables
DB_SERVER = os.getenv("AUTH_DB_SERVER")
DB_USER = os.getenv("AUTH_DB_USER")
DB_PASSWORD = os.getenv("AUTH_DB_PASSWORD")
DB_NAME = os.getenv("AUTH_DB_NAME", "ovs_studio")

# Validate required environment variables
if not all([DB_SERVER, DB_USER, DB_PASSWORD]):
    missing = []
    if not DB_SERVER: missing.append("AUTH_DB_SERVER")
    if not DB_USER: missing.append("AUTH_DB_USER")
    if not DB_PASSWORD: missing.append("AUTH_DB_PASSWORD")
    print("=" * 60)
    print("ERROR: Missing Required Environment Variables")
    print("=" * 60)
    print(f"\nMissing: {', '.join(missing)}\n")
    print("Please set these environment variables before running this script:")
    print(f"  export AUTH_DB_SERVER='your-server,1433'")
    print(f"  export AUTH_DB_USER='your-username'")
    print(f"  export AUTH_DB_PASSWORD='your-password'")
    print(f"  export AUTH_DB_NAME='ovs_studio'  # optional, defaults to ovs_studio")
    print("\nFor production Azure SQL Database:")
    print(f"  export AUTH_DB_SERVER='myserver.database.windows.net,1433'")
    sys.exit(1)

# Determine TrustServerCertificate and Encrypt based on server type
if "database.windows.net" in DB_SERVER:
    # Azure SQL Database
    trust_cert = "no"
    encrypt = "yes"
else:
    # Local or on-prem SQL Server
    trust_cert = "yes"
    encrypt = "optional"

# Connection without database (to create database)
conn_str_master = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    f"TrustServerCertificate={trust_cert};"
    f"Encrypt={encrypt};"
    f"Connection Timeout=30;"
)

# Connection with database (to create tables)
conn_str_ovs = (
    f"DRIVER={{ODBC Driver 18 for SQL Server}};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_NAME};"
    f"UID={DB_USER};"
    f"PWD={DB_PASSWORD};"
    f"TrustServerCertificate={trust_cert};"
    f"Encrypt={encrypt};"
    f"Connection Timeout=30;"
)

def create_database():
    """Create authentication database if it doesn't exist"""
    print(f"Step 1: Creating '{DB_NAME}' database...")
    try:
        conn = pyodbc.connect(conn_str_master)
        conn.autocommit = True
        cursor = conn.cursor()

        # Check if database exists
        cursor.execute(f"SELECT name FROM sys.databases WHERE name = '{DB_NAME}'")
        if cursor.fetchone():
            print(f"  ✓ Database '{DB_NAME}' already exists")
        else:
            cursor.execute(f"CREATE DATABASE {DB_NAME}")
            print(f"  ✓ Database '{DB_NAME}' created successfully")

        conn.close()
        return True
    except Exception as e:
        print(f"  ✗ Error creating database: {e}")
        return False

def create_tables():
    """Create all required tables"""
    print("\nStep 2: Creating tables...")
    try:
        conn = pyodbc.connect(conn_str_ovs)
        cursor = conn.cursor()

        # Create users table
        print("  - Creating 'users' table...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'users') AND type in (N'U'))
            CREATE TABLE users (
                user_id VARCHAR(50) PRIMARY KEY,
                username VARCHAR(100) UNIQUE NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                hashed_password VARCHAR(255) NOT NULL,
                full_name VARCHAR(255),
                role VARCHAR(20) NOT NULL DEFAULT 'user',
                is_active BIT NOT NULL DEFAULT 1,
                is_verified BIT NOT NULL DEFAULT 0,
                failed_login_attempts INT NOT NULL DEFAULT 0,
                locked_until DATETIME2,
                created_at DATETIME2 NOT NULL,
                updated_at DATETIME2 NOT NULL,
                last_login DATETIME2
            )
        ''')
        print("    ✓ 'users' table created")

        # Create refresh_tokens table
        print("  - Creating 'refresh_tokens' table...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'refresh_tokens') AND type in (N'U'))
            CREATE TABLE refresh_tokens (
                token_id INT IDENTITY(1,1) PRIMARY KEY,
                user_id VARCHAR(50) NOT NULL,
                refresh_token VARCHAR(500) UNIQUE NOT NULL,
                expires_at DATETIME2 NOT NULL,
                created_at DATETIME2 NOT NULL,
                revoked_at DATETIME2,
                is_revoked BIT NOT NULL DEFAULT 0,
                device_info VARCHAR(500),
                ip_address VARCHAR(50),
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
        ''')
        print("    ✓ 'refresh_tokens' table created")

        # Create audit_logs table
        print("  - Creating 'audit_logs' table...")
        cursor.execute('''
            IF NOT EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'audit_logs') AND type in (N'U'))
            CREATE TABLE audit_logs (
                log_id INT IDENTITY(1,1) PRIMARY KEY,
                user_id VARCHAR(50),
                event_type VARCHAR(50) NOT NULL,
                event_description TEXT,
                ip_address VARCHAR(50),
                user_agent VARCHAR(500),
                success BIT NOT NULL DEFAULT 1,
                error_message TEXT,
                created_at DATETIME2 NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE SET NULL
            )
        ''')
        print("    ✓ 'audit_logs' table created")

        conn.commit()
        conn.close()
        print("  ✓ All tables created successfully")
        return True
    except Exception as e:
        print(f"  ✗ Error creating tables: {e}")
        return False

def main():
    print("="*60)
    print("SQL Server Authentication Setup")
    print("="*60)

    if not create_database():
        print("\n✗ Setup failed at database creation")
        sys.exit(1)

    if not create_tables():
        print("\n✗ Setup failed at table creation")
        sys.exit(1)

    print("\n" + "="*60)
    print("✓ Setup completed successfully!")
    print("="*60)
    print("\nYou can now use SQL Server authentication.")
    print(f"The database '{DB_NAME}' is ready with all required tables.")

if __name__ == "__main__":
    main()
