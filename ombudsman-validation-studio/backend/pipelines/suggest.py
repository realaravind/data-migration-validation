from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import yaml
import os
import json

router = APIRouter()

# Save path for pipeline suggestions
SAVE_PATH = "pipeline_suggestions.json"


class TableAnalysisRequest(BaseModel):
    """Request to analyze a table and suggest validations"""
    table_name: str
    schema: str
    database_type: str  # 'sql' or 'snow'
    columns: List[Dict[str, Any]]  # Column metadata
    relationships: Optional[List[Dict[str, Any]]] = []  # FK relationships


class PipelineGenerateRequest(BaseModel):
    """General pipeline generation request"""
    metadata: Dict[str, Any]
    table_type: Optional[str] = "fact"  # 'fact' or 'dimension'


@router.post("/generate")
async def generate_pipeline(request: PipelineGenerateRequest):
    """
    Generate a validation pipeline based on table metadata.

    This endpoint analyzes table metadata and intelligently suggests
    appropriate validation checks based on:
    - Column types (numeric, date, string)
    - Column semantics (identifiers, measures, attributes)
    - Table relationships (foreign keys)
    - Business context (fact vs dimension)

    Returns a complete pipeline YAML ready for execution.
    """
    try:
        metadata = request.metadata
        table_type = request.table_type

        # Extract table information from metadata
        if not metadata:
            raise HTTPException(status_code=400, detail="Metadata is required")

        # Handle different metadata formats
        # Format 1: {"table_name": {"columns": [...], "relationships": [...]}}
        # Format 2: {"source": [...], "target": [...]}
        # Format 3: Direct column list

        table_name = None
        columns = []
        relationships = []
        schema = "dbo"

        # Try to extract from nested format
        if isinstance(metadata, dict):
            # Check for table-keyed format
            for key, value in metadata.items():
                if isinstance(value, dict) and ("columns" in value or isinstance(value, dict)):
                    table_name = key
                    if "columns" in value:
                        columns = value["columns"]
                    else:
                        # Flat dict of column_name: data_type
                        columns = [{"name": k, "data_type": v} for k, v in value.items()]
                    relationships = value.get("relationships", [])
                    break

            # Check for source/target format
            if not table_name and "source" in metadata:
                table_name = "unknown_table"
                source_cols = metadata.get("source", [])
                if isinstance(source_cols, list):
                    columns = source_cols if source_cols and isinstance(source_cols[0], dict) else [{"name": c, "data_type": "VARCHAR"} for c in source_cols]

        if not table_name or not columns:
            # Fallback to simple suggestions
            return {
                "status": "success",
                "pipeline_yaml": generate_simple_pipeline(metadata),
                "suggestions": generate_simple_suggestions(metadata)
            }

        # Use intelligent suggestion logic from intelligent_suggest module
        from .intelligent_suggest import suggest_fact_validations, FactAnalysisRequest

        # Build request for intelligent analysis
        analysis_request = FactAnalysisRequest(
            fact_table=table_name,
            fact_schema=schema,
            database_type="sql",  # Default to SQL Server
            columns=columns,
            relationships=relationships
        )

        # Get intelligent suggestions
        result = await suggest_fact_validations(analysis_request)

        return {
            "status": "success",
            "table_name": table_name,
            "table_type": table_type,
            "analysis": result.get("analysis", {}),
            "suggested_checks": result.get("suggested_checks", []),
            "pipeline_yaml": result.get("pipeline_yaml", ""),
            "total_validations": result.get("total_validations", 0)
        }

    except HTTPException:
        raise
    except Exception as e:
        # Log error and return fallback
        print(f"[ERROR] Pipeline generation failed: {str(e)}")
        import traceback
        traceback.print_exc()

        # Return simple fallback suggestions
        return {
            "status": "partial",
            "error": str(e),
            "pipeline_yaml": generate_simple_pipeline(request.metadata),
            "suggestions": generate_simple_suggestions(request.metadata)
        }


