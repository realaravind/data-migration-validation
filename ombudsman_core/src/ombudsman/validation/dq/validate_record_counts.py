# src/ombudsman/validation/dq/validate_record_counts.py

def validate_record_counts(sql_conn, snow_conn, table, mapping):
    sql_table = mapping[table]["sql"]
    snow_table = mapping[table]["snow"]

    sql_cnt = sql_conn.fetch_one(f"SELECT COUNT(*) FROM {sql_table}")
    snow_cnt = snow_conn.fetch_one(f"SELECT COUNT(*) FROM {snow_table}")

    status = "FAIL" if sql_cnt != snow_cnt else "PASS"

    return {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "sql_count": sql_cnt,
        "snow_count": snow_cnt
    }