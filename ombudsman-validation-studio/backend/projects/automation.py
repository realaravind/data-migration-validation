"""
Project Automation Module

Handles automated project setup including:
- Metadata extraction for all tables
- Relationship inference
- Automated pipeline creation
- Batch creation and execution
"""

from typing import Dict, List, Optional, Any
import sys
import os
import json
import yaml
from pathlib import Path

# Add core to Python path
sys.path.insert(0, "/core/src")

from ombudsman.core.metadata_loader import MetadataLoader
from ombudsman.core.relationship_inferrer import RelationshipInferrer


class ProjectAutomation:
    """Handles automated project setup and pipeline generation"""

    def __init__(self, project_id: str, project_name: str):
        """
        Initialize automation for a project.

        Args:
            project_id: Unique project identifier
            project_name: Project name (used for prefixing pipelines)
        """
        self.project_id = project_id
        self.project_name = project_name
        self.projects_dir = Path("/data/projects")
        self.project_dir = self.projects_dir / project_id

        # Ensure project directory exists
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def extract_all_metadata(self, connection: str, schema: Optional[str] = None) -> Dict[str, Any]:
        """
        Extract metadata for all tables in the specified connection.

        Args:
            connection: "sqlserver" or "snowflake"
            schema: Optional schema name to filter tables

        Returns:
            Dictionary of table metadata:
            {
                "schema.table": {
                    "columns": {"col1": "INT", ...},
                    "schema": "dbo",
                    "table": "table_name",
                    "object_type": "TABLE"
                },
                ...
            }
        """
        print(f"[ProjectAutomation] Extracting metadata from {connection}")

        # Create metadata loader
        loader = MetadataLoader(connection)

        # Get all tables
        tables = loader.get_tables(schema=schema)
        print(f"[ProjectAutomation] Found {len(tables)} tables")

        metadata = {}

        for table_info in tables:
            table_schema = table_info.get('TABLE_SCHEMA') or table_info.get('schema', schema or 'dbo')
            table_name = table_info.get('TABLE_NAME') or table_info.get('table')

            if not table_name:
                continue

            # Get column metadata for this table
            try:
                # Pass schema.table format to get_columns (it expects a single parameter)
                full_table_name = f"{table_schema}.{table_name}"
                columns_list = loader.get_columns(full_table_name)

                # Convert columns list to dict format expected by RelationshipInferrer
                # From: [{"name": "col1", "data_type": "INT", ...}, ...]
                # To: {"col1": "INT", "col2": "VARCHAR", ...}
                columns_dict = {col["name"]: col["data_type"] for col in columns_list}

                # Build metadata structure
                table_key = f"{table_schema}.{table_name}"
                metadata[table_key] = {
                    "columns": columns_dict,
                    "schema": table_schema,
                    "table": table_name,
                    "object_type": "TABLE"
                }

                print(f"[ProjectAutomation]   - {table_key}: {len(columns_dict)} columns")

            except Exception as e:
                print(f"[ProjectAutomation] Warning: Could not extract metadata for {table_schema}.{table_name}: {e}")
                continue

        # Save metadata to project directory
        metadata_file = self.project_dir / "metadata.json"
        with open(metadata_file, 'w') as f:
            json.dump(metadata, f, indent=2)

        print(f"[ProjectAutomation] Metadata saved to {metadata_file}")

        return metadata

    def infer_relationships(self, metadata: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Infer relationships from metadata.

        Args:
            metadata: Table metadata dictionary

        Returns:
            List of inferred relationships:
            [
                {
                    "fact_table": "fact_sales",
                    "fk_column": "customer_id",
                    "dim_table": "dim_customer",
                    "dim_column": "customer_id",
                    "confidence": "high",
                    "reason": "Column name match + fact/dim pattern"
                },
                ...
            ]
        """
        print(f"[ProjectAutomation] Inferring relationships from {len(metadata)} tables")

        # Create relationship inferrer
        inferrer = RelationshipInferrer()

        # Infer all relationships
        relationships = inferrer.infer_all_relationships(metadata)

        print(f"[ProjectAutomation] Found {len(relationships)} potential relationships")

        # Save relationships to project directory
        relationships_file = self.project_dir / "relationships.json"
        with open(relationships_file, 'w') as f:
            json.dump(relationships, f, indent=2)

        print(f"[ProjectAutomation] Relationships saved to {relationships_file}")

        return relationships

    def get_metadata(self) -> Optional[Dict[str, Any]]:
        """Load saved metadata for this project"""
        metadata_file = self.project_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        with open(metadata_file, 'r') as f:
            return json.load(f)

    def get_relationships(self) -> Optional[List[Dict[str, Any]]]:
        """Load saved relationships for this project"""
        relationships_file = self.project_dir / "relationships.json"

        if not relationships_file.exists():
            return None

        with open(relationships_file, 'r') as f:
            return json.load(f)

    def save_relationships(self, relationships: List[Dict[str, Any]]):
        """
        Save updated relationships (after user validation/editing).

        Args:
            relationships: List of relationship dictionaries
        """
        relationships_file = self.project_dir / "relationships.json"

        with open(relationships_file, 'w') as f:
            json.dump(relationships, f, indent=2)

        print(f"[ProjectAutomation] Updated relationships saved to {relationships_file}")

    def get_setup_status(self) -> Dict[str, Any]:
        """
        Get current setup status for this project.

        Returns:
            {
                "has_metadata": bool,
                "has_relationships": bool,
                "table_count": int,
                "relationship_count": int,
                "ready_for_automation": bool
            }
        """
        metadata = self.get_metadata()
        relationships = self.get_relationships()

        has_metadata = metadata is not None
        has_relationships = relationships is not None

        return {
            "has_metadata": has_metadata,
            "has_relationships": has_relationships,
            "table_count": len(metadata) if metadata else 0,
            "relationship_count": len(relationships) if relationships else 0,
            "ready_for_automation": has_metadata and has_relationships
        }
