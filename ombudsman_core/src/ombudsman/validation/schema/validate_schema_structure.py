# src/ombudsman/validation/schema/validate_schema_structure.py

from ...core.utils import diff_lists

def validate_schema_structure(sql_tables, snow_tables):
    missing_in_sql, missing_in_snow = diff_lists(snow_tables, sql_tables)

    return {
        "missing_in_sql": missing_in_sql,
        "missing_in_snow": missing_in_snow,
        "extra_in_sql": list(set(sql_tables) - set(snow_tables)),
        "extra_in_snow": list(set(snow_tables) - set(sql_tables)),
        "status": "FAIL" if missing_in_sql or missing_in_snow else "PASS",
        "severity": "HIGH" if missing_in_sql or missing_in_snow else "NONE"
    }