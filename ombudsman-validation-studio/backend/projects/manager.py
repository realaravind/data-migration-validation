from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Dict, List, Any
import os
import json
import yaml
from datetime import datetime
import shutil

from auth.dependencies import require_user_or_admin, optional_authentication
from auth.models import UserInDB
from .automation import ProjectAutomation

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
async def create_project(
    project: ProjectCreate,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Create a new project.

    Requires: User or Admin role
    """
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

        # Merge SQL and Snowflake relationships into main relationships.yaml for core engine
        core_config_dir = "/core/src/ombudsman/config"
        merged_relationships = []

        # Load SQL relationships
        if os.path.exists(f"{config_dir}/sql_relationships.yaml"):
            with open(f"{config_dir}/sql_relationships.yaml", "r") as f:
                sql_rels = yaml.safe_load(f) or {}
                if isinstance(sql_rels, dict) and "relationships" in sql_rels:
                    merged_relationships.extend(sql_rels["relationships"])
                elif isinstance(sql_rels, list):
                    merged_relationships.extend(sql_rels)

        # Load Snowflake relationships
        if os.path.exists(f"{config_dir}/snow_relationships.yaml"):
            with open(f"{config_dir}/snow_relationships.yaml", "r") as f:
                snow_rels = yaml.safe_load(f) or {}
                if isinstance(snow_rels, dict) and "relationships" in snow_rels:
                    merged_relationships.extend(snow_rels["relationships"])
                elif isinstance(snow_rels, list):
                    merged_relationships.extend(snow_rels)

        # Write merged relationships to core config
        os.makedirs(core_config_dir, exist_ok=True)
        with open(f"{core_config_dir}/relationships.yaml", "w") as f:
            yaml.dump(merged_relationships, f, default_flow_style=False, sort_keys=False)

        print(f"[PROJECT_LOAD] Merged {len(merged_relationships)} relationships to core config")

        # Copy other config files to core engine
        for filename in ["tables.yaml", "column_mappings.yaml", "schema_mappings.yaml", "sql_relationships.yaml", "snow_relationships.yaml"]:
            src = f"{config_dir}/{filename}"
            dst = f"{core_config_dir}/{filename}"
            if os.path.exists(src):
                shutil.copy2(src, dst)

        # Build Snowflake connection config from project metadata
        config["snowflake"] = {
            "user": os.getenv("SNOWFLAKE_USER", ""),
            "password": os.getenv("SNOWFLAKE_PASSWORD", ""),
            "account": os.getenv("SNOWFLAKE_ACCOUNT", ""),
            "warehouse": os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
            "database": metadata.get("snowflake_database", "SAMPLEDW"),
            "schema": metadata.get("snowflake_schemas", ["PUBLIC"])[0] if metadata.get("snowflake_schemas") else "PUBLIC",
            "role": os.getenv("SNOWFLAKE_ROLE", "")
        }

        return {
            "status": "success",
            "message": f"Project loaded: {metadata['name']}",
            "metadata": metadata,
            "config": config
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load project: {str(e)}")


@router.post("/{project_id}/save")
async def save_project(
    project_id: str,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Save current state to project.

    Requires: User or Admin role
    """
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
async def delete_project(
    project_id: str,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Delete a project.

    Requires: User or Admin role
    """
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

        # NOTE: No longer saving to core config - everything is project-specific now

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


# ============================================================================
# PROJECT AUTOMATION ENDPOINTS
# ============================================================================

class SetupRequest(BaseModel):
    """Request to extract metadata and infer relationships"""
    connection: str  # "sqlserver" or "snowflake"
    schema: Optional[str] = None


@router.post("/{project_id}/setup")
async def setup_project(
    project_id: str,
    payload: SetupRequest,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Extract metadata and infer relationships for a project.

    This is the first step after project creation:
    1. Extracts metadata for all tables
    2. Infers relationships between tables
    3. Saves both to project directory

    Requires: User or Admin role
    """
    try:
        project_dir = f"{PROJECTS_DIR}/{project_id}"
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load project metadata
        with open(f"{project_dir}/project.json", "r") as f:
            project_metadata = json.load(f)

        # Create automation instance
        automation = ProjectAutomation(project_id, project_metadata["name"])

        # Extract metadata
        print(f"[PROJECT_SETUP] Extracting metadata for {project_id} from {payload.connection}")
        metadata = automation.extract_all_metadata(payload.connection, payload.schema)

        # Infer relationships
        print(f"[PROJECT_SETUP] Inferring relationships for {project_id}")
        relationships = automation.infer_relationships(metadata)

        # Update project metadata
        project_metadata["updated_at"] = datetime.now().isoformat()
        project_metadata["has_metadata"] = True
        project_metadata["has_relationships"] = True

        with open(f"{project_dir}/project.json", "w") as f:
            json.dump(project_metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"Metadata extracted and relationships inferred for {project_metadata['name']}",
            "table_count": len(metadata),
            "relationship_count": len(relationships),
            "metadata": metadata,
            "relationships": relationships
        }

    except Exception as e:
        print(f"[PROJECT_SETUP] Error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to setup project: {str(e)}")


@router.get("/{project_id}/relationships")
async def get_relationships(project_id: str):
    """
    Get inferred relationships for a project.

    Returns the relationships that were inferred during setup.
    """
    try:
        project_dir = f"{PROJECTS_DIR}/{project_id}"
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Create automation instance
        automation = ProjectAutomation(project_id, "")

        # Get relationships
        relationships = automation.get_relationships()

        if relationships is None:
            return {
                "status": "not_ready",
                "message": "No relationships found. Run setup first.",
                "relationships": []
            }

        return {
            "status": "success",
            "relationship_count": len(relationships),
            "relationships": relationships
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get relationships: {str(e)}")


@router.put("/{project_id}/relationships")
async def update_relationships(
    project_id: str,
    relationships: List[Dict[str, Any]],
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Update relationships after user validation/editing.

    This allows users to validate and correct the inferred relationships
    before proceeding to automation.

    Requires: User or Admin role
    """
    try:
        project_dir = f"{PROJECTS_DIR}/{project_id}"
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load project metadata
        with open(f"{project_dir}/project.json", "r") as f:
            project_metadata = json.load(f)

        # Create automation instance
        automation = ProjectAutomation(project_id, project_metadata["name"])

        # Save updated relationships
        automation.save_relationships(relationships)

        # Update project metadata
        project_metadata["updated_at"] = datetime.now().isoformat()

        with open(f"{project_dir}/project.json", "w") as f:
            json.dump(project_metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"Relationships updated for {project_metadata['name']}",
            "relationship_count": len(relationships)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update relationships: {str(e)}")


@router.get("/{project_id}/status")
async def get_setup_status(project_id: str):
    """
    Get project setup status.

    Returns whether the project has metadata and relationships,
    and whether it's ready for automation.
    """
    try:
        project_dir = f"{PROJECTS_DIR}/{project_id}"
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load project metadata
        with open(f"{project_dir}/project.json", "r") as f:
            project_metadata = json.load(f)

        # Create automation instance
        automation = ProjectAutomation(project_id, project_metadata["name"])

        # Get setup status
        status = automation.get_setup_status()

        return {
            "status": "success",
            "project_name": project_metadata["name"],
            **status
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get setup status: {str(e)}")


@router.post("/{project_id}/automate")
async def automate_project(
    project_id: str,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Automate pipeline creation and execution for all tables in a project.

    This endpoint:
    1. Loads metadata and relationships from the project
    2. Creates intelligent pipelines for ALL tables (fact and dimension)
    3. Prefixes all pipelines with {project_name}_
    4. Creates a batch file with {project_name}_batch naming
    5. Executes the batch

    Requires: User or Admin role
    """
    try:
        project_dir = f"{PROJECTS_DIR}/{project_id}"
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load project metadata
        with open(f"{project_dir}/project.json", "r") as f:
            project_metadata = json.load(f)

        project_name = project_metadata["name"]
        safe_project_name = project_name.lower().replace(" ", "_")

        # Create automation instance
        automation = ProjectAutomation(project_id, project_name)

        # Check if setup is complete
        status = automation.get_setup_status()
        if not status["ready_for_automation"]:
            raise HTTPException(
                status_code=400,
                detail=f"Project not ready for automation. has_metadata: {status['has_metadata']}, has_relationships: {status['has_relationships']}"
            )

        # Get metadata and relationships
        metadata = automation.get_metadata()
        relationships = automation.get_relationships()

        print(f"[PROJECT_AUTOMATE] Starting automation for project '{project_name}'")
        print(f"[PROJECT_AUTOMATE] Found {len(metadata)} tables and {len(relationships)} relationships")

        # Import pipeline generation logic
        from pipelines.intelligent_suggest import suggest_fact_validations, FactAnalysisRequest

        # Create pipelines directory
        pipelines_dir = f"{project_dir}/pipelines"
        os.makedirs(pipelines_dir, exist_ok=True)

        # Generate pipelines for ALL tables
        created_pipelines = []

        for table_key, table_meta in metadata.items():
            # Parse schema and table name
            parts = table_key.split('.')
            if len(parts) == 2:
                schema, table_name = parts
            else:
                schema = "dbo"
                table_name = table_key

            print(f"[PROJECT_AUTOMATE] Generating pipeline for {schema}.{table_name}")

            # Get columns for this table
            columns_dict = table_meta.get("columns", {})

            # Convert columns dict to list format expected by intelligent_suggest
            columns_list = [
                {"name": "columns", "type": columns_dict},
                {"name": "object_type", "type": table_meta.get("object_type", "TABLE")}
            ]

            # Get relationships for this table
            table_relationships = [
                rel for rel in relationships
                if rel.get("fact_table", "").lower() == table_name.lower()
            ]

            # Create request for pipeline generation
            request = FactAnalysisRequest(
                fact_table=table_name,
                fact_schema=schema,
                database_type="sql",
                columns=columns_list,
                relationships=table_relationships
            )

            # Generate pipeline YAML using existing logic
            # Note: This is a synchronous function, we need to call it directly
            try:
                pipeline_yaml_content = await suggest_fact_validations(request)

                # Save pipeline with project prefix
                pipeline_name = f"{safe_project_name}_{table_name}"
                pipeline_file = f"{pipelines_dir}/{pipeline_name}.yaml"

                with open(pipeline_file, "w") as f:
                    f.write(pipeline_yaml_content["yaml"])

                # Save metadata
                metadata_file = f"{pipelines_dir}/{pipeline_name}.meta.json"
                pipeline_metadata = {
                    "pipeline_name": pipeline_name,
                    "description": f"Automated validation pipeline for {schema}.{table_name}",
                    "tags": ["automated", "project", schema, table_name],
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat(),
                    "table": table_name,
                    "schema": schema
                }
                with open(metadata_file, "w") as f:
                    json.dump(pipeline_metadata, f, indent=2)

                created_pipelines.append({
                    "pipeline_name": pipeline_name,
                    "table": table_name,
                    "schema": schema,
                    "file": pipeline_file
                })

                print(f"[PROJECT_AUTOMATE] Created pipeline: {pipeline_name}")

            except Exception as e:
                print(f"[PROJECT_AUTOMATE] Warning: Could not create pipeline for {table_name}: {e}")
                continue

        # Create batch file
        batch_name = f"{safe_project_name}_batch"
        batch_file = f"{project_dir}/{batch_name}.yaml"

        batch_yaml = {
            "batch": {
                "name": batch_name,
                "description": f"Automated batch execution for {project_name}",
                "pipelines": [p["pipeline_name"] for p in created_pipelines]
            }
        }

        with open(batch_file, "w") as f:
            yaml.dump(batch_yaml, f, default_flow_style=False, sort_keys=False)

        print(f"[PROJECT_AUTOMATE] Created batch file: {batch_file}")

        # Update project metadata
        project_metadata["updated_at"] = datetime.now().isoformat()
        project_metadata["automation_completed"] = True
        project_metadata["batch_name"] = batch_name
        project_metadata["pipeline_count"] = len(created_pipelines)

        with open(f"{project_dir}/project.json", "w") as f:
            json.dump(project_metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"Automation completed for project '{project_name}'",
            "batch_name": batch_name,
            "batch_file": batch_file,
            "pipelines_created": len(created_pipelines),
            "pipelines": created_pipelines
        }

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to automate project: {str(e)}")
