# src/ombudsman/validation/schema/validate_schema_datatypes.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def normalize_sql_type(t):
    return t.lower().replace(" ", "")

def normalize_snow_type(t):
    return t.lower().replace(" ", "")

def validate_schema_datatypes(sql_conn=None, snow_conn=None, mapping=None, metadata=None, table=None, **kwargs):
    """
    Validate that data types match between SQL Server and Snowflake tables.
    Queries both databases and compares column data types.
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

        # Query SQL Server column types
        sql_query = f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = PARSENAME('{sql_table}', 2)
            AND TABLE_NAME = PARSENAME('{sql_table}', 1)
            ORDER BY ORDINAL_POSITION
        """
        sql_results = sql_conn.fetch_many(sql_query)
        sql_types = {row[0]: normalize_sql_type(row[1]) for row in sql_results}

        # Query Snowflake column types
        # Get database name from connection
        snow_db = snow_conn.database

        # Parse snow_table - handle "DATABASE.SCHEMA.TABLE", "SCHEMA.TABLE", and "TABLE" formats
        parts = snow_table.split('.')
        if len(parts) == 3:
            # DATABASE.SCHEMA.TABLE - use the database from the identifier
            snow_db = parts[0]
            snow_schema = parts[1]
            snow_table_name = parts[2]
        elif len(parts) == 2:
            # SCHEMA.TABLE
            snow_schema = parts[0]
            snow_table_name = parts[1]
        else:
            # Just TABLE - default to PUBLIC schema
            snow_schema = 'PUBLIC'
            snow_table_name = snow_table

        snow_query = f"""
            SELECT COLUMN_NAME, DATA_TYPE
            FROM {snow_db}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = '{snow_schema}'
            AND TABLE_NAME = '{snow_table_name}'
            ORDER BY ORDINAL_POSITION
        """
        snow_results = snow_conn.fetch_many(snow_query)
        snow_types = {row[0]: normalize_snow_type(row[1]) for row in snow_results}

        # Compare types for each column
        mismatches = []
        for col_name in sql_types.keys():
            if col_name not in snow_types:
                mismatches.append({
                    "column": col_name,
                    "sql_type": sql_types[col_name],
                    "snow_type": None,
                    "match": False,
                    "severity": "HIGH"
                })
            elif sql_types[col_name] != snow_types[col_name]:
                mismatches.append({
                    "column": col_name,
                    "sql_type": sql_types[col_name],
                    "snow_type": snow_types[col_name],
                    "match": False,
                    "severity": "MEDIUM"
                })

        return {
            "status": "FAIL" if mismatches else "PASS",
            "severity": "HIGH" if any(m["severity"] == "HIGH" for m in mismatches) else ("MEDIUM" if mismatches else "NONE"),
            "sql_types": sql_types,
            "snow_types": snow_types,
            "mismatches": mismatches,
            "mismatch_count": len(mismatches)
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "severity": "HIGH",
            "message": f"Failed to validate schema datatypes: {str(e)}"
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
        table_res = []
        for col in sql_columns[table]:
            col_name = col["name"]
            sql_type = normalize_sql_type(col["type"])
            snow_col = next((c for c in snow_columns.get(table, []) if c["name"] == col_name), None)

            if not snow_col:
                table_res.append({
                    "column": col_name,
                    "sql_type": sql_type,
                    "snow_type": None,
                    "match": False,
                    "severity": "HIGH"
                })
                continue

            snow_type = normalize_snow_type(snow_col["type"])
            match = sql_type == snow_type

            table_res.append({
                "column": col_name,
                "sql_type": sql_type,
                "snow_type": snow_type,
                "match": match,
                "severity": "NONE" if match else "MEDIUM"
            })

        results[table] = table_res

    return {
        "status": "PASS" if all(all(r["match"] for r in res) for res in results.values()) else "FAIL",
        "severity": "HIGH" if any(any(r["severity"] == "HIGH" for r in res) for res in results.values()) else "NONE",
        "results": results
    }