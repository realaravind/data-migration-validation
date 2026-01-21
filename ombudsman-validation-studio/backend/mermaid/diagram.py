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
    project_name: Optional[str] = None  # Project name - if not provided, uses active project
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
        # Get project name - use provided or fallback to active project
        project_name = request.project_name
        if not project_name:
            # Try to get active project from session/state
            import sys
            sys.path.insert(0, "/app/projects")
            from context import get_active_project

            active_project = get_active_project()
            if active_project:
                project_name = active_project.get("project_id", "default_project")
            else:
                project_name = "default_project"

        config_dir = f"/data/projects/{project_name}/config"
        tables_file = f"{config_dir}/tables.yaml"
        relationships_file = f"{config_dir}/relationships.yaml"
        sql_relationships_file = f"{config_dir}/sql_relationships.yaml"
        snow_relationships_file = f"{config_dir}/snow_relationships.yaml"

        if not os.path.exists(tables_file):
            raise HTTPException(
                status_code=404,
                detail="No table metadata found. Please extract metadata first using Database Mapping."
            )

        # Load YAML files
        with open(tables_file, "r") as f:
            tables_yaml = yaml.safe_load(f) or {}

        # Load relationships from multiple possible sources
        relationships_yaml = []

        # Try sql_relationships.yaml first (new format)
        if os.path.exists(sql_relationships_file):
            with open(sql_relationships_file, "r") as f:
                sql_rels = yaml.safe_load(f) or {}
                # Handle wrapped format {relationships: [...]}
                if isinstance(sql_rels, dict) and "relationships" in sql_rels:
                    relationships_yaml.extend(sql_rels["relationships"])
                elif isinstance(sql_rels, list):
                    relationships_yaml.extend(sql_rels)

        # Add snowflake relationships if they exist
        if os.path.exists(snow_relationships_file):
            with open(snow_relationships_file, "r") as f:
                snow_rels = yaml.safe_load(f) or {}
                # Handle wrapped format {relationships: [...]}
                if isinstance(snow_rels, dict) and "relationships" in snow_rels:
                    relationships_yaml.extend(snow_rels["relationships"])
                elif isinstance(snow_rels, list):
                    relationships_yaml.extend(snow_rels)

        # Fallback to old relationships.yaml if no new files found
        if not relationships_yaml and os.path.exists(relationships_file):
            with open(relationships_file, "r") as f:
                rels = yaml.safe_load(f) or []
                if isinstance(rels, list):
                    relationships_yaml = rels

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
        # Get active project's config directory
        import sys
        sys.path.insert(0, "/app/projects")
        from context import get_active_project, get_project_config_dir

        active_project = get_active_project()
        if active_project:
            project_name = active_project.get("project_id", "default_project")
        else:
            project_name = "default_project"

        config_dir = get_project_config_dir()
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
        for table_name, table_data in source_tables.items():
            # Handle wrapped format {columns: {...}, object_type: TABLE}
            if isinstance(table_data, dict) and "columns" in table_data:
                columns = table_data["columns"]
            else:
                # Old format: table_data is the columns dict directly
                columns = table_data

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