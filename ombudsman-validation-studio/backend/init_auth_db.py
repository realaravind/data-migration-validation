#!/usr/bin/env python3
"""Initialize authentication database schema"""

import pyodbc
import os
import sys

# Connection string - MUST be set via environment variable for production
conn_str = os.getenv('SQLSERVER_CONN_STR')
if not conn_str:
    print("❌ ERROR: SQLSERVER_CONN_STR environment variable is not set!")
    print("Please configure database connection in .env file")
    sys.exit(1)

print("Connecting to SQL Server...")
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# Create Users table
print("Creating Users table...")
try:
    cursor.execute("""
    CREATE TABLE Users (
        user_id VARCHAR(100) PRIMARY KEY,
        username NVARCHAR(100) NOT NULL UNIQUE,
        email NVARCHAR(255) NOT NULL UNIQUE,
        hashed_password NVARCHAR(255) NOT NULL,
        full_name NVARCHAR(255),
        role VARCHAR(50) NOT NULL DEFAULT 'user',
        is_active BIT NOT NULL DEFAULT 1,
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        updated_at DATETIME2 NOT NULL DEFAULT GETDATE()
    )
    """)
    conn.commit()
    print("✅ Users table created successfully")
except Exception as e:
    if 'already exists' in str(e) or 'There is already an object' in str(e):
        print("⚠️  Users table already exists")
    else:
        print(f"❌ Error creating Users table: {e}")

# Create RefreshTokens table
print("Creating RefreshTokens table...")
try:
    cursor.execute("""
    CREATE TABLE RefreshTokens (
        token_id BIGINT IDENTITY(1,1) PRIMARY KEY,
        user_id VARCHAR(100) NOT NULL,
        refresh_token NVARCHAR(500) NOT NULL UNIQUE,
        expires_at DATETIME2 NOT NULL,
        created_at DATETIME2 NOT NULL DEFAULT GETDATE(),
        FOREIGN KEY (user_id) REFERENCES Users(user_id) ON DELETE CASCADE
    )
    """)
    conn.commit()
    print("✅ RefreshTokens table created successfully")
except Exception as e:
    if 'already exists' in str(e) or 'There is already an object' in str(e):
        print("⚠️  RefreshTokens table already exists")
    else:
        print(f"❌ Error creating RefreshTokens table: {e}")

# Verify tables
print("\nVerifying tables...")
cursor.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_NAME IN ('Users', 'RefreshTokens')")
tables = [row[0] for row in cursor.fetchall()]
print(f"Tables found: {tables}")

conn.close()
print("\n✅ Database initialization complete!")
