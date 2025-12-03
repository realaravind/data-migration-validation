from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import os
import json
import yaml
from datetime import datetime
import shutil

router = APIRouter()

PROJECTS_DIR = "/data/projects"  # Persistent storage for projects

class ProjectMetadata(BaseModel):
    """Project metadata"""
    name: str
    description: Optional[str] = ""
    created_at: str
    updated_at: str
    sql_database: str
    sql_schemas: List[str]
    snowflake_database: str
    snowflake_schemas: List[str]
    schema_mappings: Dict[str, str] = {}


class ProjectCreate(BaseModel):
    """Request to create a new project"""
    name: str
    description: Optional[str] = ""
    sql_database: str = "SampleDW"
    sql_schemas: List[str] = ["dbo", "dim", "fact"]
    snowflake_database: str = "SAMPLEDW"
    snowflake_schemas: List[str] = ["PUBLIC", "DIM", "FACT"]
    schema_mappings: Optional[Dict[str, str]] = None


@router.post("/create")
async def create_project(project: ProjectCreate):
    """Create a new project"""
    try:
        os.makedirs(PROJECTS_DIR, exist_ok=True)

        # Create project directory
        project_id = project.name.lower().replace(" ", "_")
        project_dir = f"{PROJECTS_DIR}/{project_id}"

        if os.path.exists(project_dir):
            raise HTTPException(status_code=400, detail=f"Project '{project.name}' already exists")

        os.makedirs(project_dir, exist_ok=True)
        os.makedirs(f"{project_dir}/config", exist_ok=True)

        # Auto-map schemas if not provided
        schema_mappings = project.schema_mappings or {}
        if not schema_mappings:
            # Intelligent schema auto-mapping
            schema_mappings = auto_map_schemas(project.sql_schemas, project.snowflake_schemas)

        # Create project metadata
        metadata = {
            "name": project.name,
            "description": project.description,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "sql_database": project.sql_database,
            "sql_schemas": project.sql_schemas,
            "snowflake_database": project.snowflake_database,
            "snowflake_schemas": project.snowflake_schemas,
            "schema_mappings": schema_mappings,
            "project_id": project_id
        }

        # Save metadata
        with open(f"{project_dir}/project.json", "w") as f:
            json.dump(metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"Project '{project.name}' created successfully",
            "project_id": project_id,
            "metadata": metadata
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create project: {str(e)}")


@router.get("/active")
async def get_active_project():
    """Get the currently active project"""
    try:
        from .context import get_active_project

        active = get_active_project()
        if not active:
            return {
                "status": "no_active_project",
                "message": "No project is currently active"
            }

        return {
            "status": "success",
            "active_project": active
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get active project: {str(e)}")


@router.get("/list")
async def list_projects():
    """List all projects"""
    try:
        os.makedirs(PROJECTS_DIR, exist_ok=True)

        projects = []
        for project_id in os.listdir(PROJECTS_DIR):
            project_dir = f"{PROJECTS_DIR}/{project_id}"
            metadata_file = f"{project_dir}/project.json"

            if os.path.isdir(project_dir) and os.path.exists(metadata_file):
                with open(metadata_file, "r") as f:
                    metadata = json.load(f)
                    projects.append(metadata)

        # Sort by updated_at descending
        projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)

        return {
            "status": "success",
            "projects": projects,
            "count": len(projects)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list projects: {str(e)}")


@router.get("/{project_id}")
async def load_project(project_id: str):
    """Load a project and set it as active"""
    try:
        from .context import set_active_project

        project_dir = f"{PROJECTS_DIR}/{project_id}"

        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load metadata
        with open(f"{project_dir}/project.json", "r") as f:
            metadata = json.load(f)

        # Set as active project
        set_active_project(project_id, metadata)

        # Load configuration files if they exist
        config = {}
        config_dir = f"{project_dir}/config"

        if os.path.exists(f"{config_dir}/tables.yaml"):
            with open(f"{config_dir}/tables.yaml", "r") as f:
                config["tables"] = yaml.safe_load(f)

        if os.path.exists(f"{config_dir}/relationships.yaml"):
            with open(f"{config_dir}/relationships.yaml", "r") as f:
                config["relationships"] = yaml.safe_load(f)

        if os.path.exists(f"{config_dir}/column_mappings.yaml"):
            with open(f"{config_dir}/column_mappings.yaml", "r") as f:
                config["column_mappings"] = yaml.safe_load(f)

        if os.path.exists(f"{config_dir}/schema_mappings.yaml"):
            with open(f"{config_dir}/schema_mappings.yaml", "r") as f:
                config["schema_mappings"] = yaml.safe_load(f)

        # Load separate SQL and Snowflake relationships
        if os.path.exists(f"{config_dir}/sql_relationships.yaml"):
            with open(f"{config_dir}/sql_relationships.yaml", "r") as f:
                config["sql_relationships"] = yaml.safe_load(f)

        if os.path.exists(f"{config_dir}/snow_relationships.yaml"):
            with open(f"{config_dir}/snow_relationships.yaml", "r") as f:
                config["snow_relationships"] = yaml.safe_load(f)

        # Copy config files to core engine
        core_config_dir = "/core/src/ombudsman/config"
        for filename in ["tables.yaml", "relationships.yaml", "column_mappings.yaml", "schema_mappings.yaml", "sql_relationships.yaml", "snow_relationships.yaml"]:
            src = f"{config_dir}/{filename}"
            dst = f"{core_config_dir}/{filename}"
            if os.path.exists(src):
                shutil.copy2(src, dst)

        return {
            "status": "success",
            "message": f"Project loaded: {metadata['name']}",
            "metadata": metadata,
            "config": config
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load project: {str(e)}")


@router.post("/{project_id}/save")
async def save_project(project_id: str):
    """Save current state to project"""
    try:
        project_dir = f"{PROJECTS_DIR}/{project_id}"

        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Copy config files from core engine to project
        core_config_dir = "/core/src/ombudsman/config"
        project_config_dir = f"{project_dir}/config"

        for filename in ["tables.yaml", "relationships.yaml", "column_mappings.yaml", "schema_mappings.yaml", "sql_relationships.yaml", "snow_relationships.yaml"]:
            src = f"{core_config_dir}/{filename}"
            dst = f"{project_config_dir}/{filename}"
            if os.path.exists(src):
                shutil.copy2(src, dst)

        # Update metadata
        metadata_file = f"{project_dir}/project.json"
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        metadata["updated_at"] = datetime.now().isoformat()

        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"Project saved: {metadata['name']}",
            "updated_at": metadata["updated_at"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save project: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    try:
        project_dir = f"{PROJECTS_DIR}/{project_id}"

        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load metadata for confirmation message
        with open(f"{project_dir}/project.json", "r") as f:
            metadata = json.load(f)

        # Delete project directory
        shutil.rmtree(project_dir)

        return {
            "status": "success",
            "message": f"Project deleted: {metadata['name']}"
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete project: {str(e)}")


@router.post("/{project_id}/relationships/{database_type}")
async def save_relationships(project_id: str, database_type: str, relationships_data: Dict[str, Any]):
    """Save SQL or Snowflake relationships to project and core engine

    Args:
        project_id: The project ID
        database_type: Either 'sql' or 'snow'
        relationships_data: The relationships data including relationships, metrics, and diagram
    """
    try:
        if database_type not in ['sql', 'snow']:
            raise HTTPException(status_code=400, detail="database_type must be 'sql' or 'snow'")

        project_dir = f"{PROJECTS_DIR}/{project_id}"
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Prepare the YAML data
        yaml_data = {
            "relationships": relationships_data.get("relationships", []),
            "metrics": relationships_data.get("metrics", {}),
            "diagram": relationships_data.get("diagram", "")
        }

        # Save to project config
        project_config_dir = f"{project_dir}/config"
        os.makedirs(project_config_dir, exist_ok=True)

        filename = f"{database_type}_relationships.yaml"
        with open(f"{project_config_dir}/{filename}", "w") as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

        # Also save to core engine for immediate use
        core_config_dir = "/core/src/ombudsman/config"
        with open(f"{core_config_dir}/{filename}", "w") as f:
            yaml.dump(yaml_data, f, default_flow_style=False, sort_keys=False)

        # Update project metadata
        metadata_file = f"{project_dir}/project.json"
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        metadata["updated_at"] = datetime.now().isoformat()

        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"{database_type.upper()} relationships saved successfully",
            "updated_at": metadata["updated_at"]
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save relationships: {str(e)}")


def auto_map_schemas(sql_schemas: List[str], snowflake_schemas: List[str]) -> Dict[str, str]:
    """Intelligently map SQL Server schemas to Snowflake schemas"""
    mappings = {}

    for sql_schema in sql_schemas:
        # Exact match (case-insensitive)
        for snow_schema in snowflake_schemas:
            if sql_schema.lower() == snow_schema.lower():
                mappings[sql_schema] = snow_schema
                break

        # Partial match if no exact match
        if sql_schema not in mappings:
            for snow_schema in snowflake_schemas:
                # Check if snow_schema starts with or contains sql_schema
                if sql_schema.lower() in snow_schema.lower():
                    mappings[sql_schema] = snow_schema
                    break

        # Default to same name (uppercase for Snowflake)
        if sql_schema not in mappings:
            # Try uppercase version
            upper_schema = sql_schema.upper()
            if upper_schema in snowflake_schemas:
                mappings[sql_schema] = upper_schema
            else:
                # Use first available or same name
                mappings[sql_schema] = snowflake_schemas[0] if snowflake_schemas else sql_schema.upper()

    return mappings
