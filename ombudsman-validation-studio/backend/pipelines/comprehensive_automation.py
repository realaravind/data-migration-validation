"""
Comprehensive Pipeline Automation

This module provides end-to-end pipeline automation for all matching tables:
1. Analyzes each table using intelligent suggest logic
2. Generates validations and custom queries with joins
3. Creates individual pipelines with project_ prefix
4. Bundles all pipelines into a batch operation (projectname_batch)
"""

from typing import List, Dict, Any, Optional
import yaml
import os
import json
from pathlib import Path
import asyncio

# Import existing intelligent modules
from .intelligent_suggest import (
    _extract_metadata_structure,
    format_yaml,
    suggest_fact_validations,
    FactAnalysisRequest
)
from .intelligent_query_generator import IntelligentQueryGenerator


class ComprehensivePipelineAutomation:
    """
    Automates pipeline creation for all tables in a project using intelligent analysis
    """

    def __init__(self, project_id: str, projects_dir: str = "/data/projects"):
        self.project_id = project_id
        self.projects_dir = projects_dir
        self.project_dir = f"{projects_dir}/{project_id}"
        self.config_dir = f"{self.project_dir}/config"
        self.pipelines_dir = f"{self.project_dir}/pipelines"

        # Ensure pipelines directory exists
        os.makedirs(self.pipelines_dir, exist_ok=True)

        # Load project configuration
        self.metadata = self._load_metadata()
        self.relationships = self._load_relationships()
        self.table_mappings = self._load_table_mappings()

    def _load_metadata(self) -> Dict[str, Any]:
        """Load table metadata from tables.yaml"""
        tables_file = f"{self.config_dir}/tables.yaml"
        if os.path.exists(tables_file):
            with open(tables_file, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _load_relationships(self) -> List[Dict[str, Any]]:
        """Load relationships from both sql_relationships.yaml and snow_relationships.yaml"""
        relationships = []

        # Load SQL Server relationships
        sql_rel_file = f"{self.config_dir}/sql_relationships.yaml"
        if os.path.exists(sql_rel_file):
            with open(sql_rel_file, "r") as f:
                sql_rels = yaml.safe_load(f) or {}
                if isinstance(sql_rels, dict) and "relationships" in sql_rels:
                    relationships.extend(sql_rels["relationships"])
                elif isinstance(sql_rels, list):
                    relationships.extend(sql_rels)

        # Load Snowflake relationships
        snow_rel_file = f"{self.config_dir}/snow_relationships.yaml"
        if os.path.exists(snow_rel_file):
            with open(snow_rel_file, "r") as f:
                snow_rels = yaml.safe_load(f) or {}
                if isinstance(snow_rels, dict) and "relationships" in snow_rels:
                    relationships.extend(snow_rels["relationships"])
                elif isinstance(snow_rels, list):
                    relationships.extend(snow_rels)

        return relationships

    def _load_table_mappings(self) -> Dict[str, Any]:
        """Load table mappings from mapping.yaml"""
        mapping_file = f"{self.config_dir}/mapping.yaml"
        if os.path.exists(mapping_file):
            with open(mapping_file, "r") as f:
                return yaml.safe_load(f) or {}
        return {}

    def _is_fact_table(self, table_name: str) -> bool:
        """Check if table is a fact table"""
        table_lower = table_name.lower()
        return 'fact' in table_lower or table_lower.startswith('fact')

    def _is_dim_table(self, table_name: str) -> bool:
        """Check if table is a dimension table"""
        table_lower = table_name.lower()
        return 'dim' in table_lower or table_lower.startswith('dim')

    def _get_table_relationships(self, table_name: str) -> List[Dict[str, Any]]:
        """Get all relationships for a specific table"""
        table_lower = table_name.lower()
        table_rels = []

        for rel in self.relationships:
            source_table = rel.get("source_table", "").lower()
            target_table = rel.get("target_table", "").lower()
            dim_table = rel.get("dim_table", "").lower()

            # Match relationships where this table is the source or fact table
            if source_table == table_lower or dim_table == target_table.lower():
                table_rels.append(rel)

        return table_rels

    def _analyze_table_columns(self, columns: Dict[str, str]) -> Dict[str, List[str]]:
        """
        Analyze columns and categorize them.
        Returns: {
            'numeric_columns': [...],
            'date_columns': [...],
            'fk_columns': [...],
            'categorical_columns': [...]
        }
        """
        numeric_columns = []
        date_columns = []
        fk_columns = []
        categorical_columns = []

        # Extract actual columns dict if wrapped
        if 'columns' in columns and isinstance(columns['columns'], dict):
            actual_columns = columns['columns']
        else:
            actual_columns = columns

        for col_name, col_type in actual_columns.items():
            if not isinstance(col_type, str):
                continue

            col_type_lower = col_type.lower()
            col_name_lower = col_name.lower()

            # Numeric columns
            if any(t in col_type_lower for t in ['int', 'decimal', 'numeric', 'number', 'float', 'money']):
                numeric_columns.append(col_name)

            # Date columns
            if any(t in col_type_lower for t in ['date', 'datetime', 'timestamp']):
                date_columns.append(col_name)

            # FK columns
            if any(suffix in col_name_lower for suffix in ['id', 'key', '_fk']):
                if col_name_lower not in ['id', 'factid', 'rowid']:
                    fk_columns.append(col_name)

            # Categorical columns (string types with specific keywords)
            if any(t in col_type_lower for t in ['varchar', 'char', 'string', 'text']):
                if any(k in col_name_lower for k in ['category', 'type', 'status', 'region', 'segment', 'name']):
                    categorical_columns.append(col_name)

        return {
            'numeric_columns': numeric_columns,
            'date_columns': date_columns,
            'fk_columns': fk_columns,
            'categorical_columns': categorical_columns
        }

    async def _generate_complete_pipeline_using_intelligent_suggest(
        self, table_name: str, table_metadata: Dict[str, Any],
        relationships: List[Dict[str, Any]]
    ) -> str:
        """
        Generate COMPLETE pipeline YAML using BOTH Pipeline Builder functions:
        1. suggest_fact_validations() - generates all validation steps
        2. IntelligentQueryGenerator.generate_intelligent_queries() - generates 30 custom queries with JOINs

        This replicates clicking BOTH buttons in the Pipeline Builder UI:
        - "Analyze & Suggest" button
        - "Suggest Custom Queries with Joins" button
        """
        try:
            # Extract columns from metadata
            columns = table_metadata.get('columns', {})
            if isinstance(columns, dict):
                # Convert to list format expected by suggest_fact_validations
                columns_list = [
                    {"name": col_name, "data_type": col_type}
                    for col_name, col_type in columns.items()
                ]
            else:
                columns_list = columns

            # Parse schema from table name
            table_parts = table_name.rsplit('.', 1)
            if len(table_parts) == 2:
                schema, table = table_parts
            else:
                schema, table = "PUBLIC", table_parts[0]

            # STEP 1: Call suggest_fact_validations() to get validation steps
            analysis_request = FactAnalysisRequest(
                fact_table=table_name,
                fact_schema=schema,
                database_type="snow",
                columns=columns_list,
                relationships=relationships
            )

            result = await suggest_fact_validations(analysis_request)

            if "pipeline_yaml" not in result:
                print(f"[AUTOMATION] Warning: No pipeline_yaml in result for {table_name}")
                return None

            pipeline_yaml_str = result["pipeline_yaml"]
            total_validations = result.get("total_validations", 0)
            print(f"[AUTOMATION] Step 1: Generated {total_validations} validation steps")

            # STEP 2: Generate custom queries using IntelligentQueryGenerator
            # (This is what "Suggest Custom Queries with Joins" button does)
            try:
                generator = IntelligentQueryGenerator(metadata_path=self.config_dir)
                intelligent_queries = generator.generate_intelligent_queries(database="snow")

                # Filter queries for this specific table
                table_queries = [q for q in intelligent_queries if q.get('fact_table') == table_name]

                if table_queries:
                    print(f"[AUTOMATION] Step 2: Generated {len(table_queries)} custom queries with JOINs")

                    # Instead of modifying the dictionary and re-dumping YAML,
                    # append custom queries as YAML text to preserve SQL formatting
                    custom_queries_yaml = []

                    for idx, query in enumerate(table_queries):
                        sql_query = query.get('sql_server_query', '')
                        snow_query = query.get('snowflake_query', '')
                        description = query.get('description', '')

                        # Format as YAML with literal block scalars (|) for SQL
                        custom_step_yaml = f"""  - name: custom_sql_{idx+1}
    description: {description}
    validator: custom_sql
    config:
      sql_query: |
        {sql_query.replace(chr(10), chr(10) + '        ')}
      snow_query: |
        {snow_query.replace(chr(10), chr(10) + '        ')}
      comparison_type: exact_match
      tolerance: 0.0"""

                        custom_queries_yaml.append(custom_step_yaml)

                    # Append custom queries to the existing pipeline YAML
                    if custom_queries_yaml:
                        # Find the steps section and append
                        pipeline_yaml_str = pipeline_yaml_str.rstrip()
                        for custom_yaml in custom_queries_yaml:
                            pipeline_yaml_str += "\n" + custom_yaml

                    print(f"[AUTOMATION] Total steps: {total_validations + len(table_queries)}")
                else:
                    print(f"[AUTOMATION] Step 2: No custom queries generated for {table_name}")

            except Exception as e:
                print(f"[AUTOMATION] Warning: Could not generate custom queries: {e}")
                # Continue with just the validations

            return pipeline_yaml_str

        except Exception as e:
            print(f"[AUTOMATION] Error calling intelligent suggest for {table_name}: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _generate_custom_queries_with_joins(self, table_name: str, table_metadata: Dict[str, Any],
                                           relationships: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate custom SQL queries with joins using IntelligentQueryGenerator logic.
        These queries provide analytical validation across multiple dimensions.
        """
        custom_queries = []

        # Only generate join queries for fact tables with relationships
        if not self._is_fact_table(table_name) or not relationships:
            return custom_queries

        # Use IntelligentQueryGenerator to create queries
        try:
            # Initialize generator with project config
            generator = IntelligentQueryGenerator(metadata_path=self.config_dir)

            # Generate queries for this specific table
            # Note: IntelligentQueryGenerator expects tables to be loaded from metadata_path
            # So we'll manually call its internal methods with our data

            # Analyze columns
            column_analysis = self._analyze_table_columns(table_metadata)
            numeric_cols = column_analysis['numeric_columns']

            # Build custom queries from relationships
            for rel in relationships[:3]:  # Limit to top 3 relationships to avoid too many queries
                dim_table = rel.get("dim_table") or rel.get("target_table")
                fk_column = rel.get("fk_column") or rel.get("source_column")
                dim_column = rel.get("dim_column") or rel.get("target_column", f"{dim_table}_KEY")

                if not dim_table or not fk_column:
                    continue

                # Get dimension table columns
                dim_metadata = self.metadata.get("snow", {}).get(dim_table) or self.metadata.get("sql", {}).get(dim_table)
                if not dim_metadata:
                    continue

                dim_column_analysis = self._analyze_table_columns(dim_metadata)
                dim_categorical = dim_column_analysis['categorical_columns']

                # Generate aggregation query for each measure and categorical column
                for measure in numeric_cols[:2]:  # Top 2 measures
                    for cat_col in dim_categorical[:1]:  # Top 1 categorical
                        # Split table names for schema.table format
                        fact_parts = table_name.rsplit('.', 1)
                        dim_parts = dim_table.rsplit('.', 1)

                        if len(fact_parts) == 2:
                            fact_schema, fact_name = fact_parts
                        else:
                            fact_schema, fact_name = "FACT", fact_parts[0]

                        if len(dim_parts) == 2:
                            dim_schema, dim_name = dim_parts
                        else:
                            dim_schema, dim_name = "DIM", dim_parts[0]

                        # SQL Server query
                        sql_query = f"""
SELECT
    d.{cat_col},
    SUM(f.{measure}) as total_{measure.lower()},
    COUNT(*) as record_count
FROM {fact_schema}.{fact_name} f
INNER JOIN {dim_schema}.{dim_name} d
    ON f.{fk_column} = d.{dim_column}
GROUP BY d.{cat_col}
ORDER BY total_{measure.lower()} DESC
                        """.strip()

                        # Snowflake query
                        snow_query = f"""
SELECT
    d.{cat_col.upper()},
    SUM(f.{measure.upper()}) as TOTAL_{measure.upper()},
    COUNT(*) as RECORD_COUNT
FROM {fact_schema.upper()}.{fact_name.upper()} f
INNER JOIN {dim_schema.upper()}.{dim_name.upper()} d
    ON f.{fk_column.upper()} = d.{dim_column.upper()}
GROUP BY d.{cat_col.upper()}
ORDER BY TOTAL_{measure.upper()} DESC
                        """.strip()

                        custom_queries.append({
                            "name": f"Total {measure} by {cat_col}",
                            "sql_query": sql_query,
                            "snow_query": snow_query,
                            "comparison_type": "aggregation",
                            "tolerance": 0.01
                        })

        except Exception as e:
            print(f"[AUTOMATION] Warning: Could not generate custom queries for {table_name}: {e}")

        return custom_queries

    async def create_comprehensive_pipelines(self) -> Dict[str, Any]:
        """
        Create comprehensive pipelines for all tables in the project.
        Each table gets ONE complete pipeline with all validations and custom queries.
        Uses the existing Pipeline Builder's "Analyze & Suggest" and custom query generator.

        Returns:
            {
                "status": "success",
                "pipelines_created": [...],
                "batch_pipeline": "projectname_batch",
                "summary": {...}
            }
        """
        pipelines_created = []
        batch_pipeline_list = []

        print(f"\n[AUTOMATION] Starting comprehensive pipeline generation for project: {self.project_id}")
        print(f"[AUTOMATION] Using Pipeline Builder's intelligent suggest logic")
        print(f"[AUTOMATION] Found {len(self.metadata.get('snow', {}))} Snowflake tables")
        print(f"[AUTOMATION] Found {len(self.metadata.get('sql', {}))} SQL Server tables")
        print(f"[AUTOMATION] Found {len(self.relationships)} relationships")

        # Process each table (use Snowflake as primary source)
        for table_name, table_metadata in self.metadata.get("snow", {}).items():
            try:
                print(f"\n[AUTOMATION] Processing table: {table_name}")

                # Clean table name for pipeline naming
                clean_table_name = table_name.replace('.', '_')

                # Get relationships for this table
                table_relationships = self._get_table_relationships(table_name)
                print(f"[AUTOMATION]   - Found {len(table_relationships)} relationships")

                # Use Pipeline Builder's complete intelligent suggest
                # This returns a COMPLETE pipeline YAML with ALL validations AND custom queries
                print(f"[AUTOMATION]   - Calling Pipeline Builder's Analyze & Suggest...")
                pipeline_yaml_data = await self._generate_complete_pipeline_using_intelligent_suggest(
                    table_name, table_metadata, table_relationships
                )

                if not pipeline_yaml_data:
                    print(f"[AUTOMATION]   - Skipping {table_name}: No pipeline generated")
                    continue

                # Update pipeline name in the YAML to match our naming convention
                pipeline_name = f"{self.project_id}_{clean_table_name}_validation"
                pipeline_file = f"{pipeline_name}.yaml"

                # Replace the pipeline name in the YAML
                pipeline_yaml = pipeline_yaml_data.replace(
                    f"name: {table_name}",
                    f"name: {pipeline_name}"
                )

                # Save pipeline
                pipeline_path = f"{self.pipelines_dir}/{pipeline_file}"
                with open(pipeline_path, "w") as f:
                    f.write(pipeline_yaml)

                print(f"[AUTOMATION]   - Created comprehensive pipeline: {pipeline_file}")
                print(f"[AUTOMATION]   - Pipeline includes ALL validations + custom queries from Pipeline Builder")
                pipelines_created.append(pipeline_name)
                batch_pipeline_list.append(pipeline_file)

            except Exception as e:
                print(f"[AUTOMATION] Error processing table {table_name}: {e}")
                import traceback
                traceback.print_exc()

        # Create batch operation
        batch_pipeline_name = f"{self.project_id}_batch"
        batch_yaml = self._create_batch_pipeline(batch_pipeline_name, batch_pipeline_list)

        batch_path = f"{self.pipelines_dir}/{batch_pipeline_name}.yaml"
        with open(batch_path, "w") as f:
            f.write(batch_yaml)

        print(f"\n[AUTOMATION] Created batch pipeline: {batch_pipeline_name}.yaml")
        print(f"[AUTOMATION] Total pipelines created: {len(pipelines_created)}")

        return {
            "status": "success",
            "pipelines_created": pipelines_created,
            "batch_pipeline": batch_pipeline_name,
            "summary": {
                "total_tables_processed": len(self.metadata.get("snow", {})),
                "total_pipelines": len(pipelines_created),
                "total_relationships": len(self.relationships),
                "batch_file": f"{batch_pipeline_name}.yaml"
            }
        }

    def _build_pipeline_yaml(self, pipeline_name: str, table_name: str,
                            table_metadata: Dict[str, Any], validation_steps: List[Dict[str, Any]],
                            custom_queries: List[Dict[str, Any]],
                            relationships: List[Dict[str, Any]]) -> str:
        """Build complete pipeline YAML"""

        # Parse table name for schema.table format
        table_parts = table_name.rsplit('.', 1)
        if len(table_parts) == 2:
            schema, table = table_parts
        else:
            schema, table = "PUBLIC", table_parts[0]

        # Build mapping
        mapping = {
            table_name: {
                "sql": table_name,
                "snow": table_name
            }
        }

        # Add dimension table mappings for relationships
        for rel in relationships:
            dim_table = rel.get("dim_table") or rel.get("target_table")
            if dim_table:
                mapping[dim_table] = {
                    "sql": dim_table,
                    "snow": dim_table
                }

        # Build metadata
        metadata = {
            table_name: _extract_metadata_structure([
                {"name": "columns", "type": table_metadata.get("columns", {})},
                {"name": "object_type", "type": table_metadata.get("object_type", "TABLE")}
            ])
        }

        # Add foreign keys to metadata
        if relationships:
            metadata[table_name]["foreign_keys"] = {
                rel.get("dim_table") or rel.get("target_table"): {
                    "column": rel.get("fk_column") or rel.get("source_column"),
                    "references": f"{rel.get('dim_table') or rel.get('target_table')}.{rel.get('dim_column') or rel.get('target_column')}"
                }
                for rel in relationships
            }

        # Build pipeline structure
        pipeline = {
            "pipeline": {
                "name": pipeline_name,
                "description": f"Comprehensive validation for {table_name} (auto-generated)",
                "type": "table_validation",
                "category": "auto_generated",
                "source": {
                    "connection": "${SQLSERVER_CONNECTION}",
                    "database": "${SQL_DATABASE}",
                    "schema": schema,
                    "table": table
                },
                "target": {
                    "connection": "${SNOWFLAKE_CONNECTION}",
                    "database": "${SNOWFLAKE_DATABASE}",
                    "schema": schema,
                    "table": table
                },
                "mapping": mapping,
                "metadata": metadata,
                "steps": validation_steps,
                "custom_queries": custom_queries
            },
            "execution": {
                "write_results_to": f"results/{pipeline_name}/",
                "fail_on_error": False
            }
        }

        return format_yaml(pipeline)

    def _create_batch_pipeline(self, batch_name: str, pipeline_files: List[str]) -> str:
        """Create batch operation YAML to execute all pipelines"""

        batch = {
            "batch": {
                "name": batch_name,
                "description": f"Batch execution of all {self.project_id} pipelines",
                "type": "sequential",  # or "parallel"
                "pipelines": [
                    {
                        "file": pipeline_file,
                        "enabled": True
                    }
                    for pipeline_file in pipeline_files
                ],
                "execution": {
                    "continue_on_error": True,
                    "write_results_to": f"results/{batch_name}/",
                    "generate_summary_report": True
                }
            }
        }

        return format_yaml(batch)


# API endpoint wrapper functions

async def create_comprehensive_automation(project_id: str, projects_dir: str = "/data/projects") -> Dict[str, Any]:
    """
    Main entry point for comprehensive pipeline automation.
    Uses Pipeline Builder's existing "Analyze & Suggest" and custom query generation.

    Usage:
        result = await create_comprehensive_automation("project_a")

    Returns:
        {
            "status": "success",
            "pipelines_created": ["project_a_fact_sales_validation", "project_a_dim_product_validation", ...],
            "batch_pipeline": "project_a_batch",
            "summary": {...}
        }
    """
    automation = ComprehensivePipelineAutomation(project_id, projects_dir)
    return await automation.create_comprehensive_pipelines()
