import json, os
from .validate_schema import validate_schema
from .validate_rowcounts import validate_rowcounts
from .validate_checksums import validate_checksums
from .validate_fk import validate_fk
from .validate_metrics import validate_metrics
from .validate_rules import validate_rules

from ..utils.sqlserver_conn import SQLServerConn
from ..utils.snowflake_conn import SnowflakeConn


def load_metadata():
    import yaml
    tables = yaml.safe_load(open("ombudsman/config/tables.yaml"))
    fks = yaml.safe_load(open("ombudsman/config/relationships.yaml"))
    return tables, fks


def main():
    sql = SQLServerConn(os.getenv("SQLSERVER_CONN_STR"))
    snow = SnowflakeConn()

    tables, fks = load_metadata()

    results = {
        "schema": validate_schema(tables["sql"], tables["snow"]),
        "rowcounts": validate_rowcounts(sql, snow, tables["sql"].keys()),
        "checksums": validate_checksums(sql, snow, tables["sql"].keys()),
        "fk": validate_fk(sql, snow, fks),
        "metrics": validate_metrics(sql, snow, "ombudsman/config/validation_rules.yaml"),
        "rules": validate_rules(sql, snow, "ombudsman/config/validation_rules.yaml"),
    }

    os.makedirs("ombudsman/output/validation", exist_ok=True)
    json.dump(results, open("ombudsman/output/validation/results.json", "w"), indent=2)


if __name__ == "__main__":
    main()