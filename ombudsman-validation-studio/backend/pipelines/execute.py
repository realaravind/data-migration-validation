from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel
import yaml
import os
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional

from errors import (
    InvalidPipelineConfigError,
    PipelineNotFoundError,
    PipelineExecutionError,
    ProjectNotFoundError,
    InvalidQueryError
)

logger = logging.getLogger(__name__)

router = APIRouter()

# Results directory
RESULTS_DIR = "results"

# Store pipeline executions in memory (in production, use a database)
pipeline_runs = {}

def load_existing_runs():
    """Load existing pipeline runs from disk on startup"""
    global pipeline_runs

    if not os.path.exists(RESULTS_DIR):
        os.makedirs(RESULTS_DIR, exist_ok=True)
        return

    for filename in os.listdir(RESULTS_DIR):
        if filename.endswith('.json'):
            try:
                filepath = os.path.join(RESULTS_DIR, filename)
                with open(filepath, 'r') as f:
                    run_data = json.load(f)
                    run_id = run_data.get('run_id')
                    if run_id:
                        pipeline_runs[run_id] = run_data
            except Exception as e:
                print(f"Failed to load {filename}: {e}")

    print(f"Loaded {len(pipeline_runs)} existing pipeline runs from disk")

# Load existing runs on module import
load_existing_runs()


def validate_pipeline_config(pipeline_def):
    """
    Validate pipeline configuration before execution.

    Returns: (is_valid, error_message)
    """
    try:
        # Handle both formats: direct keys or nested under "pipeline"
        pipeline = pipeline_def.get("pipeline", pipeline_def)

        # Check required fields
        if not isinstance(pipeline, dict):
            return False, "Pipeline configuration must be a dictionary"

        # Get steps
        steps = pipeline.get("steps", [])
        custom_queries = pipeline.get("custom_queries", [])

        if not steps and not custom_queries:
            return False, "Pipeline must have either 'steps' or 'custom_queries'"

        # Validate steps structure
        if steps:
            if not isinstance(steps, list):
                return False, "'steps' must be a list"

            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    return False, f"Step {i+1} must be a dictionary"

                if "name" not in step:
                    return False, f"Step {i+1} missing required 'name' field"

                # Config is optional but should be dict if present
                if "config" in step and not isinstance(step["config"], dict):
                    return False, f"Step {i+1} 'config' must be a dictionary"

        # Validate custom_queries structure
        if custom_queries:
            if not isinstance(custom_queries, list):
                return False, "'custom_queries' must be a list"

            for i, query in enumerate(custom_queries):
                if not isinstance(query, dict):
                    return False, f"Custom query {i+1} must be a dictionary"

                if "sql_query" not in query and "snow_query" not in query:
                    return False, f"Custom query {i+1} must have either 'sql_query' or 'snow_query'"

        return True, None

    except Exception as e:
        return False, f"Pipeline validation error: {str(e)}"


def enrich_metadata(metadata):
    """
    Enrich metadata by analyzing column data types and categorizing them.

    Transforms flat column dictionaries like:
        {"table": {"col1": "INT", "col2": "VARCHAR"}}

    Into enriched format like:
        {"table": {
            "numeric_columns": ["col1"],
            "date_columns": [],
            "all_columns": ["col1", "col2"]
        }}
    """
    if not metadata or not isinstance(metadata, dict):
        return metadata

    enriched = {}

    # Numeric data types for both SQL Server and Snowflake
    numeric_types = [
        'int', 'integer', 'smallint', 'tinyint', 'bigint',
        'decimal', 'numeric', 'money', 'smallmoney',
        'float', 'real', 'double', 'number'
    ]

    # Date/time data types
    date_types = [
        'date', 'datetime', 'datetime2', 'smalldatetime',
        'time', 'timestamp', 'timestamp_ltz', 'timestamp_ntz', 'timestamp_tz'
    ]

    for table_name, columns in metadata.items():
        # If already enriched (has numeric_columns key), skip
        if isinstance(columns, dict) and 'numeric_columns' in columns:
            enriched[table_name] = columns
            continue

        # Case 1: columns is a dict with 'columns' key containing list of column names (no datatypes)
        # This is the format from intelligent_suggest - we can't determine types without datatypes
        if isinstance(columns, dict) and 'columns' in columns and isinstance(columns.get('columns'), list):
            # We have column names but no datatypes, so we can't categorize
            # Just add empty numeric_columns, date_columns, all_columns
            col_list = columns.get('columns', [])
            enriched[table_name] = {
                "columns": col_list,
                "numeric_columns": [],  # Can't determine without datatypes
                "date_columns": [],     # Can't determine without datatypes
                "all_columns": col_list
            }
            continue

        # Case 2: columns is a flat dictionary of column_name: data_type
        if isinstance(columns, dict):
            numeric_columns = []
            date_columns = []
            all_columns = []

            for col_name, data_type in columns.items():
                if not isinstance(data_type, str):
                    continue

                data_type_lower = data_type.lower()
                all_columns.append(col_name)

                # Check if numeric
                if any(t in data_type_lower for t in numeric_types):
                    numeric_columns.append(col_name)

                # Check if date/time
                elif any(t in data_type_lower for t in date_types):
                    date_columns.append(col_name)

            # Create enriched metadata for this table
            enriched[table_name] = {
                "columns": all_columns,  # For backward compatibility (validate_nulls)
                "numeric_columns": numeric_columns,
                "date_columns": date_columns,
                "all_columns": all_columns
            }
        else:
            # Pass through if format is unexpected
            enriched[table_name] = columns

    return enriched


