#!/bin/bash
set -e

echo "=== PART 2: Creating CLI and Core Structure ==="

mkdir -p src
mkdir -p src/core
mkdir -p src/cli

if [ ! -f src/core/__init__.py ]; then echo "" > src/core/__init__.py; fi
if [ ! -f src/cli/__init__.py ]; then echo "" > src/cli/__init__.py; fi

cat << 'EOF' > src/cli/cli.py
import argparse

def run_tests():
    print("Running tests (placeholder)")

def build_relationships():
    print("Building relationships (placeholder)")

def refresh_powerbi():
    print("Refreshing Power BI (placeholder)")

def main():
    p=argparse.ArgumentParser()
    sub=p.add_subparsers(dest="cmd")

    sub.add_parser("run-tests")
    sub.add_parser("build-relationships")
    sub.add_parser("refresh-powerbi")

    a=p.parse_args()
    if a.cmd=="run-tests": run_tests()
    if a.cmd=="build-relationships": build_relationships()
    if a.cmd=="refresh-powerbi": refresh_powerbi()

if __name__=="__main__":
    main()
EOF

echo "PART 2 complete."