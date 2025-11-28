import yaml
import os

def load_mapping(tables_metadata):
    mapping_file = "ombudsman/config/mapping.yaml"
    override = {}

    if os.path.exists(mapping_file):
        override = yaml.safe_load(open(mapping_file))

    final = {}

    for logical_name, meta in tables_metadata.items():
        sql_name = meta.get("sql_name")
        snow_name = meta.get("snow_name")

        if logical_name in override:
            o = override[logical_name]
            sql_name = o.get("sql_name", sql_name)
            snow_name = o.get("snow_name", snow_name)

        final[logical_name] = {
            "sql": sql_name,
            "snow": snow_name
        }

    return final