class PipelineExecuteRequest(BaseModel):
    pipeline_yaml: str
    pipeline_name: Optional[str] = "unnamed_pipeline"

class PipelineStatus(BaseModel):
    run_id: str
    pipeline_name: str
    status: str  # pending, running, completed, failed
    started_at: str
    completed_at: Optional[str] = None
    results: List[Dict] = []


@router.post("/execute")
async def execute_pipeline(request: PipelineExecuteRequest, background_tasks: BackgroundTasks):
    """Execute a validation pipeline"""
    try:
        # Parse YAML
        pipeline_def = yaml.safe_load(request.pipeline_yaml)

        # Validate pipeline configuration
        is_valid, error_msg = validate_pipeline_config(pipeline_def)
        if not is_valid:
            raise InvalidPipelineConfigError(
                message=error_msg,
                details={"pipeline_yaml": request.pipeline_yaml[:500]}  # First 500 chars for context
            )

        # Generate run ID
        run_id = f"run_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        # Initialize run status
        pipeline_runs[run_id] = {
            "run_id": run_id,
            "pipeline_name": request.pipeline_name,
            "status": "pending",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "results": [],
            "pipeline_def": pipeline_def
        }

        # Execute in background
        background_tasks.add_task(run_pipeline_async, run_id, pipeline_def, request.pipeline_name)

        return {
            "run_id": run_id,
            "status": "pending",
            "message": "Pipeline execution started",
            "validation": "passed"
        }

    except yaml.YAMLError as e:
        raise InvalidQueryError(
            message=f"Invalid YAML syntax: {str(e)}",
            query=request.pipeline_yaml[:500]
        )
    except InvalidPipelineConfigError:
        raise
    except Exception as e:
        raise PipelineExecutionError(
            message=f"Failed to start pipeline execution: {str(e)}",
            details={"pipeline_name": request.pipeline_name}
        )


