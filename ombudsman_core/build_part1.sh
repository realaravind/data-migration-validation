#!/bin/bash
set -e

echo "=== PART 1: Creating Base Project Structure ==="

mkdir -p ombudsman
mkdir -p ombudsman/scripts
mkdir -p ombudsman/docs
mkdir -p ombudsman/output
mkdir -p ombudsman/samples

mkdir -p config

if [ ! -f config/connections.yaml ]; then
    cat << 'EOF' > config/connections.yaml
sqlserver:
  conn_str: "DRIVER={ODBC Driver 18 for SQL Server};SERVER=SERVERNAME;DATABASE=DB;UID=USER;PWD=PASS"

snowflake:
  user: "USER"
  password: "PASS"
  account: "ACCOUNT"
  database: "DB"
  schema: "PUBLIC"
EOF
fi

echo "PART 1 complete."