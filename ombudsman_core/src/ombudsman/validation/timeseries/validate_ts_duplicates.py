# src/ombudsman/validation/timeseries/validate_ts_duplicates.py
'''
Timestamp uniqueness within grain (e.g., date + customer_id).


'''
import datetime

def validate_ts_duplicates(conn, table, keys):
    key_expr = ", ".join(keys)

    q = f"""
        SELECT {key_expr}, COUNT(*)
        FROM {table}
        GROUP BY {key_expr}
        HAVING COUNT(*) > 1
    """

    dups = conn.fetch_many(q)

    # Convert Row objects to JSON-serializable format
    def serialize_value(val):
        """Convert value to JSON-serializable format"""
        if isinstance(val, (datetime.date, datetime.datetime)):
            return val.isoformat()
        return val

    dups_serializable = [
        [serialize_value(val) for val in row]
        for row in dups
    ] if dups else []

    return {
        "status": "FAIL" if dups else "PASS",
        "severity": "HIGH" if dups else "NONE",
        "duplicates": dups_serializable,
        "duplicate_count": len(dups_serializable)
    }