# src/ombudsman/validation/dimensions/validate_dim_business_keys.py
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def validate_dim_business_keys(sql_conn, snow_conn, dim, mapping, metadata):
    sql_table = escape_sql_server_identifier(mapping[dim]["sql"])
    snow_table = escape_snowflake_identifier(mapping[dim]["snow"])
    bk = metadata[dim]["business_key"]

    sql_q = f"SELECT {bk} FROM {sql_table}"
    snow_q = f"SELECT {bk} FROM {snow_table}"

    sql_keys = {r[0] for r in sql_conn.fetch_many(sql_q)}
    snow_keys = {r[0] for r in snow_conn.fetch_many(snow_q)}

    missing_in_sql = list(snow_keys - sql_keys)
    missing_in_snow = list(sql_keys - snow_keys)

    status = "FAIL" if missing_in_sql or missing_in_snow else "PASS"

    return {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "missing_in_sql": missing_in_sql,
        "missing_in_snow": missing_in_snow
    }