async def run_pipeline_async(run_id: str, pipeline_def: dict, pipeline_name: str):
    """Execute pipeline asynchronously"""
    # Import database repository
    from database import (
        ResultsRepository, PipelineRunCreate, PipelineRunUpdate,
        ValidationStepCreate, ValidationStepUpdate,
        PipelineStatus as DBPipelineStatus, StepStatus, LogLevel
    )

    # Import WebSocket event emitter
    from ws.pipeline_events import PipelineEventEmitter

    # Initialize repository (optional - only if database is configured)
    repo = None
    try:
        repo = ResultsRepository()
        logger.info("Database repository initialized for results persistence")
    except Exception as e:
        logger.warning(f"Database repository not available: {e}. Results will only be saved to JSON files.")

    # Initialize event emitter for real-time updates
    emitter = PipelineEventEmitter(run_id)

    try:
        # Update status
        pipeline_runs[run_id]["status"] = "running"

        # Emit pipeline started event
        await emitter.pipeline_started(
            pipeline_name=pipeline_name,
            total_steps=len(pipeline_def.get("pipeline", pipeline_def).get("steps", [])),
            config=pipeline_def
        )

        # Create pipeline run in database
        if repo:
            try:
                repo.create_pipeline_run(PipelineRunCreate(
                    run_id=run_id,
                    project_id=None,  # TODO: Extract from request if available
                    pipeline_name=pipeline_name,
                    pipeline_config=pipeline_def,
                    executed_by="system"  # TODO: Get from auth context
                ))
                repo.update_pipeline_run(run_id, PipelineRunUpdate(status=DBPipelineStatus.RUNNING))
            except Exception as e:
                logger.error(f"Failed to create pipeline run in database: {e}")

        # Import ombudsman core libraries
        from ombudsman.pipeline.pipeline_runner import PipelineRunner
        from ombudsman.pipeline.step_executor import StepExecutor
        from ombudsman.logging.json_logger import JsonLogger
        from ombudsman.core.registry import ValidationRegistry
        from ombudsman.core.connections import get_sql_conn, get_snow_conn

        # Build config from environment variables (no config file needed)
        cfg = {
            "connections": {
                "sql": {
                    "host": os.getenv("SQL_SERVER_HOST", "sqlserver"),
                    "port": os.getenv("SQL_SERVER_PORT", "1433"),
                    "user": os.getenv("SQL_SERVER_USER", "sa"),
                    "password": os.getenv("SQL_SERVER_PASSWORD", "YourStrong!Passw0rd"),
                    "database": os.getenv("SQL_DATABASE", "SampleDW")
                }
            },
            "snowflake": {
                "user": os.getenv("SNOWFLAKE_USER", ""),
                "password": os.getenv("SNOWFLAKE_PASSWORD", ""),
                "account": os.getenv("SNOWFLAKE_ACCOUNT", ""),
                "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
                "database": os.getenv("SNOWFLAKE_DATABASE", "SAMPLEDW"),
                "schema": os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
            }
        }

        # Initialize registry
        registry = ValidationRegistry()
        from ombudsman.bootstrap import register_validators
        register_validators(registry)

        # Register custom_sql validator for workload-based comparative validations
        from validation.validate_custom_sql import validate_custom_sql
        registry.register("custom_sql", validate_custom_sql, "comparative")
        print(f"[DEBUG] Custom SQL validator registered successfully")

        # Debug: Log registered validators
        print(f"[DEBUG] Registry initialized with {len(registry.registry)} validators")
        print(f"[DEBUG] Registered validator names: {sorted(list(registry.registry.keys()))}")
        print(f"[DEBUG] custom_sql in registry: {'custom_sql' in registry.registry}")

        # Create connections
        sql_conn = get_sql_conn(cfg)
        snow_conn = get_snow_conn(cfg)

        # Extract pipeline components
        # Handle both formats: direct keys or nested under "pipeline"
        pipeline = pipeline_def.get("pipeline", pipeline_def)
        mapping = pipeline.get("mapping", {})
        metadata = pipeline.get("metadata", {})
        steps = pipeline.get("steps", [])

        # Convert custom_queries to steps if present
        custom_queries = pipeline.get("custom_queries", [])
        if custom_queries and not steps:
            print(f"[DEBUG] Converting {len(custom_queries)} custom_queries to steps")
            steps = []
            for query in custom_queries:
                # Build config object with all parameters for the validator
                config = {
                    "sql_server_query": query.get("sql_query", ""),
                    "snowflake_query": query.get("snow_query", ""),
                    "compare_mode": "result_set",  # Default for custom queries
                    "comparison_type": query.get("comparison_type", "aggregation"),
                }
                # Add optional fields
                if "tolerance" in query:
                    config["tolerance"] = query["tolerance"]
                if "limit" in query:
                    config["limit"] = query["limit"]

                step = {
                    "name": query.get("name", "Unnamed Query"),
                    "validator": "custom_sql",
                    "config": config
                }
                steps.append(step)
            print(f"[DEBUG] Converted custom_queries to {len(steps)} steps")

        # Load actual datatypes from tables.yaml if metadata only has column names
        # This is needed because intelligent_suggest only provides column names, not datatypes
        try:
            from ombudsman.core.metadata_loader import load_metadata as load_tables_yaml
            tables_metadata = load_tables_yaml()

            # Merge datatype information into metadata
            for table_name in list(metadata.keys()):
                if table_name in tables_metadata:
                    # Replace the metadata with the full datatype info from tables.yaml
                    metadata[table_name] = tables_metadata[table_name]
                    print(f"[DEBUG] Loaded datatypes for '{table_name}' from tables.yaml")
                else:
                    print(f"[DEBUG] Table '{table_name}' not found in tables.yaml")
        except Exception as e:
            print(f"[DEBUG] Could not load tables.yaml using metadata_loader: {e}")

        # Enrich metadata with numeric_columns, date_columns, and all_columns
        # This analyzes the column data types and categorizes them
        print(f"[DEBUG] Metadata BEFORE enrichment: {list(metadata.keys()) if metadata else 'None'}")
        if metadata:
            first_table = list(metadata.keys())[0] if metadata else None
            if first_table:
                print(f"[DEBUG] First table '{first_table}' metadata structure: {list(metadata[first_table].keys()) if isinstance(metadata[first_table], dict) else type(metadata[first_table])}")

        metadata = enrich_metadata(metadata)

        print(f"[DEBUG] Metadata AFTER enrichment: {list(metadata.keys()) if metadata else 'None'}")
        if metadata:
            first_table = list(metadata.keys())[0] if metadata else None
            if first_table:
                print(f"[DEBUG] First table '{first_table}' metadata after enrichment: {list(metadata[first_table].keys()) if isinstance(metadata[first_table], dict) else type(metadata[first_table])}")
                if isinstance(metadata[first_table], dict) and 'numeric_columns' in metadata[first_table]:
                    print(f"[DEBUG] numeric_columns for '{first_table}': {metadata[first_table]['numeric_columns']}")

        # Debug: Log steps to execute
        print(f"[DEBUG] Pipeline has {len(steps)} steps to execute")
        for i, step in enumerate(steps):
            step_name = step.get("name", "UNKNOWN")
            print(f"[DEBUG] Step {i+1}: {step_name}")

        # Monkey-patch StepExecutor.run_step to support 'validator' field
        original_run_step = StepExecutor.run_step
        def patched_run_step(self, step):
            # Use 'validator' field if present, otherwise fall back to 'name'
            validator_name = step.get("validator", step.get("name"))
            # Temporarily override the name field for the original method
            original_name = step.get("name")
            step["name"] = validator_name
            result = original_run_step(self, step)
            # Restore original name
            step["name"] = original_name
            # But use original name in the result
            result.name = original_name
            return result

        StepExecutor.run_step = patched_run_step

        # Create executor
        executor = StepExecutor(
            registry=registry,
            sql_conn=sql_conn,
            snow_conn=snow_conn,
            mapping=mapping,
            metadata=metadata
        )

        # Create logger
        logger = JsonLogger()

        # Run pipeline with real-time event emission
        runner = PipelineRunner(executor, logger, cfg)

        # Emit step events during execution
        results = []
        for i, step in enumerate(steps):
            step_name = step.get("name", f"Step {i+1}")
            validator_type = step.get("validator", step.get("name"))

            # Emit step started
            await emitter.step_started(
                step_name=step_name,
                step_order=i,
                validator_type=validator_type,
                config=step.get("config")
            )

            # Execute step
            try:
                result = executor.run_step(step)
                results.append(result)

                # Emit step completed
                result_dict = result.to_dict() if hasattr(result, 'to_dict') else result
                await emitter.step_completed(
                    step_name=step_name,
                    step_order=i,
                    status=result_dict.get("status", "passed"),
                    result=result_dict
                )

            except Exception as step_error:
                # Emit step failed
                await emitter.step_failed(
                    step_name=step_name,
                    step_order=i,
                    error_message=str(step_error)
                )
                raise

        # Convert results to dict
        results_dict = [r.to_dict() if hasattr(r, 'to_dict') else r for r in results]

        # Calculate summary statistics
        start_time = datetime.fromisoformat(pipeline_runs[run_id]["started_at"])
        end_time = datetime.now()
        duration_seconds = int((end_time - start_time).total_seconds())

        successful_steps = sum(1 for r in results_dict if r.get('status') == 'passed')
        failed_steps = sum(1 for r in results_dict if r.get('status') == 'failed')
        warnings_count = sum(1 for r in results_dict if r.get('status') == 'warning')

        # Update status
        pipeline_runs[run_id]["status"] = "completed"
        pipeline_runs[run_id]["completed_at"] = end_time.isoformat()
        pipeline_runs[run_id]["results"] = results_dict

        # Emit pipeline completed event
        await emitter.pipeline_completed(
            pipeline_name=pipeline_name,
            duration_seconds=duration_seconds,
            total_steps=len(results_dict),
            successful_steps=successful_steps,
            failed_steps=failed_steps,
            warnings_count=warnings_count
        )

        # Save to database
        if repo:
            try:
                # Update pipeline run
                repo.update_pipeline_run(run_id, PipelineRunUpdate(
                    status=DBPipelineStatus.COMPLETED,
                    completed_at=end_time,
                    duration_seconds=duration_seconds,
                    total_steps=len(results_dict),
                    successful_steps=successful_steps,
                    failed_steps=failed_steps,
                    warnings_count=warnings_count,
                    errors_count=failed_steps
                ))

                # Save validation steps
                for i, result in enumerate(results_dict):
                    step_status = StepStatus.PASSED
                    if result.get('status') == 'failed':
                        step_status = StepStatus.FAILED
                    elif result.get('status') == 'warning':
                        step_status = StepStatus.WARNING

                    # Create step
                    step = repo.create_validation_step(ValidationStepCreate(
                        run_id=run_id,
                        step_name=result.get('name', f'Step {i+1}'),
                        step_order=i,
                        validator_type=result.get('validator_type'),
                        step_config=result.get('config')
                    ))

                    # Update with results
                    repo.update_validation_step(step.step_id, ValidationStepUpdate(
                        status=step_status,
                        completed_at=end_time,
                        duration_milliseconds=result.get('duration_ms'),
                        result_message=result.get('message'),
                        difference_type=result.get('difference_type'),
                        total_rows=result.get('total_rows'),
                        differing_rows_count=result.get('differing_rows'),
                        affected_columns=result.get('affected_columns'),
                        comparison_details=result.get('comparison_details'),
                        sql_row_count=result.get('sql_row_count'),
                        snowflake_row_count=result.get('snowflake_row_count'),
                        match_percentage=result.get('match_percentage'),
                        error_message=result.get('error')
                    ))

                logger.info(f"Pipeline run {run_id} saved to database successfully")
            except Exception as e:
                logger.error(f"Failed to save pipeline results to database: {e}")

        # Save results to file
        os.makedirs(RESULTS_DIR, exist_ok=True)
        with open(f"{RESULTS_DIR}/{run_id}.json", "w") as f:
            json.dump(pipeline_runs[run_id], f, indent=2)

    except Exception as e:
        pipeline_runs[run_id]["status"] = "failed"
        pipeline_runs[run_id]["completed_at"] = datetime.now().isoformat()
        pipeline_runs[run_id]["error"] = str(e)

        # Emit pipeline failed event
        try:
            start_time = datetime.fromisoformat(pipeline_runs[run_id]["started_at"])
            duration_seconds = int((datetime.now() - start_time).total_seconds())
            await emitter.pipeline_failed(
                pipeline_name=pipeline_name,
                error_message=str(e),
                duration_seconds=duration_seconds
            )
        except Exception as emit_error:
            logger.error(f"Failed to emit pipeline failed event: {emit_error}")

        # Update database
        if repo:
            try:
                repo.update_pipeline_run(run_id, PipelineRunUpdate(
                    status=DBPipelineStatus.FAILED,
                    completed_at=datetime.now(),
                    error_message=str(e)
                ))
                repo.add_execution_log(
                    run_id=run_id,
                    log_level=LogLevel.ERROR,
                    message=f"Pipeline execution failed: {str(e)}",
                    context={"error_type": type(e).__name__}
                )
            except Exception as db_error:
                logger.error(f"Failed to update database with error status: {db_error}")

        print(f"Pipeline execution failed: {e}")


