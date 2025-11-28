# src/ombudsman/validation/timeseries/validate_ts_continuity.py
'''
Ensures all required dates exist (no gaps).
''
def validate_ts_continuity(conn, table, date_col):
    q = f"""
        SELECT MIN({date_col}), MAX({date_col}), COUNT(*)
        FROM {table}
    """

    min_d, max_d, cnt = conn.fetch_one(q)

    expected = (max_d - min_d).days + 1

    missing_count = expected - cnt

    return {
        "status": "FAIL" if missing_count != 0 else "PASS",
        "severity": "MEDIUM" if missing_count else "NONE",
        "missing_count": missing_count,
        "min_date": str(min_d),
        "max_date": str(max_d)
    }