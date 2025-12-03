# src/ombudsman/validation/schema/validate_schema_columns.py

from ...core.utils import diff_lists
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_schema_columns(sql_conn=None, snow_conn=None, mapping=None, metadata=None, table=None, **kwargs):
    """
    Validate that columns match between SQL Server and Snowflake tables.
    Queries both databases and compares column lists.
    """
    # Need connections, mapping, and table
    if not sql_conn or not snow_conn or not mapping or not table:
        return {
            "status": "SKIPPED",
            "severity": "NONE",
            "message": "Missing required parameters: sql_conn, snow_conn, mapping, or table"
        }

    try:
        # Get table names from mapping
        sql_table = escape_sql_server_identifier(mapping[table]["sql"])
        snow_table = escape_snowflake_identifier(mapping[table]["snow"])

        # Query SQL Server columns
        sql_query = f"""
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = PARSENAME('{sql_table}', 2)
            AND TABLE_NAME = PARSENAME('{sql_table}', 1)
            ORDER BY ORDINAL_POSITION
        """
        sql_cols = [row[0] for row in sql_conn.fetch_many(sql_query)]

        # Query Snowflake columns
        # Get database name from connection
        snow_db = snow_conn.database
        snow_query = f"""
            SELECT COLUMN_NAME
            FROM {snow_db}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = SPLIT_PART('{snow_table}', '.', 1)
            AND TABLE_NAME = SPLIT_PART('{snow_table}', '.', 2)
            ORDER BY ORDINAL_POSITION
        """
        snow_cols = [row[0] for row in snow_conn.fetch_many(snow_query)]

        # Compare columns
        missing_in_sql, missing_in_snow = diff_lists(snow_cols, sql_cols)

        return {
            "status": "FAIL" if missing_in_sql or missing_in_snow else "PASS",
            "severity": "HIGH" if missing_in_sql or missing_in_snow else "NONE",
            "sql_columns": sql_cols,
            "snow_columns": snow_cols,
            "missing_in_sql": missing_in_sql,
            "missing_in_snow": missing_in_snow,
            "column_count_sql": len(sql_cols),
            "column_count_snow": len(snow_cols)
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "severity": "HIGH",
            "message": f"Failed to validate schema columns: {str(e)}"
        }

    # Fallback for legacy signature
    sql_columns = kwargs.get('sql_columns', {})
    snow_columns = kwargs.get('snow_columns', {})

    if not sql_columns and not snow_columns:
        return {
            "status": "SKIPPED",
            "severity": "NONE",
            "message": "No column metadata provided"
        }

    results = {}

    for table in sql_columns.keys():
        sql_cols = [c["name"] for c in sql_columns[table]]
        snow_cols = [c["name"] for c in snow_columns.get(table, [])]

        missing_in_sql, missing_in_snow = diff_lists(snow_cols, sql_cols)

        results[table] = {
            "missing_in_sql": missing_in_sql,
            "missing_in_snow": missing_in_snow,
            "extra_in_sql": list(set(sql_cols) - set(snow_cols)),
            "extra_in_snow": list(set(snow_cols) - set(sql_cols)),
            "column_order_match": sql_cols == snow_cols,
            "status": "FAIL" if missing_in_sql or missing_in_snow else "PASS",
            "severity": "HIGH" if missing_in_sql or missing_in_snow else "NONE"
        }

    return results