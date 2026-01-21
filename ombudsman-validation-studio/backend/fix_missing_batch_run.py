"""
Script to manually create missing batch run records in /results

This fixes the issue where batch executions don't create consolidated result files.
"""

import json
from pathlib import Path
from datetime import datetime
from collections import defaultdict

def generate_batch_run_for_job(job_id: str, job_data: dict):
    """Generate a consolidated batch run record for a batch job"""

    # Extract run IDs from batch job operations
    run_ids = []
    for operation in job_data.get("operations", []):
        if operation.get("status") == "completed" and operation.get("result"):
            result = operation["result"]
            # Check if this is a batch execution result with nested pipeline results
            if "results" in result and isinstance(result["results"], list):
                # Extract run_ids from nested results (batch execution)
                for nested_result in result["results"]:
                    nested_run_id = nested_result.get("run_id")
                    if nested_run_id:
                        run_ids.append(nested_run_id)
            else:
                # Regular pipeline execution - single run_id
                run_id = result.get("run_id")
                if run_id:
                    run_ids.append(run_id)

    if not run_ids:
        print(f"No completed pipeline runs found for job {job_id}")
        return None

    # Load all pipeline results
    results_dir = Path("/Users/aravind/sourcecode/projects/data-migration-validator/ombudsman-validation-studio/backend/results")
    all_results = []

    for run_id in run_ids:
        result_file = results_dir / f"{run_id}.json"
        if result_file.exists():
            try:
                with open(result_file) as f:
                    result_data = json.load(f)
                    all_results.append(result_data)
            except Exception as e:
                print(f"WARNING: Failed to load result file {run_id}.json: {e}")
                continue

    if not all_results:
        print(f"No result files found for job {job_id}")
        return None

    # Organize results by table
    tables_data = defaultdict(lambda: {
        "table_name": "",
        "schema": "",
        "validations": []
    })

    for result in all_results:
        pipeline_def = result.get("pipeline_def", {})

        # Extract table info - try new structure first (pipeline_def.source)
        source = pipeline_def.get("source")
        if not source or not isinstance(source, dict):
            # Fallback to old structure (pipeline_def.pipeline.source)
            pipeline = pipeline_def.get("pipeline", {})
            source = pipeline.get("source", {})

        schema = source.get("schema", "")
        table = source.get("table", "unknown")
        full_table = f"{schema}.{table}" if schema else table

        # Get validation steps
        steps = result.get("results", result.get("steps", []))

        # Add to table's validations
        tables_data[full_table]["table_name"] = table
        tables_data[full_table]["schema"] = schema
        tables_data[full_table]["validations"].extend(steps)

    # Create consolidated result - use job's started_at timestamp
    started_at_str = job_data.get("started_at", datetime.now().isoformat())
    started_at = datetime.fromisoformat(started_at_str) if started_at_str else datetime.now()
    consolidated_run_id = f"batch_{job_id}_{started_at.strftime('%Y%m%d_%H%M%S')}"

    # Flatten all validations in table-by-table order
    all_validations = []
    for table_key in sorted(tables_data.keys()):
        table_info = tables_data[table_key]
        all_validations.extend(table_info["validations"])

    # Calculate overall statistics
    total_validations = len(all_validations)
    passed = sum(1 for v in all_validations if v.get("status", "").upper() == "PASS")
    failed = sum(1 for v in all_validations if v.get("status", "").upper() == "FAIL")

    consolidated_result = {
        "run_id": consolidated_run_id,
        "batch_job_id": job_id,
        "batch_job_name": job_data.get("name", job_id),
        "pipeline_name": f"Batch Execution: {job_data.get('name', job_id)}",
        "execution_type": "batch_consolidation",
        "status": "PASS" if failed == 0 else "FAIL",
        "started_at": started_at.isoformat(),
        "completed_at": job_data.get("completed_at"),
        "total_pipelines": len(all_results),
        "tables_validated": sorted(list(tables_data.keys())),
        "summary": {
            "total_validations": total_validations,
            "passed": passed,
            "failed": failed,
            "pass_rate": round((passed / total_validations * 100) if total_validations > 0 else 0, 2)
        },
        "tables": [
            {
                "table": table_key,
                "schema": info["schema"],
                "table_name": info["table_name"],
                "total_validations": len(info["validations"]),
                "passed": sum(1 for v in info["validations"] if v.get("status", "").upper() == "PASS"),
                "failed": sum(1 for v in info["validations"] if v.get("status", "").upper() == "FAIL"),
            }
            for table_key, info in sorted(tables_data.items())
        ],
        "results": all_validations,
        "individual_run_ids": run_ids
    }

    # Save consolidated result
    consolidated_file = results_dir / f"{consolidated_run_id}.json"
    with open(consolidated_file, "w") as f:
        json.dump(consolidated_result, f, indent=2)

    print(f"✓ Created consolidated result: {consolidated_run_id}")
    print(f"  - Merged {len(all_results)} pipelines")
    print(f"  - {len(tables_data)} tables")
    print(f"  - {total_validations} validations")

    return consolidated_run_id


if __name__ == "__main__":
    # Fix missing batch run for job 73210d0f-41e3-4a44-9b39-0464e8316baf
    job_id = "73210d0f-41e3-4a44-9b39-0464e8316baf"
    job_file = Path(f"/Users/aravind/sourcecode/projects/data-migration-validator/ombudsman-validation-studio/backend/data/batch_jobs/{job_id}.json")

    if not job_file.exists():
        print(f"ERROR: Batch job file not found: {job_file}")
        exit(1)

    with open(job_file) as f:
        job_data = json.load(f)

    print(f"Processing batch job: {job_data.get('name', job_id)}")
    print(f"Started at: {job_data.get('started_at')}")
    print(f"Status: {job_data.get('status')}")
    print()

    run_id = generate_batch_run_for_job(job_id, job_data)

    if run_id:
        print()
        print("SUCCESS! Batch run record created.")
        print(f"Run ID: {run_id}")
    else:
        print()
        print("FAILED: Could not create batch run record.")
