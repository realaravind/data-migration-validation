#!/usr/bin/env python3
"""
Enhanced Sample Data Generator with realistic schemas

Features:
- Generates proper DATE dimension with calendar attributes
- Uses realistic table/column names
- Supports predefined schema templates
- Configurable via env variables or schema definition
"""

import os
import random
import string
from datetime import datetime, timedelta, date

import pyodbc
import snowflake.connector
import yaml


# -----------------------------------------------------------
# SCHEMA TEMPLATES
# -----------------------------------------------------------

SCHEMA_TEMPLATES = {
    "retail": {
        "dimensions": {
            "dim_customer": {
                "pk": "customer_key",
                "columns": {
                    "customer_id": "VARCHAR(50)",
                    "customer_name": "VARCHAR(100)",
                    "email": "VARCHAR(100)",
                    "segment": "VARCHAR(20)",
                    "region": "VARCHAR(50)"
                },
                "sample_data": lambda: {
                    "customer_id": f"CUST{random.randint(1000, 9999)}",
                    "customer_name": f"{random.choice(['Alice', 'Bob', 'Charlie', 'Diana', 'Eve'])} {random.choice(['Smith', 'Johnson', 'Williams', 'Brown'])}",
                    "email": f"user{random.randint(1, 999)}@example.com",
                    "segment": random.choice(['Gold', 'Silver', 'Bronze']),
                    "region": random.choice(['North', 'South', 'East', 'West'])
                }
            },
            "dim_product": {
                "pk": "product_key",
                "columns": {
                    "product_id": "VARCHAR(50)",
                    "product_name": "VARCHAR(200)",
                    "category": "VARCHAR(50)",
                    "subcategory": "VARCHAR(50)",
                    "unit_price": "DECIMAL(10,2)"
                },
                "sample_data": lambda: {
                    "product_id": f"PROD{random.randint(1000, 9999)}",
                    "product_name": f"{random.choice(['Widget', 'Gadget', 'Device', 'Tool'])} {random.choice(['Pro', 'Ultra', 'Plus', 'Max'])}",
                    "category": random.choice(['Electronics', 'Clothing', 'Food', 'Books']),
                    "subcategory": random.choice(['Premium', 'Standard', 'Economy']),
                    "unit_price": round(random.uniform(9.99, 999.99), 2)
                }
            },
            "dim_store": {
                "pk": "store_key",
                "columns": {
                    "store_id": "VARCHAR(20)",
                    "store_name": "VARCHAR(100)",
                    "city": "VARCHAR(50)",
                    "state": "VARCHAR(2)",
                    "store_type": "VARCHAR(20)"
                },
                "sample_data": lambda: {
                    "store_id": f"STR{random.randint(100, 999)}",
                    "store_name": f"Store #{random.randint(1, 999)}",
                    "city": random.choice(['New York', 'Los Angeles', 'Chicago', 'Houston', 'Phoenix']),
                    "state": random.choice(['NY', 'CA', 'IL', 'TX', 'AZ']),
                    "store_type": random.choice(['Flagship', 'Standard', 'Outlet'])
                }
            }
        },
        "facts": {
            "fact_sales": {
                "pk": "sales_key",
                "dimensions": ["dim_customer", "dim_product", "dim_store", "dim_date"],
                "metrics": {
                    "quantity": "INT",
                    "unit_price": "DECIMAL(10,2)",
                    "discount_amount": "DECIMAL(10,2)",
                    "sales_amount": "DECIMAL(12,2)",
                    "cost_amount": "DECIMAL(12,2)"
                },
                "sample_data": lambda: {
                    "quantity": random.randint(1, 10),
                    "unit_price": round(random.uniform(10, 500), 2),
                    "discount_amount": round(random.uniform(0, 50), 2),
                    "sales_amount": lambda q, up, da: round(q * up - da, 2),
                    "cost_amount": lambda q, up, da: round((q * up - da) * 0.6, 2)
                }
            }
        }
    }
}


# -----------------------------------------------------------
# DATE DIMENSION GENERATOR
# -----------------------------------------------------------

def generate_date_dimension(start_date: date, end_date: date):
    """Generate a complete date dimension with calendar attributes"""
    dates = []
    current = start_date
    date_key = 1

    while current <= end_date:
        dates.append({
            "date_key": date_key,
            "date": current,
            "year": current.year,
            "quarter": (current.month - 1) // 3 + 1,
            "month": current.month,
            "month_name": current.strftime("%B"),
            "week": current.isocalendar()[1],
            "day_of_month": current.day,
            "day_of_week": current.isoweekday(),
            "day_name": current.strftime("%A"),
            "is_weekend": 1 if current.isoweekday() >= 6 else 0,
            "is_holiday": 0,  # Could be enhanced with holiday logic
            "fiscal_year": current.year if current.month >= 7 else current.year - 1,
            "fiscal_quarter": ((current.month + 5) % 12) // 3 + 1
        })
        current += timedelta(days=1)
        date_key += 1

    return dates


