"""
Workload Pattern Analyzer with Confidence Scoring
Analyzes query patterns and suggests validations
"""

from typing import Dict, List, Tuple
from dataclasses import dataclass, field
from collections import defaultdict
import json

from .parser import TableUsage, ColumnUsage, QueryPattern


@dataclass
class ValidationSuggestion:
    """A suggested validation with confidence score"""
    validator_name: str
    table_name: str
    schema_name: str = ""
    columns: List[str] = field(default_factory=list)
    confidence: float = 0.0  # 0.0 to 1.0
    reason: str = ""
    query_count: int = 0
    total_executions: int = 0
    source: str = "workload"  # 'workload', 'ai', 'default'
    metadata: Dict = field(default_factory=dict)  # Additional validation config


class WorkloadAnalyzer:
    """Analyze workload patterns and suggest validations"""

    def __init__(self, metadata: Dict = None):
        """
        Initialize analyzer with table metadata

        metadata: Dict with table -> column -> datatype mapping
        """
        self.metadata = metadata or {}
        self.numeric_types = {'INT', 'BIGINT', 'DECIMAL', 'NUMERIC', 'FLOAT', 'REAL', 'MONEY', 'SMALLMONEY'}
        self.date_types = {'DATE', 'DATETIME', 'DATETIME2', 'SMALLDATETIME', 'TIME', 'TIMESTAMP'}

    def _is_identifier_column(self, col_name: str, table_name: str) -> bool:
        """
        Determine if a column is an identifier (ID/key) that should not be aggregated.

        Identifiers include:
        - Primary keys: *_id, *_key, *_pk
        - Surrogate keys: *_sk
        - Codes/numbers that are identifiers not measures: *_code, *_number (but not quantity/amount)
        """
        col_lower = col_name.lower()
        table_lower = table_name.lower()

        # Common identifier patterns
        id_patterns = [
            '_id', '_key', '_pk', '_sk', '_code', '_number', '_num',
            'key', 'id', 'code'
        ]

        # Check if column name ends with or equals identifier patterns
        for pattern in id_patterns:
            if col_lower.endswith(pattern) or col_lower == pattern.lstrip('_'):
                return True

        # Dimension tables: almost all columns except measures are identifiers
        if 'dim_' in table_lower or table_lower.startswith('dim'):
            # These are measures even in dim tables
            measure_keywords = ['price', 'cost', 'amount', 'total', 'balance', 'rate', 'percent', 'weight', 'size']
            if not any(keyword in col_lower for keyword in measure_keywords):
                # Likely an attribute/identifier, not a measure
                return True

        return False

    def _is_measure_column(self, col_name: str, table_name: str, col_type: str) -> bool:
        """
        Determine if a numeric column is a measure (should be aggregated).

        Measures include amounts, quantities, prices, totals, etc.
        """
        col_lower = col_name.lower()
        table_lower = table_name.lower()
        col_type_upper = col_type.upper()

        # Must be numeric first
        if not any(t in col_type_upper for t in self.numeric_types):
            return False

        # If it's an identifier, it's not a measure
        if self._is_identifier_column(col_name, table_name):
            return False

        # Common measure patterns
        measure_patterns = [
            'amount', 'quantity', 'qty', 'price', 'cost', 'total', 'sum', 'count',
            'revenue', 'sales', 'discount', 'tax', 'fee', 'balance', 'payment',
            'weight', 'volume', 'size', 'rate', 'percent', 'score', 'value'
        ]

        # Check if column name contains measure keywords
        for pattern in measure_patterns:
            if pattern in col_lower:
                return True

        # Fact tables: numeric columns are likely measures unless they're keys
        if 'fact_' in table_lower or table_lower.startswith('fact'):
            return True  # Already filtered out keys above

        return False

    def analyze_table(self, table_usage: TableUsage, patterns: List[QueryPattern]) -> List[ValidationSuggestion]:
        """Analyze a table's usage patterns and suggest validations"""

        suggestions = []

        # Get table metadata
        table_meta = self.metadata.get(table_usage.table_name, {})

        # 1. Referential Integrity - based on JOIN patterns
        suggestions.extend(self._suggest_referential_integrity(table_usage))

        # 2. Distribution Checks - based on aggregations
        suggestions.extend(self._suggest_distribution_checks(table_usage, table_meta))

        # 3. Data Quality - based on WHERE clauses
        suggestions.extend(self._suggest_data_quality(table_usage, table_meta))

        # 4. Cardinality/Uniqueness - based on GROUP BY
        suggestions.extend(self._suggest_cardinality_checks(table_usage, table_meta))

        # 5. Time Series - based on date column usage
        suggestions.extend(self._suggest_time_series(table_usage, table_meta))

        # 6. Statistics - based on numeric column aggregations
        suggestions.extend(self._suggest_statistics(table_usage, table_meta))

        # 7. Value Range - based on WHERE operators
        suggestions.extend(self._suggest_value_range(table_usage, table_meta))

        return sorted(suggestions, key=lambda x: x.confidence, reverse=True)

    def _suggest_referential_integrity(self, table_usage: TableUsage) -> List[ValidationSuggestion]:
        """Suggest referential integrity / fact-dimension conformance checks based on JOIN patterns"""
        suggestions = []

        if not table_usage.join_partners:
            return suggestions

        # Determine if this is a fact table
        table_lower = table_usage.table_name.lower()
        is_fact_table = 'fact_' in table_lower or table_lower.startswith('fact')

        # For each join partner, suggest referential integrity check
        for partner_table in table_usage.join_partners:
            # Find the join columns used (foreign keys)
            join_columns = []
            for col_name, col_usage in table_usage.columns_used.items():
                if 'join' in col_usage.usage_types:
                    # Only include if it's an identifier column (foreign key)
                    if self._is_identifier_column(col_name, table_usage.table_name):
                        join_columns.append(col_name)

            if join_columns:
                confidence = min(0.95, 0.7 + (len(join_columns) * 0.05))

                # Determine if this is fact-dimension conformance
                partner_lower = partner_table.lower()
                is_dim_partner = 'dim_' in partner_lower or partner_lower.startswith('dim')
                is_conformance = is_fact_table and is_dim_partner

                # Generate appropriate validator based on relationship type
                if is_conformance:
                    # Fact-Dimension conformance: Check that all fact keys exist in dimension
                    validator_name = 'comparative'
                    reason = f"Fact-Dimension Conformance: All {', '.join(join_columns)} in {table_usage.table_name} must exist in {partner_table}"
                    metadata = {
                        'validation_type': 'fact_dimension_conformance',
                        'fact_table': table_usage.table_name,
                        'dimension_table': partner_table,
                        'foreign_keys': join_columns,
                        'join_type': 'referential_integrity',
                        'description': f"Verify all foreign keys from {table_usage.table_name} have matching records in {partner_table}"
                    }
                else:
                    # General referential integrity
                    validator_name = 'comparative'
                    reason = f"Referential Integrity: {table_usage.table_name} → {partner_table} ({', '.join(join_columns)})"
                    metadata = {
                        'validation_type': 'referential_integrity',
                        'child_table': table_usage.table_name,
                        'parent_table': partner_table,
                        'foreign_keys': join_columns,
                        'join_type': 'foreign_key'
                    }

                suggestions.append(ValidationSuggestion(
                    validator_name=validator_name,
                    table_name=table_usage.table_name,
                    columns=join_columns,
                    confidence=confidence,
                    reason=reason,
                    query_count=table_usage.access_count,
                    total_executions=table_usage.access_count,
                    source='workload',
                    metadata=metadata
                ))

        return suggestions

    def _suggest_distribution_checks(self, table_usage: TableUsage, table_meta: Dict) -> List[ValidationSuggestion]:
        """Suggest distribution checks based on aggregation patterns"""
        suggestions = []

        aggregated_cols = []
        for col_name, col_usage in table_usage.columns_used.items():
            if 'aggregate' in col_usage.usage_types and col_usage.aggregate_functions:
                # Check if this is actually a measure column (not an ID/key)
                col_type = table_meta.get(col_name, '')
                is_measure = self._is_measure_column(col_name, table_usage.table_name, col_type)

                if is_measure:
                    # Calculate confidence based on query frequency and function variety
                    base_confidence = min(0.9, 0.6 + (col_usage.query_count * 0.05))
                    function_boost = len(col_usage.aggregate_functions) * 0.05
                    confidence = min(0.95, base_confidence + function_boost)

                    aggregated_cols.append(col_name)

                    suggestions.append(ValidationSuggestion(
                        validator_name='validate_distribution',
                        table_name=table_usage.table_name,
                        columns=[col_name],
                        confidence=confidence,
                        reason=f"Measure column used in {col_usage.query_count} queries with aggregations ({', '.join(col_usage.aggregate_functions)})",
                        query_count=col_usage.query_count,
                        total_executions=table_usage.access_count,
                        source='workload',
                        metadata={
                            'aggregate_functions': list(col_usage.aggregate_functions),
                            'operators': list(col_usage.operators),
                            'column_role': 'measure'
                        }
                    ))

        return suggestions

    def _suggest_data_quality(self, table_usage: TableUsage, table_meta: Dict) -> List[ValidationSuggestion]:
        """Suggest data quality checks based on WHERE clause usage"""
        suggestions = []

        filtered_cols = []
        for col_name, col_usage in table_usage.columns_used.items():
            if 'where' in col_usage.usage_types:
                # High filter usage indicates important column for data quality
                confidence = min(0.85, 0.5 + (col_usage.query_count * 0.05))

                # Suggest null checks for frequently filtered columns
                suggestions.append(ValidationSuggestion(
                    validator_name='validate_nulls',
                    table_name=table_usage.table_name,
                    columns=[col_name],
                    confidence=confidence,
                    reason=f"Column used in WHERE clause of {col_usage.query_count} queries",
                    query_count=col_usage.query_count,
                    total_executions=table_usage.access_count,
                    source='workload',
                    metadata={
                        'operators': list(col_usage.operators),
                        'usage_type': 'filter'
                    }
                ))

                filtered_cols.append(col_name)

        return suggestions

    def _suggest_cardinality_checks(self, table_usage: TableUsage, table_meta: Dict) -> List[ValidationSuggestion]:
        """Suggest cardinality/uniqueness checks based on GROUP BY usage"""
        suggestions = []

        grouped_cols = []
        for col_name, col_usage in table_usage.columns_used.items():
            if 'group_by' in col_usage.usage_types:
                # GROUP BY columns are often dimension keys or categorical data
                confidence = min(0.80, 0.55 + (col_usage.query_count * 0.04))

                grouped_cols.append(col_name)

                suggestions.append(ValidationSuggestion(
                    validator_name='validate_cardinality',
                    table_name=table_usage.table_name,
                    columns=[col_name],
                    confidence=confidence,
                    reason=f"Column used in GROUP BY of {col_usage.query_count} queries (likely categorical/dimension key)",
                    query_count=col_usage.query_count,
                    total_executions=table_usage.access_count,
                    source='workload',
                    metadata={
                        'usage_type': 'grouping'
                    }
                ))

        # If multiple columns are grouped together frequently, suggest composite uniqueness
        if len(grouped_cols) > 1:
            suggestions.append(ValidationSuggestion(
                validator_name='validate_composite_keys',
                table_name=table_usage.table_name,
                columns=grouped_cols,
                confidence=0.75,
                reason=f"Columns frequently grouped together ({len(grouped_cols)} columns)",
                query_count=table_usage.access_count,
                total_executions=table_usage.access_count,
                source='workload',
                metadata={
                    'usage_type': 'composite_grouping'
                }
            ))

        return suggestions

    def _suggest_time_series(self, table_usage: TableUsage, table_meta: Dict) -> List[ValidationSuggestion]:
        """Suggest time-series checks for date columns"""
        suggestions = []

        date_cols = []
        for col_name, col_usage in table_usage.columns_used.items():
            col_type = table_meta.get(col_name, '').upper()
            is_date = any(t in col_type for t in self.date_types)

            if is_date and ('where' in col_usage.usage_types or 'order_by' in col_usage.usage_types):
                # Date columns in WHERE/ORDER BY likely used for time-based analysis
                confidence = min(0.88, 0.65 + (col_usage.query_count * 0.04))

                date_cols.append(col_name)

                suggestions.append(ValidationSuggestion(
                    validator_name='validate_time_series',
                    table_name=table_usage.table_name,
                    columns=[col_name],
                    confidence=confidence,
                    reason=f"Date column used in {col_usage.query_count} queries (time-based filtering/sorting)",
                    query_count=col_usage.query_count,
                    total_executions=table_usage.access_count,
                    source='workload',
                    metadata={
                        'column_type': 'date',
                        'operators': list(col_usage.operators),
                        'usage_types': list(col_usage.usage_types)
                    }
                ))

        return suggestions

    def _suggest_statistics(self, table_usage: TableUsage, table_meta: Dict) -> List[ValidationSuggestion]:
        """Suggest statistical validation for numeric columns with aggregations"""
        suggestions = []

        stat_cols = []
        for col_name, col_usage in table_usage.columns_used.items():
            if 'aggregate' in col_usage.usage_types:
                col_type = table_meta.get(col_name, '')

                # Only suggest statistics for actual measure columns, not IDs/keys
                is_measure = self._is_measure_column(col_name, table_usage.table_name, col_type)

                if is_measure and col_usage.aggregate_functions:
                    # If using statistical functions like AVG, SUM, suggest statistics validation
                    has_stat_func = bool(col_usage.aggregate_functions & {'AVG', 'SUM', 'STDEV', 'VAR'})

                    if has_stat_func:
                        confidence = min(0.92, 0.7 + (col_usage.query_count * 0.04))

                        stat_cols.append(col_name)

                        suggestions.append(ValidationSuggestion(
                            validator_name='validate_statistics',
                            table_name=table_usage.table_name,
                            columns=[col_name],
                            confidence=confidence,
                            reason=f"Measure column with statistical aggregations in {col_usage.query_count} queries ({', '.join(col_usage.aggregate_functions & {'AVG', 'SUM', 'STDEV', 'VAR'})})",
                            query_count=col_usage.query_count,
                            total_executions=table_usage.access_count,
                            source='workload',
                            metadata={
                                'aggregate_functions': list(col_usage.aggregate_functions),
                                'column_role': 'measure'
                            }
                        ))

        return suggestions

    def _suggest_value_range(self, table_usage: TableUsage, table_meta: Dict) -> List[ValidationSuggestion]:
        """Suggest value range checks based on WHERE operators"""
        suggestions = []

        for col_name, col_usage in table_usage.columns_used.items():
            # Check if range operators are used (>, <, >=, <=, BETWEEN)
            range_operators = col_usage.operators & {'>', '<', '>=', '<=', 'BETWEEN'}

            if range_operators and 'where' in col_usage.usage_types:
                col_type = table_meta.get(col_name, '').upper()
                is_numeric = any(t in col_type for t in self.numeric_types)

                if is_numeric:
                    confidence = min(0.82, 0.58 + (col_usage.query_count * 0.04))

                    suggestions.append(ValidationSuggestion(
                        validator_name='validate_value_range',
                        table_name=table_usage.table_name,
                        columns=[col_name],
                        confidence=confidence,
                        reason=f"Numeric column with range filtering in {col_usage.query_count} queries",
                        query_count=col_usage.query_count,
                        total_executions=table_usage.access_count,
                        source='workload',
                        metadata={
                            'operators': list(range_operators),
                            'column_type': 'numeric'
                        }
                    ))

        return suggestions

    def calculate_workload_coverage(self, suggestions: List[ValidationSuggestion], total_queries: int) -> Dict:
        """Calculate how much of the workload is covered by selected validations"""

        total_executions = sum(s.total_executions for s in suggestions)
        unique_queries_covered = len(set(s.query_count for s in suggestions))

        coverage_pct = (unique_queries_covered / total_queries * 100) if total_queries > 0 else 0

        return {
            'total_queries': total_queries,
            'queries_covered': unique_queries_covered,
            'coverage_percentage': round(coverage_pct, 2),
            'total_executions_covered': total_executions,
            'validation_count': len(suggestions),
            'high_confidence_count': len([s for s in suggestions if s.confidence >= 0.8]),
            'medium_confidence_count': len([s for s in suggestions if 0.6 <= s.confidence < 0.8]),
            'low_confidence_count': len([s for s in suggestions if s.confidence < 0.6])
        }

    def merge_with_ai_suggestions(self, workload_suggestions: List[ValidationSuggestion],
                                   ai_suggestions: List[Dict]) -> List[ValidationSuggestion]:
        """Merge workload-based suggestions with AI suggestions from existing logic"""

        merged = list(workload_suggestions)  # Start with workload suggestions

        # Add AI suggestions that don't conflict
        for ai_sugg in ai_suggestions:
            validator_name = ai_sugg.get('validator', '')
            table_name = ai_sugg.get('table', '')
            columns = ai_sugg.get('columns', [])

            # Check if already suggested by workload
            conflict = any(
                ws.validator_name == validator_name and
                ws.table_name == table_name and
                set(ws.columns) == set(columns)
                for ws in workload_suggestions
            )

            if not conflict:
                # Add as AI suggestion
                merged.append(ValidationSuggestion(
                    validator_name=validator_name,
                    table_name=table_name,
                    columns=columns,
                    confidence=0.70,  # Default AI confidence
                    reason=ai_sugg.get('reason', 'AI-suggested based on table schema'),
                    query_count=0,
                    total_executions=0,
                    source='ai',
                    metadata=ai_sugg.get('metadata', {})
                ))

        return merged

    def categorize_suggestions(self, suggestions: List[ValidationSuggestion]) -> Dict[str, List[ValidationSuggestion]]:
        """Categorize suggestions by validation type"""

        categories = {
            'referential_integrity': [],
            'data_quality': [],
            'statistics': [],
            'distribution': [],
            'time_series': [],
            'cardinality': [],
            'value_range': []
        }

        for sugg in suggestions:
            if 'foreign_key' in sugg.validator_name or 'referential' in sugg.validator_name:
                categories['referential_integrity'].append(sugg)
            elif 'null' in sugg.validator_name or 'quality' in sugg.validator_name:
                categories['data_quality'].append(sugg)
            elif 'statistic' in sugg.validator_name:
                categories['statistics'].append(sugg)
            elif 'distribution' in sugg.validator_name:
                categories['distribution'].append(sugg)
            elif 'time_series' in sugg.validator_name or 'date' in sugg.validator_name:
                categories['time_series'].append(sugg)
            elif 'cardinality' in sugg.validator_name or 'unique' in sugg.validator_name:
                categories['cardinality'].append(sugg)
            elif 'range' in sugg.validator_name:
                categories['value_range'].append(sugg)
            else:
                # Default to data quality
                categories['data_quality'].append(sugg)

        return categories
