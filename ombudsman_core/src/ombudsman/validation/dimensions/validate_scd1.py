# src/ombudsman/validation/dimensions/validate_scd1.py

def validate_scd1(sql_conn, snow_conn, dim, mapping, metadata):
    sql_table = mapping[dim]["sql"]
    snow_table = mapping[dim]["snow"]

    bk = metadata[dim]["business_key"]
    attrs = metadata[dim]["scd1_attributes"]

    col_list = ", ".join([bk] + attrs)

    sql_rows = {r[0]: r[1:] for r in sql_conn.fetch_many(f"SELECT {col_list} FROM {sql_table}")}
    snow_rows = {r[0]: r[1:] for r in snow_conn.fetch_many(f"SELECT {col_list} FROM {snow_table}")}

    diffs = []

    for k in sql_rows:
        if k in snow_rows and sql_rows[k] != snow_rows[k]:
            diffs.append({
                "business_key": k,
                "sql_values": sql_rows[k],
                "snow_values": snow_rows[k]
            })

    status = "FAIL" if diffs else "PASS"

    return {
        "status": status,
        "severity": "MEDIUM" if status == "FAIL" else "NONE",
        "differences": diffs
    }