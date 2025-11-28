# src/ombudsman/validation/metrics/validate_metric_sums.py
'''
Validate that the sum of metrics is the same in both systems.
'''
def validate_metric_sums(sql_conn, snow_conn, table, metric_cols, mapping):
    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    issues = []

    for col in metric_cols:
        sql_sum = sql_conn.fetch_one(f"SELECT SUM({col}) FROM {sql_table}")
        snow_sum = snow_conn.fetch_one(f"SELECT SUM({col}) FROM {snow_table}")

        if abs((sql_sum or 0) - (snow_sum or 0)) > 0.01:
            issues.append({
                "column": col,
                "sql_sum": sql_sum,
                "snow_sum": snow_sum
            })

    return {
        "status": "FAIL" if issues else "PASS",
        "severity": "HIGH" if issues else "NONE",
        "issues": issues
    }