@router.get("/status/{run_id}")
async def get_pipeline_status(run_id: str):
    """Get status of a pipeline execution"""
    if run_id not in pipeline_runs:
        raise PipelineNotFoundError(pipeline_id=run_id)

    return pipeline_runs[run_id]


@router.get("/list")
async def list_pipelines():
    """List all pipeline executions"""
    return {
        "pipelines": [
            {
                "run_id": run_id,
                "pipeline_name": info["pipeline_name"],
                "status": info["status"],
                "started_at": info["started_at"],
                "completed_at": info.get("completed_at")
            }
            for run_id, info in pipeline_runs.items()
        ]
    }


@router.get("/templates")
async def list_pipeline_templates():
    """List available pipeline templates"""
    templates_dir = "pipelines/templates"
    templates = []

    if os.path.exists(templates_dir):
        for file in os.listdir(templates_dir):
            if file.endswith((".yaml", ".yml")):
                with open(os.path.join(templates_dir, file)) as f:
                    content = f.read()
                templates.append({
                    "name": file.replace(".yaml", "").replace(".yml", ""),
                    "filename": file,
                    "content": content
                })

    return {"templates": templates}


@router.get("/defaults")
async def list_default_pipelines():
    """List default validation pipelines"""
    defaults_dir = "pipelines/defaults"
    defaults = []

    if os.path.exists(defaults_dir):
        for file in os.listdir(defaults_dir):
            if file.endswith((".yaml", ".yml")):
                filepath = os.path.join(defaults_dir, file)
                with open(filepath) as f:
                    content = f.read()
                    pipeline_def = yaml.safe_load(content)

                defaults.append({
                    "id": file.replace(".yaml", "").replace(".yml", ""),
                    "name": pipeline_def.get("pipeline", {}).get("name", file),
                    "description": pipeline_def.get("pipeline", {}).get("description", ""),
                    "type": pipeline_def.get("pipeline", {}).get("type", "general"),
                    "category": pipeline_def.get("pipeline", {}).get("category", ""),
                    "filename": file,
                    "content": content
                })

    return {
        "defaults": defaults,
        "count": len(defaults)
    }


