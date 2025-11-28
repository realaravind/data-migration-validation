# src/ombudsman/validation/timeseries/validate_ts_rolling_drift.py
'''
Rolling 7‑day and 30‑day window drift.

'''


def validate_ts_rolling_drift(sql_conn, snow_conn, table, metric_col, date_col, mapping):
    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

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

        sql_map = {d: v for d, v in sql_vals}
        snow_map = {d: v for d, v in snow_vals}

        for d in sql_map:
            if d in snow_map:
                if abs((sql_map[d] or 0) - (snow_map[d] or 0)) > 0.01:
                    issues.append({
                        "date": d,
                        "window": win,
                        "sql_value": sql_map[d],
                        "snow_value": snow_map[d]
                    })

    return {
        "status": "FAIL" if issues else "PASS",
        "severity": "LOW" if issues else "NONE",
        "issues": issues
    }