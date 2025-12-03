# src/ombudsman/validation/dimensions/validate_composite_keys.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_composite_keys(sql_conn, snow_conn, dim, mapping, metadata):
    sql_table = escape_sql_server_identifier(mapping[dim]["sql"])
    snow_table = escape_snowflake_identifier(mapping[dim]["snow"])

    keys = metadata[dim]["composite_keys"]

    sql_key_expr = ", ".join([f"[{k}]" for k in keys])
    snow_key_expr = ", ".join(keys)

    sql_rows = sql_conn.fetch_many(f"SELECT {sql_key_expr} FROM {sql_table}")
    snow_rows = snow_conn.fetch_many(f"SELECT {snow_key_expr} FROM {snow_table}")

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