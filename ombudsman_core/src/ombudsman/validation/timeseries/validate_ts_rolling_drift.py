# src/ombudsman/validation/timeseries/validate_ts_rolling_drift.py
'''
Rolling 7‑day and 30‑day window drift.

'''
from datetime import date, datetime
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier


def validate_ts_rolling_drift(sql_conn, snow_conn, table, metric_col, date_col, mapping):
    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    q_tmpl = lambda tbl, win: f"""
        SELECT
            {date_col},
            AVG({metric_col}) OVER (
                ORDER BY {date_col}
                ROWS BETWEEN {win} PRECEDING AND CURRENT ROW
            )
        FROM {tbl}
        ORDER BY {date_col}
    """

    windows = [7, 30]
    issues = []

    for win in windows:
        sql_vals = sql_conn.fetch_many(q_tmpl(sql_table, win))
        snow_vals = snow_conn.fetch_many(q_tmpl(snow_table, win))

        # Helper to safely convert dates and values
        def safe_convert_date(d):
            if isinstance(d, (date, datetime)):
                return d.isoformat()
            return str(d)

        def safe_convert_value(v):
            if v is None:
                return 0
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0

        # Convert to JSON-serializable format
        sql_map = {safe_convert_date(d): safe_convert_value(v) for d, v in sql_vals}
        snow_map = {safe_convert_date(d): safe_convert_value(v) for d, v in snow_vals}

        for d_str in sql_map:
            if d_str in snow_map:
                sql_val = sql_map[d_str]
                snow_val = snow_map[d_str]

                if abs(sql_val - snow_val) > 0.01:
                    issues.append({
                        "date": d_str,  # Already a string
                        "window": win,
                        "sql_value": round(sql_val, 2),
                        "snow_value": round(snow_val, 2),
                        "difference": round(abs(sql_val - snow_val), 2)
                    })

    return {
        "status": "FAIL" if issues else "PASS",
        "severity": "LOW" if issues else "NONE",
        "issues": issues
    }