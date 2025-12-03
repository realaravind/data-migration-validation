# src/ombudsman/validation/schema/validate_schema_nullability.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_schema_nullability(sql_conn=None, snow_conn=None, mapping=None, metadata=None, table=None, **kwargs):
    """
    Validate that nullability constraints match between SQL Server and Snowflake tables.
    Queries both databases and compares column nullability.
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

        # Query SQL Server column nullability
        sql_query = f"""
            SELECT COLUMN_NAME, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = PARSENAME('{sql_table}', 2)
            AND TABLE_NAME = PARSENAME('{sql_table}', 1)
            ORDER BY ORDINAL_POSITION
        """
        sql_results = sql_conn.fetch_many(sql_query)
        sql_nullability = {row[0]: (row[1] == 'YES') for row in sql_results}

        # Query Snowflake column nullability
        # Get database name from connection
        snow_db = snow_conn.database
        snow_query = f"""
            SELECT COLUMN_NAME, IS_NULLABLE
            FROM {snow_db}.INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = SPLIT_PART('{snow_table}', '.', 1)
            AND TABLE_NAME = SPLIT_PART('{snow_table}', '.', 2)
            ORDER BY ORDINAL_POSITION
        """
        snow_results = snow_conn.fetch_many(snow_query)
        snow_nullability = {row[0]: (row[1] == 'YES') for row in snow_results}

        # Compare nullability for each column
        mismatches = []
        for col_name in sql_nullability.keys():
            if col_name not in snow_nullability:
                mismatches.append({
                    "column": col_name,
                    "sql_nullable": sql_nullability[col_name],
                    "snow_nullable": None,
                    "match": False,
                    "severity": "HIGH"
                })
            elif sql_nullability[col_name] != snow_nullability[col_name]:
                mismatches.append({
                    "column": col_name,
                    "sql_nullable": sql_nullability[col_name],
                    "snow_nullable": snow_nullability[col_name],
                    "match": False,
                    "severity": "MEDIUM"
                })

        return {
            "status": "FAIL" if mismatches else "PASS",
            "severity": "HIGH" if any(m["severity"] == "HIGH" for m in mismatches) else ("MEDIUM" if mismatches else "NONE"),
            "sql_nullability": sql_nullability,
            "snow_nullability": snow_nullability,
            "mismatches": mismatches,
            "mismatch_count": len(mismatches)
        }
    except Exception as e:
        return {
            "status": "ERROR",
            "severity": "HIGH",
            "message": f"Failed to validate schema nullability: {str(e)}"
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
            name = col["name"]
            sql_null = col["nullable"]
            snow_col = next((c for c in snow_columns.get(table, []) if c["name"] == name), None)

            if snow_col is None:
                table_res.append({
                    "column": name,
                    "sql_nullable": sql_null,
                    "snow_nullable": None,
                    "match": False,
                    "severity": "HIGH"
                })
                continue

            match = sql_null == snow_col["nullable"]

            table_res.append({
                "column": name,
                "sql_nullable": sql_null,
                "snow_nullable": snow_col["nullable"],
                "match": match,
                "severity": "NONE" if match else "MEDIUM"
            })

        results[table] = table_res

    return {
        "status": "PASS" if all(all(r["match"] for r in res) for res in results.values()) else "FAIL",
        "severity": "HIGH" if any(any(r["severity"] == "HIGH" for r in res) for res in results.values()) else "NONE",
        "results": results
    }