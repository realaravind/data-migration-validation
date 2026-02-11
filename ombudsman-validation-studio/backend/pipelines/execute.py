from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel
import yaml
import os
import json
import logging
import asyncio
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Optional

from config.paths import paths
from errors import (
    InvalidPipelineConfigError,
    PipelineNotFoundError,
    PipelineExecutionError,
    ProjectNotFoundError,
    InvalidQueryError
)
from auth.dependencies import get_current_user, require_user_or_admin, optional_authentication
from auth.models import UserInDB

logger = logging.getLogger(__name__)

router = APIRouter()

# Results directory - using centralized path config
RESULTS_DIR = paths.results_dir

# Store pipeline executions in memory (in production, use a database)
pipeline_runs = {}

# Custom JSON encoder to handle datetime, date, and Decimal objects
class CustomJSONEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

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

        # Case 2: New structure with 'columns' dict and 'object_type' keys
        # metadata: {TABLE: {columns: {COL1: TYPE1, COL2: TYPE2}, object_type: TABLE}}
        if isinstance(columns, dict) and 'columns' in columns and isinstance(columns['columns'], dict):
            numeric_columns = []
            date_columns = []
            all_columns = []

            # Iterate over the actual columns dict, not the parent dict
            for col_name, data_type in columns['columns'].items():
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
            # IMPORTANT: Preserve existing keys like foreign_keys, business_key, object_type, etc.
            enriched[table_name] = {
                **columns,  # Preserve all existing keys
                "columns": all_columns,  # For backward compatibility (validate_nulls)
                "numeric_columns": numeric_columns,
                "date_columns": date_columns,
                "all_columns": all_columns
            }
            continue

        # Case 3: Old flat dictionary of column_name: data_type (no 'columns' wrapper)
        if isinstance(columns, dict):
            numeric_columns = []
            date_columns = []
            all_columns = []

            # First pass: collect metadata keys that are NOT column definitions
            # (like foreign_keys, business_key, object_type, etc.)
            special_keys = {}
            column_data = {}

            for key, value in columns.items():
                # If value is a string, it's likely a column datatype
                if isinstance(value, str):
                    column_data[key] = value
                # If it's a dict or other structure, it's metadata (like foreign_keys)
                else:
                    special_keys[key] = value

            # Analyze column data types
            for col_name, data_type in column_data.items():
                data_type_lower = data_type.lower()
                all_columns.append(col_name)

                # Check if numeric
                if any(t in data_type_lower for t in numeric_types):
                    numeric_columns.append(col_name)

                # Check if date/time
                elif any(t in data_type_lower for t in date_types):
                    date_columns.append(col_name)

            # Create enriched metadata for this table
            # IMPORTANT: Preserve special keys like foreign_keys, business_key, etc.
            enriched[table_name] = {
                **special_keys,  # Preserve foreign_keys, business_key, etc.
                **column_data,  # Preserve original column datatypes
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
    project_id: Optional[str] = None
    batch_id: Optional[str] = None
    run_async: Optional[bool] = False

class PipelineStatus(BaseModel):
    run_id: str
    pipeline_name: str
    status: str  # pending, running, completed, failed
    started_at: str
    completed_at: Optional[str] = None
    results: List[Dict] = []


@router.post("/execute")
async def execute_pipeline(
    request: PipelineExecuteRequest,
    background_tasks: BackgroundTasks,
    current_user: Optional[UserInDB] = Depends(optional_authentication)
):
    """
    Execute a validation pipeline.

    Optional authentication - allows both authenticated users and internal batch executor calls.
    """
    try:
        # Parse YAML
        pipeline_def = yaml.safe_load(request.pipeline_yaml)

        # Extract pipeline info for validation
        pipeline = pipeline_def.get("pipeline", pipeline_def)
        num_steps = len(pipeline.get("steps", []))
        num_custom_queries = len(pipeline.get("custom_queries", []))
        logger.info(f"Received pipeline '{request.pipeline_name}' with {num_steps} steps and {num_custom_queries} custom_queries")

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
            "project_id": request.project_id,
            "batch_id": request.batch_id,
            "status": "pending",
            "started_at": datetime.now().isoformat(),
            "completed_at": None,
            "results": [],
            "pipeline_def": pipeline_def,
            "current_step": 0,
            "total_steps": len(pipeline_def.get("pipeline", pipeline_def).get("steps", [])),
            "current_step_name": None
        }

        # Execute in background using asyncio task (not BackgroundTasks which doesn't work well with async)
        asyncio.create_task(run_pipeline_async(run_id, pipeline_def, request.pipeline_name, request.project_id, request.batch_id))

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


