# src/ombudsman/validation/dq/validate_statistics.py

'''
(Avg / Stddev / Min / Max / Medians / Percentiles)
''' 

from ...core.utils import within_tolerance

def validate_statistics(sql_conn, snow_conn, table, mapping, metadata):
    numerics = metadata[table].get("numeric_columns", [])
    if not numerics:
        return {"status": "SKIPPED"}

    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    results = []

    for col in numerics:
        sql_stats = sql_conn.fetch_dicts(f"""
            SELECT 
                AVG({col}) AS avg_val,
                STDDEV({col}) AS std_val,
                MIN({col}) AS min_val,
                MAX({col}) AS max_val
            FROM {sql_table}
        """)[0]

        snow_stats = snow_conn.fetch_dicts(f"""
            SELECT 
                AVG({col}) AS avg_val,
                STDDEV({col}) AS std_val,
                MIN({col}) AS min_val,
                MAX({col}) AS max_val
            FROM {snow_table}
        """)[0]

        stat_issues = []

        for stat in ["avg_val", "std_val", "min_val", "max_val"]:
            v1 = sql_stats[stat]
            v2 = snow_stats[stat]

            if not within_tolerance(v1, v2, abs_tol=0.01, pct_tol=1):
                stat_issues.append((stat, v1, v2))

        if stat_issues:
            results.append({
                "column": col,
                "issues": stat_issues
            })

    status = "FAIL" if results else "PASS"

    return {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "issues": results
    }