#!/usr/bin/env python3

import argparse, os, subprocess, yaml
import pyodbc, snowflake.connector

############################################################
# SQL Server Extractor
############################################################
def extract_sqlserver_metadata(conn, schema="dbo"):
    c = pyodbc.connect(conn).cursor()
    tables = {}

    c.execute("SELECT TABLE_NAME FROM INFORMATION_SCHEMA.TABLES WHERE TABLE_SCHEMA=?", schema)
    for (t,) in c.fetchall():
        tables[t] = {"columns":{}, "relationships":{}}

    c.execute("SELECT TABLE_NAME,COLUMN_NAME,DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS WHERE TABLE_SCHEMA=?", schema)
    for t,col,dt in c.fetchall():
        tables[t]["columns"][col]=dt.upper()

    c.execute("""
        SELECT FK.TABLE_NAME, CU.COLUMN_NAME, PK.TABLE_NAME, PT.COLUMN_NAME
        FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS RC
        JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS FK ON RC.CONSTRAINT_NAME=FK.CONSTRAINT_NAME
        JOIN INFORMATION_SCHEMA.TABLE_CONSTRAINTS PK ON RC.UNIQUE_CONSTRAINT_NAME = PK.CONSTRAINT_NAME
        JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE CU ON CU.CONSTRAINT_NAME=RC.CONSTRAINT_NAME
        JOIN (
            SELECT TC.TABLE_NAME, KCU.COLUMN_NAME
            FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS TC
            JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE KCU ON TC.CONSTRAINT_NAME = KCU.CONSTRAINT_NAME
        ) PT ON PT.TABLE_NAME = PK.TABLE_NAME
        WHERE FK.TABLE_SCHEMA=?
    """, schema)
    for fact,fk,dim,dimcol in c.fetchall():
        tables[fact]["relationships"][fk]=f"{dim}.{dimcol}"

    dims={t:m for t,m in tables.items() if t.lower().startswith("dim_")}
    facts={t:m for t,m in tables.items() if t.lower().startswith("fact_")}
    return {"dimensions":dims, "facts":facts}

############################################################
# Snowflake Extractor
############################################################
def extract_snowflake_metadata(user,pwd,acct,db,sch):
    conn=snowflake.connector.connect(
        user=user, password=pwd, account=acct,
        database=db, schema=sch
    )
    c=conn.cursor()

    tables={}
    c.execute("SHOW TABLES")
    for row in c.fetchall():
        tables[row[1]]={"columns":{}, "relationships":{}}

    for t in tables:
        c.execute(f"DESCRIBE TABLE {t}")
        for r in c.fetchall():
            tables[t]["columns"][r[0]]=r[1].split("(")[0].upper()

    c.execute("""
        SELECT FK_TABLE_NAME,FK_COLUMN_NAME,PK_TABLE_NAME,PK_COLUMN_NAME
        FROM INFORMATION_SCHEMA.REFERENTIAL_CONSTRAINTS
    """)
    for fact,fk,dim,dimcol in c.fetchall():
        if fact in tables:
            tables[fact]["relationships"][fk]=f"{dim}.{dimcol}"

    dims={t:m for t,m in tables.items() if t.lower().startswith("dim_")}
    facts={t:m for t,m in tables.items() if t.lower().startswith("fact_")}
    return {"dimensions":dims,"facts":facts}

############################################################
# Helpers
############################################################
def sanitize(x):
    return x.replace("(","_").replace(")","").replace(",","_").replace(" ","_")

def write_yaml(meta):
    os.makedirs("ombudsman/output",exist_ok=True)
    with open("ombudsman/output/relationships.yaml","w") as f:
        yaml.dump(meta,f)

############################################################
# DDL Builders
############################################################
def sqlserver_ddl(meta):
    lines=[]
    for t,m in {**meta["dimensions"],**meta["facts"]}.items():
        lines.append(f"CREATE TABLE {t} (")
        for c,dt in m["columns"].items():
            lines.append(f"  {c} {dt},")
        lines[-1]=lines[-1][:-1]
        lines.append(");\n")
    return "\n".join(lines)

