# src/ombudsman/validation/ri/validate_foreign_keys.py

def validate_foreign_keys(conn, table, fk_column, ref_table, ref_column):
    missing_q = f"""
        SELECT DISTINCT f.{fk_column}
        FROM {table} f
        LEFT JOIN {ref_table} d
            ON f.{fk_column} = d.{ref_column}
        WHERE d.{ref_column} IS NULL
    """

    missing = [r[0] for r in conn.fetch_many(missing_q)]

    return {
        "status": "FAIL" if missing else "PASS",
        "severity": "HIGH" if missing else "NONE",
        "missing_keys": missing
    }