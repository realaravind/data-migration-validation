import yaml

def validate_rules(sql_conn, snow_conn, rules_file):
    rules = yaml.safe_load(open(rules_file))["validations"]
    results = []

    for r in rules:
        if r["type"] != "rule":
            continue

        sql_rows = sql_conn.fetch_many(r["query"])
        snow_rows = snow_conn.fetch_many(r["query"])

        ok = (len(sql_rows) == 0 and len(snow_rows) == 0)

        results.append({
            "name": r["name"],
            "violations_sql": len(sql_rows),
            "violations_snow": len(snow_rows),
            "ok": ok
        })

    return results