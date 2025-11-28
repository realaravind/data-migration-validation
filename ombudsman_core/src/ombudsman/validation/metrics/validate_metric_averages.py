# src/ombudsman/validation/metrics/validate_metric_averages.py

def validate_metric_averages(sql_conn, snow_conn, table, metric_cols, mapping):
    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    issues = []

    for col in metric_cols:
        sql_avg = sql_conn.fetch_one(f"SELECT AVG({col}) FROM {sql_table}")
        snow_avg = snow_conn.fetch_one(f"SELECT AVG({col}) FROM {snow_table}")

        if sql_avg is None or snow_avg is None:
            continue

        if abs(sql_avg - snow_avg) > 0.01:
            issues.append({
                "column": col,
                "sql_avg": sql_avg,
                "snow_avg": snow_avg
            })

    return {
        "status": "FAIL" if issues else "PASS",
        "severity": "MEDIUM" if issues else "NONE",
        "issues": issues
    }