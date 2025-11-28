# src/ombudsman/validation/dimensions/validate_dim_surrogate_keys.py

def validate_dim_surrogate_keys(sql_conn, snow_conn, dim, mapping, metadata):
    sql_table = mapping[dim]["sql"]
    snow_table = mapping[dim]["snow"]

    bk = metadata[dim]["business_key"]
    sk = metadata[dim]["surrogate_key"]

    sql_q = f"SELECT {bk}, {sk} FROM {sql_table}"
    snow_q = f"SELECT {bk}, {sk} FROM {snow_table}"

    sql_map = {bk: sk for bk, sk in sql_conn.fetch_many(sql_q)}
    snow_map = {bk: sk for bk, sk in snow_conn.fetch_many(snow_q)}

    key_mismatches = []

    for k in sql_map:
        if k in snow_map and sql_map[k] != snow_map[k]:
            key_mismatches.append({
                "business_key": k,
                "sql_sk": sql_map[k],
                "snow_sk": snow_map[k]
            })

    status = "FAIL" if key_mismatches else "PASS"

    return {
        "status": status,
        "severity": "MEDIUM" if status == "FAIL" else "NONE",
        "mismatches": key_mismatches
    }