@router.get("/defaults/{pipeline_id}")
async def get_default_pipeline(pipeline_id: str):
    """Get a specific default pipeline by ID"""
    defaults_dir = "pipelines/defaults"
    filepath = os.path.join(defaults_dir, f"{pipeline_id}.yaml")

    # Try .yml extension if .yaml doesn't exist
    if not os.path.exists(filepath):
        filepath = os.path.join(defaults_dir, f"{pipeline_id}.yml")

    if not os.path.exists(filepath):
        raise PipelineNotFoundError(pipeline_id=pipeline_id)

    with open(filepath) as f:
        content = f.read()
        pipeline_def = yaml.safe_load(content)

    return {
        "id": pipeline_id,
        "name": pipeline_def.get("pipeline", {}).get("name", pipeline_id),
        "description": pipeline_def.get("pipeline", {}).get("description", ""),
        "type": pipeline_def.get("pipeline", {}).get("type", "general"),
        "category": pipeline_def.get("pipeline", {}).get("category", ""),
        "content": content,
        "parsed": pipeline_def
    }


@router.delete("/{run_id}")
async def delete_pipeline_run(run_id: str):
    """Delete a pipeline run"""
    if run_id in pipeline_runs:
        del pipeline_runs[run_id]

        # Delete results file
        results_file = f"{RESULTS_DIR}/{run_id}.json"
        if os.path.exists(results_file):
            os.remove(results_file)

        return {"message": "Pipeline run deleted"}

    raise PipelineNotFoundError(pipeline_id=run_id)


