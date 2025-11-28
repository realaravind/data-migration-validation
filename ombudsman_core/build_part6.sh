#!/bin/bash
set -e

echo "=============================================================="
echo "=== PART 6: Documentation, Samples, DDL, ERD, YAML Builder ==="
echo "=============================================================="

BASE_DIR="ombudsman"

###############################################
# Friendly Help Menu
###############################################
show_help() {
    echo ""
    echo "=============================================================="
    echo " Ombudsman Build (Part 6)"
    echo "=============================================================="
    echo "Usage: build_part6.sh [options]"
    echo ""
    echo "Options:"
    echo "  --sqlserver                    Use SQL Server metadata"
    echo "  --snowflake                    Use Snowflake metadata"
    echo "  --conn-str=<string>            SQL Server connection string"
    echo "  --user=<snowflake_user>"
    echo "  --password=<snowflake_password>"
    echo "  --account=<snowflake_account>"
    echo "  --database=<snowflake_database>"
    echo "  --schema=<schema>              Defaults: dbo / PUBLIC"
    echo "  -h | --help                    Show help menu"
    echo ""
    echo "Auto-detection:"
    echo "  If no CLI args:"
    echo "   - SQLSERVER_CONN_STR → SQL Server"
    echo "   - SNOWFLAKE_USER → Snowflake"
    echo ""
}

###############################################
# Parse args
###############################################
MODE=""
ARGS=""
SCHEMA=""

while [[ "$#" -gt 0 ]]; do
    case $1 in
        --sqlserver) MODE="sqlserver" ;;
        --snowflake) MODE="snowflake" ;;
        --conn-str=*) ARGS="$ARGS --conn-str=${1#*=}" ;;
        --user=*) ARGS="$ARGS --user=${1#*=}" ;;
        --password=*) ARGS="$ARGS --password=${1#*=}" ;;
        --account=*) ARGS="$ARGS --account=${1#*=}" ;;
        --database=*) ARGS="$ARGS --database=${1#*=}" ;;
        --schema=*) SCHEMA="${1#*=}" ;;
        -h|--help) show_help; exit 0 ;;
        *) echo "⚠ Unknown argument ignored: $1" ;;
    esac
    shift
done

###############################################
# Auto-detect metadata source
###############################################
if [ -z "$MODE" ]; then
    if [ ! -z "$SQLSERVER_CONN_STR" ]; then
        MODE="sqlserver"
        ARGS="$ARGS --conn-str=\"$SQLSERVER_CONN_STR\""
        echo "✓ Auto-selected SQL Server (env)"
    elif [ ! -z "$SNOWFLAKE_USER" ]; then
        MODE="snowflake"
        ARGS="$ARGS --user=\"$SNOWFLAKE_USER\" --password=\"$SNOWFLAKE_PASSWORD\" --account=\"$SNOWFLAKE_ACCOUNT\" --database=\"$SNOWFLAKE_DATABASE\""
        echo "✓ Auto-selected Snowflake (env)"
    fi
fi

###############################################
# Validation
###############################################
if [ -z "$MODE" ]; then
    echo ""
    echo "❌ ERROR: No metadata source specified."
    echo "Use --sqlserver or --snowflake"
    echo "Or environment variables"
    exit 1
fi

if [ ! -z "$SCHEMA" ]; then
    ARGS="$ARGS --schema=$SCHEMA"
fi

echo ""
echo "=============================================================="
echo " Selected source: $MODE"
echo " Args: $ARGS"
echo "=============================================================="
echo ""

###############################################
# Create docs structure
###############################################
mkdir -p $BASE_DIR/docs/sections
mkdir -p $BASE_DIR/docs/assets
mkdir -p $BASE_DIR/samples/sqlserver
mkdir -p $BASE_DIR/samples/snowflake
mkdir -p $BASE_DIR/scripts
mkdir -p $BASE_DIR/output

###############################################
# mkdocs.yml
###############################################
cat << 'EOF' > $BASE_DIR/mkdocs.yml
site_name: Migration Testing Framework
theme:
  name: material
nav:
  - Home: docs/index.md
  - Getting Started:
      - Installation: docs/sections/install.md
      - Running Tests: docs/sections/run_tests.md
  - Relationship Builder: docs/sections/relationships.md
  - CLI Commands: docs/sections/cli.md
  - Terraform: docs/sections/terraform.md
  - Power BI: docs/sections/powerbi.md
EOF

###############################################
# Docs
###############################################
cat << 'EOF' > $BASE_DIR/docs/index.md
# Migration Testing Framework

Enterprise framework for validating migrations between SQL Server and Snowflake.
EOF

cat << 'EOF' > $BASE_DIR/docs/sections/install.md
# Installation

pip install -r src/core/requirements.txt
EOF

cat << 'EOF' > $BASE_DIR/docs/sections/run_tests.md
# Running Tests

python src/core/run_tests.py
EOF

cat << 'EOF' > $BASE_DIR/docs/sections/relationships.md
# Relationship Builder

python -m src.cli.cli build-relationships
EOF

cat << 'EOF' > $BASE_DIR/docs/sections/cli.md
# CLI Commands

python -m src.cli.cli <command>
EOF

cat << 'EOF' > $BASE_DIR/docs/sections/terraform.md
# Terraform

terraform init && terraform apply
EOF

cat << 'EOF' > $BASE_DIR/docs/sections/powerbi.md
# Power BI Refresh

python -m src.cli.cli refresh-powerbi
EOF

###############################################
# Sample SQL
###############################################
cat << 'EOF' > $BASE_DIR/samples/sqlserver/sample_dim_customer.sql
CREATE TABLE dbo.dim_customer(
  customer_id INT PRIMARY KEY,
  first_name NVARCHAR(50),
  last_name NVARCHAR(50)
);
EOF

cat << 'EOF' > $BASE_DIR/samples/snowflake/sample_fact_sales.sql
CREATE TABLE fact_sales(
  sale_id INT,
  customer_id INT,
  sale_amount NUMBER(18,2),
  sale_date DATE
);
EOF

###############################################
# run_all.sh
###############################################
cat << 'EOF' > $BASE_DIR/scripts/run_all.sh
#!/bin/bash
python ombudsman/scripts/generate_ddl.py $@
EOF
chmod +x $BASE_DIR/scripts/run_all.sh

###############################################
# Install the REAL dynamic generate_ddl.py
###############################################
cat << 'EOF' > $BASE_DIR/scripts/generate_ddl.py
<INSERTED BELOW AUTOMATICALLY>
EOF

###############################################
# Now insert the actual generate_ddl.py content
###############################################
sed -i 's|<INSERTED BELOW AUTOMATICALLY>|'"$(sed 's/|/\\|/g' generate_ddl.py)"'|g' $BASE_DIR/scripts/generate_ddl.py

chmod +x $BASE_DIR/scripts/generate_ddl.py

###############################################
# Final ZIP
###############################################
cat << 'EOF' > $BASE_DIR/finalize_project.sh
#!/bin/bash
set -e
zip -r migration-testing.zip . -x "*.git*" -x "*__pycache__*" -x "*.DS_Store*"
echo "Created migration-testing.zip"
EOF
chmod +x $BASE_DIR/finalize_project.sh

echo ""
echo "=== PART 6 complete ==="

echo "------------------------------------------"
echo "Step 6: Running validation engine"
echo "------------------------------------------"

python3 src/ombudsman/validation/run_validations.py

echo "Validation completed. Results stored in:"
echo "ombudsman/output/validation/results.json"