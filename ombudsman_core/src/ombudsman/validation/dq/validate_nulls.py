# src/ombudsman/validation/dq/validate_nulls.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_nulls(sql_conn, snow_conn, table, mapping, metadata):
    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    cols = metadata[table]["columns"]

    results = []
    issues = []
    explain_data = {}

    for col in cols:
        sql_q = f"SELECT COUNT(*) FROM {sql_table} WHERE [{col}] IS NULL"
        snow_q = f"SELECT COUNT(*) FROM {snow_table} WHERE {col} IS NULL"

        sql_nulls = sql_conn.fetch_one(sql_q)
        snow_nulls = snow_conn.fetch_one(snow_q)

        match = sql_nulls == snow_nulls

        results.append({
            "column": col,
            "sql_nulls": sql_nulls,
            "snow_nulls": snow_nulls,
            "difference": abs(sql_nulls - snow_nulls) if sql_nulls and snow_nulls else 0,
            "match": match,
            "severity": "HIGH" if not match else "NONE"
        })

        if not match:
            issues.append({
                "column": col,
                "sql_nulls": sql_nulls,
                "snow_nulls": snow_nulls,
                "difference": abs(sql_nulls - snow_nulls)
            })

        # ALWAYS collect explain data - show sample NULL rows regardless of pass/fail
        try:
            sql_null_samples = sql_conn.fetch_dicts(f"SELECT TOP 20 * FROM {sql_table} WHERE [{col}] IS NULL")
            snow_null_samples = snow_conn.fetch_dicts(f"SELECT * FROM {snow_table} WHERE {col} IS NULL LIMIT 20")

            # Also get sample non-NULL rows for context
            sql_non_null_samples = sql_conn.fetch_dicts(f"SELECT TOP 10 * FROM {sql_table} WHERE [{col}] IS NOT NULL")
            snow_non_null_samples = snow_conn.fetch_dicts(f"SELECT * FROM {snow_table} WHERE {col} IS NOT NULL LIMIT 10")

            if match:
                interpretation = f"Column '{col}' NULL counts match: {sql_nulls} NULLs in both SQL Server and Snowflake"
            else:
                interpretation = f"Column '{col}' has {sql_nulls} NULLs in SQL Server vs {snow_nulls} NULLs in Snowflake (difference: {abs(sql_nulls - snow_nulls)})"

            explain_data[col] = {
                "sql_null_count": sql_nulls,
                "snow_null_count": snow_nulls,
                "sql_null_samples": sql_null_samples[:20],
                "snow_null_samples": snow_null_samples[:20],
                "sql_non_null_samples": sql_non_null_samples[:10],
                "snow_non_null_samples": snow_non_null_samples[:10],
                "interpretation": interpretation,
                "queries": {
                    "sql_null_count": f"SELECT COUNT(*) FROM {sql_table} WHERE [{col}] IS NULL",
                    "snow_null_count": f"SELECT COUNT(*) FROM {snow_table} WHERE {col} IS NULL",
                    "sql_null_samples": f"SELECT TOP 20 * FROM {sql_table} WHERE [{col}] IS NULL",
                    "snow_null_samples": f"SELECT * FROM {snow_table} WHERE {col} IS NULL LIMIT 20"
                }
            }
        except Exception as e:
            # If explain fails, provide basic info
            if match:
                interpretation = f"Column '{col}' NULL counts match: {sql_nulls} NULLs in both SQL Server and Snowflake"
            else:
                interpretation = f"Column '{col}' has {sql_nulls} NULLs in SQL Server vs {snow_nulls} NULLs in Snowflake (difference: {abs(sql_nulls - snow_nulls)})"

            explain_data[col] = {
                "sql_null_count": sql_nulls,
                "snow_null_count": snow_nulls,
                "interpretation": interpretation,
                "error": f"Could not fetch sample data: {str(e)}"
            }

    return {
        "status": "FAIL" if any(not r["match"] for r in results) else "PASS",
        "severity": "HIGH" if issues else "NONE",
        "results": results,
        "issues": issues,
        "explain": explain_data  # Always include explain data
    }