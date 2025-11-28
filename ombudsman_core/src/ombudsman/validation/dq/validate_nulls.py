# src/ombudsman/validation/dq/validate_nulls.py

def validate_nulls(sql_conn, snow_conn, table, mapping, metadata):
    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    cols = metadata[table]["columns"]

    results = []

    for col in cols:
        sql_q = f"SELECT COUNT(*) FROM {sql_table} WHERE {col} IS NULL"
        snow_q = f"SELECT COUNT(*) FROM {snow_table} WHERE {col} IS NULL"

        sql_nulls = sql_conn.fetch_one(sql_q)
        snow_nulls = snow_conn.fetch_one(snow_q)

        match = sql_nulls == snow_nulls

        results.append({
            "column": col,
            "sql_nulls": sql_nulls,
            "snow_nulls": snow_nulls,
            "match": match,
            "severity": "HIGH" if not match else "NONE"
        })

    return {
        "status": "FAIL" if any(not r["match"] for r in results) else "PASS",
        "results": results
    }