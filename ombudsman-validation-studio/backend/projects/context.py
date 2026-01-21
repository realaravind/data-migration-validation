"""
Project context management - tracks the active project
"""
import json
import os
from typing import Optional, Dict, Any

# Global variable to track active project
_active_project_id: Optional[str] = None
_active_project_metadata: Optional[Dict[str, Any]] = None

PROJECTS_DIR = "/data/projects"
ACTIVE_PROJECT_FILE = "/data/.active_project"


def set_active_project(project_id: str, metadata: Dict[str, Any]):
    """Set the active project"""
    global _active_project_id, _active_project_metadata
    _active_project_id = project_id
    _active_project_metadata = metadata

    # Persist to JSON file (new format)
    os.makedirs(os.path.dirname(ACTIVE_PROJECT_FILE), exist_ok=True)
    with open(ACTIVE_PROJECT_FILE, "w") as f:
        json.dump({"project_id": project_id, "metadata": metadata}, f, indent=2)

    # ALSO persist to plain text file for legacy compatibility (used by bug reports)
    legacy_file = "/data/active_project.txt"
    os.makedirs(os.path.dirname(legacy_file), exist_ok=True)
    with open(legacy_file, "w") as f:
        f.write(project_id)


def get_active_project() -> Optional[Dict[str, Any]]:
    """Get the active project metadata"""
    global _active_project_id, _active_project_metadata

    # Return from memory if available
    if _active_project_id and _active_project_metadata:
        return {
            "project_id": _active_project_id,
            **_active_project_metadata
        }

    # Try to load from file
    if os.path.exists(ACTIVE_PROJECT_FILE):
        try:
            with open(ACTIVE_PROJECT_FILE, "r") as f:
                data = json.load(f)
                _active_project_id = data.get("project_id")
                _active_project_metadata = data.get("metadata", {})
                return {
                    "project_id": _active_project_id,
                    **_active_project_metadata
                }
        except Exception:
            pass

    return None


def clear_active_project():
    """Clear the active project"""
    global _active_project_id, _active_project_metadata
    _active_project_id = None
    _active_project_metadata = None

    # Remove JSON file (new format)
    if os.path.exists(ACTIVE_PROJECT_FILE):
        os.remove(ACTIVE_PROJECT_FILE)

    # ALSO remove legacy plain text file
    legacy_file = "/data/active_project.txt"
    if os.path.exists(legacy_file):
        os.remove(legacy_file)


def get_project_config_dir(project_id: Optional[str] = None) -> str:
    """Get the config directory for a project (or active project if not specified)"""
    if project_id is None:
        active = get_active_project()
        if active:
            project_id = active.get("project_id")

    if project_id:
        return f"{PROJECTS_DIR}/{project_id}/config"
    else:
        # Fallback to core config directory
        return "/core/src/ombudsman/config"


def get_project_database_config(project_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Get database configuration for a project"""
    if project_id is None:
        active = get_active_project()
        if active:
            return {
                "sql_database": active.get("sql_database"),
                "sql_schemas": active.get("sql_schemas", []),
                "snowflake_database": active.get("snowflake_database"),
                "snowflake_schemas": active.get("snowflake_schemas", []),
                "schema_mappings": active.get("schema_mappings", {})
            }
    else:
        # Load from project file
        project_file = f"{PROJECTS_DIR}/{project_id}/project.json"
        if os.path.exists(project_file):
            with open(project_file, "r") as f:
                metadata = json.load(f)
                return {
                    "sql_database": metadata.get("sql_database"),
                    "sql_schemas": metadata.get("sql_schemas", []),
                    "snowflake_database": metadata.get("snowflake_database"),
                    "snowflake_schemas": metadata.get("snowflake_schemas", []),
                    "schema_mappings": metadata.get("schema_mappings", {})
                }

    return None
