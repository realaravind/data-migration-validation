# src/ombudsman/validation/dq/validate_record_counts.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_record_counts(sql_conn, snow_conn, table, mapping, metadata=None):
    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    sql_cnt = sql_conn.fetch_one(f"SELECT COUNT(*) FROM {sql_table}")
    snow_cnt = snow_conn.fetch_one(f"SELECT COUNT(*) FROM {snow_table}")

    status = "FAIL" if sql_cnt != snow_cnt else "PASS"

    result = {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "sql_count": sql_cnt,
        "snow_count": snow_cnt
    }

    # ALWAYS add explain data - show sample rows regardless of pass/fail
    explain_data = {}

    # Get sample rows from both databases (top 20 rows)
    try:
        sql_samples = sql_conn.fetch_dicts(f"SELECT TOP 20 * FROM {sql_table}")
        snow_samples = snow_conn.fetch_dicts(f"SELECT * FROM {snow_table} LIMIT 20")

        explain_data["sql_samples"] = sql_samples[:20]
        explain_data["snow_samples"] = snow_samples[:20]
        explain_data["sql_count"] = sql_cnt
        explain_data["snow_count"] = snow_cnt
        explain_data["difference"] = abs(sql_cnt - snow_cnt)

        if status == "PASS":
            explain_data["interpretation"] = f"Record counts match: {sql_cnt} rows in both SQL Server and Snowflake"
        elif sql_cnt > snow_cnt:
            explain_data["interpretation"] = f"SQL Server has {abs(sql_cnt - snow_cnt)} more rows than Snowflake (SQL: {sql_cnt}, Snow: {snow_cnt})"
        else:
            explain_data["interpretation"] = f"Snowflake has {abs(sql_cnt - snow_cnt)} more rows than SQL Server (SQL: {sql_cnt}, Snow: {snow_cnt})"

        explain_data["queries"] = {
            "sql_count": f"SELECT COUNT(*) FROM {sql_table}",
            "snow_count": f"SELECT COUNT(*) FROM {snow_table}",
            "sql_samples": f"SELECT TOP 20 * FROM {sql_table}",
            "snow_samples": f"SELECT * FROM {snow_table} LIMIT 20"
        }

        result["explain"] = explain_data
    except Exception as e:
        # If sample query fails, provide basic explain
        explain_data["sql_count"] = sql_cnt
        explain_data["snow_count"] = snow_cnt
        explain_data["difference"] = abs(sql_cnt - snow_cnt)

        if status == "PASS":
            explain_data["interpretation"] = f"Record counts match: {sql_cnt} rows in both SQL Server and Snowflake"
        elif sql_cnt > snow_cnt:
            explain_data["interpretation"] = f"SQL Server has {abs(sql_cnt - snow_cnt)} more rows than Snowflake"
        else:
            explain_data["interpretation"] = f"Snowflake has {abs(sql_cnt - snow_cnt)} more rows than SQL Server"

        explain_data["error"] = f"Could not fetch sample data: {str(e)}"
        result["explain"] = explain_data

    return result