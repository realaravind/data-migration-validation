#!/usr/bin/env python3
import os
import pyodbc

conn_str = os.getenv("SQLSERVER_CONN_STR")

if not conn_str:
    raise Exception("SQLSERVER_CONN_STR is not set")

print("Connecting to SQL Server...")

conn = pyodbc.connect(conn_str, autocommit=True)
cur = conn.cursor()

cur.execute("SELECT @@VERSION")
row = cur.fetchone()

print("Connected successfully.")
print("SQL Server version:")
print(row[0])