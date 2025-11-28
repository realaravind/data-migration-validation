# src/ombudsman/validation/schema/validate_schema_columns.py

from ...core.utils import diff_lists

def validate_schema_columns(sql_columns, snow_columns):
    results = {}

    for table in sql_columns.keys():
        sql_cols = [c["name"] for c in sql_columns[table]]
        snow_cols = [c["name"] for c in snow_columns.get(table, [])]

        missing_in_sql, missing_in_snow = diff_lists(snow_cols, sql_cols)

        results[table] = {
            "missing_in_sql": missing_in_sql,
            "missing_in_snow": missing_in_snow,
            "extra_in_sql": list(set(sql_cols) - set(snow_cols)),
            "extra_in_snow": list(set(snow_cols) - set(sql_cols)),
            "column_order_match": sql_cols == snow_cols,
            "status": "FAIL" if missing_in_sql or missing_in_snow else "PASS",
            "severity": "HIGH" if missing_in_sql or missing_in_snow else "NONE"
        }

    return results