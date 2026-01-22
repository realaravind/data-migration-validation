"""
Intelligent Query Generator - Generates analytical validation queries using metadata and relationships

Thinks like a data analyst to suggest meaningful multi-dimensional queries for fact tables.
"""

from typing import List, Dict, Any, Tuple
import yaml
import os

from config.paths import paths


class IntelligentQueryGenerator:
    """Generate intelligent validation queries based on star schema patterns"""

    def __init__(self, metadata_path: str = None):
        self.metadata_path = metadata_path or str(paths.core_config_dir)
        self.tables = {}
        self.relationships = []
        self._load_metadata()

    def _load_metadata(self):
        """Load table metadata and relationships from YAML files"""
        tables_file = f"{self.metadata_path}/tables.yaml"
        relationships_file = f"{self.metadata_path}/relationships.yaml"

        # Load tables
        if os.path.exists(tables_file):
            with open(tables_file, "r") as f:
                self.tables = yaml.safe_load(f) or {}

        # Load relationships (might be empty, we'll infer them)
        if os.path.exists(relationships_file):
            with open(relationships_file, "r") as f:
                self.relationships = yaml.safe_load(f) or []

    def _is_fact_table(self, table_name: str) -> bool:
        """Check if table is a fact table"""
        table_lower = table_name.lower()
        return 'fact' in table_lower or table_lower.startswith('fact')

    def _is_dim_table(self, table_name: str) -> bool:
        """Check if table is a dimension table"""
        table_lower = table_name.lower()
        return 'dim' in table_lower or table_lower.startswith('dim')

    def _is_identifier(self, col_name: str) -> bool:
        """Check if column is an identifier/key"""
        col_lower = col_name.lower()
        patterns = ['_id', '_key', '_pk', '_sk', 'key', 'id']
        return any(col_lower.endswith(p) or col_lower == p.lstrip('_') for p in patterns)

    def _is_measure(self, col_name: str, col_type: str) -> bool:
        """Check if column is a measure (numeric, non-key)"""
        col_lower = col_name.lower()
        col_type_upper = col_type.upper() if col_type else ""

        # Must be numeric
        numeric_types = ['INT', 'BIGINT', 'DECIMAL', 'NUMERIC', 'FLOAT', 'REAL', 'MONEY', 'NUMBER']
        if not any(t in col_type_upper for t in numeric_types):
            return False

        # Must not be an identifier
        if self._is_identifier(col_name):
            return False

        # Measure keywords
        measure_keywords = [
            'amount', 'quantity', 'qty', 'price', 'cost', 'total', 'sum',
            'revenue', 'sales', 'discount', 'tax', 'fee', 'balance', 'value'
        ]
        return any(keyword in col_lower for keyword in measure_keywords)

    def _is_categorical(self, col_name: str, col_type: str) -> bool:
        """Check if column is categorical (good for grouping)"""
        col_lower = col_name.lower()
        col_type_upper = col_type.upper() if col_type else ""

        # String types
        if any(t in col_type_upper for t in ['VARCHAR', 'CHAR', 'STRING', 'TEXT', 'NVARCHAR']):
            # Exclude long description fields (likely email, full descriptions, comments)
            if any(x in col_lower for x in ['email', 'description', 'notes', 'comment', 'address']):
                return False

            # Good categorical fields with explicit keywords
            categorical_keywords = [
                'category', 'type', 'status', 'region', 'segment', 'class',
                'group', 'level', 'grade', 'tier', 'state', 'city', 'country',
                'quarter', 'year', 'month', 'day', 'week'  # Time dimensions
            ]
            if any(keyword in col_lower for keyword in categorical_keywords):
                return True

            # For string columns, if they contain '_name' (like month_name, day_name),
            # they're likely categorical attributes in dimension tables
            if '_name' in col_lower and 'customer' not in col_lower and 'product' not in col_lower:
                return True

        return False

    def _infer_foreign_keys(self, fact_table: str, fact_columns: Dict[str, str], database: str = None) -> List[Tuple[str, str, str]]:
        """
        Infer foreign key relationships from naming patterns.
        Returns: List of (fk_column, dim_table, dim_column) tuples
        """
        relationships = []

        # Determine which databases to search
        databases_to_search = [database] if database else list(self.tables.keys())

        for col_name, col_type in fact_columns.items():
            if not self._is_identifier(col_name):
                continue

            col_lower = col_name.lower()

            # Pattern: dim_<table>_key or <table>_key
            if '_key' in col_lower:
                # Extract table name
                parts = col_lower.split('_key')[0].split('_')

                # Look for matching dimension table in the specified database(s)
                for db_key in databases_to_search:
                    if db_key not in self.tables:
                        continue

                    for table_name in self.tables[db_key]:
                        if self._is_dim_table(table_name):
                            # Extract dimension name
                            dim_parts = table_name.lower().replace('dim_', '').replace('dim.', '').split('.')
                            dim_name = dim_parts[-1]

                            # Match pattern: dim_product_key → dim_product
                            if dim_name in parts:
                                # Find primary key in dimension table
                                dim_table_data = self.tables[db_key][table_name]
                                # Extract columns from table data (handle both flat and nested structures)
                                if isinstance(dim_table_data, dict) and 'columns' in dim_table_data:
                                    dim_cols = dim_table_data['columns']
                                else:
                                    dim_cols = dim_table_data

                                # Find the primary key in dimension table
                                # Look for columns ending with _key or matching the FK name pattern
                                for dim_col, dim_type in dim_cols.items():
                                    dim_col_lower = dim_col.lower()
                                    # Match: dim_product_key (FK) → product_key (PK) OR date_key (PK)
                                    if (dim_col_lower == col_lower or
                                        dim_col_lower == f"{dim_name}_key" or
                                        (dim_col_lower.endswith('_key') and dim_name in dim_col_lower)):
                                        # Use the ACTUAL column name from the fact table, not the dimension PK
                                        relationships.append((col_name, table_name, dim_col))
                                        break

        return relationships

    def _classify_fact_columns(self, table_name: str, columns: Dict[str, str]) -> Dict[str, List[Dict[str, str]]]:
        """
        Classify fact table columns into categories.
        Returns: {
            'foreign_keys': [...],
            'measures': [...],
            'attributes': [...]
        }
        """
        result = {
            'foreign_keys': [],
            'measures': [],
            'attributes': []
        }

        for col_name, col_type in columns.items():
            if self._is_identifier(col_name):
                # Check if it's a foreign key
                is_fk = any(
                    x in col_name.lower()
                    for x in ['dim_', 'dimension_', 'customer', 'product', 'store', 'date']
                )
                if is_fk and not col_name.lower().endswith(('_key', '_sk', '_pk')):
                    is_fk = False  # Not actually a FK

                if is_fk:
                    result['foreign_keys'].append({'name': col_name, 'type': col_type})
                # Skip primary keys in joins
            elif self._is_measure(col_name, col_type):
                result['measures'].append({'name': col_name, 'type': col_type})
            elif self._is_categorical(col_name, col_type):
                result['attributes'].append({'name': col_name, 'type': col_type})

        return result

    def generate_intelligent_queries(self, database: str = "snow") -> List[Dict[str, Any]]:
        """
        Generate intelligent validation queries based on star schema intelligence.

        Args:
            database: Which database to use ("sql" or "snow")

        Returns:
            List of query suggestions with metadata
        """
        suggestions = []

        if database not in self.tables:
            return suggestions

        # Find all fact tables
        for table_name, table_data in self.tables[database].items():
            if not self._is_fact_table(table_name):
                continue

            # Extract columns from table data (handle both flat and nested structures)
            if isinstance(table_data, dict) and 'columns' in table_data:
                columns = table_data['columns']
            else:
                columns = table_data

            # Classify columns
            classified = self._classify_fact_columns(table_name, columns)

            # Infer foreign keys (only in the current database)
            fk_relationships = self._infer_foreign_keys(table_name, columns, database)

            # Generate queries based on analyst patterns
            suggestions.extend(
                self._generate_fact_dimension_queries(
                    table_name, classified, fk_relationships, database
                )
            )

        return suggestions

    def _generate_fact_dimension_queries(
        self,
        fact_table: str,
        classified: Dict[str, List[Dict]],
        fk_relationships: List[Tuple[str, str, str]],
        database: str
    ) -> List[Dict[str, Any]]:
        """
        Generate multi-dimensional JOIN queries that a data analyst would write.

        Patterns:
        1. Aggregations by single dimension (Sales by Product)
        2. Aggregations by multiple dimensions (Sales by Product and Region)
        3. Time-based aggregations (Sales by Month)
        4. Top N analysis (Top 10 Products by Revenue)
        5. Fact-dimension conformance checks
        """
        queries = []

        measures = classified['measures']
        fks = classified['foreign_keys']

        if not measures or not fk_relationships:
            return queries

        # Build dimension lookup
        dim_info = {}
        for fk_col, dim_table, dim_pk in fk_relationships:
            dim_cols = self._get_dimension_columns(dim_table, database)
            dim_info[fk_col] = {
                'table': dim_table,
                'pk': dim_pk,
                'categorical_cols': [c for c in dim_cols if self._is_categorical(c['name'], c['type'])]
            }

        # Pattern 1: Single dimension aggregations
        for fk_col, dim_data in dim_info.items():
            for cat_col in dim_data['categorical_cols'][:2]:  # Top 2 categorical columns
                for measure in measures[:3]:  # Top 3 measures
                    query = self._build_single_dim_query(
                        fact_table, measure, fk_col, dim_data, cat_col, database
                    )
                    queries.append(query)

        # Pattern 2: Multi-dimensional aggregations (2 dimensions)
        if len(dim_info) >= 2:
            dim_pairs = list(dim_info.items())[:2]  # Top 2 dimensions
            for measure in measures[:2]:  # Top 2 measures
                query = self._build_multi_dim_query(
                    fact_table, measure, dim_pairs, database
                )
                queries.append(query)

        # Pattern 3: Conformance checks
        for fk_col, dim_data in dim_info.items():
            query = self._build_conformance_check(
                fact_table, fk_col, dim_data, database
            )
            queries.append(query)

        return queries

    def _get_dimension_columns(self, dim_table: str, database: str) -> List[Dict[str, str]]:
        """Get columns from a dimension table"""
        if database in self.tables and dim_table in self.tables[database]:
            table_data = self.tables[database][dim_table]
            # Extract columns from table data (handle both flat and nested structures)
            if isinstance(table_data, dict) and 'columns' in table_data:
                columns = table_data['columns']
            else:
                columns = table_data

            return [
                {'name': name, 'type': dtype}
                for name, dtype in columns.items()
            ]
        return []

    def _build_single_dim_query(
        self,
        fact_table: str,
        measure: Dict,
        fk_col: str,
        dim_data: Dict,
        cat_col: Dict,
        database: str
    ) -> Dict[str, Any]:
        """
        Build a single-dimension aggregation query.
        Example: Total sales by product category
        """
        dim_table = dim_data['table']
        dim_pk = dim_data['pk']

        # Extract schema and table names
        fact_schema, fact_name = self._split_table_name(fact_table)
        dim_schema, dim_name = self._split_table_name(dim_table)

        # SQL Server version (lowercase)
        sql_query = f"""
SELECT
    d.{cat_col['name']},
    SUM(f.{measure['name']}) as total_{measure['name'].lower()},
    COUNT(*) as record_count
FROM {fact_schema}.{fact_name} f
INNER JOIN {dim_schema}.{dim_name} d
    ON f.{fk_col} = d.{dim_pk}
GROUP BY d.{cat_col['name']}
ORDER BY total_{measure['name'].lower()} DESC
        """.strip()

        # Snowflake version (uppercase)
        snow_query = f"""
SELECT
    d.{cat_col['name'].upper()},
    SUM(f.{measure['name'].upper()}) as TOTAL_{measure['name'].upper()},
    COUNT(*) as RECORD_COUNT
FROM {fact_schema.upper()}.{fact_name.upper()} f
INNER JOIN {dim_schema.upper()}.{dim_name.upper()} d
    ON f.{fk_col.upper()} = d.{dim_pk.upper()}
GROUP BY d.{cat_col['name'].upper()}
ORDER BY TOTAL_{measure['name'].upper()} DESC
        """.strip()

        return {
            'name': f"Total {measure['name']} by {cat_col['name']}",
            'description': f"Aggregate {measure['name']} from {fact_name} grouped by {dim_name}.{cat_col['name']}",
            'pattern': 'single_dimension_aggregation',
            'fact_table': fact_table,
            'dimension_tables': [dim_table],
            'measures': [measure['name']],
            'group_by': [cat_col['name']],
            'sql_server_query': sql_query,
            'snowflake_query': snow_query,
            'complexity': 'simple',
            'analytical_value': 'high'
        }

    def _build_multi_dim_query(
        self,
        fact_table: str,
        measure: Dict,
        dim_pairs: List[Tuple[str, Dict]],
        database: str
    ) -> Dict[str, Any]:
        """
        Build a multi-dimensional aggregation query.
        Example: Total sales by product category and customer region
        """
        fact_schema, fact_name = self._split_table_name(fact_table)

        # Build JOINs and GROUP BY
        joins_sql = []
        joins_snow = []
        group_by_sql = []
        group_by_snow = []
        select_dims_sql = []
        select_dims_snow = []
        dim_tables = []

        for idx, (fk_col, dim_data) in enumerate(dim_pairs):
            alias = f"d{idx+1}"
            dim_table = dim_data['table']
            dim_pk = dim_data['pk']
            dim_schema, dim_name = self._split_table_name(dim_table)
            dim_tables.append(dim_table)

            # Get first categorical column
            cat_cols = dim_data['categorical_cols']
            if not cat_cols:
                # If no categorical columns, skip this dimension from GROUP BY
                # But still add the JOIN
                joins_sql.append(
                    f"INNER JOIN {dim_schema}.{dim_name} {alias} ON f.{fk_col} = {alias}.{dim_pk}"
                )
                joins_snow.append(
                    f"INNER JOIN {dim_schema.upper()}.{dim_name.upper()} {alias} ON f.{fk_col.upper()} = {alias}.{dim_pk.upper()}"
                )
                continue

            cat_col = cat_cols[0]

            # SQL Server
            joins_sql.append(
                f"INNER JOIN {dim_schema}.{dim_name} {alias} ON f.{fk_col} = {alias}.{dim_pk}"
            )
            group_by_sql.append(f"{alias}.{cat_col['name']}")
            select_dims_sql.append(f"{alias}.{cat_col['name']}")

            # Snowflake
            joins_snow.append(
                f"INNER JOIN {dim_schema.upper()}.{dim_name.upper()} {alias} ON f.{fk_col.upper()} = {alias}.{dim_pk.upper()}"
            )
            group_by_snow.append(f"{alias}.{cat_col['name'].upper()}")
            select_dims_snow.append(f"{alias}.{cat_col['name'].upper()}")

        # SQL Server query
        sql_query = f"""
SELECT
    {', '.join(select_dims_sql)},
    SUM(f.{measure['name']}) as total_{measure['name'].lower()},
    COUNT(*) as record_count
FROM {fact_schema}.{fact_name} f
{chr(10).join(joins_sql)}
GROUP BY {', '.join(group_by_sql)}
ORDER BY total_{measure['name'].lower()} DESC
        """.strip()

        # Snowflake query
        snow_query = f"""
SELECT
    {', '.join(select_dims_snow)},
    SUM(f.{measure['name'].upper()}) as TOTAL_{measure['name'].upper()},
    COUNT(*) as RECORD_COUNT
FROM {fact_schema.upper()}.{fact_name.upper()} f
{chr(10).join(joins_snow)}
GROUP BY {', '.join(group_by_snow)}
ORDER BY TOTAL_{measure['name'].upper()} DESC
        """.strip()

        dim_names = ' and '.join([self._split_table_name(d)[1] for d in dim_tables])

        return {
            'name': f"Total {measure['name']} by {dim_names}",
            'description': f"Multi-dimensional analysis of {measure['name']} across {len(dim_pairs)} dimensions",
            'pattern': 'multi_dimension_aggregation',
            'fact_table': fact_table,
            'dimension_tables': dim_tables,
            'measures': [measure['name']],
            'group_by': group_by_sql,
            'sql_server_query': sql_query,
            'snowflake_query': snow_query,
            'complexity': 'medium',
            'analytical_value': 'very_high'
        }

    def _build_conformance_check(
        self,
        fact_table: str,
        fk_col: str,
        dim_data: Dict,
        database: str
    ) -> Dict[str, Any]:
        """
        Build a conformance check query (orphaned foreign keys).
        Example: Find sales with invalid product keys
        """
        dim_table = dim_data['table']
        dim_pk = dim_data['pk']

        fact_schema, fact_name = self._split_table_name(fact_table)
        dim_schema, dim_name = self._split_table_name(dim_table)

        # SQL Server query
        sql_query = f"""
SELECT COUNT(*) as orphaned_count
FROM {fact_schema}.{fact_name} f
LEFT JOIN {dim_schema}.{dim_name} d
    ON f.{fk_col} = d.{dim_pk}
WHERE d.{dim_pk} IS NULL
        """.strip()

        # Snowflake query
        snow_query = f"""
SELECT COUNT(*) as ORPHANED_COUNT
FROM {fact_schema.upper()}.{fact_name.upper()} f
LEFT JOIN {dim_schema.upper()}.{dim_name.upper()} d
    ON f.{fk_col.upper()} = d.{dim_pk.upper()}
WHERE d.{dim_pk.upper()} IS NULL
        """.strip()

        return {
            'name': f"Conformance: {fact_name} → {dim_name}",
            'description': f"Check referential integrity: {fk_col} must exist in {dim_name}.{dim_pk}",
            'pattern': 'fact_dimension_conformance',
            'fact_table': fact_table,
            'dimension_tables': [dim_table],
            'foreign_keys': [fk_col],
            'sql_server_query': sql_query,
            'snowflake_query': snow_query,
            'complexity': 'simple',
            'analytical_value': 'critical'
        }

    def _split_table_name(self, full_name: str) -> Tuple[str, str]:
        """Split schema.table into (schema, table)"""
        if '.' in full_name:
            parts = full_name.rsplit('.', 1)
            return parts[0], parts[1]
        return 'dbo', full_name
