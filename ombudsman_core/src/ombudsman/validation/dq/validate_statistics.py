# src/ombudsman/validation/dq/validate_statistics.py

'''
(Avg / Stddev / Min / Max / Medians / Percentiles)
''' 

from ...core.utils import within_tolerance
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_statistics(sql_conn, snow_conn, table, mapping, metadata):
    numerics = metadata[table].get("numeric_columns", [])
    if not numerics:
        return {"status": "SKIPPED"}

    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    issues = []
    details = []
    explain_data = {}  # ALWAYS generate explain data

    for col in numerics:
        sql_stats = sql_conn.fetch_dicts(f"""
            SELECT
                AVG({col}) AS avg_val,
                STDEV({col}) AS std_val,
                MIN({col}) AS min_val,
                MAX({col}) AS max_val
            FROM {sql_table}
        """)[0]

        snow_stats = snow_conn.fetch_dicts(f"""
            SELECT
                AVG({col}) AS avg_val,
                STDDEV({col}) AS std_val,
                MIN({col}) AS min_val,
                MAX({col}) AS max_val
            FROM {snow_table}
        """)[0]

        col_issues = []

        stat_labels = {
            "avg_val": "Average",
            "std_val": "Std Deviation",
            "min_val": "Minimum",
            "max_val": "Maximum"
        }

        for stat in ["avg_val", "std_val", "min_val", "max_val"]:
            v1 = sql_stats[stat]
            v2 = snow_stats[stat]

            # Convert to float and round for JSON serialization
            sql_val = round(float(v1), 2) if v1 is not None else None
            snow_val = round(float(v2), 2) if v2 is not None else None

            # Calculate difference
            diff = round(abs(sql_val - snow_val), 2) if sql_val is not None and snow_val is not None else None

            match = within_tolerance(v1, v2, abs_tol=0.01, pct_tol=1)

            # Add to flattened details (all statistics with column name)
            details.append({
                "column": col,
                "statistic": stat_labels[stat],
                "sql_value": sql_val,
                "snowflake_value": snow_val,
                "difference": diff,
                "match": match
            })

            # Add to issues (only mismatches)
            if not match:
                col_issues.append({
                    "column": col,
                    "statistic": stat_labels[stat],
                    "sql_value": sql_val,
                    "snowflake_value": snow_val,
                    "difference": diff
                })

        if col_issues:
            issues.extend(col_issues)

        # ALWAYS collect explain data - for all columns regardless of pass/fail
        # Get sample rows showing actual values (use database-specific syntax)
        sql_samples = sql_conn.fetch_dicts(f"SELECT TOP 20 * FROM {sql_table} ORDER BY {col}")
        snow_samples = snow_conn.fetch_dicts(f"SELECT * FROM {snow_table} ORDER BY {col} LIMIT 20")

        # Get value distribution (create buckets) - use database-specific syntax
        sql_dist_query = f"""
            SELECT
                CASE
                    WHEN {col} < (SELECT AVG({col}) - STDEV({col}) FROM {sql_table}) THEN 'Low'
                    WHEN {col} > (SELECT AVG({col}) + STDEV({col}) FROM {sql_table}) THEN 'High'
                    ELSE 'Normal'
                END as bucket,
                COUNT(*) as count
            FROM {sql_table}
            WHERE {col} IS NOT NULL
            GROUP BY CASE
                    WHEN {col} < (SELECT AVG({col}) - STDEV({col}) FROM {sql_table}) THEN 'Low'
                    WHEN {col} > (SELECT AVG({col}) + STDEV({col}) FROM {sql_table}) THEN 'High'
                    ELSE 'Normal'
                END
        """

        snow_dist_query = f"""
            SELECT
                CASE
                    WHEN {col} < (SELECT AVG({col}) - STDDEV({col}) FROM {snow_table}) THEN 'Low'
                    WHEN {col} > (SELECT AVG({col}) + STDDEV({col}) FROM {snow_table}) THEN 'High'
                    ELSE 'Normal'
                END as bucket,
                COUNT(*) as count
            FROM {snow_table}
            WHERE {col} IS NOT NULL
            GROUP BY bucket
        """

        try:
            sql_dist = sql_conn.fetch_dicts(sql_dist_query)
            snow_dist = snow_conn.fetch_dicts(snow_dist_query)
        except:
            sql_dist = []
            snow_dist = []

        if col_issues:
            interpretation = f"Statistics mismatch for column '{col}': {len(col_issues)} metric(s) differ between SQL Server and Snowflake"
        else:
            interpretation = f"Statistics match for column '{col}': all metrics are consistent between SQL Server and Snowflake"

        explain_data[col] = {
            "sql_samples": sql_samples[:20],
            "snow_samples": snow_samples[:20],
            "sql_distribution": {row['bucket']: row['count'] for row in sql_dist},
            "snow_distribution": {row['bucket']: row['count'] for row in snow_dist},
            "interpretation": interpretation,
            "queries": {
                "sql_statistics": f"SELECT AVG({col}), STDEV({col}), MIN({col}), MAX({col}) FROM {sql_table}",
                "snow_statistics": f"SELECT AVG({col}), STDDEV({col}), MIN({col}), MAX({col}) FROM {snow_table}",
                "sql_samples": f"SELECT TOP 20 * FROM {sql_table} ORDER BY {col}",
                "snow_samples": f"SELECT * FROM {snow_table} ORDER BY {col} LIMIT 20",
                "sql_distribution": sql_dist_query.strip(),
                "snow_distribution": snow_dist_query.strip()
            }
        }

    status = "FAIL" if issues else "PASS"

    return {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "issues": issues,
        "details": details,
        "explain": explain_data  # Always include explain data
    }