# src/ombudsman/validation/dimensions/validate_composite_keys.py

def validate_composite_keys(sql_conn, snow_conn, dim, mapping, metadata):
    sql_table = mapping[dim]["sql"]
    snow_table = mapping[dim]["snow"]

    keys = metadata[dim]["composite_keys"]

    key_expr = ", ".join(keys)

    sql_rows = sql_conn.fetch_many(f"SELECT {key_expr} FROM {sql_table}")
    snow_rows = snow_conn.fetch_many(f"SELECT {key_expr} FROM {snow_table}")

    sql_set = set(sql_rows)
    snow_set = set(snow_rows)

    missing_in_sql = list(snow_set - sql_set)
    missing_in_snow = list(sql_set - snow_set)

    status = "FAIL" if missing_in_sql or missing_in_snow else "PASS"

    return {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "missing_in_sql": missing_in_sql,
        "missing_in_snow": missing_in_snow
    }