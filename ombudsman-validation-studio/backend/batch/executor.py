"""
Batch Executor

Executes batch operations with support for:
- Parallel execution
- Sequential execution
- Error handling and retries
- Progress tracking
"""

import asyncio
import uuid
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Thread

from config.paths import paths

logger = logging.getLogger(__name__)

# Build backend URL from SERVER_HOST and BACKEND_PORT (standard env vars)
SERVER_HOST = os.getenv("SERVER_HOST", "localhost")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
BACKEND_URL = f"http://{SERVER_HOST}:{BACKEND_PORT}"
from .models import (
    BatchJob,
    BatchJobStatus,
    BatchJobType,
    BatchOperation,
    BatchOperationStatus,
    PipelineExecutionItem,
    DataGenItem
)
from .job_manager import batch_job_manager


class BatchExecutor:
    """
    Executes batch operations.

    Handles parallel/sequential execution, error handling,
    and progress tracking.
    """

    def __init__(self):
        """Initialize executor"""
        self.executor = ThreadPoolExecutor(max_workers=10)

    def execute_job_async(self, job_id: str):
        """
        Execute a batch job asynchronously in a background thread.

        Args:
            job_id: Job to execute
        """
        thread = Thread(target=self._execute_job, args=(job_id,), daemon=True)
        thread.start()

    def _execute_job(self, job_id: str):
        """
        Execute a batch job (runs in background thread).

        Args:
            job_id: Job to execute
        """
        job = batch_job_manager.get_job(job_id)
        if not job:
            return

        try:
            # Update status to running
            batch_job_manager.update_job_status(job_id, BatchJobStatus.RUNNING)

            # Execute based on job type
            if job.job_type == BatchJobType.BULK_PIPELINE_EXECUTION:
                self._execute_pipeline_batch(job)
            elif job.job_type == BatchJobType.BATCH_DATA_GENERATION:
                self._execute_data_gen_batch(job)
            elif job.job_type == BatchJobType.MULTI_PROJECT_VALIDATION:
                self._execute_multi_project_batch(job)
            elif job.job_type == BatchJobType.BULK_METADATA_EXTRACTION:
                self._execute_metadata_batch(job)
            else:
                # Generic execution
                self._execute_generic_batch(job)

            # Determine final status
            if job.failure_count > 0 and job.success_count > 0:
                final_status = BatchJobStatus.PARTIAL_SUCCESS
            elif job.failure_count > 0:
                final_status = BatchJobStatus.FAILED
            else:
                final_status = BatchJobStatus.COMPLETED

            # Generate consolidated result for pipeline executions
            if job.job_type == BatchJobType.BULK_PIPELINE_EXECUTION:
                try:
                    print(f"[BATCH {job_id}] Generating consolidated result...")
                    self._generate_consolidated_result(job)
                    print(f"[BATCH {job_id}] Consolidated result generated successfully")
                except Exception as consolidation_error:
                    print(f"[BATCH {job_id}] ERROR: Failed to generate consolidated result: {consolidation_error}")
                    import traceback
                    print(f"[BATCH {job_id}] Traceback:\n{traceback.format_exc()}")
                    # Don't fail the entire batch job if consolidation fails
                    # The individual pipeline results are still valid

            batch_job_manager.update_job_status(job_id, final_status)

        except Exception as e:
            print(f"Error executing batch job {job_id}: {e}")
            batch_job_manager.update_job_status(job_id, BatchJobStatus.FAILED)

    def _execute_pipeline_batch(self, job: BatchJob):
        """Execute bulk pipeline operations"""
        if job.parallel_execution:
            self._execute_parallel(job, self._execute_pipeline_operation)
        else:
            self._execute_sequential(job, self._execute_pipeline_operation)

    def _execute_data_gen_batch(self, job: BatchJob):
        """Execute batch data generation"""
        if job.parallel_execution:
            self._execute_parallel(job, self._execute_data_gen_operation)
        else:
            self._execute_sequential(job, self._execute_data_gen_operation)

    def _execute_multi_project_batch(self, job: BatchJob):
        """Execute multi-project validation"""
        if job.parallel_execution:
            self._execute_parallel(job, self._execute_project_operation)
        else:
            self._execute_sequential(job, self._execute_project_operation)

    def _execute_metadata_batch(self, job: BatchJob):
        """Execute bulk metadata extraction"""
        if job.parallel_execution:
            self._execute_parallel(job, self._execute_metadata_operation)
        else:
            self._execute_sequential(job, self._execute_metadata_operation)

    def _execute_generic_batch(self, job: BatchJob):
        """Execute generic batch operations"""
        if job.parallel_execution:
            self._execute_parallel(job, self._execute_generic_operation)
        else:
            self._execute_sequential(job, self._execute_generic_operation)

    def _execute_sequential(self, job: BatchJob, operation_func: Callable):
        """
        Execute operations sequentially.

        Args:
            job: Batch job
            operation_func: Function to execute each operation
        """
        for operation in job.operations:
            # Check if job was cancelled
            current_job = batch_job_manager.get_job(job.job_id)
            if current_job.status == BatchJobStatus.CANCELLED:
                break

            # Skip if already completed/failed/skipped
            if operation.status != BatchOperationStatus.PENDING:
                continue

            # Execute operation
            batch_job_manager.update_operation_status(
                job.job_id, operation.operation_id, BatchOperationStatus.RUNNING
            )

            try:
                result = operation_func(operation)
                batch_job_manager.update_operation_status(
                    job.job_id, operation.operation_id,
                    BatchOperationStatus.COMPLETED, result=result
                )
            except Exception as e:
                batch_job_manager.update_operation_status(
                    job.job_id, operation.operation_id,
                    BatchOperationStatus.FAILED, error=str(e)
                )

                # Stop on error if configured
                if job.stop_on_error:
                    break

    def _execute_parallel(self, job: BatchJob, operation_func: Callable):
        """
        Execute operations in parallel.

        Args:
            job: Batch job
            operation_func: Function to execute each operation
        """
        max_workers = min(job.max_parallel, len(job.operations))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for operation in job.operations:
                if operation.status != BatchOperationStatus.PENDING:
                    continue

                future = executor.submit(self._execute_operation_with_tracking, job, operation, operation_func)
                futures[future] = operation

            # Wait for completion
            for future in as_completed(futures):
                operation = futures[future]

                # Check if job was cancelled
                current_job = batch_job_manager.get_job(job.job_id)
                if current_job.status == BatchJobStatus.CANCELLED:
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    break

                # Check stop on error
                if job.stop_on_error and operation.status == BatchOperationStatus.FAILED:
                    # Cancel remaining futures
                    for f in futures:
                        f.cancel()
                    break

    def _execute_operation_with_tracking(self, job: BatchJob, operation: BatchOperation, operation_func: Callable):
        """Execute single operation with progress tracking"""
        batch_job_manager.update_operation_status(
            job.job_id, operation.operation_id, BatchOperationStatus.RUNNING
        )

        try:
            result = operation_func(operation)
            batch_job_manager.update_operation_status(
                job.job_id, operation.operation_id,
                BatchOperationStatus.COMPLETED, result=result
            )
        except Exception as e:
            batch_job_manager.update_operation_status(
                job.job_id, operation.operation_id,
                BatchOperationStatus.FAILED, error=str(e)
            )

    # Operation executors for different types

    def _execute_pipeline_operation(self, operation: BatchOperation) -> Dict[str, Any]:
        """Execute a single pipeline operation"""
        # Import here to avoid circular imports
        import requests
        import yaml
        from pathlib import Path

        pipeline_data = operation.metadata or {}
        pipeline_id = pipeline_data.get("pipeline_id")

        if not pipeline_id:
            raise ValueError("No pipeline_id in operation metadata")

        # Remove .yaml extension if present (will be added back when searching)
        if pipeline_id.endswith('.yaml'):
            pipeline_id = pipeline_id[:-5]

        # Load pipeline YAML content
        # Try multiple locations for pipeline file
        pipeline_yaml = None
        # Add timestamp to make job name unique: Pipelinename_timestamp
        pipeline_name = f"{pipeline_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        found_file_path = None

        # Search in project directories and flat pipelines directory
        search_paths = [
            paths.pipelines_dir,  # Flat directory
            paths.projects_dir    # Project-based directories
        ]

        for base_path in search_paths:
            if not base_path.exists():
                continue

            # If searching in projects directory, scan all projects
            if base_path.name == "projects":
                for project_dir in base_path.iterdir():
                    if project_dir.is_dir():
                        pipeline_dir = project_dir / "pipelines"
                        if pipeline_dir.exists():
                            pipeline_file = pipeline_dir / f"{pipeline_id}.yaml"
                            if pipeline_file.exists():
                                with open(pipeline_file, 'r') as f:
                                    pipeline_yaml = f.read()
                                    found_file_path = pipeline_file
                                    break
            else:
                # Direct search in flat directory
                pipeline_file = base_path / f"{pipeline_id}.yaml"
                if pipeline_file.exists():
                    with open(pipeline_file, 'r') as f:
                        pipeline_yaml = f.read()
                        found_file_path = pipeline_file
                        break

            if pipeline_yaml:
                break

        if not pipeline_yaml:
            raise ValueError(f"Pipeline file not found: {pipeline_id}.yaml")

        # Parse YAML to check if it's a batch file
        try:
            parsed_yaml = yaml.safe_load(pipeline_yaml)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML in {pipeline_id}.yaml: {e}")

        # Check if this is a batch file (has 'batch' root key instead of 'pipeline')
        if "batch" in parsed_yaml and "batch" not in parsed_yaml.get("pipeline", {}):
            print(f"[BATCH EXECUTOR] Detected batch file: {pipeline_id}.yaml")
            batch_def = parsed_yaml["batch"]
            batch_name = batch_def.get("name", pipeline_id)
            pipelines_to_execute = batch_def.get("pipelines", [])

            if not pipelines_to_execute:
                raise ValueError(f"Batch file {pipeline_id}.yaml has no pipelines to execute")

            print(f"[BATCH EXECUTOR] Batch '{batch_name}' contains {len(pipelines_to_execute)} pipelines")

            # Execute each pipeline in the batch
            results = []
            for idx, pipeline_item in enumerate(pipelines_to_execute):
                pipeline_filename = pipeline_item.get("file")
                if not pipeline_filename:
                    print(f"[BATCH EXECUTOR] Skipping pipeline {idx+1}: no 'file' specified")
                    continue

                # Remove .yaml extension if present
                pipeline_file_id = pipeline_filename.replace(".yaml", "").replace(".yml", "")

                print(f"[BATCH EXECUTOR] Executing pipeline {idx+1}/{len(pipelines_to_execute)}: {pipeline_filename}")

                # Recursively call this method with the nested pipeline
                nested_operation = BatchOperation(
                    operation_id=f"{operation.operation_id}_nested_{idx}",
                    operation_type="pipeline_execution",
                    status=BatchOperationStatus.PENDING,
                    metadata={
                        "pipeline_id": pipeline_file_id,
                        # Add timestamp to make job name unique: Pipelinename_timestamp
                        "pipeline_name": f"{pipeline_file_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                    }
                )

                try:
                    nested_result = self._execute_pipeline_operation(nested_operation)
                    results.append(nested_result)
                    print(f"[BATCH EXECUTOR] Pipeline {pipeline_filename} completed: {nested_result.get('status')}")
                except Exception as e:
                    print(f"[BATCH EXECUTOR] Pipeline {pipeline_filename} failed: {e}")
                    results.append({
                        "pipeline_id": pipeline_file_id,
                        "status": "failed",
                        "error": str(e)
                    })
                    # Continue with next pipeline even if this one fails

            # Return consolidated result for the batch
            successful = sum(1 for r in results if r.get("status") == "pending" or r.get("status") == "completed")
            failed = sum(1 for r in results if r.get("status") == "failed")

            return {
                "run_id": f"batch_{pipeline_id}",
                "status": "completed" if failed == 0 else "partial",
                "pipeline_id": pipeline_id,
                "batch_name": batch_name,
                "total_pipelines": len(pipelines_to_execute),
                "successful": successful,
                "failed": failed,
                "results": results
            }

        # Regular pipeline file - execute normally
        logger.info(f"[BATCH EXECUTOR] Executing regular pipeline: {pipeline_id}.yaml")
        logger.info(f"[BATCH EXECUTOR] Calling POST {BACKEND_URL}/pipelines/execute")

        try:
            response = requests.post(
                f"{BACKEND_URL}/pipelines/execute",
                json={
                    "pipeline_yaml": pipeline_yaml,
                    "pipeline_name": pipeline_name
                },
                timeout=300
            )
            logger.info(f"[BATCH EXECUTOR] Pipeline execute response: status={response.status_code}")
        except Exception as req_error:
            logger.error(f"[BATCH EXECUTOR] Failed to call pipeline execute endpoint: {req_error}")
            raise Exception(f"Failed to call pipeline execute: {req_error}")

        if response.status_code != 200:
            logger.error(f"[BATCH EXECUTOR] Pipeline execute failed: {response.text}")
            raise Exception(f"Pipeline execution failed: {response.text}")

        result = response.json()
        run_id = result.get("run_id")
        logger.info(f"[BATCH EXECUTOR] Pipeline started with run_id: {run_id}")

        # Poll for completion (pipeline runs async)
        import time
        max_wait_seconds = 300  # 5 minutes max
        poll_interval = 2  # Check every 2 seconds
        elapsed = 0

        while elapsed < max_wait_seconds:
            time.sleep(poll_interval)
            elapsed += poll_interval

            try:
                status_response = requests.get(
                    f"{BACKEND_URL}/pipelines/status/{run_id}",
                    timeout=30
                )
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    current_status = status_data.get("status")
                    logger.info(f"[BATCH EXECUTOR] Pipeline {run_id} status: {current_status} (elapsed: {elapsed}s)")

                    if current_status in ["completed", "failed"]:
                        # Check for step failures
                        results = status_data.get("results", [])
                        failed_steps = [r for r in results if r.get("status") == "FAIL"]
                        logger.info(f"[BATCH EXECUTOR] Pipeline {run_id} finished: {len(results)} steps, {len(failed_steps)} failed")

                        if current_status == "failed" or failed_steps:
                            # Collect error details
                            error_messages = []
                            if status_data.get("error"):
                                error_messages.append(status_data.get("error"))
                            for step in failed_steps:
                                step_error = step.get("details", {}).get("error") or step.get("details", {}).get("message")
                                if step_error:
                                    error_messages.append(f"{step.get('name')}: {step_error}")

                            error_summary = "; ".join(error_messages) if error_messages else "Pipeline execution had failures"
                            logger.error(f"[BATCH EXECUTOR] Pipeline failed: {error_summary}")
                            raise Exception(f"Pipeline failed: {error_summary}")

                        # Success
                        logger.info(f"[BATCH EXECUTOR] Pipeline {run_id} completed successfully")
                        return {
                            "run_id": run_id,
                            "status": "completed",
                            "pipeline_id": pipeline_id,
                            "results_summary": {
                                "total_steps": len(results),
                                "passed": len([r for r in results if r.get("status") == "PASS"]),
                                "failed": len(failed_steps)
                            }
                        }
            except requests.RequestException as e:
                logger.warning(f"[BATCH EXECUTOR] Status poll failed: {e}")

        # Timeout - return pending status
        return {
            "run_id": run_id,
            "status": "timeout",
            "pipeline_id": pipeline_id,
            "message": f"Pipeline did not complete within {max_wait_seconds} seconds"
        }

    def _execute_data_gen_operation(self, operation: BatchOperation) -> Dict[str, Any]:
        """Execute a single data generation operation"""
        import requests

        data_gen_data = operation.metadata or {}
        schema_type = data_gen_data.get("schema_type")
        row_count = data_gen_data.get("row_count", 1000)

        if not schema_type:
            raise ValueError("No schema_type in operation metadata")

        # Call data generation endpoint
        response = requests.post(
            f"{BACKEND_URL}/data/generate",
            json={
                "schema_type": schema_type,
                "row_count": row_count
            },
            timeout=600
        )

        if response.status_code != 200:
            raise Exception(f"Data generation failed: {response.text}")

        result = response.json()
        return {
            "job_id": result.get("job_id"),
            "schema_type": schema_type,
            "row_count": row_count,
            "status": result.get("status")
        }

    def _execute_metadata_operation(self, operation: BatchOperation) -> Dict[str, Any]:
        """Execute a single metadata extraction operation"""
        import requests

        metadata = operation.metadata or {}
        connection_type = metadata.get("connection_type")
        schema_name = metadata.get("schema_name")

        if not connection_type:
            raise ValueError("No connection_type in operation metadata")

        # Call metadata extraction endpoint
        response = requests.post(
            f"{BACKEND_URL}/metadata/extract",
            json={
                "source": connection_type,
                "schema": schema_name
            },
            timeout=300
        )

        if response.status_code != 200:
            raise Exception(f"Metadata extraction failed: {response.text}")

        result = response.json()
        return {
            "connection_type": connection_type,
            "schema": schema_name,
            "table_count": len(result.get("tables", [])),
            "status": "success"
        }

    def _execute_project_operation(self, operation: BatchOperation) -> Dict[str, Any]:
        """Execute a multi-project validation operation"""
        import requests

        metadata = operation.metadata or {}
        project_id = metadata.get("project_id")
        pipeline_ids = metadata.get("pipeline_ids", [])

        if not project_id:
            raise ValueError("No project_id in operation metadata")

        # Execute all pipelines for this project
        results = []
        for pipeline_id in pipeline_ids:
            response = requests.post(
                f"{BACKEND_URL}/pipelines/execute",
                json={
                    "pipeline_id": pipeline_id,
                    "project_id": project_id
                },
                timeout=300
            )

            if response.status_code == 200:
                results.append({
                    "pipeline_id": pipeline_id,
                    "status": "success",
                    "result": response.json()
                })
            else:
                results.append({
                    "pipeline_id": pipeline_id,
                    "status": "failed",
                    "error": response.text
                })

        return {
            "project_id": project_id,
            "total_pipelines": len(pipeline_ids),
            "successful": sum(1 for r in results if r["status"] == "success"),
            "failed": sum(1 for r in results if r["status"] == "failed"),
            "results": results
        }

    def _execute_generic_operation(self, operation: BatchOperation) -> Dict[str, Any]:
        """Execute a generic operation"""
        # For custom operations, just simulate success
        import time
        time.sleep(1)  # Simulate work

        return {
            "operation_id": operation.operation_id,
            "status": "completed",
            "message": "Generic operation completed"
        }

    def _generate_consolidated_result(self, job: BatchJob):
        """
        Generate a unified result file that merges all individual pipeline results.
        Organizes validation steps by table in logical order.
        """
        import json
        from pathlib import Path
        from datetime import datetime
        from collections import defaultdict

        # Collect all run IDs from completed operations
        print(f"[Batch {job.job_id}] Collecting run IDs from {len(job.operations)} operations...")
        run_ids = []
        for operation in job.operations:
            if operation.status == BatchOperationStatus.COMPLETED and operation.result:
                # Check if this is a batch execution result with nested pipeline results
                if "results" in operation.result and isinstance(operation.result["results"], list):
                    # Extract run_ids from nested results (batch execution)
                    for nested_result in operation.result["results"]:
                        nested_run_id = nested_result.get("run_id")
                        if nested_run_id:
                            run_ids.append(nested_run_id)
                            print(f"[Batch {job.job_id}]   Found nested run_id: {nested_run_id}")
                else:
                    # Regular pipeline execution - single run_id
                    run_id = operation.result.get("run_id")
                    if run_id:
                        run_ids.append(run_id)
                        print(f"[Batch {job.job_id}]   Found run_id: {run_id}")

        if not run_ids:
            print(f"[Batch {job.job_id}] No completed pipeline runs to consolidate")
            return

        print(f"[Batch {job.job_id}] Found {len(run_ids)} pipeline runs to consolidate")

        # Load all pipeline results
        results_dir = paths.results_dir
        all_results = []

        for run_id in run_ids:
            result_file = results_dir / f"{run_id}.json"
            if result_file.exists():
                try:
                    with open(result_file) as f:
                        result_data = json.load(f)
                        all_results.append(result_data)
                except json.JSONDecodeError as e:
                    print(f"[WARNING] Skipping malformed result file {run_id}.json: {e}")
                    print(f"[WARNING] File may be truncated or corrupted. Pipeline likely crashed during execution.")
                    continue
                except Exception as e:
                    print(f"[WARNING] Failed to load result file {run_id}.json: {e}")
                    continue

        if not all_results:
            print(f"[Batch {job.job_id}] No result files found")
            return

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

        # Create consolidated result
        consolidated_run_id = f"batch_{job.job_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

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
            "batch_job_id": job.job_id,
            "batch_job_name": job.name,
            "pipeline_name": f"Batch Execution: {job.name}",
            "execution_type": "batch_consolidation",
            "status": "PASS" if failed == 0 else "FAIL",
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
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

        print(f"[Batch {job.job_id}] Created consolidated result: {consolidated_run_id}")
        print(f"[Batch {job.job_id}] Merged {len(all_results)} pipelines, {len(tables_data)} tables, {total_validations} validations")


# Global executor instance
batch_executor = BatchExecutor()
