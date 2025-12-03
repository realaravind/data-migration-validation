# src/ombudsman/validation/timeseries/validate_period_over_period.py
'''
WoW / MoM / YoY comparisons.
'''
from datetime import timedelta, date, datetime
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_period_over_period(sql_conn, snow_conn, table, metric_col, date_col, mapping):
    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    q = lambda tbl: f"""
        SELECT {date_col}, {metric_col}
        FROM {tbl}
        ORDER BY {date_col}
    """

    try:
        sql = sql_conn.fetch_many(q(sql_table))
        snow = snow_conn.fetch_many(q(snow_table))
    except Exception as e:
        return {
            "status": "ERROR",
            "severity": "HIGH",
            "issues": [],
            "error": f"Failed to fetch data: {str(e)}"
        }

    # Helper to safely convert dates and values to JSON-serializable formats
    def safe_convert_date(d):
        if d is None:
            return None
        if isinstance(d, datetime):
            return d.date().isoformat()
        if isinstance(d, date):
            return d.isoformat()
        # If it's already a string, try to parse and re-format
        if isinstance(d, str):
            return d
        # Fallback - convert to string
        return str(d)

    def safe_convert_value(v):
        if v is None:
            return 0.0
        try:
            return float(v)
        except (TypeError, ValueError):
            return 0.0

    # Convert dates to strings for dictionary keys and values to floats (JSON serializable)
    try:
        sql_map = {}
        for d, v in sql:
            date_key = safe_convert_date(d)
            if date_key:
                sql_map[date_key] = safe_convert_value(v)

        snow_map = {}
        for d, v in snow:
            date_key = safe_convert_date(d)
            if date_key:
                snow_map[date_key] = safe_convert_value(v)
    except Exception as e:
        return {
            "status": "ERROR",
            "severity": "HIGH",
            "issues": [],
            "error": f"Failed to convert dates: {str(e)}"
        }

    issues = []

    offsets = {
        "wow": 7,
        "mom": 30,
        "yoy": 365
    }

    for label, offset in offsets.items():
        for d_str in sql_map:
            # Parse string back to date to calculate offset
            try:
                from datetime import datetime as dt
                # Handle different date formats
                if isinstance(d_str, str):
                    if 'T' in d_str:
                        d = dt.fromisoformat(d_str[:10]).date()
                    else:
                        d = dt.fromisoformat(d_str).date()
                elif isinstance(d_str, date):
                    d = d_str
                elif isinstance(d_str, datetime):
                    d = d_str.date()
                else:
                    continue  # Skip if we can't parse

                prev = d - timedelta(days=offset)
                prev_str = prev.isoformat()
            except Exception as e:
                # Log the error but continue
                print(f"[DEBUG] Failed to parse date '{d_str}': {e}")
                continue  # Skip if date parsing fails

            # Check if both current date and previous date exist in both maps
            if d_str in sql_map and d_str in snow_map and prev_str in sql_map and prev_str in snow_map:
                # Values are already floats from safe_convert_value
                sql_delta = sql_map[d_str] - sql_map[prev_str]
                snow_delta = snow_map[d_str] - snow_map[prev_str]

                if abs(sql_delta - snow_delta) > 0.01:
                    issues.append({
                        "period": label,
                        "date": d_str,  # Already a string from safe_convert_date
                        "sql_delta": round(sql_delta, 2),
                        "snow_delta": round(snow_delta, 2),
                        "difference": round(abs(sql_delta - snow_delta), 2)
                    })

    return {
        "status": "FAIL" if issues else "PASS",
        "severity": "LOW" if issues else "NONE",
        "issues": issues
    }