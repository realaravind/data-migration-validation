"""
Centralized Path Configuration Module

All application paths are configurable via environment variables with sensible defaults.
Directories are automatically created if they don't exist.

Environment Variables:
- OMBUDSMAN_DATA_DIR: Base directory for all data (default: ./data for dev, /data for production)
- OMBUDSMAN_CORE_DIR: Core library config directory (default: ../ombudsman_core/src/ombudsman/config)
- OMBUDSMAN_LOG_DIR: Log directory (default: ./logs)

Usage:
    from config.paths import paths

    # Access paths
    projects_dir = paths.projects_dir
    pipelines_dir = paths.pipelines_dir

    # Get project-specific path
    project_config = paths.get_project_config_dir("my_project")
"""

import os
from pathlib import Path
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def _is_production() -> bool:
    """Check if running in production environment."""
    return os.getenv("ENVIRONMENT", "development").lower() in ("production", "prod")


def _get_default_data_dir() -> str:
    """Get default data directory based on environment."""
    if _is_production():
        return "/data"
    # Development: relative to backend directory
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def _get_default_core_dir() -> str:
    """Get default core config directory based on environment."""
    if _is_production():
        return "/core/src/ombudsman/config"
    # Development: relative to project root
    backend_dir = os.path.dirname(os.path.dirname(__file__))
    project_root = os.path.dirname(os.path.dirname(backend_dir))
    return os.path.join(project_root, "ombudsman_core", "src", "ombudsman", "config")


