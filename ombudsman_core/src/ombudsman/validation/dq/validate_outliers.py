# src/ombudsman/validation/dq/validate_outliers.py
'''
(Z-score or IQR)
Detects outliers in numeric columns between SQL Server and Snowflake.

...

import numpy as np

def validate_outliers(sql_conn, snow_conn, table, mapping, metadata):
    numerics = metadata[table].get("numeric_columns", [])
    if not numerics:
        return {"status": "SKIPPED"}

    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    results = []

    for col in numerics:
        sql_vals = np.array([r[0] for r in sql_conn.fetch_many(f"SELECT {col} FROM {sql_table}") if r[0] is not None])
        snow_vals = np.array([r[0] for r in snow_conn.fetch_many(f"SELECT {col} FROM {snow_table}") if r[0] is not None])

        if len(sql_vals) < 3 or len(snow_vals) < 3:
            continue

        sql_z = np.abs((sql_vals - sql_vals.mean()) / sql_vals.std())
        snow_z = np.abs((snow_vals - snow_vals.mean()) / snow_vals.std())

        sql_out = sql_vals[sql_z > 3].tolist()
        snow_out = snow_vals[snow_z > 3].tolist()

        if sql_out or snow_out:
            results.append({
                "column": col,
                "sql_outliers": sql_out,
                "snow_outliers": snow_out
            })

    status = "FAIL" if results else "PASS"

    return {
        "status": status,
        "severity": "LOW" if status == "FAIL" else "NONE",
        "outliers": results
    }