#!/usr/bin/env python3
"""Generate a workload and convert it to a validation pipeline"""

import sys
import os
import yaml
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(__file__))

from workload_generator import WorkloadGenerator

def convert_workload_to_pipeline(queries, table_name="dim_product"):
    """Convert workload queries to validation pipeline YAML"""

    workload_id = f"wl_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    pipeline_name = f"comparative_{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    pipeline = {
        "metadata": {
            "name": f"{table_name}_comparative_validation",
            "description": f"Comparative validations from Query Store for dim.{table_name}",
            "generated_from": f"workload_{workload_id}",
            "project_id": "dw_validation",
            "created_at": datetime.now().isoformat(),
            "validation_count": len(queries),
            "validation_type": "comparative"
        },
        "source": {
            "type": "sqlserver",
            "database": "${SQL_DATABASE}",
            "schema": "dim",
            "table": table_name
        },
        "target": {
            "type": "snowflake",
            "database": "${SNOWFLAKE_DATABASE}",
            "schema": "DIM",
            "table": table_name.upper()
        },
        "steps": []
    }

    for i, query in enumerate(queries, 1):
        # Check if query has ORDER BY clause
        query_text = query['raw_text'].upper()
        has_order_by = 'ORDER BY' in query_text

        # If no ORDER BY, ignore row order during comparison
        # If has ORDER BY, respect the order as it's intentional
        ignore_row_order = not has_order_by

        step = {
            "name": f"comparative_validation_{i}_query_{query['query_id']}",
            "type": "comparative",
            "validator": "custom_sql",
            "description": f"Compare query results between SQL Server and Snowflake (Query ID: {query['query_id']})",
            "enabled": True,
            "config": {
                "sql_server_query": query['raw_text'],
                "snowflake_query": query['raw_text'],  # Will be transformed by column mapping
                "compare_mode": "result_set",
                "tolerance": 0.0,
                "ignore_column_order": True,
                "ignore_row_order": ignore_row_order
            },
            "metadata": {
                "query_id": query['query_id'],
                "total_executions": query['stats'].get('total_executions', 0),
                "avg_duration_ms": query['stats'].get('avg_duration', 0),
                "last_execution_time": query['stats'].get('last_execution_time', '')
            }
        }
        pipeline["steps"].append(step)

    return pipeline

def main():
    print("Generating workload and converting to pipeline...\n")

    # Create generator instance
    generator = WorkloadGenerator()

    # Generate workload
    queries = generator.generate_workload("Retail")
    print(f"Generated {len(queries)} queries\n")

    # Convert to pipeline
    pipeline = convert_workload_to_pipeline(queries, "dim_product")

    # Save pipeline
    script_dir = Path(__file__).parent
    pipelines_dir = script_dir / "pipelines"
    pipelines_dir.mkdir(exist_ok=True)

    pipeline_file = pipelines_dir / f"comparative_dim_product_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml"

    with open(pipeline_file, 'w') as f:
        yaml.dump(pipeline, f, default_flow_style=False, sort_keys=False)

    print(f"Pipeline saved to: {pipeline_file}")
    print(f"\nPipeline contains {len(pipeline['steps'])} validation steps")

    # Show JOIN queries
    join_queries = [q for q in queries if 'JOIN' in q['raw_text']]
    print(f"\nJOIN queries in pipeline: {len(join_queries)}")
    for i, q in enumerate(join_queries, 1):
        print(f"\n{i}. Query ID {q['query_id']}:")
        print(f"   {q['raw_text'][:100]}{'...' if len(q['raw_text']) > 100 else ''}")

    print(f"\n✅ Done! Pipeline file: {pipeline_file.name}")

if __name__ == "__main__":
    main()