# -----------------------------------------------------------
# ENHANCED DATA GENERATION
# -----------------------------------------------------------

def generate_schema_data(schema_name="retail",
                        rows_per_dim=100,
                        rows_per_fact=1000,
                        start_date=None,
                        end_date=None,
                        broken_fk_rate=0.0):
    """
    Generate data based on schema template

    Args:
        schema_name: Name of schema template to use
        rows_per_dim: Number of rows per dimension
        rows_per_fact: Number of rows per fact table
        start_date: Start date for date dimension
        end_date: End date for date dimension
        broken_fk_rate: Percentage of broken foreign keys (for testing)
    """
    if schema_name not in SCHEMA_TEMPLATES:
        raise ValueError(f"Unknown schema: {schema_name}")

    schema = SCHEMA_TEMPLATES[schema_name]

    # Default date range: 2020-2024
    if not start_date:
        start_date = date(2020, 1, 1)
    if not end_date:
        end_date = date(2024, 12, 31)

    data = {
        "dimensions": {},
        "facts": {}
    }

    # Generate date dimension
    print("Generating date dimension...")
    data["dimensions"]["dim_date"] = generate_date_dimension(start_date, end_date)

    # Generate other dimensions
    for dim_name, dim_def in schema["dimensions"].items():
        print(f"Generating {dim_name}...")
        dim_data = []
        for i in range(1, rows_per_dim + 1):
            row = {dim_def["pk"]: i}
            row.update(dim_def["sample_data"]())
            dim_data.append(row)
        data["dimensions"][dim_name] = dim_data

    # Generate facts
    for fact_name, fact_def in schema["facts"].items():
        print(f"Generating {fact_name}...")
        fact_data = []
        date_keys = [d["date_key"] for d in data["dimensions"]["dim_date"]]

        for i in range(1, rows_per_fact + 1):
            row = {fact_def["pk"]: i}

            # Add dimension foreign keys
            for dim in fact_def["dimensions"]:
                fk_col = f"{dim}_key"
                if dim == "dim_date":
                    # Always valid date key
                    row[fk_col] = random.choice(date_keys)
                elif random.random() < broken_fk_rate:
                    # Broken FK for testing
                    row[fk_col] = random.randint(99999, 199999)
                else:
                    # Valid FK
                    row[fk_col] = random.randint(1, rows_per_dim)

            # Add metrics
            metric_sample = fact_def["sample_data"]()
            for metric_name, metric_value in metric_sample.items():
                if callable(metric_value):
                    # Computed metric (e.g., sales_amount = quantity * unit_price - discount)
                    row[metric_name] = metric_value(*[row.get(k, 0) for k in ['quantity', 'unit_price', 'discount_amount']])
                else:
                    row[metric_name] = metric_value

            fact_data.append(row)

        data["facts"][fact_name] = fact_data

    return data, schema


# -----------------------------------------------------------
# DATABASE LOADERS
# -----------------------------------------------------------

