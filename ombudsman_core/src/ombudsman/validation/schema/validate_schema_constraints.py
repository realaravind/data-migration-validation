# src/ombudsman/validation/schema/validate_schema_constraints.py

from ...core.utils import diff_lists

def validate_schema_constraints(sql_constraints, snow_constraints):
    results = {}

    for table in sql_constraints.keys():
        sql_pk = sql_constraints[table].get("primary_key", [])
        snow_pk = snow_constraints.get(table, {}).get("primary_key", [])

        pk_match = sql_pk == snow_pk

        missing_fk_sql = []
        missing_fk_snow = []

        sql_fks = sql_constraints[table].get("foreign_keys", [])
        snow_fks = snow_constraints.get(table, {}).get("foreign_keys", [])

        for fk in sql_fks:
            if fk not in snow_fks:
                missing_fk_snow.append(fk)

        for fk in snow_fks:
            if fk not in sql_fks:
                missing_fk_sql.append(fk)

        results[table] = {
            "primary_key_match": pk_match,
            "missing_fk_in_sql": missing_fk_sql,
            "missing_fk_in_snow": missing_fk_snow,
            "status": "FAIL" if missing_fk_sql or missing_fk_snow or not pk_match else "PASS",
            "severity": "HIGH" if missing_fk_sql or missing_fk_snow else "NONE"
        }

    return results