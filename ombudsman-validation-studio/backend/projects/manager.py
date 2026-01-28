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
from config.paths import paths
from .automation import ProjectAutomation

router = APIRouter()

# Use configurable paths - set via OMBUDSMAN_DATA_DIR environment variable
def get_projects_dir() -> str:
    """Get projects directory path."""
    return str(paths.projects_dir)

class AzureDevOpsConfig(BaseModel):
    """Azure DevOps configuration for a project"""
    enabled: bool = False
    organization_url: Optional[str] = None  # e.g., https://dev.azure.com/myorg
    project_name: Optional[str] = None
    pat_token: Optional[str] = None  # Personal Access Token (will be encrypted)
    work_item_type: str = "Bug"  # Bug, Task, User Story, Issue
    area_path: Optional[str] = None
    iteration_path: Optional[str] = None
    assigned_to: Optional[str] = None  # Email of default assignee
    auto_tags: List[str] = ["ombudsman", "data-validation"]
    tag_prefix: Optional[str] = "OVS-"


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
    azure_devops: Optional[AzureDevOpsConfig] = None


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
        os.makedirs(get_projects_dir(), exist_ok=True)

        # Create project directory
        project_id = project.name.lower().replace(" ", "_")
        project_dir = f"{get_projects_dir()}/{project_id}"

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
        os.makedirs(get_projects_dir(), exist_ok=True)

        projects = []
        for project_id in os.listdir(get_projects_dir()):
            project_dir = f"{get_projects_dir()}/{project_id}"
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

        project_dir = f"{get_projects_dir()}/{project_id}"

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
        core_config_dir = str(paths.core_config_dir)
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
        project_dir = f"{get_projects_dir()}/{project_id}"

        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Copy config files from core engine to project
        core_config_dir = str(paths.core_config_dir)
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


class SchemaMappingsUpdate(BaseModel):
    """Request to update schema mappings"""
    schema_mappings: Dict[str, str]