def load_to_sqlserver(data, schema_def, progress_callback=None):
    """
    Load generated data to SQL Server with transaction management.

    Args:
        data: Generated data dictionary
        schema_def: Schema definition
        progress_callback: Optional callback function(stage, progress, message)
    """
    conn_str = os.getenv("SQLSERVER_CONN_STR")
    if not conn_str:
        raise Exception("SQLSERVER_CONN_STR not set")

    def report_progress(stage, progress, message):
        """Helper to report progress"""
        if progress_callback:
            progress_callback(stage, progress, message)
        print(f"[{stage}] {progress}% - {message}")

    # Step 1: Detect if we're using Azure SQL Database
    # Azure SQL Database doesn't support CREATE DATABASE or USE statements
    # The database is already specified in the connection string
    is_azure_sql = "database.windows.net" in conn_str.lower()

    if not is_azure_sql:
        # For regular SQL Server, create database with autocommit=True
        report_progress("init", 0, "Initializing database")
        try:
            conn_autocommit = pyodbc.connect(conn_str, autocommit=True)
            cursor_autocommit = conn_autocommit.cursor()

            # CREATE DATABASE must run with autocommit=True (not in a transaction)
            cursor_autocommit.execute("IF DB_ID('SampleDW') IS NULL CREATE DATABASE SampleDW;")
            cursor_autocommit.execute("USE SampleDW;")

            cursor_autocommit.close()
            conn_autocommit.close()
        except Exception as e:
            # If database creation fails, it might already exist - continue
            print(f"[init] Database creation note: {e}")
            pass
    else:
        # For Azure SQL, database is already specified in connection string
        report_progress("init", 0, "Using Azure SQL Database from connection string")

    # Step 2: Connect with autocommit=False for transactional data loading
    conn = pyodbc.connect(conn_str, autocommit=False)
    cursor = conn.cursor()

    try:
        # For regular SQL Server, use the database
        # For Azure SQL, skip this step (database already in connection string)
        if not is_azure_sql:
            cursor.execute("USE SampleDW;")
            conn.commit()

        # Create schemas
        # For Azure SQL, use SAMPLE_ prefix to avoid polluting production schemas
        # For regular SQL Server, use regular DIM/FACT schemas in the SampleDW database
        dim_schema = "SAMPLE_DIM" if is_azure_sql else "DIM"
        fact_schema = "SAMPLE_FACT" if is_azure_sql else "FACT"

        report_progress("schema", 5, f"Creating schemas ({dim_schema}, {fact_schema})...")
        # Create schemas - split into separate statements for Azure SQL compatibility
        try:
            cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{dim_schema}') BEGIN EXEC('CREATE SCHEMA {dim_schema}') END")
        except:
            # Schema might already exist, continue
            pass
        try:
            cursor.execute(f"IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = '{fact_schema}') BEGIN EXEC('CREATE SCHEMA {fact_schema}') END")
        except:
            # Schema might already exist, continue
            pass
        conn.commit()

        # Drop existing tables (facts first to avoid FK issues)
        report_progress("cleanup", 10, "Dropping existing tables...")
        for fact_name in data["facts"]:
            cursor.execute(f"IF OBJECT_ID('{fact_schema}.{fact_name}') IS NOT NULL DROP TABLE {fact_schema}.{fact_name};")

        for dim_name in data["dimensions"]:
            cursor.execute(f"IF OBJECT_ID('{dim_schema}.{dim_name}') IS NOT NULL DROP TABLE {dim_schema}.{dim_name};")

        conn.commit()  # Commit table drops

        # Create and populate date dimension
        report_progress("dimensions", 15, "Creating dim_date...")
        cursor.execute(f"""
            CREATE TABLE {dim_schema}.dim_date(
                date_key INT PRIMARY KEY,
                date DATE,
                year INT,
                quarter INT,
                month INT,
                month_name VARCHAR(20),
                week INT,
                day_of_month INT,
                day_of_week INT,
                day_name VARCHAR(20),
                is_weekend INT,
                is_holiday INT,
                fiscal_year INT,
                fiscal_quarter INT
            );
        """)

        date_rows = data["dimensions"]["dim_date"]
        total_date_rows = len(date_rows)
        for idx, row in enumerate(date_rows):
            cursor.execute(f"""
                INSERT INTO {dim_schema}.dim_date VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """, (
                row["date_key"], row["date"], row["year"], row["quarter"], row["month"],
                row["month_name"], row["week"], row["day_of_month"], row["day_of_week"],
                row["day_name"], row["is_weekend"], row["is_holiday"], row["fiscal_year"],
                row["fiscal_quarter"]
            ))
            # Report progress every 100 rows
            if idx % 100 == 0:
                progress = 15 + int((idx / total_date_rows) * 10)
                report_progress("dimensions", progress, f"Inserting dim_date: {idx}/{total_date_rows}")

        conn.commit()  # Commit date dimension
        report_progress("dimensions", 25, f"dim_date complete ({total_date_rows} rows)")

        # Create other dimensions
        dim_count = len([d for d in data["dimensions"].keys() if d != "dim_date"])
        for dim_idx, (dim_name, dim_data) in enumerate(data["dimensions"].items()):
            if dim_name == "dim_date":
                continue

            dim_progress_base = 25 + int((dim_idx / dim_count) * 25)

            dim_def = schema_def["dimensions"][dim_name]
            columns = []
            for col_name, col_type in dim_def["columns"].items():
                # Convert to SQL Server types
                sql_type = col_type.replace("VARCHAR", "NVARCHAR")
                columns.append(f"{col_name} {sql_type}")

            pk_col = dim_def["pk"]
            columns_str = f"{pk_col} INT PRIMARY KEY, " + ", ".join(columns)

            report_progress("dimensions", dim_progress_base, f"Creating {dim_name}...")
            cursor.execute(f"CREATE TABLE {dim_schema}.{dim_name}({columns_str});")

            total_rows = len(dim_data)
            for row_idx, row in enumerate(dim_data):
                cols = [pk_col] + list(dim_def["columns"].keys())
                values = [row[c] for c in cols]
                placeholders = ", ".join(["?"] * len(values))
                cursor.execute(f"INSERT INTO {dim_schema}.{dim_name} VALUES ({placeholders});", values)

                # Report progress every 20 rows
                if row_idx % 20 == 0:
                    report_progress("dimensions", dim_progress_base, f"{dim_name}: {row_idx}/{total_rows}")

            conn.commit()  # Commit each dimension
            report_progress("dimensions", dim_progress_base + 5, f"{dim_name} complete ({total_rows} rows)")

        # Create fact tables
        fact_count = len(data["facts"])
        for fact_idx, (fact_name, fact_data) in enumerate(data["facts"].items()):
            fact_progress_base = 50 + int((fact_idx / fact_count) * 45)

            fact_def = schema_def["facts"][fact_name]
            pk_col = fact_def["pk"]

            # Build column list
            columns = [f"{pk_col} INT PRIMARY KEY"]

            # Add dimension FK columns
            for dim in fact_def["dimensions"]:
                columns.append(f"{dim}_key INT")

            # Add metric columns
            for metric_name, metric_type in fact_def["metrics"].items():
                sql_type = metric_type.replace("VARCHAR", "NVARCHAR")
                columns.append(f"{metric_name} {sql_type}")

            columns_str = ", ".join(columns)

            report_progress("facts", fact_progress_base, f"Creating {fact_name}...")
            cursor.execute(f"CREATE TABLE {fact_schema}.{fact_name}({columns_str});")

            total_rows = len(fact_data)
            for row_idx, row in enumerate(fact_data):
                cols = [pk_col] + [f"{d}_key" for d in fact_def["dimensions"]] + list(fact_def["metrics"].keys())
                values = [row[c] for c in cols]
                placeholders = ", ".join(["?"] * len(values))
                cursor.execute(f"INSERT INTO {fact_schema}.{fact_name} VALUES ({placeholders});", values)

                # Report progress every 50 rows
                if row_idx % 50 == 0:
                    report_progress("facts", fact_progress_base, f"{fact_name}: {row_idx}/{total_rows}")

            conn.commit()  # Commit each fact table
            report_progress("facts", fact_progress_base + 10, f"{fact_name} complete ({total_rows} rows)")

        report_progress("complete", 100, "SQL Server data load complete!")
        conn.close()

    except Exception as e:
        # Rollback on error
        print(f"[ERROR] Data generation failed: {str(e)}")
        report_progress("error", 0, f"Rolling back due to error: {str(e)}")
        try:
            conn.rollback()
            print("[ROLLBACK] Transaction rolled back successfully")
        except Exception as rb_error:
            print(f"[ROLLBACK ERROR] Failed to rollback: {rb_error}")
        finally:
            conn.close()
        raise  # Re-raise the exception


