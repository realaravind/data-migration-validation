# src/ombudsman/validation/dq/validate_distribution.py
'''
Kolmogorov–Smirnov or Chi‑Square test)
Detects distribution drift between SQL Server and Snowflake for numeric columns.

'''


import numpy as np
from scipy.stats import ks_2samp

def validate_distribution(sql_conn, snow_conn, table, mapping, metadata):
    numerics = metadata[table].get("numeric_columns", [])
    if not numerics:
        return {"status": "SKIPPED"}

    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    results = []

    for col in numerics:
        sql_vals = [r[0] for r in sql_conn.fetch_many(f"SELECT {col} FROM {sql_table}")]
        snow_vals = [r[0] for r in snow_conn.fetch_many(f"SELECT {col} FROM {snow_table}")]

        sql_vals = np.array([v for v in sql_vals if v is not None])
        snow_vals = np.array([v for v in snow_vals if v is not None])

        if len(sql_vals) == 0 or len(snow_vals) == 0:
            continue

        ks_stat, p_value = ks_2samp(sql_vals, snow_vals)

        results.append({
            "column": col,
            "ks_statistic": float(ks_stat),
            "p_value": float(p_value),
            "distribution_match": p_value > 0.05,
            "severity": "MEDIUM" if p_value <= 0.05 else "NONE"
        })

    status = "FAIL" if any(not r["distribution_match"] for r in results) else "PASS"

    return {
        "status": status,
        "results": results
    }