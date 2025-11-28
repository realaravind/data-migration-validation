import os

def ensure_validation_schema(snow_conn):
    schema = os.getenv("VALIDATION_SCHEMA", "VALIDATION")

    snow_conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")

    snow_conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema}.VALIDATION_RUNS (
            run_id STRING,
            run_timestamp TIMESTAMP,
            total_checks NUMBER,
            failed_checks NUMBER,
            passed_checks NUMBER
        )
    """)

    snow_conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema}.VALIDATION_RESULTS (
            run_id STRING,
            validation_name STRING,
            category STRING,
            status STRING,
            severity STRING,
            details STRING
        )
    """)

    snow_conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {schema}.VALIDATION_DETAILS (
            run_id STRING,
            validation_name STRING,
            row_number NUMBER,
            content VARIANT
        )
    """)

    return schema