def run_pipeline_background(run_id: str, pipeline_def: dict, pipeline_name: str):
    """Sync wrapper to run async pipeline execution in background"""
    logger.info(f"[BACKGROUND] Starting pipeline execution wrapper for run_id: {run_id}")

    # Create and run the async task
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(run_pipeline_async(run_id, pipeline_def, pipeline_name))
        loop.close()
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[BACKGROUND] Pipeline wrapper failed for {run_id}: {e}")
        logger.error(f"[BACKGROUND] Traceback:\n{error_details}")


async def run_pipeline_async(run_id: str, pipeline_def: dict, pipeline_name: str, project_id: Optional[str] = None, batch_id: Optional[str] = None):
    """Execute pipeline asynchronously"""
    logger.info(f"[ASYNC] Starting pipeline execution for run_id: {run_id}, project_id: {project_id}, batch_id: {batch_id}")

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
                    project_id=project_id,
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

        # Build config - use pipeline_def connections if provided, otherwise check active project, then fall back to environment variables
        pipeline = pipeline_def.get("pipeline", pipeline_def)

        # Check if pipeline definition includes connection config
        if "connections" in pipeline_def and "snowflake" in pipeline_def:
            cfg = pipeline_def
            print(f"[CONFIG] Using connections from pipeline_def root")
        elif "connections" in pipeline and "snowflake" in pipeline:
            cfg = pipeline
            print(f"[CONFIG] Using connections from pipeline nested")
        else:
            # Check if there's an active project
            print(f"[CONFIG] No connection config in pipeline, checking for active project")
            try:
                from projects.context import get_active_project
                active_project = get_active_project()

                if active_project:
                    # get_active_project returns the full metadata dict, not just project_id
                    if isinstance(active_project, dict):
                        metadata = active_project
                        print(f"[CONFIG] Found active project: {metadata.get('name')} (ID: {metadata.get('project_id')})")
                    else:
                        # If it's just a string (project_id), load the metadata
                        print(f"[CONFIG] Found active project ID: {active_project}")
                        project_dir = paths.get_project_dir(active_project)
                        if os.path.exists(f"{project_dir}/project.json"):
                            with open(f"{project_dir}/project.json", "r") as f:
                                metadata = json.load(f)
                        else:
                            raise Exception("Project metadata not found")

                    logger.info(f"[CONFIG] Using active project config - SQL DB: {metadata.get('sql_database')}, Snowflake DB: {metadata.get('snowflake_database')}")
                    logger.info(f"[CONFIG] SQL connection: host={os.getenv('MSSQL_HOST', 'NOT SET')}, port={os.getenv('MSSQL_PORT', '1433')}, user={os.getenv('MSSQL_USER', 'sa')}")
                    cfg = {
                        "connections": {
                            "sql": {
                                "host": os.getenv("MSSQL_HOST", "host.docker.internal"),
                                "port": os.getenv("MSSQL_PORT", "1433"),
                                "user": os.getenv("MSSQL_USER", "sa"),
                                "password": os.getenv("MSSQL_PASSWORD", ""),
                                "database": metadata.get("sql_database", "SampleDW")
                            }
                        },
                        "snowflake": {
                            "user": os.getenv("SNOWFLAKE_USER", ""),
                            "password": os.getenv("SNOWFLAKE_PASSWORD", ""),
                            "account": os.getenv("SNOWFLAKE_ACCOUNT", ""),
                            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
                            "database": metadata.get("snowflake_database", "SAMPLEDW"),
                            "schema": metadata.get("snowflake_schemas", ["PUBLIC"])[0] if metadata.get("snowflake_schemas") else "PUBLIC",
                            "role": os.getenv("SNOWFLAKE_ROLE", "")
                        }
                    }
                else:
                    raise Exception("No active project")

            except Exception as e:
                # Fall back to environment variables
                logger.warning(f"[CONFIG] No active project or error loading project ({e}), using environment variables")
                logger.info(f"[CONFIG] MSSQL_HOST from env: {os.getenv('MSSQL_HOST', 'NOT SET - using host.docker.internal')}")
                logger.info(f"[CONFIG] MSSQL_PORT from env: {os.getenv('MSSQL_PORT', '1433')}")
                logger.info(f"[CONFIG] MSSQL_USER from env: {os.getenv('MSSQL_USER', 'sa')}")
                logger.info(f"[CONFIG] MSSQL_DATABASE from env: {os.getenv('MSSQL_DATABASE', 'SampleDW')}")
                logger.info(f"[CONFIG] SNOWFLAKE_DATABASE from env: {os.getenv('SNOWFLAKE_DATABASE', 'SAMPLEDW')}")
                cfg = {
                    "connections": {
                        "sql": {
                            "host": os.getenv("MSSQL_HOST", "host.docker.internal"),
                            "port": os.getenv("MSSQL_PORT", "1433"),
                            "user": os.getenv("MSSQL_USER", "sa"),
                            "password": os.getenv("MSSQL_PASSWORD", ""),
                            "database": os.getenv("MSSQL_DATABASE", "SampleDW")
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
        logger.debug(f"Registry initialized with {len(registry.registry)} validators")

        # Extract pipeline components
        # Handle both formats: direct keys or nested under "pipeline"
        pipeline = pipeline_def.get("pipeline", pipeline_def)
        mapping = pipeline.get("mapping", {})
        metadata = pipeline.get("metadata", {})
        steps = pipeline.get("steps", [])

        # Convert custom_queries to steps and append to existing steps
        custom_queries = pipeline.get("custom_queries", [])
        logger.debug(f"[RUN {run_id}] Found {len(custom_queries)} custom_queries, {len(steps)} regular steps")
        if custom_queries:
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

        # Load actual datatypes from tables.yaml if metadata only has column names
        # This is needed because intelligent_suggest only provides column names, not datatypes
        try:
            from ombudsman.core.metadata_loader import load_metadata as load_tables_yaml
            tables_metadata = load_tables_yaml()

            # MERGE datatype information into metadata (DO NOT REPLACE)
            # This preserves foreign_keys and business_key from pipeline YAML
            for table_name in list(metadata.keys()):
                if table_name in tables_metadata:
                    # Store the existing metadata (which may have foreign_keys, business_key, etc.)
                    existing_metadata = metadata[table_name] if isinstance(metadata[table_name], dict) else {}

                    # Get new metadata from tables.yaml
                    new_metadata = tables_metadata[table_name] if isinstance(tables_metadata[table_name], dict) else {}

                    # Merge: start with new metadata, then overlay existing metadata (so existing wins)
                    metadata[table_name] = {**new_metadata, **existing_metadata}
        except Exception as e:
            logger.debug(f"Could not load tables.yaml using metadata_loader: {e}")

        # Enrich metadata with numeric_columns, date_columns, and all_columns
        metadata = enrich_metadata(metadata)
        logger.debug(f"[RUN {run_id}] Executing pipeline with {len(steps)} steps")

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

        # Create connections and execute pipeline
        logger.info(f"[PIPELINE] Attempting to create database connections...")
        sql_cfg = cfg.get('connections', {}).get('sql', {})
        snow_cfg = cfg.get('snowflake', {})
        logger.info(f"[PIPELINE] SQL Config: host={sql_cfg.get('host')}, port={sql_cfg.get('port')}, database={sql_cfg.get('database')}, user={sql_cfg.get('user')}")
        logger.info(f"[PIPELINE] Snowflake Config: account={snow_cfg.get('account')}, database={snow_cfg.get('database')}, schema={snow_cfg.get('schema')}, user={snow_cfg.get('user')}")

        # Try connections separately to identify which one fails
        sql_conn_ctx = None
        snow_conn_ctx = None
        try:
            logger.info("[PIPELINE] Creating SQL Server connection...")
            sql_conn_ctx = get_sql_conn(cfg)
            sql_conn = sql_conn_ctx.__enter__()
            logger.info("[PIPELINE] SQL Server connection established successfully")
        except Exception as sql_err:
            logger.error(f"[PIPELINE] SQL Server connection FAILED: {type(sql_err).__name__}: {sql_err}")
            import traceback
            logger.error(f"[PIPELINE] SQL Traceback: {traceback.format_exc()}")
            raise Exception(f"SQL Server connection failed: {sql_err}")

        try:
            logger.info("[PIPELINE] Creating Snowflake connection...")
            snow_conn_ctx = get_snow_conn(cfg)
            snow_conn = snow_conn_ctx.__enter__()
            logger.info("[PIPELINE] Snowflake connection established successfully")
        except Exception as snow_err:
            logger.error(f"[PIPELINE] Snowflake connection FAILED: {type(snow_err).__name__}: {snow_err}")
            import traceback
            logger.error(f"[PIPELINE] Snowflake Traceback: {traceback.format_exc()}")
            if sql_conn_ctx:
                sql_conn_ctx.__exit__(None, None, None)
            raise Exception(f"Snowflake connection failed: {snow_err}")

        try:
            logger.info("[PIPELINE] Both database connections established successfully")
            # Create executor
            executor = StepExecutor(
                registry=registry,
                sql_conn=sql_conn,
                snow_conn=snow_conn,
                mapping=mapping,
                metadata=metadata
            )

            # Create JSON logger for pipeline execution
            json_logger = JsonLogger()

            # Run pipeline with real-time event emission
            runner = PipelineRunner(executor, json_logger, cfg)

            # Emit step events during execution
            results = []
            for i, step in enumerate(steps):
                step_name = step.get("name", f"Step {i+1}")
                validator_type = step.get("validator", step.get("name"))

                # Update progress in pipeline_runs
                pipeline_runs[run_id]["current_step"] = i + 1
                pipeline_runs[run_id]["current_step_name"] = step_name

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
        try:
            with open(f"{RESULTS_DIR}/{run_id}.json", "w") as f:
                json.dump(pipeline_runs[run_id], f, indent=2, cls=CustomJSONEncoder)
            logger.info(f"Pipeline results saved to {RESULTS_DIR}/{run_id}.json")
        except TypeError as e:
            logger.error(f"Failed to serialize pipeline results for {run_id}: {e}")
            # Try saving with a safer fallback (convert to string representation)
            with open(f"{RESULTS_DIR}/{run_id}.json", "w") as f:
                json.dump({
                    "run_id": run_id,
                    "error": f"Failed to serialize results: {str(e)}",
                    "raw_data": str(pipeline_runs[run_id])
                }, f, indent=2)

        finally:
            # Clean up connections
            if sql_conn_ctx:
                try:
                    sql_conn_ctx.__exit__(None, None, None)
                    logger.info("[PIPELINE] SQL Server connection closed")
                except:
                    pass
            if snow_conn_ctx:
                try:
                    snow_conn_ctx.__exit__(None, None, None)
                    logger.info("[PIPELINE] Snowflake connection closed")
                except:
                    pass

    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        logger.error(f"[ASYNC] Pipeline execution failed for {run_id}: {e}")
        logger.error(f"[ASYNC] Traceback:\n{error_details}")
        print(f"[ASYNC ERROR] Pipeline {run_id} failed: {e}\n{error_details}", flush=True)

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
async def get_pipeline_status(
    run_id: str,
    current_user: Optional[UserInDB] = Depends(optional_authentication)
):
    """
    Get status of a pipeline execution.

    Authentication: Optional (public endpoint)
    """
    if run_id not in pipeline_runs:
        raise PipelineNotFoundError(pipeline_id=run_id)

    return pipeline_runs[run_id]


@router.get("/list")
async def list_pipelines(
    current_user: Optional[UserInDB] = Depends(optional_authentication)
):
    """
    List all pipeline executions.

    Authentication: Optional (public endpoint)
    """
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
async def delete_pipeline_run(
    run_id: str,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Delete a pipeline run.

    Requires: User or Admin role
    """
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

PROJECTS_DIR = paths.projects_dir  # Using centralized path config

class SavePipelineRequest(BaseModel):
    project_id: str
    pipeline_name: str
    pipeline_yaml: str
    description: Optional[str] = ""
    tags: Optional[List[str]] = []


@router.post("/custom/save")
async def save_custom_pipeline(
    request: SavePipelineRequest,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Save a custom pipeline to a project.

    Requires: User or Admin role
    """
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
        logger.debug(f"Loading pipeline from file: {pipeline_file}")
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
async def delete_custom_pipeline(
    project_id: str,
    pipeline_name: str,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Delete a custom pipeline.

    Requires: User or Admin role
    """
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
