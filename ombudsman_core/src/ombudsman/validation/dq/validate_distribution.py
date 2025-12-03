# src/ombudsman/validation/dq/validate_distribution.py
'''
Kolmogorov–Smirnov or Chi‑Square test)
Detects distribution drift between SQL Server and Snowflake for numeric columns.

'''


import numpy as np
from scipy.stats import ks_2samp
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_distribution(sql_conn, snow_conn, table, mapping, metadata):
    numerics = metadata[table].get("numeric_columns", [])
    if not numerics:
        return {"status": "SKIPPED"}

    sql_table = escape_sql_server_identifier(mapping[table]["sql"])
    snow_table = escape_snowflake_identifier(mapping[table]["snow"])

    issues = []
    results = []

    for col in numerics:
        sql_vals = [r[0] for r in sql_conn.fetch_many(f"SELECT [{col}] FROM {sql_table}")]
        snow_vals = [r[0] for r in snow_conn.fetch_many(f"SELECT {col} FROM {snow_table}")]

        sql_vals = np.array([v for v in sql_vals if v is not None])
        snow_vals = np.array([v for v in snow_vals if v is not None])

        if len(sql_vals) == 0 or len(snow_vals) == 0:
            continue

        ks_stat, p_value = ks_2samp(sql_vals, snow_vals)

        distribution_match = bool(p_value > 0.05)

        result = {
            "column": col,
            "ks_statistic": round(float(ks_stat), 2),
            "p_value": round(float(p_value), 4),
            "distribution_match": distribution_match,
            "interpretation": "Distributions are similar" if distribution_match else "Distributions differ significantly"
        }

        results.append(result)

        if not distribution_match:
            issues.append(result)

    status = "FAIL" if issues else "PASS"

    # ALWAYS add explain data - show distribution stats and samples regardless of pass/fail
    explain_data = {}
    for result in results:
        col = result["column"]
        try:
            # Get sample data for comparison
            sql_samples = sql_conn.fetch_dicts(f"SELECT TOP 20 * FROM {sql_table} ORDER BY [{col}]")
            snow_samples = snow_conn.fetch_dicts(f"SELECT * FROM {snow_table} ORDER BY {col} LIMIT 20")

            # Get value distribution buckets (quartiles)
            sql_quartiles = sql_conn.fetch_dicts(f"""
                SELECT
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY [{col}]) as q1,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY [{col}]) as q2,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY [{col}]) as q3
                FROM {sql_table}
                WHERE [{col}] IS NOT NULL
            """)

            snow_quartiles = snow_conn.fetch_dicts(f"""
                SELECT
                    PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {col}) as q1,
                    PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {col}) as q2,
                    PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {col}) as q3
                FROM {snow_table}
                WHERE {col} IS NOT NULL
            """)

            if result["distribution_match"]:
                interpretation = f"Distribution test passed for column '{col}': KS statistic={result['ks_statistic']}, p-value={result['p_value']} (threshold=0.05). Distributions are similar."
            else:
                interpretation = f"Distribution test failed for column '{col}': KS statistic={result['ks_statistic']}, p-value={result['p_value']} (threshold=0.05). This indicates the two distributions differ significantly."

            explain_data[col] = {
                "column": col,
                "ks_statistic": result["ks_statistic"],
                "p_value": result["p_value"],
                "sql_samples": sql_samples[:20],
                "snow_samples": snow_samples[:20],
                "sql_quartiles": sql_quartiles[0] if sql_quartiles else {},
                "snow_quartiles": snow_quartiles[0] if snow_quartiles else {},
                "interpretation": interpretation,
                "queries": {
                    "sql_samples": f"SELECT TOP 20 * FROM {sql_table} ORDER BY [{col}]",
                    "snow_samples": f"SELECT * FROM {snow_table} ORDER BY {col} LIMIT 20",
                    "sql_quartiles": f"SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY [{col}]) as q1, PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY [{col}]) as q2, PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY [{col}]) as q3 FROM {sql_table} WHERE [{col}] IS NOT NULL",
                    "snow_quartiles": f"SELECT PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY {col}) as q1, PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY {col}) as q2, PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY {col}) as q3 FROM {snow_table} WHERE {col} IS NOT NULL"
                }
            }
        except Exception as e:
            # If explain fails, at least provide basic info
            if result["distribution_match"]:
                interpretation = f"Distribution test passed for column '{col}': KS statistic={result['ks_statistic']}, p-value={result['p_value']} (threshold=0.05). Distributions are similar."
            else:
                interpretation = f"Distribution test failed for column '{col}': KS statistic={result['ks_statistic']}, p-value={result['p_value']} (threshold=0.05). This indicates the two distributions differ significantly."

            explain_data[col] = {
                "column": col,
                "ks_statistic": result["ks_statistic"],
                "p_value": result["p_value"],
                "interpretation": interpretation,
                "error": f"Could not fetch detailed samples: {str(e)}"
            }

    return {
        "status": status,
        "severity": "MEDIUM" if status == "FAIL" else "NONE",
        "issues": issues,
        "results": results,
        "explain": explain_data  # Always include explain data
    }