# src/ombudsman/validation/dimensions/validate_scd2.py

def validate_scd2(sql_conn, snow_conn, dim, mapping, metadata):
    sql_table = mapping[dim]["sql"]
    snow_table = mapping[dim]["snow"]

    bk = metadata[dim]["business_key"]
    eff = metadata[dim]["effective_date"]
    end = metadata[dim]["end_date"]

    sql_rows = sql_conn.fetch_dicts(f"""
        SELECT {bk}, {eff}, {end}
        FROM {sql_table}
    """)

    snow_rows = snow_conn.fetch_dicts(f"""
        SELECT {bk}, {eff}, {end}
        FROM {snow_table}
    """)

    mismatches = []
    overlap_issues = []

    sql_map = {}
    for r in sql_rows:
        sql_map.setdefault(r[bk], []).append(r)

    snow_map = {}
    for r in snow_rows:
        snow_map.setdefault(r[bk], []).append(r)

    for k in sql_map:
        sql_hist = sorted(sql_map[k], key=lambda x: x[eff])
        snow_hist = sorted(snow_map.get(k, []), key=lambda x: x[eff])

        if len(sql_hist) != len(snow_hist):
            mismatches.append({"business_key": k, "issue": "Different version counts"})
            continue

        for s1, s2 in zip(sql_hist, snow_hist):
            if s1[eff] != s2[eff] or s1[end] != s2[end]:
                mismatches.append({
                    "business_key": k,
                    "sql": s1,
                    "snow": s2
                })

        # Check overlapping periods
        for i in range(len(sql_hist) - 1):
            if sql_hist[i][end] > sql_hist[i+1][eff]:
                overlap_issues.append({
                    "business_key": k,
                    "issue": f"Overlap between {sql_hist[i]} and {sql_hist[i+1]}"
                })

    status = "FAIL" if mismatches or overlap_issues else "PASS"

    return {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "version_mismatches": mismatches,
        "overlap_issues": overlap_issues
    }