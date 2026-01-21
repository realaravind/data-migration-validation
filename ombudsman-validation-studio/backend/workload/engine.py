"""
Workload Analysis Engine
Orchestrates parsing, analysis, and suggestion generation
"""

import json
from typing import Dict, List
from datetime import datetime
from collections import defaultdict

from .parser import SQLParser, QueryPattern
from .analyzer import WorkloadAnalyzer, ValidationSuggestion
from .storage import WorkloadStorage


class WorkloadEngine:
    """Main engine for workload processing"""

    def __init__(self, storage: WorkloadStorage = None):
        self.storage = storage or WorkloadStorage()
        self.parser = SQLParser()

    def process_query_store_json(self, queries_data: List[Dict]) -> Dict:
        """
        Process Query Store JSON export

        Args:
            queries_data: List of query records from Query Store

        Returns:
            Processed workload data
        """
        # Parse all queries
        patterns = []
        total_executions = 0
        date_range = {'start': None, 'end': None}

        for query in queries_data:
            query_id = str(query.get('query_id', ''))
            raw_text = query.get('raw_text', '') or query.get('normalized_text', '')

            # Parse stats if available
            stats_json = query.get('stats')
            if isinstance(stats_json, str):
                try:
                    stats = json.loads(stats_json)
                except:
                    stats = {}
            else:
                stats = stats_json or {}

            # Extract execution info
            executions = stats.get('total_executions', 1)
            total_executions += executions

            # Track date range
            last_exec = stats.get('last_execution_time')
            if last_exec:
                if not date_range['start'] or last_exec < date_range['start']:
                    date_range['start'] = last_exec
                if not date_range['end'] or last_exec > date_range['end']:
                    date_range['end'] = last_exec

            # Parse query
            pattern = self.parser.parse_query(
                query_id=query_id,
                sql_text=raw_text,
                stats={
                    'total_executions': executions,
                    'avg_duration': stats.get('avg_duration', 0),
                    'avg_cpu_time': stats.get('avg_cpu_time', 0),
                    'avg_logical_io_reads': stats.get('avg_logical_io_reads', 0)
                }
            )

            patterns.append(pattern)

        # Aggregate patterns by table
        table_usage = self.parser.aggregate_patterns(patterns)

        # Build summary
        workload_data = {
            'query_count': len(queries_data),
            'total_executions': total_executions,
            'date_range': date_range,
            'queries': queries_data,  # Store original data
            'patterns': self._serialize_patterns(patterns),
            'table_usage': self._serialize_table_usage(table_usage)
        }

        return workload_data

    def generate_query_based_validations(self, project_id: str, workload_id: str) -> Dict:
        """
        Generate validations directly from workload queries (proper implementation).

        This creates one validation per unique query, using the original SQL.

        Args:
            project_id: Project identifier
            workload_id: Workload identifier

        Returns:
            Dictionary with validations grouped by table
        """
        # Load workload
        workload = self.storage.get_workload(project_id, workload_id)
        if not workload:
            raise ValueError(f"Workload {workload_id} not found")

        queries = workload.get('queries', [])
        if not queries:
            raise ValueError("No queries found in workload")

        # Group queries by table and deduplicate
        table_queries = {}
        seen_queries = {}  # Track unique queries by normalized SQL

        for query_data in queries:
            raw_sql = query_data.get('raw_text', '').strip()
            if not raw_sql:
                continue

            # Normalize query for deduplication (lowercase, remove extra spaces)
            normalized = ' '.join(raw_sql.lower().split())

            # Skip if we've seen this exact query before
            if normalized in seen_queries:
                # Update execution count
                seen_queries[normalized]['total_executions'] += query_data.get('stats', {}).get('total_executions', 0)
                continue

            # Extract table name from query
            # Try to find FROM clause
            import re
            from_match = re.search(r'FROM\s+(?:(\w+)\.)?(\w+)', raw_sql, re.IGNORECASE)
            if from_match:
                schema = from_match.group(1) or ''
                table = from_match.group(2)
                table_key = f"{schema}.{table}" if schema else table

                # Store unique query
                query_info = {
                    'query_id': query_data.get('query_id'),
                    'raw_text': raw_sql,
                    'normalized': normalized,
                    'total_executions': query_data.get('stats', {}).get('total_executions', 0),
                    'avg_duration': query_data.get('stats', {}).get('avg_duration', 0),
                    'table': table,
                    'schema': schema
                }

                seen_queries[normalized] = query_info

                if table_key not in table_queries:
                    table_queries[table_key] = []
                table_queries[table_key].append(query_info)

        # Create validation suggestions from unique queries
        validation_results = {}
        all_validations = []

        for table_key, queries_list in table_queries.items():
            validations = []

            for idx, query_info in enumerate(queries_list, 1):
                # Create a validation suggestion with the original SQL
                from .analyzer import ValidationSuggestion

                validation = ValidationSuggestion(
                    validator_name='workload_query',  # Special type for workload queries
                    table_name=query_info['table'],
                    schema_name=query_info['schema'],
                    columns=[],  # Not needed for custom SQL
                    confidence=0.95,  # High confidence since these are actual queries
                    reason=f"Actual workload query (executed {query_info['total_executions']} times)",
                    query_count=1,
                    total_executions=query_info['total_executions'],
                    source='workload',
                    metadata={
                        'query_id': query_info['query_id'],
                        'raw_sql': query_info['raw_text'],
                        'avg_duration_ms': query_info['avg_duration'],
                        'validation_type': 'workload_query'
                    }
                )

                validations.append(validation)
                all_validations.append(validation)

            validation_results[table_key] = {
                'table': table_key,
                'query_count': len(queries_list),
                'total_executions': sum(q['total_executions'] for q in queries_list),
                'suggestions': [self._serialize_suggestion(v) for v in validations]
            }

        return {
            'tables': validation_results,
            'total_unique_queries': len(seen_queries),
            'total_queries': len(queries),
            'deduplication_ratio': len(seen_queries) / len(queries) if queries else 0,
            'validations': [self._serialize_suggestion(v) for v in all_validations]
        }

    def analyze_workload(self, project_id: str, workload_id: str, metadata: Dict = None) -> Dict:
        """
        Analyze a stored workload and generate validation suggestions

        Args:
            project_id: Project identifier
            workload_id: Workload identifier
            metadata: Table metadata (column -> datatype mapping)

        Returns:
            Analysis results with suggestions per table
        """
        # Load workload
        workload = self.storage.get_workload(project_id, workload_id)
        if not workload:
            raise ValueError(f"Workload {workload_id} not found")

        # Deserialize table usage
        table_usage_dict = workload.get('table_usage', {})
        patterns = self._deserialize_patterns(workload.get('patterns', []))

        # Initialize analyzer with metadata
        analyzer = WorkloadAnalyzer(metadata=metadata)

        # Analyze each table
        analysis_results = {}
        all_suggestions = []

        for table_name, usage_data in table_usage_dict.items():
            # Recreate TableUsage object
            from .parser import TableUsage, ColumnUsage

            table_usage = TableUsage(table_name=table_name)
            table_usage.access_count = usage_data.get('access_count', 0)
            table_usage.join_partners = set(usage_data.get('join_partners', []))

            # Recreate column usage
            for col_name, col_data in usage_data.get('columns_used', {}).items():
                col_usage = ColumnUsage(
                    column_name=col_name,
                    table_name=table_name
                )
                col_usage.usage_types = set(col_data.get('usage_types', []))
                col_usage.aggregate_functions = set(col_data.get('aggregate_functions', []))
                col_usage.operators = set(col_data.get('operators', []))
                col_usage.query_count = col_data.get('query_count', 0)
                table_usage.columns_used[col_name] = col_usage

            # Get table patterns
            table_patterns = [p for p in patterns if table_name in p.tables]

            # Analyze and get suggestions
            suggestions = analyzer.analyze_table(table_usage, table_patterns)

            analysis_results[table_name] = {
                'access_count': table_usage.access_count,
                'query_count': len(table_patterns),
                'suggestions': [self._serialize_suggestion(s) for s in suggestions],
                'join_partners': list(table_usage.join_partners),
                'column_usage': {
                    col_name: {
                        'usage_types': list(col.usage_types),
                        'query_count': col.query_count,
                        'aggregate_functions': list(col.aggregate_functions),
                        'operators': list(col.operators)
                    }
                    for col_name, col in table_usage.columns_used.items()
                }
            }

            all_suggestions.extend(suggestions)

        # Calculate coverage
        coverage = analyzer.calculate_workload_coverage(
            all_suggestions,
            workload.get('query_count', 0)
        )

        # Categorize suggestions
        categorized = analyzer.categorize_suggestions(all_suggestions)

        # Update workload with analysis
        self.storage.update_workload(project_id, workload_id, {
            'analysis': {
                'tables': analysis_results,
                'coverage': coverage,
                'categories': {
                    cat: [self._serialize_suggestion(s) for s in suggs]
                    for cat, suggs in categorized.items()
                },
                'analyzed_at': datetime.now().isoformat()
            }
        })

        return {
            'tables': analysis_results,
            'coverage': coverage,
            'categories': {cat: len(suggs) for cat, suggs in categorized.items()},
            'total_suggestions': len(all_suggestions)
        }

    def _serialize_patterns(self, patterns: List[QueryPattern]) -> List[Dict]:
        """Convert QueryPattern objects to dicts"""
        return [
            {
                'query_id': p.query_id,
                'tables': p.tables,
                'columns': dict(p.columns),
                'joins': p.joins,
                'where_columns': p.where_columns,
                'aggregations': p.aggregations,
                'group_by_columns': p.group_by_columns,
                'order_by_columns': p.order_by_columns,
                'has_distinct': p.has_distinct,
                'query_type': p.query_type,
                'total_executions': p.total_executions,
                'avg_duration': p.avg_duration
            }
            for p in patterns
        ]

    def _deserialize_patterns(self, pattern_dicts: List[Dict]) -> List[QueryPattern]:
        """Convert dicts to QueryPattern objects"""
        from .parser import QueryPattern
        from collections import defaultdict

        patterns = []
        for p in pattern_dicts:
            pattern = QueryPattern(
                query_id=p.get('query_id', ''),
                tables=p.get('tables', []),
                columns=defaultdict(list, p.get('columns', {})),
                joins=p.get('joins', []),
                where_columns=p.get('where_columns', []),
                aggregations=p.get('aggregations', []),
                group_by_columns=p.get('group_by_columns', []),
                order_by_columns=p.get('order_by_columns', []),
                has_distinct=p.get('has_distinct', False),
                query_type=p.get('query_type', 'SELECT'),
                total_executions=p.get('total_executions', 0),
                avg_duration=p.get('avg_duration', 0.0)
            )
            patterns.append(pattern)

        return patterns

    def _serialize_table_usage(self, table_usage: Dict) -> Dict:
        """Convert TableUsage objects to dicts"""
        result = {}

        for table_name, usage in table_usage.items():
            result[table_name] = {
                'table_name': usage.table_name,
                'schema_name': usage.schema_name,
                'access_count': usage.access_count,
                'join_partners': list(usage.join_partners),
                'columns_used': {
                    col_name: {
                        'column_name': col.column_name,
                        'table_name': col.table_name,
                        'usage_types': list(col.usage_types),
                        'aggregate_functions': list(col.aggregate_functions),
                        'operators': list(col.operators),
                        'query_count': col.query_count
                    }
                    for col_name, col in usage.columns_used.items()
                }
            }

        return result

    def _serialize_suggestion(self, suggestion: ValidationSuggestion) -> Dict:
        """Convert ValidationSuggestion to dict"""
        return {
            'validator_name': suggestion.validator_name,
            'table_name': suggestion.table_name,
            'schema_name': suggestion.schema_name,
            'columns': suggestion.columns,
            'confidence': suggestion.confidence,
            'reason': suggestion.reason,
            'query_count': suggestion.query_count,
            'total_executions': suggestion.total_executions,
            'source': suggestion.source,
            'metadata': suggestion.metadata
        }