@router.put("/{project_id}/update-schema-mappings")
async def update_schema_mappings(
    project_id: str,
    update: SchemaMappingsUpdate
):
    """
    Update schema mappings in project metadata.

    Args:
        project_id: Project ID
        update: Schema mappings to update

    Returns:
        Success message
    """
    try:
        project_dir = f"{get_projects_dir()}/{project_id}"
        metadata_file = f"{project_dir}/project.json"

        if not os.path.exists(metadata_file):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load existing metadata
        with open(metadata_file, "r") as f:
            metadata = json.load(f)

        # Update schema mappings
        metadata["schema_mappings"] = update.schema_mappings
        metadata["updated_at"] = datetime.now().isoformat()

        # Save updated metadata
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

        return {
            "status": "success",
            "message": "Schema mappings updated successfully",
            "schema_mappings": update.schema_mappings
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update schema mappings: {str(e)}")


@router.delete("/{project_id}")
async def delete_project(
    project_id: str,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Delete a project and all associated data.

    Cascade deletes:
    - Project directory (config, pipelines, results)
    - Batch jobs that reference project pipelines
    - Query store data for the project
    - Results stored outside project directory

    Requires: User or Admin role
    """
    try:
        project_dir = f"{get_projects_dir()}/{project_id}"

        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load metadata for confirmation message
        with open(f"{project_dir}/project.json", "r") as f:
            metadata = json.load(f)

        project_name = metadata.get("name", project_id)

        print(f"[PROJECT_DELETE] Starting cascade delete for project: {project_name} ({project_id})")

        # Track deleted items
        deleted_items = {
            "project_dir": False,
            "batch_jobs": [],
            "results": [],
            "queries": []
        }

        # 1. Collect pipeline names from project (to identify related batch jobs)
        pipeline_names = set()
        pipelines_dir = f"{project_dir}/pipelines"
        if os.path.exists(pipelines_dir):
            for filename in os.listdir(pipelines_dir):
                if filename.endswith('.yaml') or filename.endswith('.yml'):
                    pipeline_name = filename.replace('.yaml', '').replace('.yml', '')
                    pipeline_names.add(pipeline_name)
                    # Also match project prefix patterns
                    if pipeline_name.startswith(f"{project_id}_"):
                        pipeline_names.add(pipeline_name)

        print(f"[PROJECT_DELETE] Found {len(pipeline_names)} pipelines to track")

        # 2. Delete associated batch jobs
        batch_jobs_dir = str(paths.batch_jobs_dir)
        if os.path.exists(batch_jobs_dir):
            for batch_file in os.listdir(batch_jobs_dir):
                if not batch_file.endswith('.json'):
                    continue

                batch_path = f"{batch_jobs_dir}/{batch_file}"
                try:
                    with open(batch_path, 'r') as f:
                        batch_data = json.load(f)

                    # Check if batch belongs to this project
                    batch_name = batch_data.get('batch_name', '')
                    batch_pipelines = batch_data.get('pipelines', [])

                    # Delete if batch name contains project_id OR any pipeline belongs to project
                    should_delete = False
                    if project_id in batch_name:
                        should_delete = True
                    else:
                        # Check if any pipeline in batch belongs to this project
                        for pipeline in batch_pipelines:
                            if pipeline in pipeline_names:
                                should_delete = True
                                break

                    if should_delete:
                        os.remove(batch_path)
                        deleted_items["batch_jobs"].append(batch_file)
                        print(f"[PROJECT_DELETE] Deleted batch job: {batch_file}")

                except Exception as e:
                    print(f"[PROJECT_DELETE] Warning: Could not process batch file {batch_file}: {e}")

        # 3. Delete associated results
        results_dir = str(paths.results_dir)
        if os.path.exists(results_dir):
            for result_file in os.listdir(results_dir):
                if not result_file.endswith('.json'):
                    continue

                result_path = f"{results_dir}/{result_file}"
                try:
                    with open(result_path, 'r') as f:
                        result_data = json.load(f)

                    # Check if result belongs to project pipelines
                    pipeline_name = result_data.get('pipeline_name', '')

                    if pipeline_name in pipeline_names or project_id in pipeline_name:
                        os.remove(result_path)
                        deleted_items["results"].append(result_file)
                        print(f"[PROJECT_DELETE] Deleted result: {result_file}")

                except Exception as e:
                    print(f"[PROJECT_DELETE] Warning: Could not process result file {result_file}: {e}")

        # 4. Delete project-specific query store data
        queries_dir = str(paths.queries_dir)
        if os.path.exists(queries_dir):
            project_queries_dir = f"{queries_dir}/{project_id}"
            if os.path.exists(project_queries_dir):
                shutil.rmtree(project_queries_dir)
                deleted_items["queries"].append(project_id)
                print(f"[PROJECT_DELETE] Deleted query store: {project_queries_dir}")

        # 5. Finally, delete the project directory itself
        shutil.rmtree(project_dir)
        deleted_items["project_dir"] = True
        print(f"[PROJECT_DELETE] Deleted project directory: {project_dir}")

        # 6. Clear active project if this was the active one
        try:
            from .context import get_active_project, clear_active_project
            active = get_active_project()
            if active and active.get("project_id") == project_id:
                clear_active_project()
                print(f"[PROJECT_DELETE] Cleared active project context")
        except Exception as e:
            print(f"[PROJECT_DELETE] Warning: Could not clear active project: {e}")

        print(f"[PROJECT_DELETE] Cascade delete completed successfully")
        print(f"[PROJECT_DELETE]   - Batch jobs deleted: {len(deleted_items['batch_jobs'])}")
        print(f"[PROJECT_DELETE]   - Results deleted: {len(deleted_items['results'])}")
        print(f"[PROJECT_DELETE]   - Query stores deleted: {len(deleted_items['queries'])}")

        return {
            "status": "success",
            "message": f"Project '{project_name}' and all associated data deleted successfully",
            "deleted": {
                "project_directory": project_dir,
                "batch_jobs_count": len(deleted_items["batch_jobs"]),
                "batch_jobs": deleted_items["batch_jobs"],
                "results_count": len(deleted_items["results"]),
                "results": deleted_items["results"],
                "query_stores_count": len(deleted_items["queries"])
            }
        }

    except Exception as e:
        import traceback
        traceback.print_exc()
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

        project_dir = f"{get_projects_dir()}/{project_id}"
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


@router.post("/{project_id}/extract-metadata")
async def extract_metadata(
    project_id: str,
    payload: SetupRequest,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Extract metadata for all tables in a project.

    Step 1: Extract table metadata only (no relationship inference)

    Requires: User or Admin role
    """
    try:
        project_dir = f"{get_projects_dir()}/{project_id}"
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load project metadata
        with open(f"{project_dir}/project.json", "r") as f:
            project_metadata = json.load(f)

        # Create automation instance
        automation = ProjectAutomation(project_id, project_metadata["name"])

        # Extract metadata only
        print(f"[METADATA_EXTRACT] Extracting metadata for {project_id} from {payload.connection}")
        metadata = automation.extract_all_metadata(payload.connection, payload.schema)

        # Update project metadata
        project_metadata["updated_at"] = datetime.now().isoformat()
        project_metadata["has_metadata"] = True

        with open(f"{project_dir}/project.json", "w") as f:
            json.dump(project_metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"Metadata extracted for {project_metadata['name']}",
            "table_count": len(metadata),
            "metadata": metadata
        }

    except Exception as e:
        print(f"[METADATA_EXTRACT] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/infer-relationships")
async def infer_relationships_endpoint(
    project_id: str,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Infer relationships for a project.

    Step 2: Infer FK relationships from extracted metadata
    (requires metadata to be extracted first)

    Requires: User or Admin role
    """
    try:
        project_dir = f"{get_projects_dir()}/{project_id}"
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load project metadata
        with open(f"{project_dir}/project.json", "r") as f:
            project_metadata = json.load(f)

        # Create automation instance
        automation = ProjectAutomation(project_id, project_metadata["name"])

        # Get existing metadata
        metadata = automation.get_metadata()
        if not metadata:
            raise HTTPException(status_code=400, detail="No metadata found. Please extract metadata first.")

        # Infer relationships
        print(f"[RELATIONSHIP_INFER] Inferring relationships for {project_id}")
        relationships = automation.infer_relationships(metadata)

        # Update project metadata
        project_metadata["updated_at"] = datetime.now().isoformat()
        project_metadata["has_relationships"] = True

        with open(f"{project_dir}/project.json", "w") as f:
            json.dump(project_metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"Relationships inferred for {project_metadata['name']}",
            "relationship_count": len(relationships),
            "relationships": relationships
        }

    except Exception as e:
        print(f"[RELATIONSHIP_INFER] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{project_id}/setup")
async def setup_project(
    project_id: str,
    payload: SetupRequest,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Complete auto-setup for a project:
    1. Extracts metadata from both SQL Server and Snowflake (all schemas)
    2. Creates table mappings between SQL and Snowflake
    3. Infers relationships between tables
    4. Generates YAML configuration files
    5. Saves all data to project directory

    Requires: User or Admin role
    """
    try:
        project_dir = f"{get_projects_dir()}/{project_id}"
        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        # Load project metadata
        with open(f"{project_dir}/project.json", "r") as f:
            project_metadata = json.load(f)

        # Import database mapping functions
        from mapping.database_mapping import (
            extract_sqlserver_tables,
            extract_snowflake_tables,
            create_table_mappings,
            generate_yaml_files
        )

        # Set active project for config directory
        from projects.context import set_active_project
        set_active_project(project_id, project_metadata)

        # Get schema mappings from project
        schema_mappings = project_metadata.get("schema_mappings", {})
        if not schema_mappings:
            raise HTTPException(status_code=400, detail="No schema mappings found in project. Please configure schema mappings first.")

        print(f"[PROJECT_SETUP] Starting auto-setup for {project_id}")
        print(f"[PROJECT_SETUP] Schema mappings: {schema_mappings}")

        # Extract metadata from all mapped schemas
        all_sql_metadata = {}
        all_snow_metadata = {}
        schema_results = []

        for sql_schema, snow_schema in schema_mappings.items():
            print(f"[PROJECT_SETUP] Extracting {sql_schema} (SQL) -> {snow_schema} (Snowflake)")

            # Extract from SQL Server
            sql_metadata = extract_sqlserver_tables(
                database=project_metadata.get("sql_database"),
                schema=sql_schema,
                patterns=["%"],
                specific_tables=None
            )
            print(f"[PROJECT_SETUP]   SQL Server: {len(sql_metadata)} tables in {sql_schema}")

            # Extract from Snowflake
            snow_metadata = extract_snowflake_tables(
                database=project_metadata.get("snowflake_database"),
                schema=snow_schema,
                patterns=["%"],
                specific_tables=None
            )
            print(f"[PROJECT_SETUP]   Snowflake: {len(snow_metadata)} tables in {snow_schema}")

            # Add to combined metadata with schema prefix
            for table_name, table_data in sql_metadata.items():
                all_sql_metadata[f"{sql_schema}.{table_name}"] = {
                    **table_data,
                    "schema": sql_schema,
                    "table": table_name
                }

            for table_name, table_data in snow_metadata.items():
                all_snow_metadata[f"{snow_schema}.{table_name}"] = {
                    **table_data,
                    "schema": snow_schema,
                    "table": table_name
                }

            schema_results.append({
                "sql_schema": sql_schema,
                "snowflake_schema": snow_schema,
                "sql_tables": len(sql_metadata),
                "snowflake_tables": len(snow_metadata)
            })

        # Create table mappings
        print(f"[PROJECT_SETUP] Creating table mappings...")
        mappings = create_table_mappings(all_sql_metadata, all_snow_metadata)
        print(f"[PROJECT_SETUP] Created {len(mappings)} table mappings")

        # Generate YAML files
        print(f"[PROJECT_SETUP] Generating YAML configuration files...")
        from pydantic import BaseModel
        class DummyRequest(BaseModel):
            sql_server_database: str
            snowflake_database: str
            sql_server_schema: str
            snowflake_schema: str

        dummy_request = DummyRequest(
            sql_server_database=project_metadata.get("sql_database"),
            snowflake_database=project_metadata.get("snowflake_database"),
            sql_server_schema=list(schema_mappings.keys())[0] if schema_mappings else "dbo",
            snowflake_schema=list(schema_mappings.values())[0] if schema_mappings else "PUBLIC"
        )

        yaml_output = generate_yaml_files(mappings, dummy_request, schema_mappings)
        print(f"[PROJECT_SETUP] YAML generation result: {yaml_output}")

        # Check if YAML generation failed
        if "error" in yaml_output:
            print(f"[PROJECT_SETUP] ERROR: YAML generation failed - {yaml_output['error']}")
        else:
            print(f"[PROJECT_SETUP] ✓ YAML files saved successfully:")
            print(f"[PROJECT_SETUP]   - tables.yaml ({yaml_output.get('sql_tables_count', 0)} SQL, {yaml_output.get('snow_tables_count', 0)} Snowflake)")
            print(f"[PROJECT_SETUP]   - column_mappings.yaml ({yaml_output.get('column_mappings_count', 0)} mappings)")
            print(f"[PROJECT_SETUP]   - relationships.yaml ({yaml_output.get('relationships_count', 0)} relationships)")
            print(f"[PROJECT_SETUP]   - schema_mappings.yaml ({yaml_output.get('schema_mappings_count', 0)} mappings)")

        # Infer relationships
        print(f"[PROJECT_SETUP] Inferring relationships...")
        automation = ProjectAutomation(project_id, project_metadata["name"])
        relationships = automation.infer_relationships(all_sql_metadata)
        print(f"[PROJECT_SETUP] Inferred {len(relationships)} relationships")

        # Update project metadata
        project_metadata["updated_at"] = datetime.now().isoformat()
        project_metadata["has_metadata"] = True
        project_metadata["has_relationships"] = True
        project_metadata["table_mappings_count"] = len(mappings)

        with open(f"{project_dir}/project.json", "w") as f:
            json.dump(project_metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"Complete auto-setup finished for {project_metadata['name']}",
            "table_count": len(all_sql_metadata),
            "relationship_count": len(relationships),
            "table_mappings_count": len(mappings),
            "schema_results": schema_results,
            "metadata": all_sql_metadata,
            "relationships": relationships
        }

    except Exception as e:
        print(f"[PROJECT_SETUP] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to setup project: {str(e)}")


@router.post("/{project_id}/setup-from-existing")
async def setup_project_from_existing(
    project_id: str,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Setup project using existing YAML files instead of re-extracting metadata.
    This loads tables, relationships, and mappings from YAML configuration files.

    Requires: User or Admin role
    """
    try:
        project_dir = f"{get_projects_dir()}/{project_id}"
        config_dir = f"{project_dir}/config"

        if not os.path.exists(project_dir):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")

        if not os.path.exists(config_dir):
            raise HTTPException(status_code=400, detail="No config directory found. Please run 'Extract Metadata' first.")

        # Load project metadata
        with open(f"{project_dir}/project.json", "r") as f:
            project_metadata = json.load(f)

        print(f"[SETUP_FROM_EXISTING] Loading existing YAML files for {project_id}")

        # Set active project for config directory
        from context import set_active_project
        set_active_project(project_id, project_metadata)

        # Load tables.yaml
        tables_yaml_path = f"{config_dir}/tables.yaml"
        if not os.path.exists(tables_yaml_path):
            raise HTTPException(status_code=400, detail="No tables.yaml found. Please run 'Extract Metadata' first.")

        with open(tables_yaml_path, "r") as f:
            tables_data = yaml.safe_load(f) or {}

        # Load relationships from multiple possible sources (same logic as diagram generation)
        relationships = []

        # Try sql_relationships.yaml first (new format)
        sql_relationships_file = f"{config_dir}/sql_relationships.yaml"
        if os.path.exists(sql_relationships_file):
            with open(sql_relationships_file, "r") as f:
                sql_rels = yaml.safe_load(f) or {}
                # Handle wrapped format {relationships: [...]}
                if isinstance(sql_rels, dict) and "relationships" in sql_rels:
                    relationships.extend(sql_rels["relationships"])
                elif isinstance(sql_rels, list):
                    relationships.extend(sql_rels)

        # Add snowflake relationships if they exist
        snow_relationships_file = f"{config_dir}/snow_relationships.yaml"
        if os.path.exists(snow_relationships_file):
            with open(snow_relationships_file, "r") as f:
                snow_rels = yaml.safe_load(f) or {}
                # Handle wrapped format {relationships: [...]}
                if isinstance(snow_rels, dict) and "relationships" in snow_rels:
                    relationships.extend(snow_rels["relationships"])
                elif isinstance(snow_rels, list):
                    relationships.extend(snow_rels)

        # Fallback to old relationships.yaml if no new files found
        if not relationships:
            relationships_yaml_path = f"{config_dir}/relationships.yaml"
            if os.path.exists(relationships_yaml_path):
                with open(relationships_yaml_path, "r") as f:
                    rels = yaml.safe_load(f) or []
                    if isinstance(rels, list):
                        relationships = rels

        # Load column_mappings.yaml
        column_mappings_path = f"{config_dir}/column_mappings.yaml"
        column_mappings = {}
        if os.path.exists(column_mappings_path):
            with open(column_mappings_path, "r") as f:
                column_mappings = yaml.safe_load(f) or {}

        # Load schema_mappings.yaml
        schema_mappings_path = f"{config_dir}/schema_mappings.yaml"
        schema_mappings = {}
        if os.path.exists(schema_mappings_path):
            with open(schema_mappings_path, "r") as f:
                schema_mappings = yaml.safe_load(f) or {}

        # Convert tables_data to metadata format
        sql_metadata = tables_data.get("sql", {})
        snow_metadata = tables_data.get("snow", {})

        # Count tables
        sql_table_count = len(sql_metadata)
        snow_table_count = len(snow_metadata)

        print(f"[SETUP_FROM_EXISTING] Loaded {sql_table_count} SQL tables, {snow_table_count} Snowflake tables")
        print(f"[SETUP_FROM_EXISTING] Loaded {len(relationships)} relationships")
        print(f"[SETUP_FROM_EXISTING] Loaded {len(column_mappings)} table mappings")
        print(f"[SETUP_FROM_EXISTING] Loaded {len(schema_mappings)} schema mappings")

        # Ensure pipelines directory exists (but don't copy old templates)
        # Pipelines will be created by comprehensive automation endpoint
        pipelines_dir = f"{project_dir}/pipelines"
        os.makedirs(pipelines_dir, exist_ok=True)

        print(f"[SETUP_FROM_EXISTING] Pipelines directory ready for comprehensive automation")
        print(f"[SETUP_FROM_EXISTING] Use 'Setup Project Automation' to generate intelligent pipelines")

        # Update project metadata
        project_metadata["updated_at"] = datetime.now().isoformat()
        project_metadata["has_metadata"] = True
        project_metadata["has_relationships"] = len(relationships) > 0
        project_metadata["table_mappings_count"] = len(column_mappings)

        with open(f"{project_dir}/project.json", "w") as f:
            json.dump(project_metadata, f, indent=2)

        return {
            "status": "success",
            "message": f"Configuration loaded for {project_metadata['name']}. Use 'Setup Project Automation' to generate pipelines.",
            "sql_table_count": sql_table_count,
            "snowflake_table_count": snow_table_count,
            "relationship_count": len(relationships),
            "table_mappings_count": len(column_mappings),
            "schema_mappings_count": len(schema_mappings),
            "metadata": sql_metadata,
            "relationships": relationships,
            "loaded_from": "existing_yaml_files",
            "next_step": "Click 'Setup Project Automation' to generate intelligent pipelines for all tables"
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[SETUP_FROM_EXISTING] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Failed to load existing configuration: {str(e)}")


@router.post("/{project_id}/create-comprehensive-pipelines")
async def create_comprehensive_pipelines(
    project_id: str,
    current_user: Optional[UserInDB] = Depends(optional_authentication)
):
    """
    Create comprehensive pipelines for all tables in the project.

    This endpoint:
    1. Analyzes each table using intelligent suggest logic
    2. Generates validation steps and custom queries with joins
    3. Creates individual pipelines with project_ prefix
    4. Creates a batch operation (projectname_batch) to run all pipelines

    Authentication: Optional (allows internal calls and authenticated users)
    """
    try:
        print(f"\n[COMPREHENSIVE_AUTOMATION] Starting for project: {project_id}")

        # Import the comprehensive automation module
        from pipelines.comprehensive_automation import create_comprehensive_automation

        # Execute comprehensive automation (now async - uses Pipeline Builder logic)
        result = await create_comprehensive_automation(project_id, get_projects_dir())

        print(f"[COMPREHENSIVE_AUTOMATION] Completed successfully")
        print(f"[COMPREHENSIVE_AUTOMATION] Pipelines created: {len(result['pipelines_created'])}")
        print(f"[COMPREHENSIVE_AUTOMATION] Batch pipeline: {result['batch_pipeline']}")

        return result

    except Exception as e:
        print(f"[COMPREHENSIVE_AUTOMATION] Error: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create comprehensive pipelines: {str(e)}"
        )


@router.get("/{project_id}/relationships")
async def get_relationships(project_id: str):
    """
    Get inferred relationships for a project.

    Returns the relationships that were inferred during setup.
    """
    try:
        project_dir = f"{get_projects_dir()}/{project_id}"
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
        project_dir = f"{get_projects_dir()}/{project_id}"
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
        project_dir = f"{get_projects_dir()}/{project_id}"
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
        project_dir = f"{get_projects_dir()}/{project_id}"
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

# Azure DevOps Configuration Endpoints

@router.post("/{project_id}/azure-devops/configure")
async def configure_azure_devops(
    project_id: str,
    config: AzureDevOpsConfig,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Configure Azure DevOps integration for a project.
    
    Args:
        project_id: Project ID
        config: Azure DevOps configuration
        
    Returns:
        Success message with configuration status
    """
    try:
        project_dir = f"{get_projects_dir()}/{project_id}"
        metadata_file = f"{project_dir}/project.json"
        
        if not os.path.exists(metadata_file):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        # Load existing metadata
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        # Update Azure DevOps configuration
        metadata["azure_devops"] = config.dict()
        metadata["updated_at"] = datetime.now().isoformat()
        
        # Save updated metadata
        with open(metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)
        
        return {
            "status": "success",
            "message": "Azure DevOps configuration updated successfully",
            "config": config.dict()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to configure Azure DevOps: {str(e)}")


@router.get("/{project_id}/azure-devops/config")
async def get_azure_devops_config(project_id: str):
    """
    Get Azure DevOps configuration for a project.
    
    Args:
        project_id: Project ID
        
    Returns:
        Azure DevOps configuration or None if not configured
    """
    try:
        project_dir = f"{get_projects_dir()}/{project_id}"
        metadata_file = f"{project_dir}/project.json"
        
        if not os.path.exists(metadata_file):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        azure_config = metadata.get("azure_devops")
        
        if not azure_config:
            return {
                "status": "not_configured",
                "message": "Azure DevOps is not configured for this project",
                "config": None
            }
        
        # Mask the PAT token in the response
        if azure_config.get("pat_token"):
            azure_config["pat_token"] = "***REDACTED***"
        
        return {
            "status": "configured",
            "message": "Azure DevOps configuration found",
            "config": azure_config
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get Azure DevOps config: {str(e)}")


@router.delete("/{project_id}/azure-devops/configure")
async def delete_azure_devops_config(
    project_id: str,
    current_user: UserInDB = Depends(require_user_or_admin)
):
    """
    Delete Azure DevOps configuration from a project.
    
    Args:
        project_id: Project ID
        
    Returns:
        Success message
    """
    try:
        project_dir = f"{get_projects_dir()}/{project_id}"
        metadata_file = f"{project_dir}/project.json"
        
        if not os.path.exists(metadata_file):
            raise HTTPException(status_code=404, detail=f"Project not found: {project_id}")
        
        with open(metadata_file, "r") as f:
            metadata = json.load(f)
        
        # Remove Azure DevOps configuration
        if "azure_devops" in metadata:
            del metadata["azure_devops"]
            metadata["updated_at"] = datetime.now().isoformat()
            
            with open(metadata_file, "w") as f:
                json.dump(metadata, f, indent=2)
            
            return {
                "status": "success",
                "message": "Azure DevOps configuration removed successfully"
            }
        else:
            return {
                "status": "not_configured",
                "message": "Azure DevOps was not configured for this project"
            }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete Azure DevOps config: {str(e)}")


class AzureDevOpsTestRequest(BaseModel):
    organization_url: str
    project_name: str
    pat_token: str


@router.post("/{project_id}/azure-devops/test")
async def test_azure_devops_connection(
    project_id: str,
    test_request: AzureDevOpsTestRequest
):
    """
    Test Azure DevOps connection without saving configuration.

    Args:
        project_id: Project ID
        test_request: Connection parameters to test

    Returns:
        Connection test results
    """
    try:
        from bugs.azure_devops_service import AzureDevOpsService

        # Initialize Azure DevOps service with provided credentials
        azure_service = AzureDevOpsService(
            organization_url=test_request.organization_url,
            project_name=test_request.project_name,
            pat_token=test_request.pat_token
        )

        # Test the connection
        result = azure_service.test_connection()

        return result

    except Exception as e:
        return {
            "success": False,
            "message": f"Connection test failed: {str(e)}",
            "error_details": str(e)
        }


def auto_map_schemas(sql_schemas: List[str], snowflake_schemas: List[str]) -> Dict[str, str]:
    """Auto-generate schema mappings between SQL Server and Snowflake using intelligent fuzzy matching"""
    # Use the intelligent schema mapper from mapping/schema_mapper.py
    from mapping.schema_mapper import auto_map_schemas as intelligent_mapper

    # Get intelligent mappings with confidence scores
    intelligent_mappings = intelligent_mapper(sql_schemas, snowflake_schemas, confidence_threshold=0.7)

    # Extract only the auto-mapped schemas
    mappings = {}
    for sql_schema, mapping_info in intelligent_mappings.items():
        if mapping_info.get("auto_mapped") and mapping_info.get("snowflake_schema"):
            mappings[sql_schema] = mapping_info["snowflake_schema"]
            print(f"[AUTO_MAP] {sql_schema} → {mapping_info['snowflake_schema']} (confidence: {mapping_info['confidence']})")
        else:
            # Low confidence - log warning
            print(f"[AUTO_MAP] WARNING: {sql_schema} has low confidence mapping (confidence: {mapping_info.get('confidence', 0)})")
            # Still include the best match but log it
            if mapping_info.get("snowflake_schema"):
                mappings[sql_schema] = mapping_info["snowflake_schema"]

    return mappings
