"""
Project context management - tracks the active project
"""
import json
import os
from typing import Optional, Dict, Any

from config.paths import paths

# Global variable to track active project
_active_project_id: Optional[str] = None
_active_project_metadata: Optional[Dict[str, Any]] = None


def set_active_project(project_id: str, metadata: Dict[str, Any]):
    """Set the active project"""
    global _active_project_id, _active_project_metadata
    _active_project_id = project_id
    _active_project_metadata = metadata

    # Persist to JSON file (new format)
    active_project_file = paths.active_project_file
    os.makedirs(active_project_file.parent, exist_ok=True)
    with open(active_project_file, "w") as f:
        json.dump({"project_id": project_id, "metadata": metadata}, f, indent=2)

    # ALSO persist to plain text file for legacy compatibility (used by bug reports)
    legacy_file = paths.active_project_file_legacy
    os.makedirs(legacy_file.parent, exist_ok=True)
    with open(legacy_file, "w") as f:
        f.write(project_id)


def get_active_project() -> Optional[Dict[str, Any]]:
    """Get the active project metadata"""
    global _active_project_id, _active_project_metadata

    # Helper to validate project exists on disk
    def project_exists(project_id: str) -> bool:
        if not project_id:
            return False
        project_dir = paths.get_project_dir(project_id)
        project_file = project_dir / "project.json"
        return project_file.exists()

    # Return from memory if available AND project still exists
    if _active_project_id and _active_project_metadata:
        if project_exists(_active_project_id):
            return {
                "project_id": _active_project_id,
                **_active_project_metadata
            }
        else:
            # Project was deleted - clear stale state
            print(f"[PROJECT_CONTEXT] Active project '{_active_project_id}' no longer exists, clearing")
            clear_active_project()
            return None

    # Try to load from file
    active_project_file = paths.active_project_file
    if active_project_file.exists():
        try:
            with open(active_project_file, "r") as f:
                data = json.load(f)
                project_id = data.get("project_id")

                # Validate project still exists before setting as active
                if project_id and project_exists(project_id):
                    _active_project_id = project_id
                    _active_project_metadata = data.get("metadata", {})
                    return {
                        "project_id": _active_project_id,
                        **_active_project_metadata
                    }
                else:
                    # Project was deleted - clear stale file
                    print(f"[PROJECT_CONTEXT] Persisted active project '{project_id}' no longer exists, clearing")
                    clear_active_project()
                    return None
        except Exception as e:
            print(f"[PROJECT_CONTEXT] Error loading active project: {e}")
            pass

    return None


def clear_active_project():
    """Clear the active project"""
    global _active_project_id, _active_project_metadata
    _active_project_id = None
    _active_project_metadata = None

    # Remove JSON file (new format)
    active_project_file = paths.active_project_file
    if active_project_file.exists():
        os.remove(active_project_file)

    # ALSO remove legacy plain text file
    legacy_file = paths.active_project_file_legacy
    if legacy_file.exists():
        os.remove(legacy_file)


def get_project_config_dir(project_id: Optional[str] = None) -> str:
    """Get the config directory for a project (or active project if not specified)"""
    if project_id is None:
        active = get_active_project()
        if active:
            project_id = active.get("project_id")

    if project_id:
        return str(paths.get_project_config_dir(project_id))
    else:
        # Fallback to core config directory
        return str(paths.core_config_dir)


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
        project_file = paths.get_project_dir(project_id) / "project.json"
        if project_file.exists():
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
