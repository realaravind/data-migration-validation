#!/bin/sh
set -e

for f in pipelines/*.yaml; do
  echo "Running pipeline: $f"
  ombudsman validate "$f"
done