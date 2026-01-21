# src/ombudsman/validation/sql_utils.py
"""
SQL utility functions for escaping identifiers and handling reserved keywords.
"""
import os
import re

def substitute_schema_names(sql_text, schema_mappings, target_database=None):
    """
    Substitute schema names in SQL text based on provided mappings.

    Handles all common SQL identifier formats:
    - database.schema.table
    - schema.table
    - table (when preceded by FROM, JOIN, UPDATE, INTO, etc.)

    Args:
        sql_text: The SQL query text to transform
        schema_mappings: Dict mapping source schemas to target schemas
                        e.g., {'SAMPLE_DIM': 'DIM', 'SAMPLE_FACT': 'FACT'}
        target_database: Optional target database name to prepend

    Returns:
        Transformed SQL text with substituted schema names

    Examples:
        Input:  "SELECT * FROM SAMPLE_DIM.DIM_CUSTOMER"
        Output: "SELECT * FROM DIM.DIM_CUSTOMER"

        Input:  "SELECT * FROM SAMPLEDW.SAMPLE_FACT.FACT_SALES"
        Output: "SELECT * FROM SAMPLEDW.FACT.FACT_SALES"
    """
    if not sql_text or not schema_mappings:
        return sql_text

    transformed_sql = sql_text

    # Sort mappings by length (longest first) to avoid partial replacements
    sorted_mappings = sorted(schema_mappings.items(), key=lambda x: len(x[0]), reverse=True)

    for source_schema, target_schema in sorted_mappings:
        # Pattern 1: database.schema.table (3-part identifier)
        # Matches: SAMPLEDW.SAMPLE_DIM.table_name
        # Replaces schema part while keeping database and table
        pattern1 = r'\b(\w+)\.' + re.escape(source_schema) + r'\.(\w+)\b'
        transformed_sql = re.sub(
            pattern1,
            lambda m: f"{m.group(1)}.{target_schema}.{m.group(2)}",
            transformed_sql,
            flags=re.IGNORECASE
        )

        # Pattern 2: schema.table (2-part identifier)
        # Matches: SAMPLE_DIM.table_name
        # Replaces with: target_schema.table_name
        pattern2 = r'\b' + re.escape(source_schema) + r'\.(\w+)\b'
        transformed_sql = re.sub(
            pattern2,
            f"{target_schema}.\\1",
            transformed_sql,
            flags=re.IGNORECASE
        )

        # Pattern 3: Standalone schema references (e.g., in WITH clauses)
        # Only replace if followed by specific SQL keywords or context
        # This is more conservative to avoid false positives
        pattern3 = r'\bFROM\s+' + re.escape(source_schema) + r'\b(?!\.)'
        transformed_sql = re.sub(
            pattern3,
            f"FROM {target_schema}",
            transformed_sql,
            flags=re.IGNORECASE
        )

    return transformed_sql

def escape_sql_server_identifier(identifier):
    """
    Escape SQL Server identifiers (table names, column names) with square brackets.
    Handles schema-qualified names and replaces first part with database name.

    SQL Server uses 3-part naming: database.schema.table
    Snowflake uses 2-part or 3-part naming: schema.table or database.schema.table

    This function converts Snowflake-style names to SQL Server-style names by:
    - If 3 parts: Replace first part (Snowflake database) with SQL Server database
    - If 2 parts: Prepend SQL Server database name
    - If 1 part: Prepend SQL Server database and default schema

    Args:
        identifier: Table name or column name, possibly schema-qualified

    Returns:
        Properly escaped identifier for SQL Server with database prefix

    Examples:
        'customer' -> '[SampleDW].[dbo].[customer]'
        'FACT.fact_sales' -> '[SampleDW].[FACT].[fact_sales]'
        'PUBLIC.FACT.FACT_SALES' -> '[SampleDW].[FACT].[FACT_SALES]'
        'DIM.DIM_CUSTOMER' -> '[SampleDW].[DIM].[DIM_CUSTOMER]'
    """
    if not identifier:
        return identifier

    # Get database name from environment
    sql_database = os.getenv("SQL_DATABASE", "SampleDW")

    # Split by dots to handle schema-qualified names
    parts = identifier.split('.')

    # Handle different formats
    if len(parts) == 3:
        # 3 parts: Assume first part is Snowflake database, replace with SQL Server database
        # PUBLIC.FACT.FACT_SALES -> SampleDW.FACT.FACT_SALES
        parts = [sql_database, parts[1], parts[2]]
    elif len(parts) == 2:
        # 2 parts (schema.table), add database as first part
        parts = [sql_database] + parts
    elif len(parts) == 1:
        # 1 part (table), add database and default schema
        default_schema = os.getenv("SQL_SCHEMA", "dbo")
        parts = [sql_database, default_schema] + parts

    # Escape each part with square brackets
    escaped_parts = [f"[{part.strip()}]" for part in parts if part.strip()]

    # Join back with dots
    return '.'.join(escaped_parts)


def escape_snowflake_identifier(identifier):
    """
    Handle Snowflake identifiers and convert 3-part names to proper format.

    Snowflake uses: database.schema.table

    If the identifier has 3 parts, we need to replace the first part
    with the actual Snowflake database name from environment.

    Args:
        identifier: Table name or column name, possibly schema-qualified

    Returns:
        Properly formatted identifier for Snowflake

    Examples:
        'customer' -> 'SAMPLEDW.PUBLIC.customer'
        'FACT.fact_sales' -> 'SAMPLEDW.FACT.fact_sales'
        'PUBLIC.FACT.FACT_SALES' -> 'SAMPLEDW.FACT.FACT_SALES'
        'DIM.DIM_CUSTOMER' -> 'SAMPLEDW.DIM.DIM_CUSTOMER'
    """
    if not identifier:
        return identifier

    # Get Snowflake database name from environment
    snow_database = os.getenv("SNOWFLAKE_DATABASE", "SAMPLEDW")

    # Split by dots
    parts = identifier.split('.')

    # Handle different formats
    if len(parts) == 3:
        # 3 parts: Replace first part with correct Snowflake database
        # PUBLIC.FACT.FACT_SALES -> SAMPLEDW.FACT.FACT_SALES
        return f"{snow_database}.{parts[1]}.{parts[2]}"
    elif len(parts) == 2:
        # 2 parts (schema.table): Add database prefix
        return f"{snow_database}.{parts[0]}.{parts[1]}"
    elif len(parts) == 1:
        # 1 part (table): Add database and default schema
        default_schema = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")
        return f"{snow_database}.{default_schema}.{parts[0]}"

    return identifier
