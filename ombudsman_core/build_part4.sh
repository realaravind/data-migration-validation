#!/bin/bash
set -e

echo "=== PART 4: Adding Utils, Logging, Common Modules ==="

mkdir -p src/utils

cat << 'EOF' > src/utils/log.py
def log(msg):
    print("[LOG]", msg)
EOF

cat << 'EOF' > src/utils/helpers.py
def flatten_dict(d):
    return {k:str(v) for k,v in d.items()}
EOF

echo "PART 4 complete."