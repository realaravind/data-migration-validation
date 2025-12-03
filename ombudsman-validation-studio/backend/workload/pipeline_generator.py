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

        # Load column mappings for this project
        print(f"[DEBUG generate_comparative_pipelines] Loading column mappings for project_id: '{project_id}'")
        self.column_mappings = self._load_column_mappings(project_id)
        print(f"[DEBUG generate_comparative_pipelines] Loaded column mappings: {len(self.column_mappings)} tables")
        if self.column_mappings:
            print(f"[DEBUG generate_comparative_pipelines] Tables with mappings: {list(self.column_mappings.keys())}")

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
                'validation_count': len(validations)
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
            'validations': validation_rules
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

        # Base rule structure
        rule = {
            'name': f'validation_{index}_{validator_name.lower().replace(" ", "_")}',
            'type': self._map_validator_type(validator_name),
            'description': reason,
            'confidence': round(confidence * 100, 1),
            'enabled': True
        }

        # Add validator-specific configuration
        if 'row count' in validator_name.lower():
            rule['validator'] = 'row_count_check'
            rule['config'] = {
                'tolerance': 0.01  # 1% tolerance
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
                    'sql_server_query': sql_server_query.strip(),
                    'snowflake_query': snowflake_query.strip(),
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
                    'sql_server_query': sql_server_query.strip(),
                    'snowflake_query': snowflake_query.strip(),
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
            rule['validator'] = 'referential_integrity'
            rule['config'] = {
                'columns': columns,
                'reference_table': metadata.get('reference_table', ''),
                'reference_columns': metadata.get('reference_columns', columns)
            }

        elif 'distribution' in validator_name.lower():
            rule['validator'] = 'distribution_check'
            rule['config'] = {
                'columns': columns,
                'aggregations': metadata.get('aggregations', ['SUM', 'AVG', 'COUNT']),
                'tolerance': 0.05  # 5% tolerance
            }

        elif 'data quality' in validator_name.lower() or 'null check' in validator_name.lower():
            rule['validator'] = 'data_quality'
            rule['config'] = {
                'columns': columns,
                'checks': ['not_null', 'data_type', 'range']
            }

        elif 'cardinality' in validator_name.lower() or 'uniqueness' in validator_name.lower():
            rule['validator'] = 'cardinality_check'
            rule['config'] = {
                'columns': columns,
                'check_type': 'unique_count',
                'tolerance': 0.02  # 2% tolerance
            }

        elif 'time series' in validator_name.lower() or 'date' in validator_name.lower():
            rule['validator'] = 'time_series_check'
            rule['config'] = {
                'columns': columns,
                'checks': ['continuity', 'range', 'distribution']
            }

        elif 'statistics' in validator_name.lower():
            rule['validator'] = 'statistical_check'
            rule['config'] = {
                'columns': columns,
                'metrics': metadata.get('metrics', ['AVG', 'STDEV', 'MIN', 'MAX']),
                'tolerance': 0.05  # 5% tolerance
            }

        elif 'value range' in validator_name.lower() or 'range' in validator_name.lower():
            rule['validator'] = 'value_range_check'
            rule['config'] = {
                'columns': columns,
                'min_value': metadata.get('min_value'),
                'max_value': metadata.get('max_value'),
                'tolerance': 0.05
            }

        else:
            # Default/generic validator
            rule['validator'] = 'generic_comparison'
            rule['config'] = {
                'columns': columns,
                'comparison_type': 'exact_match'
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
                'validation_type': 'comparative'
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
                'sql_server_query': sql_server_query,
                'snowflake_query': snowflake_query,
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

    def list_generated_pipelines(self, project_id: str = None) -> List[Dict[str, Any]]:
        """List all generated pipelines"""
        pipelines = []

        for yaml_file in self.pipelines_dir.glob('*.yaml'):
            try:
                with open(yaml_file, 'r') as f:
                    data = yaml.safe_load(f)

                metadata = data.get('metadata', {})

                # Filter by project if specified
                if project_id and metadata.get('project_id') != project_id:
                    continue

                pipelines.append({
                    'filename': yaml_file.name,
                    'path': str(yaml_file),
                    'name': metadata.get('name', yaml_file.stem),
                    'table': data.get('source', {}).get('table', 'unknown'),
                    'validation_count': metadata.get('validation_count', 0),
                    'created_at': metadata.get('created_at'),
                    'project_id': metadata.get('project_id')
                })
            except Exception as e:
                print(f"Error reading {yaml_file}: {e}")
                continue

        # Sort by creation date (newest first)
        pipelines.sort(key=lambda x: x.get('created_at', ''), reverse=True)

        return pipelines
