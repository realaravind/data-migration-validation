# src/ombudsman/validation/dq/validate_uniqueness.py

def validate_uniqueness(sql_conn, snow_conn, table, mapping, metadata):
    keys = metadata[table].get("unique_keys", [])
    if not keys:
        return {"status": "SKIPPED"}

    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    key_expr = ", ".join(keys)

    sql_q = f"""
        SELECT COUNT(*) - COUNT(DISTINCT {key_expr})
        FROM {sql_table}
    """

    snow_q = f"""
        SELECT COUNT(*) - COUNT(DISTINCT {key_expr})
        FROM {snow_table}
    """

    sql_dupes = sql_conn.fetch_one(sql_q)
    snow_dupes = snow_conn.fetch_one(snow_q)

    status = "FAIL" if sql_dupes or snow_dupes else "PASS"

    return {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "sql_duplicates": sql_dupes,
        "snow_duplicates": snow_dupes
    }