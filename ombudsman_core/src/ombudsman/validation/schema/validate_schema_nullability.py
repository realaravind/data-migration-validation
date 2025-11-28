# src/ombudsman/validation/schema/validate_schema_nullability.py

def validate_schema_nullability(sql_columns, snow_columns):
    results = {}

    for table in sql_columns.keys():
        table_res = []

        for col in sql_columns[table]:
            name = col["name"]
            sql_null = col["nullable"]
            snow_col = next((c for c in snow_columns.get(table, []) if c["name"] == name), None)

            if snow_col is None:
                table_res.append({
                    "column": name,
                    "sql_nullable": sql_null,
                    "snow_nullable": None,
                    "match": False,
                    "severity": "HIGH"
                })
                continue

            match = sql_null == snow_col["nullable"]

            table_res.append({
                "column": name,
                "sql_nullable": sql_null,
                "snow_nullable": snow_col["nullable"],
                "match": match,
                "severity": "NONE" if match else "MEDIUM"
            })

        results[table] = table_res

    return results