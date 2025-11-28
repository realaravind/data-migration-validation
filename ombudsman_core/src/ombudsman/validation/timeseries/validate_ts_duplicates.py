# src/ombudsman/validation/timeseries/validate_ts_duplicates.py
'''
Timestamp uniqueness within grain (e.g., date + customer_id).


'''
def validate_ts_duplicates(conn, table, keys):
    key_expr = ", ".join(keys)

    q = f"""
        SELECT {key_expr}, COUNT(*)
        FROM {table}
        GROUP BY {key_expr}
        HAVING COUNT(*) > 1
    """

    dups = conn.fetch_many(q)

    return {
        "status": "FAIL" if dups else "PASS",
        "severity": "HIGH" if dups else "NONE",
        "duplicates": dups
    }