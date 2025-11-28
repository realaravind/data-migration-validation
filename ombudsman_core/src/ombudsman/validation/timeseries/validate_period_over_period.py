# src/ombudsman/validation/timeseries/validate_period_over_period.py
'''
WoW / MoM / YoY comparisons.
'''

def validate_period_over_period(sql_conn, snow_conn, table, metric_col, date_col, mapping):
    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    q = lambda tbl: f"""
        SELECT {date_col}, {metric_col}
        FROM {tbl}
        ORDER BY {date_col}
    """

    sql = sql_conn.fetch_many(q(sql_table))
    snow = snow_conn.fetch_many(q(snow_table))

    sql_map = {d: v for d, v in sql}
    snow_map = {d: v for d, v in snow}

    issues = []

    offsets = {
        "wow": 7,
        "mom": 30,
        "yoy": 365
    }

    for label, offset in offsets.items():
        for d in sql_map:
            prev = d - timedelta(days=offset)
            if prev in sql_map and prev in snow_map:
                sql_delta = sql_map[d] - sql_map[prev]
                snow_delta = snow_map[d] - snow_map[prev]

                if abs(sql_delta - snow_delta) > 0.01:
                    issues.append({
                        "period": label,
                        "date": d,
                        "sql_delta": sql_delta,
                        "snow_delta": snow_delta
                    })

    return {
        "status": "FAIL" if issues else "PASS",
        "severity": "LOW" if issues else "NONE",
        "issues": issues
    }