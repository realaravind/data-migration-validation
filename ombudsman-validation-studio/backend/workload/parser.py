"""
SQL Query Parser for Workload Analysis
Extracts tables, columns, and patterns from SQL queries
"""

import re
import sqlparse
from sqlparse.sql import IdentifierList, Identifier, Where, Function, Comparison
from sqlparse.tokens import Keyword, DML
from typing import Dict, List, Set, Tuple
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class ColumnUsage:
    """Track how a column is used in queries"""
    column_name: str
    table_name: str
    usage_types: Set[str] = field(default_factory=set)  # 'where', 'join', 'select', 'group_by', 'order_by', 'aggregate'
    aggregate_functions: Set[str] = field(default_factory=set)  # 'SUM', 'AVG', 'COUNT', 'MIN', 'MAX'
    operators: Set[str] = field(default_factory=set)  # '=', '>', '<', 'BETWEEN', 'IN', 'LIKE'
    query_count: int = 0


@dataclass
class TableUsage:
    """Track table usage patterns"""
    table_name: str
    schema_name: str = ""
    access_count: int = 0
    join_partners: Set[str] = field(default_factory=set)  # Tables joined with
    columns_used: Dict[str, ColumnUsage] = field(default_factory=dict)


@dataclass
class QueryPattern:
    """Extracted patterns from a single query"""
    query_id: str
    tables: List[str]
    columns: Dict[str, List[str]]  # table -> [columns]
    joins: List[Tuple[str, str]]  # [(table1, table2), ...]
    where_columns: List[Tuple[str, str, str]]  # [(table, column, operator), ...]
    aggregations: List[Tuple[str, str, str]]  # [(table, column, function), ...]
    group_by_columns: List[Tuple[str, str]]  # [(table, column), ...]
    order_by_columns: List[Tuple[str, str]]  # [(table, column), ...]
    has_distinct: bool = False
    query_type: str = "SELECT"  # SELECT, INSERT, UPDATE, DELETE
    total_executions: int = 0
    avg_duration: float = 0.0


