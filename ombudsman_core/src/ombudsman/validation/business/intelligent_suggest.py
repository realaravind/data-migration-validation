"""
Intelligent Custom Query Suggestion System

Analyzes metadata and relationships to automatically suggest meaningful
business validation queries based on your actual schema.
"""
from ombudsman.validation.sql_utils import escape_sql_server_identifier, escape_snowflake_identifier

def suggest_queries_from_metadata(metadata, mapping, relationships=None):
    """
    Generate intelligent query suggestions based on discovered metadata.

    Args:
        metadata: Table metadata (from metadata_loader)
        mapping: Table mapping (sql -> snowflake)
        relationships: Optional relationship definitions

    Returns:
        List of suggested query definitions ready to use
    """
    suggestions = []

    # Group tables by type
    fact_tables = [t for t in metadata.keys() if t.lower().startswith('fact') or 'fact' in t.lower()]
    dim_tables = [t for t in metadata.keys() if t.lower().startswith('dim') or 'dimension' in t.lower()]

    # 1. Suggest record count validations for all tables
    for table in metadata.keys():
        if table in mapping:
            sql_table = escape_sql_server_identifier(mapping[table]["sql"])
            snow_table = escape_snowflake_identifier(mapping[table]["snow"])

            suggestions.append({
                "name": f"Record Count - {table}",
                "category": "Basic Validation",
                "priority": "HIGH",
                "comparison_type": "count",
                "sql_query": f"SELECT COUNT(*) as count FROM {sql_table}",
                "snow_query": f"SELECT COUNT(*) as count FROM {snow_table}",
                "description": f"Validate total record count for {table}"
            })

    # 2. Suggest metric aggregations for fact tables
    for fact_table in fact_tables:
        if fact_table not in metadata:
            continue

        numeric_cols = metadata[fact_table].get("numeric_columns", [])
        sql_table = escape_sql_server_identifier(mapping[fact_table]["sql"])
        snow_table = escape_snowflake_identifier(mapping[fact_table]["snow"])

        # Skip if no numeric columns
        if not numeric_cols:
            continue

        # Suggest sum validation for each numeric column
        for col in numeric_cols[:3]:  # Limit to first 3 numeric columns
            suggestions.append({
                "name": f"Total {col} - {fact_table}",
                "category": "Metric Validation",
                "priority": "HIGH",
                "comparison_type": "aggregation",
                "tolerance": 0.01,
                "sql_query": f"""SELECT
    SUM({col}) as total_{col.lower()},
    AVG({col}) as avg_{col.lower()},
    COUNT(*) as row_count
FROM {sql_table}""",
                "snow_query": f"""SELECT
    SUM({col}) as total_{col.lower()},
    AVG({col}) as avg_{col.lower()},
    COUNT(*) as row_count
FROM {snow_table}""",
                "description": f"Validate sum and average of {col} in {fact_table}"
            })

    # 3. Suggest fact + dimension join queries
    if relationships:
        for fact_table in fact_tables:
            if fact_table not in metadata:
                continue

            # Find related dimensions
            related_dims = []
            for rel_name, rel_def in relationships.items():
                if isinstance(rel_def, dict):
                    if rel_def.get('fact_table') == fact_table or rel_def.get('from_table') == fact_table:
                        dim_table = rel_def.get('dim_table') or rel_def.get('to_table')
                        if dim_table and dim_table in dim_tables:
                            related_dims.append({
                                'table': dim_table,
                                'fact_key': rel_def.get('fact_key') or rel_def.get('from_column'),
                                'dim_key': rel_def.get('dim_key') or rel_def.get('to_column')
                            })

            # Create join query for each related dimension
            for rel in related_dims[:2]:  # Limit to 2 dimensions per fact
                dim_table = rel['table']
                fact_key = rel['fact_key']
                dim_key = rel['dim_key']

                if not all([dim_table, fact_key, dim_key]):
                    continue

                # Get grouping column (first non-key column in dimension)
                dim_cols = metadata.get(dim_table, {}).get("all_columns", [])
                group_col = next((c for c in dim_cols if c != dim_key), dim_key)

                # Get metric column (first numeric in fact)
                fact_metrics = metadata[fact_table].get("numeric_columns", [])
                metric_col = fact_metrics[0] if fact_metrics else "1"

                sql_fact = escape_sql_server_identifier(mapping[fact_table]["sql"])
                snow_fact = escape_snowflake_identifier(mapping[fact_table]["snow"])
                sql_dim = escape_sql_server_identifier(mapping[dim_table]["sql"])
                snow_dim = escape_snowflake_identifier(mapping[dim_table]["snow"])

                suggestions.append({
                    "name": f"{fact_table} by {dim_table}",
                    "category": "Join Validation",
                    "priority": "MEDIUM",
                    "comparison_type": "rowset",
                    "tolerance": 0.01,
                    "limit": 20,
                    "sql_query": f"""SELECT
    d.{group_col},
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {sql_fact} f
INNER JOIN {sql_dim} d ON f.{fact_key} = d.{dim_key}
GROUP BY d.{group_col}
ORDER BY total_metric DESC""",
                    "snow_query": f"""SELECT
    d.{group_col},
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {snow_fact} f
INNER JOIN {snow_dim} d ON f.{fact_key} = d.{dim_key}
GROUP BY d.{group_col}
ORDER BY total_metric DESC""",
                    "description": f"Validate {fact_table} metrics grouped by {dim_table}.{group_col}"
                })

    # 4. Suggest date-based queries if date dimension exists
    date_dims = [t for t in dim_tables if 'date' in t.lower() or 'time' in t.lower()]
    if date_dims and fact_tables:
        date_dim = date_dims[0]

        # Find date columns in date dimension
        date_cols = metadata.get(date_dim, {}).get("all_columns", [])
        date_col = next((c for c in date_cols if 'date' in c.lower() and 'key' not in c.lower()), None)
        year_col = next((c for c in date_cols if 'year' in c.lower()), 'Year')
        month_col = next((c for c in date_cols if 'month' in c.lower() and 'name' not in c.lower()), 'Month')

        if date_col and relationships:
            # Find fact table connected to date dimension
            for fact_table in fact_tables:
                if fact_table not in metadata:
                    continue

                # Find date key relationship
                date_key = None
                fact_date_key = None

                for rel_name, rel_def in relationships.items():
                    if isinstance(rel_def, dict):
                        if (rel_def.get('fact_table') == fact_table and rel_def.get('dim_table') == date_dim) or \
                           (rel_def.get('from_table') == fact_table and rel_def.get('to_table') == date_dim):
                            date_key = rel_def.get('dim_key') or rel_def.get('to_column')
                            fact_date_key = rel_def.get('fact_key') or rel_def.get('from_column')
                            break

                if date_key and fact_date_key:
                    fact_metrics = metadata[fact_table].get("numeric_columns", [])
                    metric_col = fact_metrics[0] if fact_metrics else "1"

                    sql_fact = escape_sql_server_identifier(mapping[fact_table]["sql"])
                    snow_fact = escape_snowflake_identifier(mapping[fact_table]["snow"])
                    sql_date = escape_sql_server_identifier(mapping[date_dim]["sql"])
                    snow_date = escape_snowflake_identifier(mapping[date_dim]["snow"])

                    # Find quarter column if it exists
                    quarter_col = next((c for c in date_cols if 'quarter' in c.lower()), 'Quarter')

                    # 1. Yearly trend query
                    suggestions.append({
                        "name": f"Yearly Trend - {fact_table}",
                        "category": "Time-Based Validation",
                        "priority": "HIGH",
                        "comparison_type": "rowset",
                        "tolerance": 0.01,
                        "limit": 10,
                        "sql_query": f"""SELECT
    d.[{year_col}] as year_val,
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {sql_fact} f
INNER JOIN {sql_date} d ON f.{fact_date_key} = d.{date_key}
GROUP BY d.[{year_col}]
ORDER BY d.[{year_col}]""",
                        "snow_query": f"""SELECT
    d.{year_col} as year_val,
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {snow_fact} f
INNER JOIN {snow_date} d ON f.{fact_date_key} = d.{date_key}
GROUP BY d.{year_col}
ORDER BY d.{year_col}""",
                        "description": f"Validate yearly trends for {fact_table}"
                    })

                    # 2. Quarterly trend query
                    suggestions.append({
                        "name": f"Quarterly Trend - {fact_table}",
                        "category": "Time-Based Validation",
                        "priority": "HIGH",
                        "comparison_type": "rowset",
                        "tolerance": 0.01,
                        "limit": 20,
                        "sql_query": f"""SELECT
    d.[{year_col}] as year_val,
    d.[{quarter_col}] as quarter_val,
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {sql_fact} f
INNER JOIN {sql_date} d ON f.{fact_date_key} = d.{date_key}
GROUP BY d.[{year_col}], d.[{quarter_col}]
ORDER BY d.[{year_col}], d.[{quarter_col}]""",
                        "snow_query": f"""SELECT
    d.{year_col} as year_val,
    d.{quarter_col} as quarter_val,
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {snow_fact} f
INNER JOIN {snow_date} d ON f.{fact_date_key} = d.{date_key}
GROUP BY d.{year_col}, d.{quarter_col}
ORDER BY d.{year_col}, d.{quarter_col}""",
                        "description": f"Validate quarterly trends for {fact_table}"
                    })

                    # 3. Monthly trend query
                    suggestions.append({
                        "name": f"Monthly Trend - {fact_table}",
                        "category": "Time-Based Validation",
                        "priority": "HIGH",
                        "comparison_type": "rowset",
                        "tolerance": 0.01,
                        "limit": 12,
                        "sql_query": f"""SELECT
    d.[{year_col}] as year_val,
    d.[{month_col}] as month_val,
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {sql_fact} f
INNER JOIN {sql_date} d ON f.{fact_date_key} = d.{date_key}
GROUP BY d.[{year_col}], d.[{month_col}]
ORDER BY d.[{year_col}], d.[{month_col}]""",
                        "snow_query": f"""SELECT
    d.{year_col} as year_val,
    d.{month_col} as month_val,
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {snow_fact} f
INNER JOIN {snow_date} d ON f.{fact_date_key} = d.{date_key}
GROUP BY d.{year_col}, d.{month_col}
ORDER BY d.{year_col}, d.{month_col}""",
                        "description": f"Validate monthly trends for {fact_table}"
                    })

                    # 4. Rolling 12 months query
                    suggestions.append({
                        "name": f"Rolling 12 Months - {fact_table}",
                        "category": "Time-Based Validation",
                        "priority": "HIGH",
                        "comparison_type": "rowset",
                        "tolerance": 0.01,
                        "limit": 12,
                        "sql_query": f"""SELECT
    d.[{year_col}] as year_val,
    d.[{month_col}] as month_val,
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {sql_fact} f
INNER JOIN {sql_date} d ON f.{fact_date_key} = d.{date_key}
WHERE d.[{date_col}] >= DATEADD(MONTH, -12, GETDATE())
GROUP BY d.[{year_col}], d.[{month_col}]
ORDER BY d.[{year_col}], d.[{month_col}]""",
                        "snow_query": f"""SELECT
    d.{year_col} as year_val,
    d.{month_col} as month_val,
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {snow_fact} f
INNER JOIN {snow_date} d ON f.{fact_date_key} = d.{date_key}
WHERE d.{date_col} >= DATEADD(MONTH, -12, CURRENT_DATE())
GROUP BY d.{year_col}, d.{month_col}
ORDER BY d.{year_col}, d.{month_col}""",
                        "description": f"Validate rolling 12 months trends for {fact_table}"
                    })

                    break  # Only create date-based queries for first fact table

    # 5. Suggest Top N queries for dimensions
    for dim_table in dim_tables[:2]:  # Limit to first 2 dimensions
        if dim_table not in metadata or not fact_tables:
            continue

        # Find fact table related to this dimension
        related_fact = None
        dim_key = None
        fact_key = None

        if relationships:
            for rel_name, rel_def in relationships.items():
                if isinstance(rel_def, dict):
                    if rel_def.get('dim_table') == dim_table or rel_def.get('to_table') == dim_table:
                        related_fact = rel_def.get('fact_table') or rel_def.get('from_table')
                        dim_key = rel_def.get('dim_key') or rel_def.get('to_column')
                        fact_key = rel_def.get('fact_key') or rel_def.get('from_column')
                        if related_fact in fact_tables:
                            break

        if not related_fact or not dim_key or not fact_key:
            continue

        # Get name column from dimension
        dim_cols = metadata[dim_table].get("all_columns", [])
        name_col = next((c for c in dim_cols if 'name' in c.lower()), dim_cols[0] if dim_cols else dim_key)

        # Get metric from fact
        fact_metrics = metadata.get(related_fact, {}).get("numeric_columns", [])
        metric_col = fact_metrics[0] if fact_metrics else "1"

        sql_fact = escape_sql_server_identifier(mapping[related_fact]["sql"])
        snow_fact = escape_snowflake_identifier(mapping[related_fact]["snow"])
        sql_dim = escape_sql_server_identifier(mapping[dim_table]["sql"])
        snow_dim = escape_snowflake_identifier(mapping[dim_table]["snow"])

        dim_name = dim_table.replace('dim_', '').replace('Dim', '').title()

        suggestions.append({
            "name": f"Top 5 {dim_name}",
            "category": "Top N Validation",
            "priority": "MEDIUM",
            "comparison_type": "rowset",
            "tolerance": 0.01,
            "limit": 5,
            "sql_query": f"""SELECT TOP 5
    d.{name_col},
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {sql_fact} f
INNER JOIN {sql_dim} d ON f.{fact_key} = d.{dim_key}
GROUP BY d.{name_col}
ORDER BY total_metric DESC""",
            "snow_query": f"""SELECT
    d.{name_col},
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {snow_fact} f
INNER JOIN {snow_dim} d ON f.{fact_key} = d.{dim_key}
GROUP BY d.{name_col}
ORDER BY total_metric DESC
LIMIT 5""",
            "description": f"Validate top 5 {dim_name} by total metrics"
        })

    # 6. Suggest multi-dimension join (if we have multiple dimensions)
    if len(dim_tables) >= 2 and fact_tables and relationships:
        fact_table = fact_tables[0]

        # Find 2 dimensions related to this fact
        related_dims = []
        for rel_name, rel_def in relationships.items():
            if isinstance(rel_def, dict):
                if rel_def.get('fact_table') == fact_table or rel_def.get('from_table') == fact_table:
                    dim = rel_def.get('dim_table') or rel_def.get('to_table')
                    if dim in dim_tables and len(related_dims) < 2:
                        related_dims.append({
                            'table': dim,
                            'fact_key': rel_def.get('fact_key') or rel_def.get('from_column'),
                            'dim_key': rel_def.get('dim_key') or rel_def.get('to_column')
                        })

        if len(related_dims) >= 2:
            dim1 = related_dims[0]
            dim2 = related_dims[1]

            # Get grouping columns
            dim1_cols = metadata.get(dim1['table'], {}).get("all_columns", [])
            dim2_cols = metadata.get(dim2['table'], {}).get("all_columns", [])

            dim1_group = next((c for c in dim1_cols if 'name' in c.lower() or c != dim1['dim_key']), dim1['dim_key'])
            dim2_group = next((c for c in dim2_cols if 'name' in c.lower() or c != dim2['dim_key']), dim2['dim_key'])

            fact_metrics = metadata.get(fact_table, {}).get("numeric_columns", [])
            metric_col = fact_metrics[0] if fact_metrics else "1"

            sql_fact = escape_sql_server_identifier(mapping[fact_table]["sql"])
            snow_fact = escape_snowflake_identifier(mapping[fact_table]["snow"])
            sql_dim1 = escape_sql_server_identifier(mapping[dim1['table']]["sql"])
            snow_dim1 = escape_snowflake_identifier(mapping[dim1['table']]["snow"])
            sql_dim2 = escape_sql_server_identifier(mapping[dim2['table']]["sql"])
            snow_dim2 = escape_snowflake_identifier(mapping[dim2['table']]["snow"])

            dim1_name = dim1['table'].replace('dim_', '').replace('Dim', '').title()
            dim2_name = dim2['table'].replace('dim_', '').replace('Dim', '').title()

            suggestions.append({
                "name": f"{fact_table} by {dim1_name} and {dim2_name}",
                "category": "Complex Join Validation",
                "priority": "LOW",
                "comparison_type": "rowset",
                "tolerance": 0.01,
                "limit": 50,
                "sql_query": f"""SELECT
    d1.{dim1_group},
    d2.{dim2_group},
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {sql_fact} f
INNER JOIN {sql_dim1} d1 ON f.{dim1['fact_key']} = d1.{dim1['dim_key']}
INNER JOIN {sql_dim2} d2 ON f.{dim2['fact_key']} = d2.{dim2['dim_key']}
GROUP BY d1.{dim1_group}, d2.{dim2_group}
ORDER BY total_metric DESC""",
                "snow_query": f"""SELECT
    d1.{dim1_group},
    d2.{dim2_group},
    SUM({metric_col}) as total_metric,
    COUNT(*) as record_count
FROM {snow_fact} f
INNER JOIN {snow_dim1} d1 ON f.{dim1['fact_key']} = d1.{dim1['dim_key']}
INNER JOIN {snow_dim2} d2 ON f.{dim2['fact_key']} = d2.{dim2['dim_key']}
GROUP BY d1.{dim1_group}, d2.{dim2_group}
ORDER BY total_metric DESC""",
                "description": f"Validate {fact_table} metrics by {dim1_name} and {dim2_name}"
            })

    return suggestions


def format_suggestions_for_display(suggestions):
    """
    Format suggestions in a user-friendly way grouped by category.
    """
    categorized = {}
    for sugg in suggestions:
        category = sugg.get('category', 'Other')
        if category not in categorized:
            categorized[category] = []
        categorized[category].append(sugg)

    return categorized


def save_suggestions_to_yaml(suggestions, output_file):
    """
    Save suggested queries to a YAML file ready to use.
    """
    import yaml

    # Convert to YAML format (remove extra fields like category, priority)
    yaml_queries = []
    for sugg in suggestions:
        yaml_query = {
            'name': sugg['name'],
            'comparison_type': sugg['comparison_type'],
            'sql_query': sugg['sql_query'],
            'snow_query': sugg['snow_query']
        }

        # Add optional fields
        if 'tolerance' in sugg:
            yaml_query['tolerance'] = sugg['tolerance']
        if 'limit' in sugg:
            yaml_query['limit'] = sugg['limit']

        # Add description as comment
        if 'description' in sugg:
            yaml_query['_comment'] = sugg['description']

        yaml_queries.append(yaml_query)

    with open(output_file, 'w') as f:
        yaml.dump(yaml_queries, f, default_flow_style=False, sort_keys=False)

    return len(yaml_queries)