def load_to_snowflake(data, schema_def):
    """Load generated data to Snowflake"""
    conn = snowflake.connector.connect(
        user=os.getenv("SNOWFLAKE_USER"),
        password=os.getenv("SNOWFLAKE_PASSWORD"),
        account=os.getenv("SNOWFLAKE_ACCOUNT"),
        warehouse=os.getenv("SNOWFLAKE_WAREHOUSE"),
        role=os.getenv("SNOWFLAKE_ROLE"),
    )
    cursor = conn.cursor()

    db = os.getenv("SNOWFLAKE_DATABASE", "SAMPLEDW")

    cursor.execute(f"CREATE DATABASE IF NOT EXISTS {db}")
    cursor.execute(f"USE DATABASE {db}")

    # Create schemas
    print("Creating schemas...")
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {db}.DIM")
    cursor.execute(f"CREATE SCHEMA IF NOT EXISTS {db}.FACT")

    # Drop existing tables
    print("Dropping existing tables...")
    for fact_name in data["facts"]:
        cursor.execute(f"DROP TABLE IF EXISTS {db}.FACT.{fact_name}")

    for dim_name in data["dimensions"]:
        cursor.execute(f"DROP TABLE IF EXISTS {db}.DIM.{dim_name}")

    # Create date dimension
    print("Creating dim_date...")
    cursor.execute(f"""
        CREATE TABLE {db}.DIM.dim_date(
            date_key INT,
            date DATE,
            year INT,
            quarter INT,
            month INT,
            month_name STRING,
            week INT,
            day_of_month INT,
            day_of_week INT,
            day_name STRING,
            is_weekend INT,
            is_holiday INT,
            fiscal_year INT,
            fiscal_quarter INT
        );
    """)

    # Batch insert for dim_date
    print(f"Inserting {len(data['dimensions']['dim_date'])} rows into dim_date...")
    date_values = [
        (row["date_key"], row["date"], row["year"], row["quarter"], row["month"],
         row["month_name"], row["week"], row["day_of_month"], row["day_of_week"],
         row["day_name"], row["is_weekend"], row["is_holiday"], row["fiscal_year"],
         row["fiscal_quarter"])
        for row in data["dimensions"]["dim_date"]
    ]
    cursor.executemany(f"""
        INSERT INTO {db}.DIM.dim_date VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, date_values)

    # Create other dimensions
    for dim_name, dim_data in data["dimensions"].items():
        if dim_name == "dim_date":
            continue

        dim_def = schema_def["dimensions"][dim_name]
        columns = []
        for col_name, col_type in dim_def["columns"].items():
            # Convert to Snowflake types
            snow_type = col_type.replace("DECIMAL", "NUMBER").replace("VARCHAR", "STRING").replace("NVARCHAR", "STRING")
            columns.append(f"{col_name} {snow_type}")

        pk_col = dim_def["pk"]
        columns_str = f"{pk_col} INT, " + ", ".join(columns)

        print(f"Creating {dim_name}...")
        cursor.execute(f"CREATE TABLE {db}.DIM.{dim_name}({columns_str});")

        # Batch insert for dimension
        print(f"Inserting {len(dim_data)} rows into {dim_name}...")
        cols = [pk_col] + list(dim_def["columns"].keys())
        dim_values = [tuple(row[c] for c in cols) for row in dim_data]
        placeholders = ", ".join(["%s"] * len(cols))
        cursor.executemany(f"INSERT INTO {db}.DIM.{dim_name} VALUES ({placeholders})", dim_values)

    # Create fact tables
    for fact_name, fact_data in data["facts"].items():
        fact_def = schema_def["facts"][fact_name]
        pk_col = fact_def["pk"]

        # Build column list
        columns = [f"{pk_col} INT"]

        # Add dimension FK columns
        for dim in fact_def["dimensions"]:
            columns.append(f"{dim}_key INT")

        # Add metric columns
        for metric_name, metric_type in fact_def["metrics"].items():
            snow_type = metric_type.replace("DECIMAL", "NUMBER").replace("VARCHAR", "STRING")
            columns.append(f"{metric_name} {snow_type}")

        columns_str = ", ".join(columns)

        print(f"Creating {fact_name}...")
        cursor.execute(f"CREATE TABLE {db}.FACT.{fact_name}({columns_str});")

        # Batch insert for fact table
        print(f"Inserting {len(fact_data)} rows into {fact_name}...")
        cols = [pk_col] + [f"{d}_key" for d in fact_def["dimensions"]] + list(fact_def["metrics"].keys())
        fact_values = [tuple(row[c] for c in cols) for row in fact_data]
        placeholders = ", ".join(["%s"] * len(cols))
        cursor.executemany(f"INSERT INTO {db}.FACT.{fact_name} VALUES ({placeholders})", fact_values)

    print("Snowflake data load complete!")


# -----------------------------------------------------------
# MAIN
# -----------------------------------------------------------

def main(progress_callback=None):
    """
    Main entry point for sample data generation.

    Args:
        progress_callback: Optional callback function(stage, progress, message)
                          for progress tracking
    """
    mode = os.getenv("SAMPLE_SOURCE", "sqlserver").lower()
    schema_name = os.getenv("SAMPLE_SCHEMA", "retail")
    rows_per_dim = int(os.getenv("SAMPLE_DIM_ROWS", "100"))
    rows_per_fact = int(os.getenv("SAMPLE_FACT_ROWS", "1000"))
    broken_fk_rate = float(os.getenv("BROKEN_FK_RATE", "0.0"))

    # Generate data
    print(f"Generating {schema_name} schema with {rows_per_dim} rows/dimension, {rows_per_fact} rows/fact...")
    data, schema_def = generate_schema_data(
        schema_name=schema_name,
        rows_per_dim=rows_per_dim,
        rows_per_fact=rows_per_fact,
        broken_fk_rate=broken_fk_rate
    )

    # Load to target
    if mode == "sqlserver":
        load_to_sqlserver(data, schema_def, progress_callback)
    elif mode == "snowflake":
        load_to_snowflake(data, schema_def)
    elif mode == "both":
        load_to_sqlserver(data, schema_def, progress_callback)
        load_to_snowflake(data, schema_def)
    else:
        raise ValueError(f"Unknown mode: {mode}")


if __name__ == "__main__":
    main()