class SQLParser:
    """Parse SQL queries and extract patterns"""

    def __init__(self):
        self.table_usage: Dict[str, TableUsage] = {}
        self.column_usage: Dict[str, Dict[str, ColumnUsage]] = defaultdict(dict)  # table -> column -> usage

    def parse_query(self, query_id: str, sql_text: str, stats: dict = None) -> QueryPattern:
        """Parse a single SQL query and extract patterns"""

        # Parse SQL
        parsed = sqlparse.parse(sql_text)[0] if sqlparse.parse(sql_text) else None
        if not parsed:
            return QueryPattern(query_id=query_id, tables=[], columns={}, joins=[],
                              where_columns=[], aggregations=[], group_by_columns=[], order_by_columns=[])

        pattern = QueryPattern(
            query_id=query_id,
            tables=[],
            columns=defaultdict(list),
            joins=[],
            where_columns=[],
            aggregations=[],
            group_by_columns=[],
            order_by_columns=[]
        )

        # Add stats if provided
        if stats:
            pattern.total_executions = stats.get('total_executions', 0)
            pattern.avg_duration = stats.get('avg_duration', 0.0)

        # Determine query type
        pattern.query_type = self._get_query_type(parsed)

        # Extract tables from FROM and JOIN clauses
        pattern.tables = self._extract_tables(parsed)

        # Extract columns
        pattern.columns = self._extract_columns(parsed, pattern.tables)

        # Extract JOINs
        pattern.joins = self._extract_joins(parsed)

        # Extract WHERE clause patterns
        pattern.where_columns = self._extract_where_columns(parsed)

        # Extract aggregations
        pattern.aggregations = self._extract_aggregations(parsed)

        # Extract GROUP BY
        pattern.group_by_columns = self._extract_group_by(parsed)

        # Extract ORDER BY
        pattern.order_by_columns = self._extract_order_by(parsed)

        # Check for DISTINCT
        pattern.has_distinct = 'DISTINCT' in sql_text.upper()

        return pattern

    def _get_query_type(self, parsed) -> str:
        """Determine query type (SELECT, INSERT, UPDATE, DELETE)"""
        for token in parsed.tokens:
            if token.ttype is DML:
                return token.value.upper()
        return "SELECT"

    def _extract_tables(self, parsed) -> List[str]:
        """Extract table names from FROM and JOIN clauses"""
        tables = []
        from_seen = False

        for token in parsed.tokens:
            if from_seen:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        tables.append(self._get_real_name(identifier))
                elif isinstance(token, Identifier):
                    tables.append(self._get_real_name(token))

            if token.ttype is Keyword and token.value.upper() in ('FROM', 'JOIN', 'INNER JOIN', 'LEFT JOIN', 'RIGHT JOIN'):
                from_seen = True
            elif token.ttype is Keyword and token.value.upper() in ('WHERE', 'GROUP', 'ORDER', 'HAVING', 'LIMIT'):
                from_seen = False

        return list(set(tables))

    def _get_real_name(self, identifier) -> str:
        """Get the real name from an identifier (handle aliases)"""
        if isinstance(identifier, Identifier):
            # Get the real name, not the alias
            return identifier.get_real_name() or str(identifier.get_name())
        return str(identifier).strip()

    def _extract_columns(self, parsed, tables: List[str]) -> Dict[str, List[str]]:
        """Extract columns mentioned in SELECT clause"""
        columns = defaultdict(list)

        # Simple regex-based extraction for SELECT clause
        sql_text = str(parsed)

        # Extract SELECT ... FROM
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', sql_text, re.IGNORECASE | re.DOTALL)
        if select_match:
            select_clause = select_match.group(1)

            # Split by comma and extract column names
            col_list = [c.strip() for c in select_clause.split(',')]
            for col in col_list:
                # Handle table.column format
                if '.' in col and ' AS ' not in col.upper():
                    parts = col.split('.')
                    if len(parts) == 2:
                        table = parts[0].strip('[]').strip()
                        column = parts[1].strip('[]').strip()
                        columns[table].append(column)
                elif col != '*' and not col.upper().startswith('CASE'):
                    # Try to associate with first table if no table prefix
                    if tables:
                        columns[tables[0]].append(col.split()[0])  # Get column before any alias

        return dict(columns)

    def _extract_joins(self, parsed) -> List[Tuple[str, str]]:
        """Extract JOIN relationships"""
        joins = []
        sql_text = str(parsed).upper()

        # Find all JOIN ... ON patterns
        join_pattern = r'JOIN\s+(\w+)\s+(?:\w+\s+)?ON\s+(\w+)\.(\w+)\s*=\s*(\w+)\.(\w+)'
        matches = re.finditer(join_pattern, sql_text, re.IGNORECASE)

        for match in matches:
            table1 = match.group(2)
            table2 = match.group(4)
            if table1 and table2:
                joins.append((table1, table2))

        return joins

    def _extract_where_columns(self, parsed) -> List[Tuple[str, str, str]]:
        """Extract columns used in WHERE clause with operators"""
        where_cols = []
        sql_text = str(parsed)

        # Extract WHERE clause
        where_match = re.search(r'WHERE\s+(.*?)(?:GROUP BY|ORDER BY|HAVING|LIMIT|$)', sql_text, re.IGNORECASE | re.DOTALL)
        if where_match:
            where_clause = where_match.group(1)

            # Find column comparisons
            # Pattern: table.column operator value
            pattern = r'(\w+)\.(\w+)\s*(=|<|>|<=|>=|<>|!=|LIKE|IN|BETWEEN)\s*'
            matches = re.finditer(pattern, where_clause, re.IGNORECASE)

            for match in matches:
                table = match.group(1)
                column = match.group(2)
                operator = match.group(3).upper()
                where_cols.append((table, column, operator))

        return where_cols

    def _extract_aggregations(self, parsed) -> List[Tuple[str, str, str]]:
        """Extract aggregate functions (SUM, AVG, COUNT, MIN, MAX)"""
        aggs = []
        sql_text = str(parsed)

        # Pattern: AGG_FUNCTION(table.column) or AGG_FUNCTION(column)
        agg_pattern = r'(SUM|AVG|COUNT|MIN|MAX|STDEV|VAR)\s*\(\s*(?:(\w+)\.)?(\w+)\s*\)'
        matches = re.finditer(agg_pattern, sql_text, re.IGNORECASE)

        for match in matches:
            function = match.group(1).upper()
            table = match.group(2) if match.group(2) else ''
            column = match.group(3)
            aggs.append((table, column, function))

        return aggs

    def _extract_group_by(self, parsed) -> List[Tuple[str, str]]:
        """Extract GROUP BY columns"""
        group_cols = []
        sql_text = str(parsed)

        # Extract GROUP BY clause
        group_match = re.search(r'GROUP BY\s+(.*?)(?:HAVING|ORDER BY|LIMIT|$)', sql_text, re.IGNORECASE | re.DOTALL)
        if group_match:
            group_clause = group_match.group(1)

            # Split by comma
            cols = [c.strip() for c in group_clause.split(',')]
            for col in cols:
                if '.' in col:
                    parts = col.split('.')
                    if len(parts) == 2:
                        table = parts[0].strip()
                        column = parts[1].strip()
                        group_cols.append((table, column))
                else:
                    group_cols.append(('', col))

        return group_cols

    def _extract_order_by(self, parsed) -> List[Tuple[str, str]]:
        """Extract ORDER BY columns"""
        order_cols = []
        sql_text = str(parsed)

        # Extract ORDER BY clause
        order_match = re.search(r'ORDER BY\s+(.*?)(?:LIMIT|$)', sql_text, re.IGNORECASE | re.DOTALL)
        if order_match:
            order_clause = order_match.group(1)

            # Split by comma and remove ASC/DESC
            cols = [c.strip() for c in order_clause.split(',')]
            for col in cols:
                col = re.sub(r'\s+(ASC|DESC)\s*$', '', col, flags=re.IGNORECASE).strip()
                if '.' in col:
                    parts = col.split('.')
                    if len(parts) == 2:
                        table = parts[0].strip()
                        column = parts[1].strip()
                        order_cols.append((table, column))
                else:
                    order_cols.append(('', col))

        return order_cols

    def aggregate_patterns(self, patterns: List[QueryPattern]) -> Dict[str, TableUsage]:
        """Aggregate multiple query patterns into table usage statistics"""
        table_usage = {}

        for pattern in patterns:
            # Track table access
            for table in pattern.tables:
                if table not in table_usage:
                    table_usage[table] = TableUsage(table_name=table)

                table_usage[table].access_count += pattern.total_executions or 1

                # Track join partners
                for join_pair in pattern.joins:
                    if table in join_pair:
                        partner = join_pair[1] if join_pair[0] == table else join_pair[0]
                        table_usage[table].join_partners.add(partner)

                # Track column usage
                # WHERE columns
                for tbl, col, op in pattern.where_columns:
                    if tbl == table or (not tbl and table in pattern.tables):
                        actual_table = tbl or table
                        if col not in table_usage[actual_table].columns_used:
                            table_usage[actual_table].columns_used[col] = ColumnUsage(
                                column_name=col, table_name=actual_table
                            )
                        table_usage[actual_table].columns_used[col].usage_types.add('where')
                        table_usage[actual_table].columns_used[col].operators.add(op)
                        table_usage[actual_table].columns_used[col].query_count += 1

                # Aggregation columns
                for tbl, col, func in pattern.aggregations:
                    if tbl == table or (not tbl and table in pattern.tables):
                        actual_table = tbl or table
                        if col not in table_usage[actual_table].columns_used:
                            table_usage[actual_table].columns_used[col] = ColumnUsage(
                                column_name=col, table_name=actual_table
                            )
                        table_usage[actual_table].columns_used[col].usage_types.add('aggregate')
                        table_usage[actual_table].columns_used[col].aggregate_functions.add(func)
                        table_usage[actual_table].columns_used[col].query_count += 1

                # GROUP BY columns
                for tbl, col in pattern.group_by_columns:
                    if tbl == table or (not tbl and table in pattern.tables):
                        actual_table = tbl or table
                        if col not in table_usage[actual_table].columns_used:
                            table_usage[actual_table].columns_used[col] = ColumnUsage(
                                column_name=col, table_name=actual_table
                            )
                        table_usage[actual_table].columns_used[col].usage_types.add('group_by')
                        table_usage[actual_table].columns_used[col].query_count += 1

        return table_usage