class PathConfig:
    """
    Centralized path configuration with auto-creation of directories.

    All paths are configurable via environment variables and directories
    are created automatically when first accessed.
    """

    def __init__(self):
        self._initialized = False
        self._data_dir: Optional[Path] = None
        self._core_dir: Optional[Path] = None
        self._log_dir: Optional[Path] = None

    def initialize(self):
        """Initialize all paths and create directories."""
        if self._initialized:
            return

        # Base directories from environment
        self._data_dir = Path(os.getenv("OMBUDSMAN_DATA_DIR", _get_default_data_dir()))
        self._core_dir = Path(os.getenv("OMBUDSMAN_CORE_DIR", _get_default_core_dir()))
        self._log_dir = Path(os.getenv("OMBUDSMAN_LOG_DIR",
                                        os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")))

        # Create all required directories
        self._ensure_directories()
        self._initialized = True

        logger.info(f"Path configuration initialized:")
        logger.info(f"  Data directory: {self._data_dir}")
        logger.info(f"  Core directory: {self._core_dir}")
        logger.info(f"  Log directory: {self._log_dir}")

    def _ensure_directories(self):
        """Create all required directories if they don't exist.

        Note: This method is called during initialization, so we must use
        direct path construction (self._data_dir / "subdir") instead of
        property accessors (self.projects_dir) to avoid infinite recursion.
        """
        directories = [
            self._data_dir / "projects",
            self._data_dir / "pipelines",
            self._data_dir / "batch_jobs",
            self._data_dir / "batch_templates",
            self._data_dir / "auth",
            self._data_dir / "results",
            self._data_dir / "queries",
            self._data_dir / "workloads",
            self._data_dir / "audit_logs",
            self._data_dir / "mapping_intelligence",
            self._log_dir,
        ]

        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                logger.debug(f"Ensured directory exists: {directory}")
            except Exception as e:
                logger.warning(f"Could not create directory {directory}: {e}")

    def _ensure_init(self):
        """Ensure paths are initialized before access."""
        if not self._initialized:
            self.initialize()

    # =========================================================================
    # Base Directories
    # =========================================================================

    @property
    def data_dir(self) -> Path:
        """Base data directory."""
        self._ensure_init()
        return self._data_dir

    @property
    def core_config_dir(self) -> Path:
        """Core library config directory (relationships, column mappings, etc)."""
        self._ensure_init()
        return self._core_dir

    @property
    def log_dir(self) -> Path:
        """Log directory."""
        self._ensure_init()
        return self._log_dir

    # =========================================================================
    # Data Subdirectories
    # =========================================================================

    @property
    def projects_dir(self) -> Path:
        """Projects directory."""
        self._ensure_init()
        return self._data_dir / "projects"

    @property
    def pipelines_dir(self) -> Path:
        """Pipelines directory (flat structure for non-project pipelines)."""
        self._ensure_init()
        return self._data_dir / "pipelines"

    @property
    def batch_jobs_dir(self) -> Path:
        """Batch jobs directory."""
        self._ensure_init()
        return self._data_dir / "batch_jobs"

    @property
    def batch_templates_dir(self) -> Path:
        """Batch templates directory."""
        self._ensure_init()
        return self._data_dir / "batch_templates"

    @property
    def auth_dir(self) -> Path:
        """Auth database directory."""
        self._ensure_init()
        return self._data_dir / "auth"

    @property
    def results_dir(self) -> Path:
        """Validation results directory."""
        self._ensure_init()
        return self._data_dir / "results"

    @property
    def queries_dir(self) -> Path:
        """Query history directory."""
        self._ensure_init()
        return self._data_dir / "queries"

    @property
    def workloads_dir(self) -> Path:
        """Workloads directory."""
        self._ensure_init()
        return self._data_dir / "workloads"

    @property
    def audit_logs_dir(self) -> Path:
        """Audit logs directory."""
        self._ensure_init()
        return self._data_dir / "audit_logs"

    @property
    def mapping_intelligence_dir(self) -> Path:
        """ML mapping intelligence directory."""
        self._ensure_init()
        return self._data_dir / "mapping_intelligence"

    @property
    def query_history_dir(self) -> Path:
        """Query history storage directory."""
        self._ensure_init()
        return self._data_dir / "query_history"

    @property
    def config_backups_dir(self) -> Path:
        """Configuration backups directory."""
        self._ensure_init()
        return self._data_dir / "config_backups"

    @property
    def pipeline_runs_dir(self) -> Path:
        """Pipeline runs directory."""
        self._ensure_init()
        return self._data_dir / "pipeline_runs"

    # =========================================================================
    # Special Files
    # =========================================================================

    @property
    def active_project_file(self) -> Path:
        """Active project marker file."""
        self._ensure_init()
        return self._data_dir / ".active_project"

    @property
    def active_project_file_legacy(self) -> Path:
        """Legacy active project file (for backwards compatibility)."""
        self._ensure_init()
        return self._data_dir / "active_project.txt"

    @property
    def notification_rules_file(self) -> Path:
        """Notification rules file."""
        self._ensure_init()
        return self._data_dir / "notification_rules.json"

    # =========================================================================
    # Project-Specific Paths
    # =========================================================================

    def get_project_dir(self, project_id: str) -> Path:
        """Get directory for a specific project."""
        self._ensure_init()
        project_dir = self.projects_dir / project_id
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir

    def get_project_config_dir(self, project_id: str) -> Path:
        """Get config directory for a specific project."""
        config_dir = self.get_project_dir(project_id) / "config"
        config_dir.mkdir(parents=True, exist_ok=True)
        return config_dir

    def get_project_pipelines_dir(self, project_id: str) -> Path:
        """Get pipelines directory for a specific project."""
        pipelines_dir = self.get_project_dir(project_id) / "pipelines"
        pipelines_dir.mkdir(parents=True, exist_ok=True)
        return pipelines_dir

    def get_project_results_dir(self, project_id: str) -> Path:
        """Get results directory for a specific project."""
        results_dir = self.get_project_dir(project_id) / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        return results_dir

    def get_project_workloads_dir(self, project_id: str) -> Path:
        """Get workloads directory for a specific project."""
        workloads_dir = self.get_project_dir(project_id) / "workloads"
        workloads_dir.mkdir(parents=True, exist_ok=True)
        return workloads_dir

    def get_project_bugs_dir(self, project_id: str) -> Path:
        """Get bugs directory for a specific project."""
        bugs_dir = self.get_project_dir(project_id) / "bugs"
        bugs_dir.mkdir(parents=True, exist_ok=True)
        return bugs_dir

    # =========================================================================
    # Helper Methods
    # =========================================================================

    def resolve_path(self, path: str) -> Path:
        """
        Resolve a path that may be relative or absolute.
        Relative paths are resolved from the data directory.
        """
        self._ensure_init()
        p = Path(path)
        if p.is_absolute():
            return p
        return self._data_dir / path

    def get_pipeline_search_paths(self, project_id: Optional[str] = None) -> list[Path]:
        """Get list of paths to search for pipelines."""
        self._ensure_init()
        paths = []
        if project_id:
            paths.append(self.get_project_pipelines_dir(project_id))
        paths.append(self.pipelines_dir)
        paths.append(self.batch_jobs_dir)
        return paths

    def as_dict(self) -> dict:
        """Return all paths as a dictionary for debugging."""
        self._ensure_init()
        return {
            "data_dir": str(self._data_dir),
            "core_config_dir": str(self._core_dir),
            "log_dir": str(self._log_dir),
            "projects_dir": str(self.projects_dir),
            "pipelines_dir": str(self.pipelines_dir),
            "batch_jobs_dir": str(self.batch_jobs_dir),
            "batch_templates_dir": str(self.batch_templates_dir),
            "auth_dir": str(self.auth_dir),
            "results_dir": str(self.results_dir),
            "queries_dir": str(self.queries_dir),
            "workloads_dir": str(self.workloads_dir),
            "audit_logs_dir": str(self.audit_logs_dir),
            "mapping_intelligence_dir": str(self.mapping_intelligence_dir),
            "active_project_file": str(self.active_project_file),
        }


# Singleton instance
paths = PathConfig()


# Convenience function to initialize paths on import
def init_paths():
    """Initialize paths configuration. Called automatically on first access."""
    paths.initialize()


# For backwards compatibility, expose key paths as module-level constants
# These will trigger initialization on first access
def get_projects_dir() -> str:
    """Get projects directory as string (for backwards compatibility)."""
    return str(paths.projects_dir)


def get_core_config_dir() -> str:
    """Get core config directory as string (for backwards compatibility)."""
    return str(paths.core_config_dir)


def get_data_dir() -> str:
    """Get data directory as string (for backwards compatibility)."""
    return str(paths.data_dir)
