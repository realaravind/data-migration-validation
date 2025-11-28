import json

def validate_schema(sql_meta, snow_meta):
    diff = {"tables_missing_in_sql": [], "tables_missing_in_snow": []}

    sql_tables = set(sql_meta.keys())
    snow_tables = set(snow_meta.keys())

    diff["tables_missing_in_sql"] = list(snow_tables - sql_tables)
    diff["tables_missing_in_snow"] = list(sql_tables - snow_tables)

    return diff