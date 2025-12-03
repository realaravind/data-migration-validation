# src/ombudsman/validation/metrics/validate_metric_sums.py
'''
Validate that the sum of metrics is the same in both systems.
Supports optional date dimension for time-based grouping.
'''
from decimal import Decimal
from datetime import date, datetime
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_metric_sums(sql_conn, snow_conn, table, metric_cols, mapping, date_col=None, group_by=None):
    """
    Validate metric sums with optional time-based grouping.

    Args:
        sql_conn: SQL Server connection
        snow_conn: Snowflake connection
        table: Table name
        metric_cols: List of metric columns to validate
        mapping: Table mapping
        date_col: Optional date column for time-based grouping
        group_by: Optional grouping level: 'day', 'week', 'month', 'year', 'quarter'
    """
    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    issues = []

    # If no date column, do overall sum (original behavior)
    if not date_col:
        for col in metric_cols:
            sql_sum = sql_conn.fetch_one(f"SELECT SUM({col}) FROM {sql_table}")
            snow_sum = snow_conn.fetch_one(f"SELECT SUM({col}) FROM {snow_table}")

            # Convert Decimal to float for JSON serialization
            sql_sum_val = float(sql_sum) if sql_sum is not None else 0
            snow_sum_val = float(snow_sum) if snow_sum is not None else 0

            if abs(sql_sum_val - snow_sum_val) > 0.01:
                issues.append({
                    "column": col,
                    "sql_sum": sql_sum_val,
                    "snow_sum": snow_sum_val,
                    "difference": abs(sql_sum_val - snow_sum_val)
                })
    else:
        # Time-based grouping
        group_by = group_by or 'day'  # Default to daily

        # Build GROUP BY expression based on level
        if group_by == 'day':
            sql_group_expr = f"CAST({date_col} AS DATE)"
            snow_group_expr = f"DATE({date_col})"
        elif group_by == 'week':
            sql_group_expr = f"DATEPART(YEAR, {date_col}), DATEPART(WEEK, {date_col})"
            snow_group_expr = f"YEAR({date_col}), WEEK({date_col})"
        elif group_by == 'month':
            sql_group_expr = f"DATEPART(YEAR, {date_col}), DATEPART(MONTH, {date_col})"
            snow_group_expr = f"YEAR({date_col}), MONTH({date_col})"
        elif group_by == 'quarter':
            sql_group_expr = f"DATEPART(YEAR, {date_col}), DATEPART(QUARTER, {date_col})"
            snow_group_expr = f"YEAR({date_col}), QUARTER({date_col})"
        elif group_by == 'year':
            sql_group_expr = f"DATEPART(YEAR, {date_col})"
            snow_group_expr = f"YEAR({date_col})"
        else:
            sql_group_expr = f"CAST({date_col} AS DATE)"
            snow_group_expr = f"DATE({date_col})"

        for col in metric_cols:
            # Build queries with grouping
            if group_by == 'day':
                sql_query = f"""
                    SELECT {sql_group_expr} as period, SUM({col}) as total
                    FROM {sql_table}
                    GROUP BY {sql_group_expr}
                    ORDER BY period
                """
                snow_query = f"""
                    SELECT {snow_group_expr} as period, SUM({col}) as total
                    FROM {snow_table}
                    GROUP BY {snow_group_expr}
                    ORDER BY period
                """
            else:
                # For week/month/quarter/year, format as string
                sql_query = f"""
                    SELECT {sql_group_expr}, SUM({col}) as total
                    FROM {sql_table}
                    GROUP BY {sql_group_expr}
                    ORDER BY {sql_group_expr}
                """
                snow_query = f"""
                    SELECT {snow_group_expr}, SUM({col}) as total
                    FROM {snow_table}
                    GROUP BY {snow_group_expr}
                    ORDER BY {snow_group_expr}
                """

            try:
                sql_results = sql_conn.fetch_many(sql_query)
                snow_results = snow_conn.fetch_many(snow_query)
            except Exception as e:
                return {
                    "status": "ERROR",
                    "severity": "HIGH",
                    "issues": [],
                    "error": f"Failed to fetch grouped data: {str(e)}"
                }

            # Helper to safely convert dates and values
            def safe_convert_period(p):
                if isinstance(p, (date, datetime)):
                    return p.isoformat()
                return str(p) if p is not None else ""

            def safe_convert_value(v):
                if v is None:
                    return 0.0
                try:
                    return float(v)
                except (TypeError, ValueError):
                    return 0.0

            # Build maps for comparison
            if group_by == 'day':
                sql_map = {safe_convert_period(p): safe_convert_value(v) for p, v in sql_results}
                snow_map = {safe_convert_period(p): safe_convert_value(v) for p, v in snow_results}
            else:
                # Multiple columns for period (year, week/month/quarter)
                sql_map = {}
                for row in sql_results:
                    if len(row) == 3:  # year, period, total
                        key = f"{row[0]}-{row[1]:02d}"
                        sql_map[key] = safe_convert_value(row[2])
                    elif len(row) == 2:  # year only, total
                        key = str(row[0])
                        sql_map[key] = safe_convert_value(row[1])

                snow_map = {}
                for row in snow_results:
                    if len(row) == 3:
                        key = f"{row[0]}-{row[1]:02d}"
                        snow_map[key] = safe_convert_value(row[2])
                    elif len(row) == 2:
                        key = str(row[0])
                        snow_map[key] = safe_convert_value(row[1])

            # Compare periods
            all_periods = set(sql_map.keys()) | set(snow_map.keys())
            for period in sorted(all_periods):
                sql_val = sql_map.get(period, 0.0)
                snow_val = snow_map.get(period, 0.0)

                if abs(sql_val - snow_val) > 0.01:
                    issues.append({
                        "column": col,
                        "period": period,
                        "group_by": group_by,
                        "sql_sum": round(sql_val, 2),
                        "snow_sum": round(snow_val, 2),
                        "difference": round(abs(sql_val - snow_val), 2)
                    })

    # ALWAYS add explain data - regardless of pass/fail
    explain_data = {}
    if issues or not issues:  # Always generate
        try:
            explain_data = {}
            for issue in issues[:5]:  # Limit to first 5 issues for explain
                col = issue["column"]

                # Get sample rows for this column
                sql_samples = sql_conn.fetch_dicts(f"SELECT TOP 20 * FROM {sql_table} ORDER BY {col} DESC")
                snow_samples = snow_conn.fetch_dicts(f"SELECT * FROM {snow_table} ORDER BY {col} DESC LIMIT 20")

                key = f"{col}" if "period" not in issue else f"{col}_{issue['period']}"

                explain_data[key] = {
                    "column": col,
                    "sql_sum": issue.get("sql_sum"),
                    "snow_sum": issue.get("snow_sum"),
                    "difference": issue.get("difference"),
                    "period": issue.get("period") if "period" in issue else "overall",
                    "sql_samples": sql_samples[:20],
                    "snow_samples": snow_samples[:20],
                    "interpretation": f"Sum mismatch in column '{col}': SQL={issue.get('sql_sum', 0)}, Snow={issue.get('snow_sum', 0)}, Difference={issue.get('difference', 0)}",
                    "queries": {
                        "sql_sum": f"SELECT SUM({col}) FROM {sql_table}",
                        "snow_sum": f"SELECT SUM({col}) FROM {snow_table}",
                        "sql_samples": f"SELECT TOP 20 * FROM {sql_table} ORDER BY {col} DESC",
                        "snow_samples": f"SELECT * FROM {snow_table} ORDER BY {col} DESC LIMIT 20"
                    }
                }
        except Exception as e:
            # If explain fails, at least log the error
            pass

    return {
        "status": "FAIL" if issues else "PASS",
        "severity": "HIGH" if issues else "NONE",
        "issues": issues,
        "explain": explain_data
    }