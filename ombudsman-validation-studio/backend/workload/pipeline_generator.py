"""
Pipeline Generator - Converts workload-based validations to YAML pipelines
"""

from typing import List, Dict, Any
from datetime import datetime
import yaml
from pathlib import Path


class PipelineGenerator:
    """Generate YAML validation pipelines from selected validations"""

    def __init__(self, pipelines_dir: str = "data/pipelines"):
        self.pipelines_dir = Path(pipelines_dir)
        self.pipelines_dir.mkdir(parents=True, exist_ok=True)
        self.column_mappings = {}  # Will be loaded per project
        self.schema_mappings = {}  # Will be loaded per project

    def _load_column_mappings(self, project_id: str) -> Dict[str, Dict[str, str]]:
        """
        Load column mappings from project config.

        Returns:
            Dict mapping table_key -> {source_col_lower -> (source_col_actual, target_col)}
        """
        print(f"[DEBUG] _load_column_mappings called with project_id: '{project_id}'")
        mappings_path = Path(f"data/projects/{project_id}/config/column_mappings.yaml")
        print(f"[DEBUG] Looking for mappings at: {mappings_path}")
        print(f"[DEBUG] Absolute path: {mappings_path.absolute()}")
        print(f"[DEBUG] File exists: {mappings_path.exists()}")

        if not mappings_path.exists():
            print(f"[WARN] Column mappings not found: {mappings_path}")
            return {}

        try:
            with open(mappings_path, 'r') as f:
                raw_mappings = yaml.safe_load(f)

            # Build lookup dict: table_key -> {col_name_lower -> (source_actual, target_actual)}
            result = {}
            for table_key, table_data in raw_mappings.items():
                col_map = {}
                for mapping in table_data.get('mappings', []):
                    source_col = mapping['source']
                    target_col = mapping['target']
                    # Store with lowercase key for case-insensitive lookup
                    col_map[source_col.lower()] = (source_col, target_col)
                result[table_key] = col_map

            print(f"[INFO] Loaded column mappings for {len(result)} tables from {project_id}")
            return result
        except Exception as e:
            print(f"[ERROR] Failed to load column mappings: {e}")
            return {}

    def _load_schema_mappings(self, project_id: str) -> Dict[str, str]:
        """
        Load schema mappings from project config.

        Returns:
            Dict mapping source schema names to target schema names (e.g., {"SAMPLE_DIM": "DIM", "SAMPLE_FACT": "FACT"})
        """
        print(f"[SCHEMA_MAPPING] Loading schema mappings for project_id: '{project_id}'")
        mappings_path = Path(f"data/projects/{project_id}/config/schema_mappings.yaml")
        print(f"[SCHEMA_MAPPING] Looking for mappings at: {mappings_path}")

        if not mappings_path.exists():
            print(f"[SCHEMA_MAPPING] Schema mappings not found, using defaults")
            # Return default mappings for common patterns
            return {"DIM": "DIM", "FACT": "FACT", "SAMPLE_DIM": "DIM", "SAMPLE_FACT": "FACT"}

        try:
            with open(mappings_path, 'r') as f:
                mappings = yaml.safe_load(f) or {}

            print(f"[SCHEMA_MAPPING] Loaded {len(mappings)} schema mappings: {mappings}")
            return mappings
        except Exception as e:
            print(f"[SCHEMA_MAPPING] Failed to load schema mappings: {e}")
            return {"DIM": "DIM", "FACT": "FACT", "SAMPLE_DIM": "DIM", "SAMPLE_FACT": "FACT"}

    def _normalize_column_name(self, col_name: str) -> str:
        """
        Normalize column name to lowercase without underscores/spaces.
        This allows matching different naming conventions:
        - UnitPrice (PascalCase)
        - unit_price (snake_case)
        - UNIT_PRICE (SCREAMING_SNAKE_CASE)
        """
        return col_name.lower().replace('_', '').replace(' ', '')

    def _apply_column_mappings(
        self,
        query: str,
        table_key: str,
        target: str = 'source'  # 'source' or 'target'
    ) -> str:
        """
        Apply column name mappings to a SQL query.

        Args:
            query: SQL query string
            table_key: Table identifier (e.g., "DIM.dim_product")
            target: Whether to map to 'source' (SQL Server) or 'target' (Snowflake)

        Returns:
            Query with column names replaced
        """
        if not self.column_mappings or table_key not in self.column_mappings:
            return query

        import re
        col_map = self.column_mappings[table_key]

        # Build a normalized lookup: normalized_name -> (source, target)
        normalized_map = {}
        for col_lower, (source_col, target_col) in col_map.items():
            norm_key = self._normalize_column_name(source_col)
            normalized_map[norm_key] = (source_col, target_col)

        # Find all word tokens in the query that might be column names
        # Match any word boundary identifier
        words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', query)

        # Check each word to see if it matches a column (after normalization)
        for word in set(words):  # Use set to avoid duplicate replacements
            norm_word = self._normalize_column_name(word)
            if norm_word in normalized_map:
                source_col, target_col = normalized_map[norm_word]
                replacement = source_col if target == 'source' else target_col

                # Replace this exact word (case-sensitive boundary match)
                # This preserves the original word boundaries
                pattern = r'\b' + re.escape(word) + r'\b'
                query = re.sub(pattern, replacement, query)

        return query

    def generate_pipelines(
        self,
        validations: List[Dict[str, Any]],
        project_id: str,
        workload_id: str
    ) -> Dict[str, Any]:
        """
        Generate YAML pipelines from selected validations.

        Returns one pipeline per table (grouped by table_name).

        Args:
            validations: List of selected validation suggestions
            project_id: Project identifier
            workload_id: Workload identifier

        Returns:
            Dictionary with pipeline_files, summary, and file paths
        """
        # Load column mappings for this project
        self.column_mappings = self._load_column_mappings(project_id)
        print(f"[DEBUG] Loaded column mappings: {len(self.column_mappings)} tables")
        if self.column_mappings:
            print(f"[DEBUG] Tables with mappings: {list(self.column_mappings.keys())}")

        # Group validations by table
        tables = {}
        for validation in validations:
            table_name = validation['table_name']
            if table_name not in tables:
                tables[table_name] = []
            tables[table_name].append(validation)

        # Generate one pipeline per table
        pipeline_files = {}
        file_paths = []

        for table_name, table_validations in tables.items():
            pipeline_data = self._create_pipeline_yaml(
                table_name=table_name,
                validations=table_validations,
                project_id=project_id,
                workload_id=workload_id
            )

            # Save to file
            filename = self._generate_filename(table_name, workload_id)
            file_path = self.pipelines_dir / filename

            with open(file_path, 'w') as f:
                yaml.dump(pipeline_data, f, default_flow_style=False, sort_keys=False)

            pipeline_files[table_name] = {
                'filename': filename,
                'path': str(file_path),
                'validation_count': len(table_validations),
                'yaml_content': yaml.dump(pipeline_data, default_flow_style=False, sort_keys=False)
            }
            file_paths.append(str(file_path))

        return {
            'pipeline_files': pipeline_files,
            'total_tables': len(tables),
            'total_validations': len(validations),
            'file_paths': file_paths,
            'generated_at': datetime.now().isoformat()
        }

    def generate_comparative_pipelines(
        self,
        queries: List[Dict[str, Any]],
        project_id: str,
        workload_id: str,
        schema_mapping: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Generate comparative validation pipelines from Query Store queries.

        Args:
            queries: List of Query Store queries with raw_text and stats
            project_id: Project identifier
            workload_id: Workload identifier
            schema_mapping: SQL Server to Snowflake schema mapping (e.g., {"dim": "DIM", "fact": "FACT"})

        Returns:
            Dictionary with pipeline_files, summary, and file paths
        """
        if schema_mapping is None:
            schema_mapping = {"dim": "DIM", "fact": "FACT", "dbo": "PUBLIC"}

        # Load column mappings and schema mappings for this project
        print(f"[DEBUG generate_comparative_pipelines] Loading column mappings for project_id: '{project_id}'")
        self.column_mappings = self._load_column_mappings(project_id)
        print(f"[DEBUG generate_comparative_pipelines] Loaded column mappings: {len(self.column_mappings)} tables")
        if self.column_mappings:
            print(f"[DEBUG generate_comparative_pipelines] Tables with mappings: {list(self.column_mappings.keys())}")

        self.schema_mappings = self._load_schema_mappings(project_id)
        print(f"[DEBUG generate_comparative_pipelines] Loaded schema mappings: {self.schema_mappings}")

        # Group queries by table (extract from SQL)
        table_queries = {}
        for query in queries:
            tables = self._extract_tables_from_query(query.get('raw_text', ''))
            for table in tables:
                if table not in table_queries:
                    table_queries[table] = []
                table_queries[table].append(query)

        # Generate one pipeline per table
        pipeline_files = {}
        file_paths = []

        for table_name, table_queries_list in table_queries.items():
            pipeline_data = self._create_comparative_pipeline_yaml(
                table_name=table_name,
                queries=table_queries_list,
                project_id=project_id,
                workload_id=workload_id,
                schema_mapping=schema_mapping
            )

            # Save to file
            filename = self._generate_filename(table_name, workload_id, prefix='comparative')
            file_path = self.pipelines_dir / filename

            with open(file_path, 'w') as f:
                yaml.dump(pipeline_data, f, default_flow_style=False, sort_keys=False)

            pipeline_files[table_name] = {
                'filename': filename,
                'path': str(file_path),
                'validation_count': len(table_queries_list),
                'yaml_content': yaml.dump(pipeline_data, default_flow_style=False, sort_keys=False)
            }
            file_paths.append(str(file_path))

        return {
            'pipeline_files': pipeline_files,
            'total_tables': len(table_queries),
            'total_validations': sum(len(q) for q in table_queries.values()),
            'file_paths': file_paths,
            'generated_at': datetime.now().isoformat()
        }

    def _create_pipeline_yaml(
        self,
        table_name: str,
        validations: List[Dict[str, Any]],
        project_id: str,
        workload_id: str
    ) -> Dict[str, Any]:
        """
        Create YAML pipeline structure for a single table.

        Pipeline format:
        - metadata: pipeline info
        - source: SQL Server table
        - target: Snowflake table
        - validations: list of validation rules
        """
        # Extract schema and table name
        schema_name = validations[0].get('schema_name', '')

        # Build validation rules
        validation_rules = []
        for idx, validation in enumerate(validations, 1):
            rule = self._create_validation_rule(validation, idx)
            validation_rules.append(rule)

        # Create pipeline structure
        pipeline = {
            'metadata': {
                'name': f'{table_name}_workload_validation',
                'description': f'Workload-based validations for {table_name}',
                'generated_from': f'workload_{workload_id}',
                'project_id': project_id,
                'created_at': datetime.now().isoformat(),
                'validation_count': len(validations),
                'active': True  # New pipelines are active by default
            },
            'source': {
                'type': 'sqlserver',
                'database': '${SQL_DATABASE}',
                'schema': schema_name or '${SQL_SCHEMA}',
                'table': table_name
            },
            'target': {
                'type': 'snowflake',
                'database': '${SNOWFLAKE_DATABASE}',
                'schema': schema_name.upper() if schema_name else '${SNOWFLAKE_SCHEMA}',
                'table': table_name.upper()
            },
            'steps': validation_rules  # Changed from 'validations' to 'steps' for executor compatibility
        }

        return pipeline

    def _create_validation_rule(
        self,
        validation: Dict[str, Any],
        index: int
    ) -> Dict[str, Any]:
        """
        Create a single validation rule from a validation suggestion.

        Maps validator names to actual validation configurations.
        """
        validator_name = validation['validator_name']
        columns = validation.get('columns', [])
        confidence = validation.get('confidence', 0.0)
        reason = validation.get('reason', '')
        metadata = validation.get('metadata', {})
        table_name = validation.get('table_name', '')
        schema_name = validation.get('schema_name', '')

        # Base rule structure
        rule = {
            'name': f'validation_{index}_{validator_name.lower().replace(" ", "_")}',
            'type': self._map_validator_type(validator_name),
            'description': reason,
            'confidence': round(confidence * 100, 1),
            'enabled': True
        }

        # PROPER IMPLEMENTATION: Handle workload_query validator type
        # This uses the EXACT original SQL from Query Store
        if validator_name == 'workload_query':
            raw_sql = metadata.get('raw_sql', '')
            query_id = metadata.get('query_id', '')

            if raw_sql:
                # Apply column mappings to the query
                table_key = f"{schema_name}.{table_name}" if schema_name else table_name

                # Map columns for SQL Server query (ensure correct casing)
                sql_server_query = self._apply_column_mappings(raw_sql, table_key, 'source') if self.column_mappings else raw_sql

                # Translate to Snowflake syntax using loaded schema mappings
                # Use loaded schema mappings if available, otherwise fall back to hardcoded defaults
                schema_mapping_to_use = self.schema_mappings if self.schema_mappings else {"dim": "DIM", "fact": "FACT", "dbo": "PUBLIC"}
                print(f"[SCHEMA_MAPPING] Using schema mappings for translation: {schema_mapping_to_use}")
                snowflake_query = self._translate_query_to_snowflake(sql_server_query, schema_mapping_to_use)

                # Map columns for Snowflake query (map to target columns)
                snowflake_query = self._apply_column_mappings(snowflake_query, table_key, 'target') if self.column_mappings else snowflake_query

                rule['validator'] = 'custom_sql'
                rule['type'] = 'comparative'
                rule['config'] = {
                    'sql_query': sql_server_query,
                    'snow_query': snowflake_query,
                    'compare_mode': 'result_set',
                    'tolerance': 0.01,  # 1% tolerance for numeric comparisons
                    'ignore_column_order': True,
                    'ignore_row_order': False
                }
                rule['metadata'] = {
                    'query_id': query_id,
                    'validation_type': 'workload_query',
                    'total_executions': metadata.get('total_executions', 0),
                    'avg_duration_ms': metadata.get('avg_duration_ms', 0)
                }
                return rule
            else:
                # Fallback if raw_sql is missing
                print(f"[WARN] workload_query validator missing raw_sql in metadata")
                rule['validator'] = 'custom_sql'
                rule['config'] = {
                    'sql_query': 'SELECT COUNT(*) as count FROM {table}',
                    'snow_query': 'SELECT COUNT(*) as count FROM {table}',
                    'compare_mode': 'result_set',
                    'tolerance': 0.01
                }
                return rule

        # Check if this is a workload-based validation (legacy pattern-based approach)
        is_workload_validation = validation.get('source') == 'workload'

        if is_workload_validation:
            # Use custom_sql for all workload validations
            # This allows us to run flexible queries on both source and target
            rule['validator'] = 'custom_sql'

            # Build a simple comparison query based on the columns involved
            if columns:
                col_list = ', '.join(columns)
                rule['config'] = {
                    'sql_query': f'SELECT {col_list}, COUNT(*) as row_count FROM {{table}} GROUP BY {col_list} ORDER BY {col_list}',
                    'snow_query': f'SELECT {col_list}, COUNT(*) as row_count FROM {{table}} GROUP BY {col_list} ORDER BY {col_list}',
                    'compare_mode': 'result_set',
                    'tolerance': 0.02  # 2% tolerance
                }
            else:
                # Fallback to simple row count
                rule['config'] = {
                    'sql_query': 'SELECT COUNT(*) as count FROM {table}',
                    'snow_query': 'SELECT COUNT(*) as count FROM {table}',
                    'compare_mode': 'result_set',
                    'tolerance': 0.01  # 1% tolerance
                }

        # Add validator-specific configuration for non-workload validations
        elif 'row count' in validator_name.lower():
            rule['validator'] = 'validate_record_counts'
            rule['config'] = {
                'tolerance_percentage': 1.0  # 1% tolerance
            }

        elif validator_name == 'comparative' and metadata.get('validation_type') in ['fact_dimension_conformance', 'referential_integrity']:
            # Fact-Dimension Conformance or Referential Integrity validation
            validation_type = metadata.get('validation_type')

            if validation_type == 'fact_dimension_conformance':
                # Fact-Dimension conformance: Check for orphaned foreign keys
                fact_table = metadata.get('fact_table', table_name)
                dim_table = metadata.get('dimension_table', '')
                foreign_keys = metadata.get('foreign_keys', columns)

                # Generate SQL to find orphaned foreign keys in fact table
                # These are keys in the fact table that don't have matching records in the dimension
                fk_columns = ', '.join(foreign_keys)
                fk_join_conditions = ' AND '.join([f'f.{fk} = d.{fk}' for fk in foreign_keys])
                fk_is_null_conditions = ' OR '.join([f'd.{fk} IS NULL' for fk in foreign_keys])

                # SQL Server query
                sql_server_query = f"""
                    SELECT COUNT(*) as orphaned_count
                    FROM {fact_table} f
                    LEFT JOIN {dim_table} d ON {fk_join_conditions}
                    WHERE {fk_is_null_conditions}
                """

                # Snowflake query (uppercase table names)
                snowflake_query = f"""
                    SELECT COUNT(*) as orphaned_count
                    FROM {fact_table.upper()} f
                    LEFT JOIN {dim_table.upper()} d ON {fk_join_conditions.upper()}
                    WHERE {fk_is_null_conditions.upper()}
                """

                rule['validator'] = 'custom_sql'
                rule['config'] = {
                    'sql_query': sql_server_query.strip(),
                    'snow_query': snowflake_query.strip(),
                    'compare_mode': 'result_set',
                    'tolerance': 0.0,  # Exact match expected (both should have 0 orphans ideally)
                    'ignore_column_order': True,
                    'ignore_row_order': False
                }
                rule['metadata'] = {
                    'validation_type': validation_type,
                    'fact_table': fact_table,
                    'dimension_table': dim_table,
                    'foreign_keys': foreign_keys,
                    'description': metadata.get('description', '')
                }

            else:
                # General referential integrity
                child_table = metadata.get('child_table', table_name)
                parent_table = metadata.get('parent_table', '')
                foreign_keys = metadata.get('foreign_keys', columns)

                fk_columns = ', '.join(foreign_keys)
                fk_join_conditions = ' AND '.join([f'c.{fk} = p.{fk}' for fk in foreign_keys])
                fk_is_null_conditions = ' OR '.join([f'p.{fk} IS NULL' for fk in foreign_keys])

                # SQL Server query
                sql_server_query = f"""
                    SELECT COUNT(*) as orphaned_count
                    FROM {child_table} c
                    LEFT JOIN {parent_table} p ON {fk_join_conditions}
                    WHERE {fk_is_null_conditions}
                """

                # Snowflake query
                snowflake_query = f"""
                    SELECT COUNT(*) as orphaned_count
                    FROM {child_table.upper()} c
                    LEFT JOIN {parent_table.upper()} p ON {fk_join_conditions.upper()}
                    WHERE {fk_is_null_conditions.upper()}
                """

                rule['validator'] = 'custom_sql'
                rule['config'] = {
                    'sql_query': sql_server_query.strip(),
                    'snow_query': snowflake_query.strip(),
                    'compare_mode': 'result_set',
                    'tolerance': 0.0,
                    'ignore_column_order': True,
                    'ignore_row_order': False
                }
                rule['metadata'] = {
                    'validation_type': validation_type,
                    'child_table': child_table,
                    'parent_table': parent_table,
                    'foreign_keys': foreign_keys
                }

        elif 'referential' in validator_name.lower():
            rule['validator'] = 'validate_foreign_keys'
            rule['config'] = {
                'foreign_keys': [{'column': col} for col in columns],
                'reference_table': metadata.get('reference_table', ''),
                'reference_columns': metadata.get('reference_columns', columns)
            }

        else:
            # Fallback for any other validator types - use custom_sql
            rule['validator'] = 'custom_sql'
            rule['config'] = {
                'sql_query': 'SELECT COUNT(*) as count FROM {table}',
                'snow_query': 'SELECT COUNT(*) as count FROM {table}',
                'compare_mode': 'result_set',
                'tolerance': 0.01
            }

        return rule

    def _map_validator_type(self, validator_name: str) -> str:
        """Map validator name to validation type category"""
        name_lower = validator_name.lower()

        if name_lower == 'comparative':
            return 'comparative'
        elif 'referential' in name_lower:
            return 'referential_integrity'
        elif 'distribution' in name_lower:
            return 'distribution'
        elif 'quality' in name_lower or 'null' in name_lower:
            return 'data_quality'
        elif 'cardinality' in name_lower or 'uniqueness' in name_lower:
            return 'cardinality'
        elif 'time' in name_lower or 'date' in name_lower:
            return 'time_series'
        elif 'statistics' in name_lower or 'statistical' in name_lower:
            return 'statistics'
        elif 'range' in name_lower:
            return 'value_range'
        elif 'row count' in name_lower:
            return 'row_count'
        else:
            return 'generic'

    def _generate_filename(self, table_name: str, workload_id: str, prefix: str = 'pipeline') -> str:
        """Generate pipeline filename"""
        # Clean table name (remove schema prefix if present)
        clean_name = table_name.split('.')[-1].lower()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        return f'{prefix}_{clean_name}_{timestamp}.yaml'

    def _create_comparative_pipeline_yaml(
        self,
        table_name: str,
        queries: List[Dict[str, Any]],
        project_id: str,
        workload_id: str,
        schema_mapping: Dict[str, str]
    ) -> Dict[str, Any]:
        """
        Create YAML pipeline structure for comparative validations.

        Pipeline format:
        - metadata: pipeline info
        - source: SQL Server table
        - target: Snowflake table
        - validations: list of custom_sql comparative validators
        """
        # Extract schema and table name
        parts = table_name.split('.')
        if len(parts) == 2:
            schema_name, table_only = parts
        else:
            schema_name = 'dbo'
            table_only = table_name

        # Map schema to Snowflake
        snowflake_schema = schema_mapping.get(schema_name.lower(), schema_name.upper())

        # Construct table key for column mappings (e.g., "DIM.dim_product")
        table_key = f"{snowflake_schema}.{table_only.lower()}"

        # Build comparative validation rules
        validation_rules = []
        for idx, query in enumerate(queries, 1):
            rule = self._create_comparative_validation_rule(
                query=query,
                index=idx,
                schema_mapping=schema_mapping,
                table_key=table_key
            )
            validation_rules.append(rule)

        # Create pipeline structure
        pipeline = {
            'metadata': {
                'name': f'{table_only}_comparative_validation',
                'description': f'Comparative validations from Query Store for {table_name}',
                'generated_from': f'workload_{workload_id}',
                'project_id': project_id,
                'created_at': datetime.now().isoformat(),
                'validation_count': len(queries),
                'validation_type': 'comparative',
                'active': True  # New pipelines are active by default
            },
            'source': {
                'type': 'sqlserver',
                'database': '${SQL_DATABASE}',
                'schema': schema_name,
                'table': table_only
            },
            'target': {
                'type': 'snowflake',
                'database': '${SNOWFLAKE_DATABASE}',
                'schema': snowflake_schema,
                'table': table_only.upper()
            },
            'steps': validation_rules
        }

        return pipeline

    def _create_comparative_validation_rule(
        self,
        query: Dict[str, Any],
        index: int,
        schema_mapping: Dict[str, str],
        table_key: str = None
    ) -> Dict[str, Any]:
        """
        Create a comparative validation rule from a Query Store query.

        The validator runs the same query on both SQL Server and Snowflake
        and compares the results.
        """
        raw_text = query.get('raw_text', '')
        stats = query.get('stats', {})
        query_id = query.get('query_id', index)

        # Apply column mappings to SQL Server query (fix column casing)
        print(f"[DEBUG] Before mapping - Query: {raw_text[:80]}")
        print(f"[DEBUG] Table key: {table_key}")
        sql_server_query = self._apply_column_mappings(raw_text, table_key, 'source') if table_key else raw_text
        print(f"[DEBUG] After SQL mapping: {sql_server_query[:80]}")

        # Translate SQL Server query to Snowflake
        snowflake_query = self._translate_query_to_snowflake(sql_server_query, schema_mapping)

        # Apply column mappings to Snowflake query (map to target columns)
        snowflake_query = self._apply_column_mappings(snowflake_query, table_key, 'target') if table_key else snowflake_query

        # Create validation rule
        rule = {
            'name': f'comparative_validation_{index}_query_{query_id}',
            'type': 'comparative',
            'validator': 'custom_sql',
            'description': f'Compare query results between SQL Server and Snowflake (Query ID: {query_id})',
            'enabled': True,
            'config': {
                'sql_query': sql_server_query,
                'snow_query': snowflake_query,
                'compare_mode': 'result_set',
                'tolerance': 0.0,
                'ignore_column_order': True,
                'ignore_row_order': False
            },
            'metadata': {
                'query_id': query_id,
                'total_executions': stats.get('total_executions', 0),
                'avg_duration_ms': stats.get('avg_duration', 0),
                'last_execution_time': stats.get('last_execution_time', '')
            }
        }

        return rule

    def _translate_query_to_snowflake(
        self,
        sql_server_query: str,
        schema_mapping: Dict[str, str]
    ) -> str:
        """
        Translate SQL Server query syntax to Snowflake syntax.

        Handles:
        - Schema name mapping (dim -> DIM, fact -> FACT)
        - Table name casing (uppercase for Snowflake)
        - SQL Server specific syntax (TOP, GETDATE, etc.)
        """
        query = sql_server_query

        # Replace schema.table references
        import re
        for sql_schema, snow_schema in schema_mapping.items():
            # Match schema.table pattern (case insensitive)
            pattern = rf'\b{sql_schema}\.(\w+)\b'
            replacement = f'{snow_schema}.\\1'
            query = re.sub(pattern, replacement, query, flags=re.IGNORECASE)

        # Convert SQL Server TOP to Snowflake LIMIT
        # TOP N -> LIMIT N
        query = re.sub(r'\bTOP\s+(\d+)\b', r'LIMIT \1', query, flags=re.IGNORECASE)

        # Convert SQL Server GETDATE() to Snowflake CURRENT_TIMESTAMP
        query = re.sub(r'\bGETDATE\(\)', 'CURRENT_TIMESTAMP', query, flags=re.IGNORECASE)

        # Convert SQL Server DATEADD to Snowflake DATEADD
        # DATEADD(day, -30, GETDATE()) -> DATEADD(day, -30, CURRENT_TIMESTAMP)
        query = re.sub(r'\bDATEADD\(day,', 'DATEADD(day,', query, flags=re.IGNORECASE)

        # Convert ISNULL to COALESCE (more portable)
        query = re.sub(r'\bISNULL\(', 'COALESCE(', query, flags=re.IGNORECASE)

        # Uppercase all table names in FROM and JOIN clauses
        # This is a simplified approach - might need refinement
        def uppercase_table_refs(match):
            prefix = match.group(1)
            whitespace = match.group(2)
            table = match.group(3).upper()
            return f'{prefix}{whitespace}{table}'

        # Match FROM/JOIN followed by whitespace and schema.table or just table
        query = re.sub(
            r'\b(FROM|JOIN)(\s+)([A-Za-z_][A-Za-z0-9_]*\.[A-Za-z_][A-Za-z0-9_]*)',
            uppercase_table_refs,
            query,
            flags=re.IGNORECASE
        )

        return query

    def _extract_tables_from_query(self, query: str) -> List[str]:
        """
        Extract table names from SQL query.

        Returns list of tables in schema.table format.
        """
        import re

        tables = []

        # Match FROM and JOIN clauses
        # Pattern: FROM/JOIN schema.table or just table
        pattern = r'\b(?:FROM|JOIN)\s+([A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)?)'
        matches = re.findall(pattern, query, flags=re.IGNORECASE)

        for match in matches:
            # Normalize to lowercase
            table = match.lower()
            if table not in tables:
                tables.append(table)

        return tables

    def get_pipeline_content(self, filepath: str) -> str:
        """Read and return pipeline YAML content"""
        with open(filepath, 'r') as f:
            return f.read()

    def list_generated_pipelines(self, project_id: str = None, active_only: bool = False) -> List[Dict[str, Any]]:
        """
        List all generated pipelines

        Args:
            project_id: Optional filter by project
            active_only: If True, return only active pipelines
        """
        pipelines = []

        # Scan both the flat pipelines_dir and project-specific directories
        projects_base = Path("/data/projects")

        search_paths = []

        # If project_id specified, only search that project
        if project_id:
            project_pipeline_dir = projects_base / project_id / "pipelines"
            if project_pipeline_dir.exists():
                search_paths.append(project_pipeline_dir)
        else:
            # Search all project directories
            if projects_base.exists():
                for project_dir in projects_base.iterdir():
                    if project_dir.is_dir():
                        pipeline_dir = project_dir / "pipelines"
                        if pipeline_dir.exists():
                            search_paths.append(pipeline_dir)

            # Also check the flat pipelines directory
            if self.pipelines_dir.exists():
                search_paths.append(self.pipelines_dir)

        # Scan all search paths for YAML files
        for search_path in search_paths:
            for yaml_file in search_path.glob('*.yaml'):
                try:
                    with open(yaml_file, 'r') as f:
                        data = yaml.safe_load(f)

                    metadata = data.get('metadata', {})

                    # Extract project_id from path if not in metadata
                    file_project_id = metadata.get('project_id')
                    if not file_project_id and 'projects' in str(yaml_file):
                        # Extract from path: /data/projects/{project_id}/pipelines/...
                        parts = yaml_file.parts
                        if 'projects' in parts:
                            proj_idx = parts.index('projects')
                            if len(parts) > proj_idx + 1:
                                file_project_id = parts[proj_idx + 1]

                    # Filter by project if specified
                    if project_id and file_project_id != project_id:
                        continue

                    # Filter by active status if requested
                    is_active = metadata.get('active', True)  # Default to True for backward compatibility
                    if active_only and not is_active:
                        continue

                    # Extract table name from correct location
                    # First try pipeline.source.table, then fall back to source.table
                    pipeline_section = data.get('pipeline', {})
                    source_section = pipeline_section.get('source', {}) if pipeline_section else data.get('source', {})
                    table_name = source_section.get('table', 'unknown')

                    # Handle custom queries pipelines (extract table from queries)
                    custom_queries = data.get('custom_queries', [])
                    if custom_queries and table_name == 'unknown':
                        # Try to extract table from first query
                        first_query = custom_queries[0]
                        sql_query = first_query.get('sql_query', '')
                        # Look for "FROM schema.table" pattern
                        import re
                        match = re.search(r'FROM\s+(\w+\.\w+)', sql_query, re.IGNORECASE)
                        if match:
                            table_name = match.group(1)

                    # Count validations from execution.validations or pipeline.steps or root-level steps/validations or custom_queries
                    execution_section = pipeline_section.get('execution', {}) if pipeline_section else data.get('execution', {})
                    validation_list = (
                        execution_section.get('validations', []) if execution_section
                        else pipeline_section.get('steps', []) if pipeline_section
                        else data.get('validations', data.get('steps', custom_queries))
                    )
                    validation_count = metadata.get('validation_count', len(validation_list))

                    # Determine type: batch or pipeline
                    # Batch files have a "batch" top-level key with "pipelines" list
                    file_type = "batch" if "batch" in data and "pipelines" in data.get("batch", {}) else "pipeline"

                    # For batch files, get the list of pipelines and description
                    batch_info = {}
                    if file_type == "batch":
                        batch_data = data.get("batch", {})
                        batch_info = {
                            "pipeline_count": len(batch_data.get("pipelines", [])),
                            "batch_type": batch_data.get("type", "sequential"),
                            "description": batch_data.get("description", ""),
                            "pipelines": [p.get("file") for p in batch_data.get("pipelines", [])]
                        }

                    pipelines.append({
                        'filename': yaml_file.name,
                        'path': str(yaml_file),
                        'name': metadata.get('name', yaml_file.stem),
                        'table': table_name,
                        'validation_count': validation_count,
                        'created_at': metadata.get('created_at'),
                        'project_id': file_project_id,
                        'active': is_active,
                        'type': file_type,
                        **batch_info  # Add batch-specific fields if it's a batch file
                    })
                except Exception as e:
                    print(f"Error reading {yaml_file}: {e}")
                    continue

        # Remove duplicates based on filename (keep first occurrence)
        seen_filenames = set()
        unique_pipelines = []
        for pipeline in pipelines:
            filename = pipeline.get('filename')
            if filename not in seen_filenames:
                seen_filenames.add(filename)
                unique_pipelines.append(pipeline)

        # Sort by creation date (newest first), handling None values
        unique_pipelines.sort(key=lambda x: x.get('created_at') or '', reverse=True)

        return unique_pipelines

    def update_pipeline_active_status(self, filename: str, active: bool) -> bool:
        """
        Update the active status of a pipeline

        Args:
            filename: Pipeline filename
            active: New active status

        Returns:
            True if successful, False otherwise
        """
        # Search for the file in multiple locations
        projects_base = Path("/data/projects")
        search_paths = [self.pipelines_dir]

        # Add all project pipeline directories
        if projects_base.exists():
            for project_dir in projects_base.iterdir():
                if project_dir.is_dir():
                    pipeline_dir = project_dir / "pipelines"
                    if pipeline_dir.exists():
                        search_paths.append(pipeline_dir)

        # Find the file
        filepath = None
        for search_path in search_paths:
            candidate = search_path / filename
            if candidate.exists():
                filepath = candidate
                break

        if not filepath:
            print(f"Pipeline file not found: {filename}")
            return False

        try:
            # Read the pipeline
            with open(filepath, 'r') as f:
                data = yaml.safe_load(f)

            # Update the active flag
            if 'metadata' not in data:
                data['metadata'] = {}
            data['metadata']['active'] = active
            data['metadata']['updated_at'] = datetime.now().isoformat()

            # Write back to file
            with open(filepath, 'w') as f:
                yaml.dump(data, f, default_flow_style=False, sort_keys=False)

            print(f"Updated pipeline {filename} active status to {active}")
            return True

        except Exception as e:
            print(f"Error updating pipeline active status: {e}")
            return False
