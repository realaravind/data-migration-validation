from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import os
import json
import sys
import yaml

# Add core to Python path
sys.path.insert(0, "/core/src")

try:
    from ombudsman.pipeline.graph import generate_mermaid, generate_mermaid_from_yaml, generate_mermaid_with_inference
    CORE_AVAILABLE = True
except Exception as e:
    CORE_AVAILABLE = False
    CORE_ERROR = str(e)

router = APIRouter()

SAVE_PATH = "diagram_saved.mmd"


@router.post("/save")
def save_diagram(payload: dict):
    content = payload["diagram"]
    with open(SAVE_PATH, "w") as f:
        f.write(content)
    return {"status": "saved", "path": SAVE_PATH}


@router.post("/load")
def load_diagram():
    if not os.path.exists(SAVE_PATH):
        return {"diagram": ""}
    with open(SAVE_PATH, "r") as f:
        return {"diagram": f.read()}


@router.post("/auto-generate")
def auto_generate(payload: dict):
    if not CORE_AVAILABLE:
        return {"diagram": f"graph TD;\n  A[Core Not Available] --> B[Error: {CORE_ERROR}]"}

    try:
        diagram = generate_mermaid(payload)
        return {"diagram": diagram}
    except Exception as e:
        return {"diagram": f"graph TD;\nError[{str(e)}]"}


class GenerateFromYamlRequest(BaseModel):
    """Request to generate Mermaid diagram from YAML files"""
    show_columns: bool = True
    highlight_broken: bool = False


@router.post("/generate-from-yaml")
def generate_from_yaml(request: GenerateFromYamlRequest):
    """
    Generate Mermaid ERD from tables.yaml and relationships.yaml files.
    """
    if not CORE_AVAILABLE:
        raise HTTPException(status_code=500, detail=f"Core engine not available: {CORE_ERROR}")

    try:
        config_dir = "/core/src/ombudsman/config"
        tables_file = f"{config_dir}/tables.yaml"
        relationships_file = f"{config_dir}/relationships.yaml"

        if not os.path.exists(tables_file):
            raise HTTPException(
                status_code=404,
                detail="No table metadata found. Please extract metadata first using Database Mapping."
            )

        # Load YAML files
        with open(tables_file, "r") as f:
            tables_yaml = yaml.safe_load(f) or {}

        relationships_yaml = []
        if os.path.exists(relationships_file):
            with open(relationships_file, "r") as f:
                relationships_yaml = yaml.safe_load(f) or []

        # Generate Mermaid diagram
        diagram = generate_mermaid_from_yaml(
            tables_yaml,
            relationships_yaml,
            show_columns=request.show_columns,
            highlight_broken=request.highlight_broken
        )

        return {
            "status": "success",
            "diagram": diagram,
            "tables_count": len(tables_yaml.get("sql", {})),
            "relationships_count": len(relationships_yaml)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate diagram: {str(e)}")


class GenerateWithInferenceRequest(BaseModel):
    """Request to generate Mermaid diagram with inferred relationships"""
    inferred_relationships: List[Dict]
    existing_relationships: Optional[List[Dict]] = None
    show_columns: bool = True
    source_database: str = "sql"  # "sql" or "snow"
    target_database: str = "snow"  # "sql" or "snow"


@router.post("/generate-with-inference")
def generate_with_inference(request: GenerateWithInferenceRequest):
    """
    Generate Mermaid ERD showing both existing and inferred relationships.
    Inferred relationships are color-coded by confidence.
    """
    if not CORE_AVAILABLE:
        raise HTTPException(status_code=500, detail=f"Core engine not available: {CORE_ERROR}")

    try:
        config_dir = "/core/src/ombudsman/config"
        tables_file = f"{config_dir}/tables.yaml"

        if not os.path.exists(tables_file):
            raise HTTPException(
                status_code=404,
                detail="No table metadata found. Please extract metadata first using Database Mapping."
            )

        # Load tables metadata
        with open(tables_file, "r") as f:
            tables_data = yaml.safe_load(f) or {}

        # Convert to metadata format
        # Use source_database to determine which tables to visualize
        tables = {}
        source_tables = tables_data.get(request.source_database, {})
        for table_name, columns in source_tables.items():
            if "." in table_name:
                schema, tbl = table_name.rsplit(".", 1)
            else:
                schema = "dbo" if request.source_database == "sql" else "PUBLIC"
                tbl = table_name

            tables[table_name] = {
                "table": tbl,
                "schema": schema,
                "columns": columns
            }

        # Generate Mermaid diagram
        diagram = generate_mermaid_with_inference(
            tables,
            request.inferred_relationships,
            request.existing_relationships
        )

        return {
            "status": "success",
            "diagram": diagram,
            "tables_count": len(tables),
            "inferred_relationships_count": len(request.inferred_relationships),
            "existing_relationships_count": len(request.existing_relationships) if request.existing_relationships else 0
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate diagram: {str(e)}")