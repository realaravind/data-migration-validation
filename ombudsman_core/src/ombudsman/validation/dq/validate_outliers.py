# src/ombudsman/validation/dq/validate_outliers.py
'''
(Z-score or IQR)
Detects outliers in numeric columns between SQL Server and Snowflake.
'''

import numpy as np
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_outliers(sql_conn, snow_conn, table, mapping, metadata):
    numerics = metadata[table].get("numeric_columns", [])
    if not numerics:
        return {"status": "SKIPPED"}

    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    issues = []
    details = []
    explain_data = {}  # ALWAYS generate explain data

    for col in numerics:
        sql_vals = np.array([r[0] for r in sql_conn.fetch_many(f"SELECT [{col}] FROM {sql_table}") if r[0] is not None])
        snow_vals = np.array([r[0] for r in snow_conn.fetch_many(f"SELECT {col} FROM {snow_table}") if r[0] is not None])

        if len(sql_vals) < 3 or len(snow_vals) < 3:
            continue

        sql_z = np.abs((sql_vals - sql_vals.mean()) / sql_vals.std())
        snow_z = np.abs((snow_vals - snow_vals.mean()) / snow_vals.std())

        sql_out = sql_vals[sql_z > 3].tolist()
        snow_out = snow_vals[snow_z > 3].tolist()

        result = {
            "column": col,
            "sql_server_outlier_count": len(sql_out),
            "snowflake_outlier_count": len(snow_out),
            "total_outliers": len(sql_out) + len(snow_out),
            "sql_server_outliers": ", ".join([str(round(float(x), 2)) for x in sql_out[:10]]) + (f" ... and {len(sql_out)-10} more" if len(sql_out) > 10 else ""),
            "snowflake_outliers": ", ".join([str(round(float(x), 2)) for x in snow_out[:10]]) + (f" ... and {len(snow_out)-10} more" if len(snow_out) > 10 else ""),
        }

        details.append(result)

        if sql_out or snow_out:
            issues.append(result)

        # ALWAYS collect explain data - show statistics regardless of pass/fail
        try:
            sql_outlier_rows = []
            snow_outlier_rows = []

            # Get full rows for outliers (limit to first 10)
            if sql_out:
                outlier_values = ", ".join([str(round(float(x), 2)) for x in sql_out[:10]])
                sql_outlier_rows = sql_conn.fetch_dicts(
                    f"SELECT TOP 10 * FROM {sql_table} WHERE [{col}] IN ({outlier_values})"
                )

            if snow_out:
                outlier_values = ", ".join([str(round(float(x), 2)) for x in snow_out[:10]])
                snow_outlier_rows = snow_conn.fetch_dicts(
                    f"SELECT * FROM {snow_table} WHERE {col} IN ({outlier_values}) LIMIT 10"
                )

            if sql_out or snow_out:
                interpretation = f"Found {len(sql_out)} outliers in SQL Server and {len(snow_out)} in Snowflake. Outliers are values more than 3 standard deviations from the mean. SQL: mean={round(float(sql_vals.mean()), 2)}, std={round(float(sql_vals.std()), 2)}. Snow: mean={round(float(snow_vals.mean()), 2)}, std={round(float(snow_vals.std()), 2)}"
            else:
                interpretation = f"No outliers found in either database. SQL: mean={round(float(sql_vals.mean()), 2)}, std={round(float(sql_vals.std()), 2)}. Snow: mean={round(float(snow_vals.mean()), 2)}, std={round(float(snow_vals.std()), 2)}"

            explain_data[col] = {
                "column": col,
                "sql_mean": round(float(sql_vals.mean()), 2),
                "sql_std": round(float(sql_vals.std()), 2),
                "snow_mean": round(float(snow_vals.mean()), 2),
                "snow_std": round(float(snow_vals.std()), 2),
                "sql_outlier_count": len(sql_out),
                "snow_outlier_count": len(snow_out),
                "sql_outlier_rows": sql_outlier_rows,
                "snow_outlier_rows": snow_outlier_rows,
                "interpretation": interpretation,
                "queries": {
                    "sql_outliers": f"SELECT * FROM {sql_table} WHERE ABS([{col}] - (SELECT AVG([{col}]) FROM {sql_table})) / (SELECT STDEV([{col}]) FROM {sql_table}) > 3",
                    "snow_outliers": f"SELECT * FROM {snow_table} WHERE ABS({col} - (SELECT AVG({col}) FROM {snow_table})) / (SELECT STDDEV({col}) FROM {snow_table}) > 3"
                }
            }
        except:
            # Fallback if queries fail
            if sql_out or snow_out:
                interpretation = f"Found {len(sql_out)} outliers in SQL Server and {len(snow_out)} in Snowflake"
            else:
                interpretation = f"No outliers found in either database"

            explain_data[col] = {
                "column": col,
                "sql_outlier_count": len(sql_out),
                "snow_outlier_count": len(snow_out),
                "interpretation": interpretation,
                "error": "Could not fetch detailed outlier rows"
            }

    status = "FAIL" if issues else "PASS"

    return {
        "status": status,
        "severity": "LOW" if status == "FAIL" else "NONE",
        "issues": issues,
        "details": details,
        "explain": explain_data  # Always include explain data
    }