def snowflake_ddl(meta):
    lines=[]
    for t,m in {**meta["dimensions"],**meta["facts"]}.items():
        lines.append(f"CREATE OR REPLACE TABLE {t} (")
        for c,dt in m["columns"].items():
            dt2=dt.replace("NVARCHAR","STRING").replace("DECIMAL","NUMBER")
            lines.append(f"  {c} {dt2},")
        lines[-1]=lines[-1][:-1]
        lines.append(");\n")
    return "\n".join(lines)

############################################################
# Mermaid ERD
############################################################
def mermaid(meta,path,broken=False):
    out=["erDiagram"]
    for t,m in {**meta["dimensions"],**meta["facts"]}.items():
        out.append(f"    {t} {{")
        for c,dt in m["columns"].items():
            out.append(f"        {sanitize(dt)} {c}")
        out.append("    }")
    for fact,m in meta["facts"].items():
        for fk,v in m["relationships"].items():
            dim,col=v.split(".")
            if broken:
                out.append(f"    {dim} ||--x{{ {fact} : {fk}_BROKEN")
            else:
                out.append(f"    {dim} ||--o{{ {fact} : {fk}")
    with open(path,"w") as f:f.write("\n".join(out))

def export_png():
    try:
        subprocess.run(["mmdc","-i","ombudsman/output/erd_mermaid.mmd",
                        "-o","ombudsman/output/erd_mermaid.png"],check=True)
    except:
        print("PNG generation failed")

############################################################
# Documentation HTML
############################################################
def generate_docs(meta):
    html="<html><body><h1>Data Model</h1>"
    for t,m in {**meta["dimensions"],**meta["facts"]}.items():
        html+=f"<h2>{t}</h2><ul>"
        for c,dt in m["columns"].items():
            html+=f"<li>{c}: {dt}</li>"
        html+="</ul>"
    html+="</body></html>"
    with open("ombudsman/output/documentation.html","w") as f:
        f.write(html)

############################################################
# DBT Model Generator
############################################################
def dbt(meta):
    os.makedirs("ombudsman/output/dbt_models",exist_ok=True)
    for t in {**meta["dimensions"],**meta["facts"]}:
        with open(f"ombudsman/output/dbt_models/{t}.sql","w") as f:
            f.write("{{ config(materialized='table') }}\nselect * from "+t)

############################################################
# Master Build
############################################################
def build(meta):
    os.makedirs("ombudsman/output",exist_ok=True)

    write_yaml(meta)

    with open("ombudsman/output/ddl_sqlserver.sql","w") as f:
        f.write(sqlserver_ddl(meta))

    with open("ombudsman/output/ddl_snowflake.sql","w") as f:
        f.write(snowflake_ddl(meta))

    mermaid(meta,"ombudsman/output/erd_mermaid.mmd",False)
    mermaid(meta,"ombudsman/output/erd_mermaid_broken.mmd",True)
    export_png()

    generate_docs(meta)
    dbt(meta)

############################################################
# CLI
############################################################
def main():
    p=argparse.ArgumentParser()
    p.add_argument("--from-sqlserver",action="store_true")
    p.add_argument("--from-snowflake",action="store_true")
    p.add_argument("--conn-str")
    p.add_argument("--user")
    p.add_argument("--password")
    p.add_argument("--account")
    p.add_argument("--database")
    p.add_argument("--schema",default="dbo")
    a=p.parse_args()

    if a.from_sqlserver:
        meta=extract_sqlserver_metadata(a.conn_str,a.schema)
    elif a.from_snowflake:
        meta=extract_snowflake_metadata(a.user,a.password,a.account,a.database,a.schema)
    else:
        raise Exception("Must specify --from-sqlserver or --from-snowflake")

    build(meta)

if __name__=="__main__":
    main()