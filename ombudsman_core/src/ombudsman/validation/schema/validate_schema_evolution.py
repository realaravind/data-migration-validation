# src/ombudsman/validation/schema/validate_schema_evolution.py

import json

def validate_schema_evolution(snow_conn, sql_columns, snow_columns, snapshot_table):
    schema = snow_conn.schema

    # Get previous snapshot if exists
    prev = snow_conn.fetch_one(
        f"SELECT content FROM {schema}.{snapshot_table} ORDER BY ts DESC LIMIT 1"
    )

    if not prev:
        return {"status": "FIRST_RUN", "changes": None}

    prev_data = json.loads(prev)

    changes = {
        "added_columns": [],
        "removed_columns": [],
        "type_changes": [],
        "nullability_changes": []
    }

    for table in sql_columns.keys():
        prev_cols = prev_data.get(table, {})
        curr_cols = {c["name"]: c for c in sql_columns[table]}

        for c in curr_cols.keys():
            if c not in prev_cols:
                changes["added_columns"].append((table, c))

        for c in prev_cols:
            if c not in curr_cols:
                changes["removed_columns"].append((table, c))

        for c, d in curr_cols.items():
            if c in prev_cols:
                p = prev_cols[c]
                if d["type"] != p["type"]:
                    changes["type_changes"].append((table, c, p["type"], d["type"]))
                if d["nullable"] != p["nullable"]:
                    changes["nullability_changes"].append((table, c))

    return {
        "status": "PASS" if not any(changes.values()) else "FAIL",
        "changes": changes,
        "severity": "MEDIUM" if any(changes.values()) else "NONE"
    }