#!/usr/bin/env python3
"""
Advanced Sample Data Generator

Creates synthetic dimensional & fact models with:
- Configurable number of dimensions and facts
- Configurable row counts
- Optional broken foreign keys (for testing)
- Random but deterministic sample data
- Runs on SQL Server or Snowflake Emulator
"""

import os
import random
import string
from datetime import datetime, timedelta

import pyodbc
import snowflake.connector


# -----------------------------------------------------------
# CONFIGURATION VIA ENV VARIABLES
# -----------------------------------------------------------

MODE = os.getenv("SAMPLE_SOURCE", "").lower()

NUM_DIMENSIONS = int(os.getenv("SAMPLE_DIM_COUNT", "3"))
NUM_FACTS = int(os.getenv("SAMPLE_FACT_COUNT", "2"))
ROWS_PER_DIM = int(os.getenv("SAMPLE_DIM_ROWS", "50"))
ROWS_PER_FACT = int(os.getenv("SAMPLE_FACT_ROWS", "200"))

BROKEN_FK_RATE = float(os.getenv("BROKEN_FK_RATE", "0.05"))  # 5% broken FK rows
random.seed(int(os.getenv("SAMPLE_SEED", "12345")))


# -----------------------------------------------------------
# UTILITY FUNCTIONS
# -----------------------------------------------------------

def random_string(n=8):
    return ''.join(random.choice(string.ascii_letters) for _ in range(n))


def random_date():
    start = datetime(2020, 1, 1)
    end = datetime(2024, 12, 31)
    delta = end - start
    return (start + timedelta(days=random.randint(0, delta.days))).date()


# -----------------------------------------------------------
# DATA MODEL GENERATION
# -----------------------------------------------------------

def generate_dimensions():
    dims = {}
    for i in range(1, NUM_DIMENSIONS + 1):
        name = f"dim_{i}"
        dims[name] = []

        for row_id in range(1, ROWS_PER_DIM + 1):
            dims[name].append({
                "id": row_id,
                "attr1": random_string(6),
                "attr2": random_string(10)
            })

    return dims


def generate_facts(dims):
    facts = {}
    dim_names = list(dims.keys())

    for i in range(1, NUM_FACTS + 1):
        name = f"fact_{i}"
        facts[name] = []

        for row_id in range(1, ROWS_PER_FACT + 1):
            row = {
                "id": row_id,
                "amount": round(random.uniform(5, 5000), 2),
                "event_date": random_date(),
            }

            # FK references to all dimensions
            for dim in dim_names:
                if random.random() < BROKEN_FK_RATE:
                    row[f"{dim}_id"] = random.randint(99999, 199999)
                else:
                    row[f"{dim}_id"] = random.randint(1, ROWS_PER_DIM)

            facts[name].append(row)

    return facts


# -----------------------------------------------------------
# SQL SERVER IMPLEMENTATION
# -----------------------------------------------------------

def load_sqlserver(dims, facts):
    conn_str = os.getenv("SQLSERVER_CONN_STR")
    if not conn_str:
        raise Exception("SQLSERVER_CONN_STR not set")

    conn = pyodbc.connect(conn_str, autocommit=True)
    cursor = conn.cursor()

    cursor.execute("IF DB_ID('SampleDW') IS NULL CREATE DATABASE SampleDW;")
    cursor.execute("USE SampleDW;")

    # Dimensions
    for dim in dims:
        cursor.execute(f"""
            IF OBJECT_ID('dbo.{dim}') IS NOT NULL DROP TABLE dbo.{dim};
            CREATE TABLE dbo.{dim}(
                {dim}_id INT PRIMARY KEY,
                attr1 NVARCHAR(100),
                attr2 NVARCHAR(100)
            );
        """)

        for row in dims[dim]:
            cursor.execute(
                f"INSERT INTO dbo.{dim} VALUES (?, ?, ?);",
                row["id"], row["attr1"], row["attr2"]
            )

    # Facts
    for fact in facts:
        dim_cols = ", ".join([f"{dim}_id INT" for dim in dims])
        fk_constraints = ", ".join(
            [f"FOREIGN KEY ({dim}_id) REFERENCES dbo.{dim}({dim}_id)" for dim in dims]
        )

        cursor.execute(f"""
            IF OBJECT_ID('dbo.{fact}') IS NOT NULL DROP TABLE dbo.{fact};
            CREATE TABLE dbo.{fact}(
                {fact}_id INT PRIMARY KEY,
                amount DECIMAL(18,2),
                event_date DATE,
                {dim_cols},
                {fk_constraints}
            );
        """)

        for row in facts[fact]:
            values = [row["id"], row["amount"], row["event_date"]] + \
                     [row[f"{dim}_id"] for dim in dims]

            placeholders = ", ".join(["?"] * len(values))
            cursor.execute(f"INSERT INTO dbo.{fact} VALUES ({placeholders});", values)

    print("SQL Server sample data loaded.")


# -----------------------------------------------------------
# SNOWFLAKE IMPLEMENTATION
# -----------------------------------------------------------

def load_snowflake(dims, facts):
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
    )
    cursor = conn.cursor()

    db = os.getenv("SNOWFLAKE_DATABASE", "SAMPLEDW")
    schema = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db}")
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {db}.{schema}")
    cursor.execute(f"USE DATABASE {db}")
    cursor.execute(f"USE SCHEMA {schema}")

    # Dimensions
    for dim in dims:
        cursor.execute(f"DROP TABLE IF EXISTS {dim}")
        cursor.execute(f"""
            CREATE TABLE {dim}(
                {dim}_id INT,
                attr1 STRING,
                attr2 STRING
            );
        """)

        for row in dims[dim]:
            cursor.execute(
                f"INSERT INTO {dim} VALUES (?, ?, ?);",
                (row["id"], row["attr1"], row["attr2"])
            )

    # Facts
    for fact in facts:
        dim_cols = ", ".join([f"{dim}_id INT" for dim in dims])

        cursor.execute(f"DROP TABLE IF EXISTS {fact}")
        cursor.execute(f"""
            CREATE TABLE {fact}(
                {fact}_id INT,
                amount NUMBER(18,2),
                event_date DATE,
                {dim_cols}
            );
        """)

        for row in facts[fact]:
            values = [row["id"], row["amount"], row["event_date"]] + \
                     [row[f"{dim}_id"] for dim in dims]

            placeholders = ", ".join(["?"] * len(values))
            cursor.execute(f"INSERT INTO {fact} VALUES ({placeholders});", values)

    print("Snowflake sample data loaded.")


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------

def main():
    if MODE not in ("sqlserver", "snowflake"):
        raise Exception("SAMPLE_SOURCE must be 'sqlserver' or 'snowflake'")

    print("Generating synthetic schema...")
    dims = generate_dimensions()
    facts = generate_facts(dims)

    if MODE == "sqlserver":
        load_sqlserver(dims, facts)
    else:
        load_snowflake(dims, facts)


if __name__ == "__main__":
    main()