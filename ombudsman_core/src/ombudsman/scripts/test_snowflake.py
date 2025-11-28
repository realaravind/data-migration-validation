#!/usr/bin/env python3
import os
import snowflake.connector

print("Testing Snowflake connection...")

conn = snowflake.connector.connect(
    user=os.getenv("SNOWFLAKE_USER"),
    password=os.getenv("SNOWFLAKE_PASSWORD"),
    account=os.getenv("SNOWFLAKE_ACCOUNT")
)

cur = conn.cursor()

cur.execute("SELECT CURRENT_VERSION()")
version = cur.fetchone()

print("Connected successfully.")
print("Snowflake version:")
print(version[0])