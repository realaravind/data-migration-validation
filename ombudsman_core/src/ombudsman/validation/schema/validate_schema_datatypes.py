# src/ombudsman/validation/schema/validate_schema_datatypes.py

def normalize_sql_type(t):
    return t.lower().replace(" ", "")

def normalize_snow_type(t):
    return t.lower().replace(" ", "")

def validate_schema_datatypes(sql_columns, snow_columns):
    results = {}

    for table in sql_columns.keys():
        table_res = []
        for col in sql_columns[table]:
            col_name = col["name"]
            sql_type = normalize_sql_type(col["type"])
            snow_col = next((c for c in snow_columns.get(table, []) if c["name"] == col_name), None)

            if not snow_col:
                table_res.append({
                    "column": col_name,
                    "sql_type": sql_type,
                    "snow_type": None,
                    "match": False,
                    "severity": "HIGH"
                })
                continue

            snow_type = normalize_snow_type(snow_col["type"])
            match = sql_type == snow_type

            table_res.append({
                "column": col_name,
                "sql_type": sql_type,
                "snow_type": snow_type,
                "match": match,
                "severity": "NONE" if match else "MEDIUM"
            })

        results[table] = table_res

    return results