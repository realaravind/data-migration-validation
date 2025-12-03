"""
Relationship Inference Engine

Predicts foreign key relationships when database constraints are not enforced.
Uses heuristics including:
- Column name pattern matching
- Fact/Dimension table detection
- Optional data sampling validation
"""

from typing import Dict, List, Tuple, Optional
import re
from difflib import SequenceMatcher


class RelationshipInferrer:
    """
    Infers foreign key relationships from table metadata using various heuristics.
    """

    def __init__(self, sql_conn=None, snow_conn=None):
        """
        Initialize the inferrer.

        Args:
            sql_conn: Optional SQL Server connection for data sampling
            snow_conn: Optional Snowflake connection for data sampling
        """
        self.sql_conn = sql_conn
        self.snow_conn = snow_conn

        # Common FK column suffixes
        self.fk_patterns = [
            r'^(.+)_id$',           # customer_id -> customer
            r'^(.+)_key$',          # customer_key -> customer
            r'^(.+)id$',            # customerid -> customer
            r'^(.+)_code$',         # customer_code -> customer
            r'^fk_(.+)$',           # fk_customer -> customer
            r'^(.+)_fk$',           # customer_fk -> customer
        ]

        # Patterns to identify fact tables
        self.fact_patterns = [
            r'^fact_',
            r'^fct_',
            r'^f_',
        ]

        # Patterns to identify dimension tables
        self.dim_patterns = [
            r'^dim_',
            r'^dimension_',
            r'^d_',
        ]

    def infer_all_relationships(self, metadata: Dict) -> List[Dict]:
        """
        Infer all relationships from metadata.

        Args:
            metadata: Dictionary with structure:
                {
                    "schema.table1": {
                        "columns": {"col1": "INT", "col2": "VARCHAR"},
                        "relationships": {},
                        "schema": "dbo",
                        "table": "table1"
                    },
                    ...
                }

        Returns:
            List of inferred relationships:
            [
                {
                    "fact_table": "fact_sales",
                    "fk_column": "customer_id",
                    "dim_table": "dim_customer",
                    "dim_column": "customer_id",
                    "confidence": "high",
                    "confidence_score": 0.95,
                    "method": "name_pattern"
                },
                ...
            ]
        """
        inferred = []

        # Classify tables as facts or dimensions
        facts = self._classify_facts(metadata)
        dimensions = self._classify_dimensions(metadata)

        # For each fact table, find potential FK relationships
        for fact_table in facts:
            fact_meta = metadata.get(fact_table, {})
            fact_columns = fact_meta.get("columns", {})

            # Look for FK columns
            for col_name, col_type in fact_columns.items():
                # Try to match FK patterns
                potential_dims = self._find_potential_dimensions(
                    col_name, col_type, dimensions, metadata
                )

                for dim_table, dim_column, confidence, method in potential_dims:
                    # Skip self-referential relationships (table pointing to itself)
                    if fact_table == dim_table:
                        continue

                    inferred.append({
                        "fact_table": fact_table,
                        "fk_column": col_name,
                        "dim_table": dim_table,
                        "dim_column": dim_column,
                        "confidence": self._classify_confidence(confidence),
                        "confidence_score": confidence,
                        "method": method
                    })

        return inferred

    def _classify_facts(self, metadata: Dict) -> List[str]:
        """Identify fact tables based on naming patterns and column analysis."""
        facts = []

        for table_key, table_meta in metadata.items():
            table_name = table_meta.get("table", table_key)

            # Check naming patterns
            is_fact = any(re.match(pattern, table_name.lower()) for pattern in self.fact_patterns)

            if is_fact:
                facts.append(table_key)
            else:
                # Heuristic: Tables with many numeric columns and potential FKs
                columns = table_meta.get("columns", {})
                numeric_count = sum(1 for dt in columns.values()
                                   if any(num_type in dt.upper()
                                         for num_type in ['INT', 'DECIMAL', 'NUMERIC', 'FLOAT', 'NUMBER']))
                fk_count = sum(1 for col in columns.keys()
                              if any(re.match(pattern, col.lower()) for pattern in self.fk_patterns))

                # If >50% numeric and has multiple potential FKs, likely a fact
                if len(columns) > 0 and numeric_count / len(columns) > 0.3 and fk_count >= 2:
                    facts.append(table_key)

        return facts

    def _classify_dimensions(self, metadata: Dict) -> List[str]:
        """Identify dimension tables based on naming patterns."""
        dimensions = []

        for table_key, table_meta in metadata.items():
            table_name = table_meta.get("table", table_key)

            # Check naming patterns
            is_dim = any(re.match(pattern, table_name.lower()) for pattern in self.dim_patterns)

            if is_dim:
                dimensions.append(table_key)
            else:
                # Heuristic: Tables with few FKs and many text columns
                columns = table_meta.get("columns", {})
                fk_count = sum(1 for col in columns.keys()
                              if any(re.match(pattern, col.lower()) for pattern in self.fk_patterns))
                text_count = sum(1 for dt in columns.values()
                                if any(text_type in dt.upper()
                                      for text_type in ['VARCHAR', 'CHAR', 'TEXT', 'STRING']))

                # If has text columns and few FKs, likely a dimension
                if fk_count <= 1 and text_count >= 2:
                    dimensions.append(table_key)

        return dimensions

    def _find_potential_dimensions(self, fk_column: str, fk_type: str,
                                   dimensions: List[str], metadata: Dict) -> List[Tuple[str, str, float, str]]:
        """
        Find potential dimension tables that this FK column might reference.

        Returns:
            List of tuples: (dim_table, dim_column, confidence_score, method)
        """
        results = []

        # Try pattern matching
        for pattern in self.fk_patterns:
            match = re.match(pattern, fk_column.lower())
            if match:
                base_name = match.group(1)

                # Look for matching dimension tables
                for dim_table in dimensions:
                    dim_meta = metadata.get(dim_table, {})
                    dim_name = dim_meta.get("table", dim_table).lower()
                    dim_columns = dim_meta.get("columns", {})

                    # Calculate name similarity
                    similarity = self._name_similarity(base_name, dim_name)

                    if similarity > 0.6:  # 60% threshold
                        # Find matching column in dimension (usually PK with same name)
                        matching_col = None
                        max_col_similarity = 0

                        for dim_col, dim_col_type in dim_columns.items():
                            col_similarity = self._name_similarity(fk_column.lower(), dim_col.lower())
                            if col_similarity > max_col_similarity:
                                max_col_similarity = col_similarity
                                matching_col = dim_col

                        if matching_col:
                            # Combined confidence: table name + column name + type match
                            type_match = 1.0 if self._types_compatible(fk_type, dim_columns.get(matching_col, '')) else 0.5
                            confidence = (similarity * 0.5 + max_col_similarity * 0.3 + type_match * 0.2)

                            results.append((
                                dim_table,
                                matching_col,
                                confidence,
                                "name_pattern"
                            ))

        # Sort by confidence (highest first) and return only the best match
        results.sort(key=lambda x: x[2], reverse=True)
        # Only return the top match if it meets minimum confidence threshold (70%)
        if results and results[0][2] >= 0.7:
            return [results[0]]
        return []

    def _name_similarity(self, name1: str, name2: str) -> float:
        """Calculate similarity between two names using sequence matcher."""
        return SequenceMatcher(None, name1.lower(), name2.lower()).ratio()

    def _types_compatible(self, type1: str, type2: str) -> bool:
        """Check if two data types are compatible for FK relationship."""
        type1_upper = type1.upper()
        type2_upper = type2.upper()

        # Integer types
        int_types = ['INT', 'INTEGER', 'BIGINT', 'SMALLINT', 'TINYINT', 'NUMBER']
        if any(t in type1_upper for t in int_types) and any(t in type2_upper for t in int_types):
            return True

        # String types
        str_types = ['VARCHAR', 'CHAR', 'TEXT', 'STRING']
        if any(t in type1_upper for t in str_types) and any(t in type2_upper for t in str_types):
            return True

        return False

    def _classify_confidence(self, score: float) -> str:
        """Classify confidence score into categories."""
        if score >= 0.85:
            return "high"
        elif score >= 0.65:
            return "medium"
        else:
            return "low"

    def validate_relationship(self, fact_table: str, fk_column: str,
                            dim_table: str, dim_column: str,
                            sample_size: int = 1000, use_snowflake: bool = False) -> Dict:
        """
        Validate a relationship by sampling data and checking FK integrity.

        Args:
            fact_table: Fact table name (schema.table)
            fk_column: FK column name in fact table
            dim_table: Dimension table name (schema.table)
            dim_column: PK column name in dimension table
            sample_size: Number of rows to sample
            use_snowflake: Use Snowflake connection instead of SQL Server

        Returns:
            {
                "total_sampled": 1000,
                "valid_fks": 950,
                "invalid_fks": 50,
                "match_rate": 0.95,
                "confidence": "high",
                "sample_invalid_values": [1234, 5678, ...]
            }
        """
        conn = self.snow_conn if use_snowflake else self.sql_conn

        if not conn:
            return {
                "error": "No database connection available for validation"
            }

        try:
            cursor = conn.cursor()

            # Sample FK values from fact table
            sample_query = f"""
                SELECT TOP {sample_size} [{fk_column}]
                FROM [{fact_table}]
                WHERE [{fk_column}] IS NOT NULL
            """ if not use_snowflake else f"""
                SELECT {fk_column}
                FROM {fact_table}
                WHERE {fk_column} IS NOT NULL
                LIMIT {sample_size}
            """

            cursor.execute(sample_query)
            fk_values = [row[0] for row in cursor.fetchall()]
            total_sampled = len(fk_values)

            if total_sampled == 0:
                return {
                    "total_sampled": 0,
                    "valid_fks": 0,
                    "invalid_fks": 0,
                    "match_rate": 0.0,
                    "confidence": "unknown",
                    "message": "No non-null FK values found"
                }

            # Check which values exist in dimension table
            fk_values_str = ','.join(f"'{v}'" if isinstance(v, str) else str(v) for v in fk_values)

            check_query = f"""
                SELECT COUNT(DISTINCT [{dim_column}])
                FROM [{dim_table}]
                WHERE [{dim_column}] IN ({fk_values_str})
            """ if not use_snowflake else f"""
                SELECT COUNT(DISTINCT {dim_column})
                FROM {dim_table}
                WHERE {dim_column} IN ({fk_values_str})
            """

            cursor.execute(check_query)
            valid_count = cursor.fetchone()[0]

            # Find invalid values (for debugging)
            invalid_query = f"""
                SELECT DISTINCT f.[{fk_column}]
                FROM [{fact_table}] f
                LEFT JOIN [{dim_table}] d ON f.[{fk_column}] = d.[{dim_column}]
                WHERE f.[{fk_column}] IS NOT NULL AND d.[{dim_column}] IS NULL
                ORDER BY f.[{fk_column}]
                OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY
            """ if not use_snowflake else f"""
                SELECT DISTINCT f.{fk_column}
                FROM {fact_table} f
                LEFT JOIN {dim_table} d ON f.{fk_column} = d.{dim_column}
                WHERE f.{fk_column} IS NOT NULL AND d.{dim_column} IS NULL
                ORDER BY f.{fk_column}
                LIMIT 10
            """

            cursor.execute(invalid_query)
            invalid_values = [row[0] for row in cursor.fetchall()]

            cursor.close()

            match_rate = valid_count / total_sampled if total_sampled > 0 else 0.0

            return {
                "total_sampled": total_sampled,
                "valid_fks": valid_count,
                "invalid_fks": total_sampled - valid_count,
                "match_rate": match_rate,
                "confidence": self._classify_confidence(match_rate),
                "sample_invalid_values": invalid_values[:10]
            }

        except Exception as e:
            return {
                "error": f"Validation failed: {str(e)}"
            }
