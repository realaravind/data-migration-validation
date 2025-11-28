import yaml

def load_metadata():
    tables = yaml.safe_load(open("ombudsman/config/tables.yaml"))
    columns = yaml.safe_load(open("ombudsman/config/columns.yaml"))
    relationships = yaml.safe_load(open("ombudsman/config/relationships.yaml"))
    return tables, columns, relationships