# ========================================
# Custom Pipeline Management for Projects
# ========================================

PROJECTS_DIR = "/data/projects"  # Same as projects/manager.py

class SavePipelineRequest(BaseModel):
    project_id: str
    pipeline_name: str
    pipeline_yaml: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = []


@router.post("/custom/save")
async def save_custom_pipeline(request: SavePipelineRequest):
    """Save a custom pipeline to a project"""
    try:
        # Validate project exists
        project_dir = f"{PROJECTS_DIR}/{request.project_id}"
        print(f"[Pipeline Save] Looking for project at: {project_dir}")
        print(f"[Pipeline Save] PROJECTS_DIR exists: {os.path.exists(PROJECTS_DIR)}")
        if os.path.exists(PROJECTS_DIR):
            print(f"[Pipeline Save] Projects found: {os.listdir(PROJECTS_DIR)}")

        if not os.path.exists(project_dir):
            raise ProjectNotFoundError(project_id=request.project_id)

        # Create pipelines directory for project
        pipelines_dir = f"{project_dir}/pipelines"
        os.makedirs(pipelines_dir, exist_ok=True)

        # Validate YAML
        try:
            pipeline_def = yaml.safe_load(request.pipeline_yaml)
        except yaml.YAMLError as e:
            raise InvalidQueryError(
                message=f"Invalid YAML syntax: {str(e)}",
                query=request.pipeline_yaml[:500]
            )

        # Save pipeline
        pipeline_file = f"{pipelines_dir}/{request.pipeline_name}.yaml"
        with open(pipeline_file, "w") as f:
            f.write(request.pipeline_yaml)

        # Save metadata
        metadata_file = f"{pipelines_dir}/{request.pipeline_name}.meta.json"
        metadata = {
            "pipeline_name": request.pipeline_name,
            "description": request.description,
            "tags": request.tags,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"Pipeline '{request.pipeline_name}' saved successfully",
            "pipeline_file": pipeline_file
        }

    except (ProjectNotFoundError, InvalidQueryError):
        raise
    except Exception as e:
        raise PipelineExecutionError(
            message=f"Failed to save pipeline: {str(e)}",
            details={"project_id": request.project_id, "pipeline_name": request.pipeline_name}
        )


