# src/ombudsman/validation/dq/validate_uniqueness.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_uniqueness(sql_conn, snow_conn, table, mapping, metadata):
    keys = metadata[table].get("unique_keys", [])
    if not keys:
        return {"status": "SKIPPED"}

    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    key_expr = ", ".join(keys)

    sql_q = f"""
        SELECT COUNT(*) - COUNT(DISTINCT {key_expr})
        FROM {sql_table}
    """

    snow_q = f"""
        SELECT COUNT(*) - COUNT(DISTINCT {key_expr})
        FROM {snow_table}
    """

    sql_dupes = sql_conn.fetch_one(sql_q)
    snow_dupes = snow_conn.fetch_one(snow_q)

    status = "FAIL" if sql_dupes or snow_dupes else "PASS"

    # ALWAYS collect explain data - show statistics and samples regardless of pass/fail
    explain_data = {}
    try:
        key_group_by = ", ".join(keys)

        # Find duplicates (SQL Server)
        sql_dupe_query = f"""
            SELECT TOP 20 {key_expr}, COUNT(*) as dup_count
            FROM {sql_table}
            GROUP BY {key_group_by}
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
        """

        # Find duplicates (Snowflake)
        snow_dupe_query = f"""
            SELECT {key_expr}, COUNT(*) as dup_count
            FROM {snow_table}
            GROUP BY {key_group_by}
            HAVING COUNT(*) > 1
            ORDER BY COUNT(*) DESC
            LIMIT 20
        """

        sql_dupe_samples = sql_conn.fetch_dicts(sql_dupe_query) if sql_dupes > 0 else []
        snow_dupe_samples = snow_conn.fetch_dicts(snow_dupe_query) if snow_dupes > 0 else []

        # Get sample unique rows for context
        sql_sample_query = f"SELECT TOP 20 * FROM {sql_table}"
        snow_sample_query = f"SELECT * FROM {snow_table} LIMIT 20"
        sql_samples = sql_conn.fetch_dicts(sql_sample_query)
        snow_samples = snow_conn.fetch_dicts(snow_sample_query)

        if status == "PASS":
            interpretation = f"No duplicate rows found in either database based on key(s): {', '.join(keys)}"
        else:
            interpretation = f"Found {sql_dupes} duplicate rows in SQL Server and {snow_dupes} in Snowflake based on key(s): {', '.join(keys)}"

        explain_data = {
            "unique_keys": keys,
            "sql_duplicate_count": sql_dupes,
            "snow_duplicate_count": snow_dupes,
            "sql_duplicate_samples": sql_dupe_samples[:20],
            "snow_duplicate_samples": snow_dupe_samples[:20],
            "sql_samples": sql_samples[:20],
            "snow_samples": snow_samples[:20],
            "interpretation": interpretation,
            "queries": {
                "sql_duplicate_count": f"SELECT COUNT(*) - COUNT(DISTINCT {key_expr}) FROM {sql_table}",
                "snow_duplicate_count": f"SELECT COUNT(*) - COUNT(DISTINCT {key_expr}) FROM {snow_table}",
                "sql_duplicate_samples": sql_dupe_query,
                "snow_duplicate_samples": snow_dupe_query,
                "sql_samples": sql_sample_query,
                "snow_samples": snow_sample_query
            }
        }
    except Exception as e:
        # If explain fails, provide basic info
        if status == "PASS":
            interpretation = f"No duplicate rows found in either database based on key(s): {', '.join(keys)}"
        else:
            interpretation = f"Found {sql_dupes} duplicate rows in SQL Server and {snow_dupes} in Snowflake based on key(s): {', '.join(keys)}"

        explain_data = {
            "unique_keys": keys,
            "sql_duplicate_count": sql_dupes,
            "snow_duplicate_count": snow_dupes,
            "interpretation": interpretation,
            "error": f"Could not fetch duplicate samples: {str(e)}"
        }

    return {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "sql_duplicates": sql_dupes,
        "snow_duplicates": snow_dupes,
        "unique_keys": keys,
        "explain": explain_data
    }