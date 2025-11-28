# src/ombudsman/validation/ri/validate_cross_system_fk_alignment.py
'''
SQL FK violations must match Snowflake FK violations.
'''
def validate_cross_system_fk_alignment(sql_result, snow_result):
    sql_missing = set(sql_result["missing_keys"])
    snow_missing = set(snow_result["missing_keys"])

    diff_sql = list(sql_missing - snow_missing)
    diff_snow = list(snow_missing - sql_missing)

    status = "FAIL" if diff_sql or diff_snow else "PASS"

    return {
        "status": status,
        "severity": "HIGH" if status == "FAIL" else "NONE",
        "extra_sql_violations": diff_sql,
        "extra_snow_violations": diff_snow
    }