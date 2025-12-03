# src/ombudsman/validation/dq/validate_domain_values.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_domain_values(sql_conn, snow_conn, table, mapping, metadata):
    domains = metadata[table].get("domain_values", {})
    if not domains:
        return {"status": "SKIPPED"}

    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    violations = []
    explain_data = {}

    for col, allowed in domains.items():
        allowed_str = ", ".join([f"'{v}'" for v in allowed])

        sql_q = f"""
            SELECT DISTINCT [{col}]
            FROM {sql_table}
            WHERE [{col}] NOT IN ({allowed_str})
        """

        snow_q = f"""
            SELECT DISTINCT {col}
            FROM {snow_table}
            WHERE {col} NOT IN ({allowed_str})
        """

        sql_bad = [v[0] for v in sql_conn.fetch_many(sql_q)]
        snow_bad = [v[0] for v in snow_conn.fetch_many(snow_q)]

        has_violations = sql_bad or snow_bad

        if has_violations:
            violations.append({
                "column": col,
                "allowed_values": list(allowed),
                "sql_invalid_values": sql_bad,
                "snow_invalid_values": snow_bad,
                "sql_invalid_count": len(sql_bad),
                "snow_invalid_count": len(snow_bad)
            })

        # ALWAYS collect explain data - show sample rows and value distributions regardless of pass/fail
        try:
            sql_invalid_samples = []
            snow_invalid_samples = []

            if sql_bad:
                sql_invalid_samples = sql_conn.fetch_dicts(
                    f"SELECT TOP 20 * FROM {sql_table} WHERE [{col}] NOT IN ({allowed_str})"
                )

            if snow_bad:
                snow_invalid_samples = snow_conn.fetch_dicts(
                    f"SELECT * FROM {snow_table} WHERE {col} NOT IN ({allowed_str}) LIMIT 20"
                )

            # Also get count of rows with each invalid value
            sql_value_counts = []
            snow_value_counts = []

            if sql_bad:
                sql_value_counts = sql_conn.fetch_dicts(
                    f"SELECT [{col}], COUNT(*) as count FROM {sql_table} WHERE [{col}] NOT IN ({allowed_str}) GROUP BY [{col}] ORDER BY COUNT(*) DESC"
                )

            if snow_bad:
                snow_value_counts = snow_conn.fetch_dicts(
                    f"SELECT {col}, COUNT(*) as count FROM {snow_table} WHERE {col} NOT IN ({allowed_str}) GROUP BY {col} ORDER BY COUNT(*) DESC"
                )

            # Get all value distributions for context
            sql_all_values = sql_conn.fetch_dicts(f"SELECT [{col}], COUNT(*) as count FROM {sql_table} GROUP BY [{col}] ORDER BY COUNT(*) DESC")
            snow_all_values = snow_conn.fetch_dicts(f"SELECT {col}, COUNT(*) as count FROM {snow_table} GROUP BY {col} ORDER BY COUNT(*) DESC")

            if has_violations:
                interpretation = f"Column '{col}' has {len(sql_bad)} invalid values in SQL Server and {len(snow_bad)} in Snowflake. Allowed values: {', '.join([str(v) for v in allowed])}"
            else:
                interpretation = f"Column '{col}' validation passed: all values are within the allowed set: {', '.join([str(v) for v in allowed])}"

            explain_data[col] = {
                "allowed_values": list(allowed),
                "sql_invalid_values": sql_bad,
                "snow_invalid_values": snow_bad,
                "sql_invalid_samples": sql_invalid_samples[:20],
                "snow_invalid_samples": snow_invalid_samples[:20],
                "sql_value_counts": sql_value_counts,
                "snow_value_counts": snow_value_counts,
                "sql_all_values": sql_all_values[:20],
                "snow_all_values": snow_all_values[:20],
                "interpretation": interpretation,
                "queries": {
                    "sql_invalid_values": f"SELECT DISTINCT [{col}] FROM {sql_table} WHERE [{col}] NOT IN ({allowed_str})",
                    "snow_invalid_values": f"SELECT DISTINCT {col} FROM {snow_table} WHERE {col} NOT IN ({allowed_str})",
                    "sql_invalid_samples": f"SELECT TOP 20 * FROM {sql_table} WHERE [{col}] NOT IN ({allowed_str})",
                    "snow_invalid_samples": f"SELECT * FROM {snow_table} WHERE {col} NOT IN ({allowed_str}) LIMIT 20",
                    "sql_all_values": f"SELECT [{col}], COUNT(*) as count FROM {sql_table} GROUP BY [{col}] ORDER BY COUNT(*) DESC",
                    "snow_all_values": f"SELECT {col}, COUNT(*) as count FROM {snow_table} GROUP BY {col} ORDER BY COUNT(*) DESC"
                }
            }
        except Exception as e:
            # If explain fails, provide basic info
            if has_violations:
                interpretation = f"Column '{col}' has {len(sql_bad)} invalid values in SQL Server and {len(snow_bad)} in Snowflake. Allowed values: {', '.join([str(v) for v in allowed])}"
            else:
                interpretation = f"Column '{col}' validation passed: all values are within the allowed set: {', '.join([str(v) for v in allowed])}"

            explain_data[col] = {
                "allowed_values": list(allowed),
                "sql_invalid_values": sql_bad,
                "snow_invalid_values": snow_bad,
                "interpretation": interpretation,
                "error": f"Could not fetch detailed samples: {str(e)}"
            }

    status = "FAIL" if violations else "PASS"

    return {
        "status": status,
        "severity": "MEDIUM" if status == "FAIL" else "NONE",
        "violations": violations,
        "explain": explain_data  # Always include explain data
    }