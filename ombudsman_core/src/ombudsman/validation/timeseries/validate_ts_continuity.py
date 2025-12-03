# src/ombudsman/validation/timeseries/validate_ts_continuity.py
'''
Ensures all required dates exist (no gaps).
'''

def validate_ts_continuity(conn, table, date_col):
    q = f"""
        SELECT MIN({date_col}), MAX({date_col}), COUNT(*)
        FROM {table}
    """

    # Use cursor directly to get all columns from the row
    cursor = conn.cursor()
    cursor.execute(q)
    result = cursor.fetchone()
    cursor.close()

    if not result:
        return {
            "status": "ERROR",
            "severity": "HIGH",
            "message": "No data returned from query"
        }

    min_d, max_d, cnt = result

    expected = (max_d - min_d).days + 1

    missing_count = expected - cnt

    return {
        "status": "FAIL" if missing_count != 0 else "PASS",
        "severity": "MEDIUM" if missing_count else "NONE",
        "missing_count": missing_count,
        "min_date": str(min_d),
        "max_date": str(max_d)
    }