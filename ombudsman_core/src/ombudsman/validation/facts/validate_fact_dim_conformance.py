# src/ombudsman/validation/facts/validate_fact_dim_conformance.py

def validate_fact_dim_conformance(sql_conn, snow_conn, fact, dim, mapping, metadata):
    fk = metadata[fact]["foreign_keys"][dim]["column"]
    dim_bk = metadata[dim]["business_key"]

    fact_sql = mapping[fact]["sql"]
    fact_snow = mapping[fact]["snow"]
    dim_sql = mapping[dim]["sql"]
    dim_snow = mapping[dim]["snow"]

    sql_fkeys = {r[0] for r in sql_conn.fetch_many(f"SELECT {fk} FROM {fact_sql}")}
    snow_fkeys = {r[0] for r in snow_conn.fetch_many(f"SELECT {fk} FROM {fact_snow}")}

    sql_dim_keys = {r[0] for r in sql_conn.fetch_many(f"SELECT {dim_bk} FROM {dim_sql}")}
    snow_dim_keys = {r[0] for r in snow_conn.fetch_many(f"SELECT {dim_bk} FROM {dim_snow}")}

    sql_orphans = list(sql_fkeys - sql_dim_keys)
    snow_orphans = list(snow_fkeys - snow_dim_keys)

    status = "FAIL" if sql_orphans or snow_orphans else "PASS"

    return {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "sql_orphans": sql_orphans,
        "snow_orphans": snow_orphans
    }