def generate_simple_suggestions(metadata):
    """
    Generate simple suggestions when intelligent analysis isn't available.

    This is a fallback for when metadata is in an unexpected format
    or intelligent analysis fails.
    """
    suggestions = []

    # Try to extract column information
    columns = []
    if isinstance(metadata, dict):
        if "source" in metadata:
            columns = metadata.get("source", [])
        else:
            for key, value in metadata.items():
                if isinstance(value, dict):
                    if "columns" in value:
                        columns = value["columns"]
                    else:
                        columns = list(value.keys())
                    break

    # Generate basic suggestions based on column names
    if isinstance(columns, list) and columns:
        col_names = [c if isinstance(c, str) else c.get("name", "") for c in columns]

        # ID/Key columns
        if any("id" in c.lower() or "key" in c.lower() for c in col_names):
            suggestions.append({
                "category": "Data Quality",
                "checks": ["validate_uniqueness", "validate_nulls"],
                "reason": "ID/Key columns detected - should be unique and non-null"
            })

        # Email columns
        if any("email" in c.lower() for c in col_names):
            suggestions.append({
                "category": "Data Quality",
                "checks": ["validate_regex_patterns"],
                "reason": "Email column detected - should match email format"
            })

        # Date columns
        if any("date" in c.lower() for c in col_names):
            suggestions.append({
                "category": "Time-Series",
                "checks": ["validate_ts_continuity"],
                "reason": "Date columns detected - check for gaps"
            })

        # Always recommend basic checks
        suggestions.append({
            "category": "Schema Validation",
            "checks": ["validate_schema_columns", "validate_schema_datatypes"],
            "reason": "Always validate schema matches between systems"
        })

        suggestions.append({
            "category": "Data Quality",
            "checks": ["validate_record_counts"],
            "reason": "Always validate row counts match"
        })

    if not suggestions:
        suggestions.append({
            "category": "Manual Review",
            "checks": [],
            "reason": "Insufficient metadata - manual pipeline definition recommended"
        })

    return suggestions


def generate_simple_pipeline(metadata):
    """
    Generate a simple pipeline YAML when intelligent analysis isn't available.
    """
    table_name = "unknown_table"

    # Try to extract table name
    if isinstance(metadata, dict):
        for key in metadata.keys():
            if key not in ["source", "target", "mapping"]:
                table_name = key
                break

    pipeline = {
        "pipeline": {
            "name": f"Basic Validation for {table_name}",
            "description": "Auto-generated basic validation pipeline",
            "type": "basic_validation",
            "category": "auto_generated",
            "source": {
                "connection": "${SQLSERVER_CONNECTION}",
                "database": "${SQL_DATABASE}",
                "schema": "dbo",
                "table": table_name
            },
            "target": {
                "connection": "${SNOWFLAKE_CONNECTION}",
                "database": "${SNOWFLAKE_DATABASE}",
                "schema": "PUBLIC",
                "table": table_name
            },
            "mapping": {
                table_name: {
                    "sql": f"dbo.{table_name}",
                    "snow": f"PUBLIC.{table_name}"
                }
            },
            "steps": [
                {
                    "name": "validate_schema_columns",
                    "config": {"table": table_name}
                },
                {
                    "name": "validate_record_counts",
                    "config": {"table": table_name}
                }
            ]
        },
        "execution": {
            "write_results_to": f"results/{table_name.lower()}/",
            "fail_on_error": False,
            "notify": {
                "email": [],
                "slack": []
            }
        }
    }

    return yaml.dump(pipeline, default_flow_style=False, sort_keys=False, indent=2)


@router.post("/save")
async def save_pipeline(payload: dict):
    """Save a pipeline suggestion for later use"""
    try:
        steps = payload.get("steps", [])
        pipeline_name = payload.get("name", "unnamed_pipeline")

        # Create saves directory if it doesn't exist
        os.makedirs("pipelines/saved", exist_ok=True)

        save_path = f"pipelines/saved/{pipeline_name}.json"

        with open(save_path, "w") as f:
            json.dump(payload, f, indent=2)

        return {
            "status": "saved",
            "path": save_path,
            "pipeline_name": pipeline_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save pipeline: {str(e)}")


@router.get("/load/{pipeline_name}")
async def load_pipeline(pipeline_name: str):
    """Load a previously saved pipeline"""
    try:
        save_path = f"pipelines/saved/{pipeline_name}.json"

        if not os.path.exists(save_path):
            raise HTTPException(status_code=404, detail=f"Pipeline '{pipeline_name}' not found")

        with open(save_path, "r") as f:
            pipeline = json.load(f)

        return {
            "status": "loaded",
            "pipeline_name": pipeline_name,
            "pipeline": pipeline
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load pipeline: {str(e)}")


@router.get("/list")
async def list_saved_pipelines():
    """List all saved pipeline suggestions"""
    try:
        saves_dir = "pipelines/saved"

        if not os.path.exists(saves_dir):
            return {"pipelines": []}

        pipelines = []
        for file in os.listdir(saves_dir):
            if file.endswith(".json"):
                pipeline_name = file.replace(".json", "")
                pipelines.append({
                    "name": pipeline_name,
                    "file": file
                })

        return {
            "pipelines": pipelines,
            "count": len(pipelines)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list pipelines: {str(e)}")
