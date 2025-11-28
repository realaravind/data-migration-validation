import yaml

def validate_metrics(sql_conn, snow_conn, rules_file):
    rules = yaml.safe_load(open(rules_file))["validations"]
    results = []

    for r in rules:
        if r["type"] != "metric":
            continue

        sql_val = sql_conn.fetch_one(r["sql_server_query"])
        snow_val = snow_conn.fetch_one(r["snowflake_query"])

        ok = abs(sql_val - snow_val) <= max(
            r.get("tolerance_abs", 0),
            abs(sql_val) * r.get("tolerance_pct", 0) / 100
        )

        results.append({
            "name": r["name"],
            "sql": sql_val,
            "snow": snow_val,
            "ok": ok
        })

    return results