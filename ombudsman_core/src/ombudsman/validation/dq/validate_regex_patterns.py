# src/ombudsman/validation/dq/validate_regex_patterns.py
'''
Validates column format such as:

email
phone
SKU format
ID format


'''


def validate_regex_patterns(sql_conn, snow_conn, table, mapping, metadata):
    patterns = metadata[table].get("regex_patterns", {})
    if not patterns:
        return {"status": "SKIPPED"}

    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    violations = []

    for col, regex in patterns.items():
        sql_q = f"""
            SELECT {col}
            FROM {sql_table}
            WHERE {col} NOT REGEXP '{regex}'
        """

        snow_q = f"""
            SELECT {col}
            FROM {snow_table}
            WHERE {col} NOT REGEXP '{regex}'
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