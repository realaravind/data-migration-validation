#!/bin/bash
set -e

echo "==============================================="
echo "=== BOOTSTRAP: Building Migration Framework ==="
echo "==============================================="

###############################################
# 1. Run build stages (all parts are required)
###############################################
for stage in build_part1.sh build_part2.sh build_part3.sh build_part4.sh build_part5.sh build_part6.sh
do
    echo ""
    echo "---------------------------------------------"
    echo "Running $stage ..."
    echo "---------------------------------------------"

    if [ -f "$stage" ]; then
        bash "$stage"
    else
        echo "❌ ERROR: $stage not found!"
        exit 1
    fi
done

###############################################
# 2. Python dependency setup (NO venv)
###############################################
if [ -f src/core/requirements.txt ]; then
    echo ""
    echo "Installing Python dependencies (system-wide)..."
    pip install --upgrade pip
    pip install -r src/core/requirements.txt
else
    echo ""
    echo "WARNING: src/core/requirements.txt not found. Skipping pip install."
fi

###############################################
# 3. Validate generated output files
###############################################
echo ""
echo "Validating generated files..."

expected_files=(
    "ombudsman/scripts/generate_ddl.py"
    "ombudsman/scripts/run_all.sh"
    "ombudsman/finalize_project.sh"
    "ombudsman/mkdocs.yml"
    "ombudsman/docs/index.md"

    # new dynamic generator outputs
    "ombudsman/output/ddl_sqlserver.sql"
    "ombudsman/output/ddl_snowflake.sql"
    "ombudsman/output/relationships.yaml"
    "ombudsman/output/erd_mermaid.mmd"
    "ombudsman/output/erd_mermaid_broken.mmd"
    "ombudsman/output/documentation.html"
)

missing=0
for f in "${expected_files[@]}"; do
    if [ ! -f "$f" ]; then
        echo "❌ Missing: $f"
        missing=1
    else
        echo "✔ Found: $f"
    fi
done

echo ""
echo "Checking optional PNG exports (skip errors)..."
optional_png=(
    "ombudsman/output/erd_mermaid.png"
    "ombudsman/output/erd_mermaid_broken.png"
)

for p in "${optional_png[@]}"; do
    if [ -f "$p" ]; then
        echo "✔ PNG found: $p"
    else
        echo "⚠ WARNING: PNG missing (mmdc may not be installed): $p"
    fi
done

###############################################
# 4. Final validation result
###############################################
if [ $missing -eq 1 ]; then
    echo ""
    echo "❌ BOOTSTRAP FAILED — Required files missing."
    echo "Check Part 6 generator or database connection."
    exit 1
fi

###############################################
# 5. Bootstrap complete
###############################################
echo ""
echo "==============================================="
echo " BOOTSTRAP COMPLETE — All required files exist "
echo "==============================================="