@router.get("/custom/project/{project_id}")
async def list_custom_pipelines(project_id: str):
    """List all custom pipelines for a project"""
    try:
        pipelines_dir = f"{PROJECTS_DIR}/{project_id}/pipelines"

        if not os.path.exists(pipelines_dir):
            return {"pipelines": []}

        pipelines = []
        for file in os.listdir(pipelines_dir):
            if file.endswith(".yaml") or file.endswith(".yml"):
                pipeline_name = file.replace(".yaml", "").replace(".yml", "")

                # Load metadata if exists
                meta_file = f"{pipelines_dir}/{pipeline_name}.meta.json"
                metadata = {}
                if os.path.exists(meta_file):
                    with open(meta_file) as f:
                        metadata = json.load(f)

                pipelines.append({
                    "pipeline_name": pipeline_name,
                    "filename": file,
                    "description": metadata.get("description", ""),
                    "tags": metadata.get("tags", []),
                    "created_at": metadata.get("created_at", ""),
                    "updated_at": metadata.get("updated_at", "")
                })

        return {
            "project_id": project_id,
            "pipelines": pipelines,
            "count": len(pipelines)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list pipelines: {str(e)}")


@router.get("/custom/project/{project_id}/{pipeline_name}")
async def get_custom_pipeline(project_id: str, pipeline_name: str):
    """Get a specific custom pipeline"""
    try:
        pipelines_dir = f"{PROJECTS_DIR}/{project_id}/pipelines"
        pipeline_file = f"{pipelines_dir}/{pipeline_name}.yaml"

        if not os.path.exists(pipeline_file):
            pipeline_file = f"{pipelines_dir}/{pipeline_name}.yml"

        if not os.path.exists(pipeline_file):
            raise PipelineNotFoundError(pipeline_id=f"{project_id}/{pipeline_name}")

        # Load pipeline YAML
        with open(pipeline_file) as f:
            content = f.read()
            pipeline_def = yaml.safe_load(content)

        # Load metadata
        meta_file = f"{pipelines_dir}/{pipeline_name}.meta.json"
        metadata = {}
        if os.path.exists(meta_file):
            with open(meta_file) as f:
                metadata = json.load(f)

        return {
            "pipeline_name": pipeline_name,
            "content": content,
            "parsed": pipeline_def,
            "metadata": metadata
        }

    except PipelineNotFoundError:
        raise
    except Exception as e:
        raise PipelineExecutionError(
            message=f"Failed to load pipeline: {str(e)}",
            details={"project_id": project_id, "pipeline_name": pipeline_name}
        )


@router.delete("/custom/project/{project_id}/{pipeline_name}")
async def delete_custom_pipeline(project_id: str, pipeline_name: str):
    """Delete a custom pipeline"""
    try:
        pipelines_dir = f"{PROJECTS_DIR}/{project_id}/pipelines"
        pipeline_file = f"{pipelines_dir}/{pipeline_name}.yaml"
        meta_file = f"{pipelines_dir}/{pipeline_name}.meta.json"

        if not os.path.exists(pipeline_file):
            pipeline_file = f"{pipelines_dir}/{pipeline_name}.yml"

        if not os.path.exists(pipeline_file):
            raise PipelineNotFoundError(pipeline_id=f"{project_id}/{pipeline_name}")

        # Delete files
        os.remove(pipeline_file)
        if os.path.exists(meta_file):
            os.remove(meta_file)

        return {
            "status": "success",
            "message": f"Pipeline '{pipeline_name}' deleted successfully"
        }

    except PipelineNotFoundError:
        raise
    except Exception as e:
        raise PipelineExecutionError(
            message=f"Failed to delete pipeline: {str(e)}",
            details={"project_id": project_id, "pipeline_name": pipeline_name}
        )
