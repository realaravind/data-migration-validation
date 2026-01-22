"""
Workload Storage Manager
Handles storing and retrieving workload data
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path
import uuid

from config.paths import paths


class WorkloadStorage:
    """Manage workload data storage"""

    def __init__(self, base_path: str = None):
        self.base_path = Path(base_path) if base_path else paths.workloads_dir
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_project_path(self, project_id: str) -> Path:
        """Get the directory path for a project's workloads"""
        project_path = self.base_path / project_id
        project_path.mkdir(parents=True, exist_ok=True)
        return project_path

    def _get_workload_path(self, project_id: str, workload_id: str) -> Path:
        """Get the file path for a specific workload"""
        return self._get_project_path(project_id) / f"{workload_id}.json"

    def save_workload(self, project_id: str, workload_data: Dict) -> str:
        """
        Save a workload to storage

        Args:
            project_id: Project identifier
            workload_data: Workload data including queries and metadata

        Returns:
            workload_id: Unique identifier for the saved workload
        """
        # Generate workload ID
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        workload_id = f"wl_{timestamp}_{unique_id}"

        # Add metadata
        workload_data['workload_id'] = workload_id
        workload_data['project_id'] = project_id
        workload_data['upload_date'] = datetime.now().isoformat()

        # Save to file
        file_path = self._get_workload_path(project_id, workload_id)
        with open(file_path, 'w') as f:
            json.dump(workload_data, f, indent=2)

        return workload_id

    def get_workload(self, project_id: str, workload_id: str) -> Optional[Dict]:
        """
        Retrieve a workload by ID

        Args:
            project_id: Project identifier
            workload_id: Workload identifier

        Returns:
            Workload data or None if not found
        """
        file_path = self._get_workload_path(project_id, workload_id)

        if not file_path.exists():
            return None

        with open(file_path, 'r') as f:
            return json.load(f)

    def list_workloads(self, project_id: str) -> List[Dict]:
        """
        List all workloads for a project

        Args:
            project_id: Project identifier

        Returns:
            List of workload summaries
        """
        project_path = self._get_project_path(project_id)
        workloads = []

        for file_path in project_path.glob("wl_*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Return summary only
                    workloads.append({
                        'workload_id': data.get('workload_id'),
                        'upload_date': data.get('upload_date'),
                        'query_count': data.get('query_count', 0),
                        'total_executions': data.get('total_executions', 0),
                        'date_range': data.get('date_range', {}),
                        'tables_count': len(data.get('analysis', {}).get('tables', {}))
                    })
            except Exception as e:
                print(f"Error reading workload {file_path}: {e}")
                continue

        # Sort by upload date, newest first
        workloads.sort(key=lambda x: x.get('upload_date', ''), reverse=True)
        return workloads

    def delete_workload(self, project_id: str, workload_id: str) -> bool:
        """
        Delete a workload

        Args:
            project_id: Project identifier
            workload_id: Workload identifier

        Returns:
            True if deleted, False if not found
        """
        file_path = self._get_workload_path(project_id, workload_id)

        if not file_path.exists():
            return False

        file_path.unlink()
        return True

    def update_workload(self, project_id: str, workload_id: str, updates: Dict) -> bool:
        """
        Update a workload (e.g., add analysis results)

        Args:
            project_id: Project identifier
            workload_id: Workload identifier
            updates: Dictionary of fields to update

        Returns:
            True if updated, False if not found
        """
        workload = self.get_workload(project_id, workload_id)

        if not workload:
            return False

        # Merge updates
        workload.update(updates)
        workload['last_updated'] = datetime.now().isoformat()

        # Save back
        file_path = self._get_workload_path(project_id, workload_id)
        with open(file_path, 'w') as f:
            json.dump(workload, f, indent=2)

        return True
