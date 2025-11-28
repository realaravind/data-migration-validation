# src/ombudsman/validation/metrics/validate_ratios.py

def validate_ratios(sql_conn, snow_conn, table, ratio_defs, mapping):
    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    issues = []

    for name, (num, den) in ratio_defs.items():
        sql_ratio = sql_conn.fetch_one(
            f"SELECT SUM({num}) / NULLIF(SUM({den}), 0) FROM {sql_table}"
        )

        snow_ratio = snow_conn.fetch_one(
            f"SELECT SUM({num}) / NULLIF(SUM({den}), 0) FROM {snow_table}"
        )

        if sql_ratio is None or snow_ratio is None:
            continue

        if abs(sql_ratio - snow_ratio) > 0.001:
            issues.append({
                "ratio": name,
                "sql_ratio": sql_ratio,
                "snow_ratio": snow_ratio
            })

    return {
        "status": "FAIL" if issues else "PASS",
        "severity": "MEDIUM" if issues else "NONE",
        "issues": issues
    }