# src/ombudsman/validation/dq/validate_domain_values.py

def validate_domain_values(sql_conn, snow_conn, table, mapping, metadata):
    domains = metadata[table].get("domain_values", {})
    if not domains:
        return {"status": "SKIPPED"}

    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    violations = []

    for col, allowed in domains.items():
        allowed_str = ", ".join([f"'{v}'" for v in allowed])

        sql_q = f"""
            SELECT DISTINCT {col}
            FROM {sql_table}
            WHERE {col} NOT IN ({allowed_str})
        """

        snow_q = f"""
            SELECT DISTINCT {col}
            FROM {snow_table}
            WHERE {col} NOT IN ({allowed_str})
        """

        sql_bad = [v[0] for v in sql_conn.fetch_many(sql_q)]
        snow_bad = [v[0] for v in snow_conn.fetch_many(snow_q)]

        if sql_bad or snow_bad:
            violations.append({
                "column": col,
                "sql_invalid": sql_bad,
                "snow_invalid": snow_bad
            })

    status = "FAIL" if violations else "PASS"

    return {
        "status": status,
        "severity": "MEDIUM" if status == "FAIL" else "NONE",
        "violations": violations
    }