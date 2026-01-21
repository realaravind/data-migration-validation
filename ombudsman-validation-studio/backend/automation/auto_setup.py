"""
Automated Project Setup

Creates pipelines and batch execution for all common tables between SQL Server and Snowflake.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import yaml
import os
from datetime import datetime
import uuid

router = APIRouter(prefix="/automation", tags=["automation"])


class AutoSetupRequest(BaseModel):
    project_id: str
    project_name: str
    snowflake_config: Dict[str, Any]


class AutoSetupResponse(BaseModel):
    success: bool
    message: str
    pipelines_created: int
    batch_id: Optional[str] = None
    batch_name: Optional[str] = None
    tables_processed: List[str]
    errors: List[str] = []


@router.post("/auto-setup-project", response_model=AutoSetupResponse)
async def auto_setup_project(request: AutoSetupRequest):
    """
    Automatically create pipelines and batch for all common tables.

    Steps:
    1. Get metadata from both SQL Server and Snowflake
    2. Find common tables
    3. For each table:
       - Analyze table
       - Suggest validations
       - Suggest custom queries
       - Create a pipeline with all suggestions
    4. Create a batch with all pipelines
    5. Execute the batch
    """
    try:
        import json
        import requests

        errors = []
        pipelines_created = []
        tables_processed = []

        print(f"[AUTO-SETUP] Starting auto-setup for project: {request.project_name}")

        # Step 1: Get metadata from both databases using the API
        print("[AUTO-SETUP] Step 1: Extracting metadata from both databases...")
        try:
            # Call the metadata extraction endpoint
            metadata_response = requests.post(
                "http://localhost:8000/metadata/extract",
                json=request.snowflake_config
            )
            if metadata_response.status_code != 200:
                raise Exception(f"Metadata extraction failed: {metadata_response.text}")

            metadata = metadata_response.json()
        except Exception as e:
            error_msg = f"Failed to extract metadata: {str(e)}"
            print(f"[AUTO-SETUP] ERROR: {error_msg}")
            return AutoSetupResponse(
                success=False,
                message=error_msg,
                pipelines_created=0,
                tables_processed=[],
                errors=[error_msg]
            )

        # Step 2: Find common tables
        print("[AUTO-SETUP] Step 2: Finding common tables...")
        sql_tables = set()
        snow_tables = set()

        for schema, tables in metadata.get("sql", {}).items():
            for table in tables.keys():
                sql_tables.add(f"{schema}.{table}")

        for schema, tables in metadata.get("snowflake", {}).items():
            for table in tables.keys():
                snow_tables.add(f"{schema}.{table}")

        common_tables = sql_tables.intersection(snow_tables)
        print(f"[AUTO-SETUP] Found {len(common_tables)} common tables: {list(common_tables)[:5]}...")

        if not common_tables:
            return AutoSetupResponse(
                success=False,
                message="No common tables found between SQL Server and Snowflake",
                pipelines_created=0,
                tables_processed=[],
                errors=["No common tables found"]
            )

        # Step 3: Create pipelines for each common table
        print(f"[AUTO-SETUP] Step 3: Creating pipelines for {len(common_tables)} tables...")

        pipelines_dir = f"pipelines/{request.project_id}"
        os.makedirs(pipelines_dir, exist_ok=True)

        for table_name in sorted(common_tables):
            try:
                schema, table = table_name.split(".")
                print(f"[AUTO-SETUP] Processing table: {table_name}")

                # Get intelligent suggestions for this table using API
                suggest_response = requests.post(
                    "http://localhost:8000/pipelines/intelligent-suggest",
                    json={
                        "metadata": metadata,
                        "schema": schema,
                        "table": table
                    }
                )

                if suggest_response.status_code == 200:
                    suggestions = suggest_response.json()
                else:
                    print(f"[AUTO-SETUP] Warning: Failed to get suggestions for {table_name}, using defaults")
                    suggestions = {"validations": [], "custom_queries": []}

                # Create pipeline YAML
                pipeline_name = f"{request.project_name}_{schema}_{table}"
                pipeline = {
                    "pipeline": {
                        "name": pipeline_name,
                        "source": {
                            "type": "sql_server",
                            "schema": schema,
                            "table": table
                        },
                        "target": {
                            "type": "snowflake",
                            "schema": schema.upper(),
                            "table": table.upper()
                        }
                    },
                    "validations": suggestions.get("validations", []),
                    "custom_queries": suggestions.get("custom_queries", [])
                }

                # Add snowflake connection config
                pipeline["snowflake"] = request.snowflake_config

                # Save pipeline using API
                save_response = requests.post(
                    "http://localhost:8000/pipelines/custom/save",
                    json={
                        "project_id": request.project_id,
                        "pipeline_name": pipeline_name,
                        "pipeline_yaml": yaml.dump(pipeline, default_flow_style=False, sort_keys=False),
                        "description": f"Automated pipeline for {table_name}",
                        "tags": ["automated", request.project_name]
                    }
                )

                if save_response.status_code == 200:
                    pipelines_created.append(pipeline_name)
                    tables_processed.append(table_name)
                    print(f"[AUTO-SETUP] Created pipeline: {pipeline_name}")
                else:
                    raise Exception(f"Failed to save pipeline: {save_response.text}")

            except Exception as e:
                error_msg = f"Failed to create pipeline for {table_name}: {str(e)}"
                print(f"[AUTO-SETUP] ERROR: {error_msg}")
                errors.append(error_msg)

        print(f"[AUTO-SETUP] Created {len(pipelines_created)} pipelines")

        # Step 4: Create a batch with all pipelines using API
        print("[AUTO-SETUP] Step 4: Creating batch execution...")
        batch_name = f"Batch_{request.project_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

        try:
            # Load all pipeline YAMLs
            pipeline_files = []
            for pipeline_name in pipelines_created:
                # Get pipeline YAML from storage
                get_response = requests.get(
                    f"http://localhost:8000/pipelines/custom/project/{request.project_id}/{pipeline_name}"
                )
                if get_response.status_code == 200:
                    pipeline_files.append({
                        "name": pipeline_name,
                        "yaml": get_response.json().get("content", "")
                    })

            # Create batch using API
            batch_response = requests.post(
                "http://localhost:8000/batch/create",
                json={
                    "name": batch_name,
                    "description": f"Automated validation for all tables in project {request.project_name}",
                    "job_type": "bulk_pipeline_execution",
                    "pipeline_files": pipeline_files
                }
            )

            if batch_response.status_code != 200:
                raise Exception(f"Failed to create batch: {batch_response.text}")

            batch_data = batch_response.json()
            batch_id = batch_data.get("job_id")

            # Step 5: Execute the batch
            print(f"[AUTO-SETUP] Step 5: Executing batch {batch_name}...")
            execute_response = requests.post(
                f"http://localhost:8000/batch/jobs/{batch_id}/execute"
            )

            if execute_response.status_code != 200:
                raise Exception(f"Failed to execute batch: {execute_response.text}")

            return AutoSetupResponse(
                success=True,
                message=f"Successfully created {len(pipelines_created)} pipelines and started batch execution",
                pipelines_created=len(pipelines_created),
                batch_id=batch_id,
                batch_name=batch_name,
                tables_processed=tables_processed,
                errors=errors
            )

        except Exception as e:
            error_msg = f"Failed to create/execute batch: {str(e)}"
            print(f"[AUTO-SETUP] ERROR: {error_msg}")
            errors.append(error_msg)

            # Return success for pipeline creation but failure for batch
            return AutoSetupResponse(
                success=False,
                message=f"Created {len(pipelines_created)} pipelines but failed to execute batch: {str(e)}",
                pipelines_created=len(pipelines_created),
                tables_processed=tables_processed,
                errors=errors
            )

    except Exception as e:
        error_msg = f"Auto-setup failed: {str(e)}"
        print(f"[AUTO-SETUP] FATAL ERROR: {error_msg}")
        return AutoSetupResponse(
            success=False,
            message=error_msg,
            pipelines_created=0,
            tables_processed=[],
            errors=[error_msg]
        )
