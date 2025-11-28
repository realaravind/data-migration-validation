# src/ombudsman/validation/facts/validate_late_arriving_facts.py

def validate_late_arriving_facts(sql_conn, snow_conn, fact, dim, mapping, metadata):
    sql_fact = mapping[fact]["sql"]
    snow_fact = mapping[fact]["snow"]
    sql_dim = mapping[dim]["sql"]
    snow_dim = mapping[dim]["snow"]

    fk = metadata[fact]["foreign_keys"][dim]["column"]
    bk = metadata[dim]["business_key"]
    eff = metadata[dim]["effective_date"]

    sql_q = f"""
        SELECT f.{fk}, d.{eff}
        FROM {sql_fact} f
        LEFT JOIN {sql_dim} d
        ON f.{fk} = d.{bk}
        WHERE f.transaction_date < d.{eff}
    """

    snow_q = f"""
        SELECT f.{fk}, d.{eff}
        FROM {snow_fact} f
        LEFT JOIN {snow_dim} d
        ON f.{fk} = d.{bk}
        WHERE f.transaction_date < d.{eff}
    """

    sql_issues = sql_conn.fetch_many(sql_q)
    snow_issues = snow_conn.fetch_many(snow_q)

    status = "FAIL" if sql_issues or snow_issues else "PASS"

    return {
        "status": status,
        "severity": "MEDIUM" if status == "FAIL" else "NONE",
        "sql_late_facts": sql_issues,
        "snow_late_facts": snow_issues
    }