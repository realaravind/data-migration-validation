"""
Mermaid Diagram Generator

Generates Entity-Relationship Diagrams (ERD) in Mermaid syntax from database metadata.
"""

from typing import Dict, List, Optional
import re


def sanitize(text: str) -> str:
    """Sanitize text for Mermaid syntax (remove special characters)."""
    # Remove parentheses, commas, and other special chars
    text = re.sub(r'[(),]', '', text)
    # Replace spaces with underscores
    text = text.replace(' ', '_')
    return text


def generate_mermaid(payload: dict) -> str:
    """
    Generate Mermaid ERD from database metadata.

    Args:
        payload: Dictionary with structure:
            {
                "tables": {
                    "schema.table1": {
                        "columns": {"col1": "INT", "col2": "VARCHAR"},
                        "table": "table1",
                        "schema": "schema"
                    },
                    ...
                },
                "relationships": [
                    {
                        "fact_table": "fact_sales",
                        "fk_column": "customer_id",
                        "dim_table": "dim_customer",
                        "dim_column": "customer_id",
                        "confidence": "high",
                        "is_broken": False
                    },
                    ...
                ],
                "options": {
                    "show_columns": True,
                    "show_confidence": True,
                    "highlight_broken": True,
                    "max_columns": 10
                }
            }

    Returns:
        Mermaid ERD syntax string
    """
    tables = payload.get("tables", {})
    relationships = payload.get("relationships", [])
    options = payload.get("options", {})

    show_columns = options.get("show_columns", True)
    show_confidence = options.get("show_confidence", True)
    highlight_broken = options.get("highlight_broken", True)
    max_columns = options.get("max_columns", 10)

    lines = ["erDiagram"]

    # Generate table definitions
    for table_key, table_meta in tables.items():
        table_name = table_meta.get("table", table_key)
        columns = table_meta.get("columns", {})

        # Add table with columns
        lines.append(f"    {sanitize(table_name)} {{")

        if show_columns and columns:
            # Limit columns to max_columns
            col_items = list(columns.items())[:max_columns]
            for col_name, col_type in col_items:
                sanitized_type = sanitize(col_type)
                sanitized_col = sanitize(col_name)  # Sanitize column name too
                lines.append(f"        {sanitized_type} {sanitized_col}")

            # Show ellipsis if there are more columns
            if len(columns) > max_columns:
                lines.append(f"        string more_columns_{len(columns) - max_columns}")

        lines.append("    }")

    # Generate relationships
    for rel in relationships:
        fact_table = rel.get("fact_table", "")
        fk_column = rel.get("fk_column", "")
        dim_table = rel.get("dim_table", "")
        confidence = rel.get("confidence", "high")
        is_broken = rel.get("is_broken", False)

        # Extract just the table name (without schema)
        fact_name = _extract_table_name(fact_table)
        dim_name = _extract_table_name(dim_table)

        # Choose relationship style based on confidence/broken status
        if is_broken and highlight_broken:
            # Broken relationship (orphaned FKs)
            rel_symbol = "||--x{"
            label = f"{sanitize(fk_column)}_BROKEN"
        elif show_confidence:
            # Show confidence level
            if confidence == "high":
                rel_symbol = "||--o{"  # Standard relationship
                label = sanitize(fk_column)
            elif confidence == "medium":
                rel_symbol = "||..o{"  # Dotted line for medium confidence
                label = f"{sanitize(fk_column)}_MEDIUM"
            else:  # low
                rel_symbol = "}|..|{"  # Weak relationship
                label = f"{sanitize(fk_column)}_LOW"
        else:
            # Standard relationship
            rel_symbol = "||--o{"
            label = sanitize(fk_column)

        lines.append(f"    {sanitize(dim_name)} {rel_symbol} {sanitize(fact_name)} : {label}")

    return "\n".join(lines)


def generate_mermaid_from_yaml(tables_yaml: Dict, relationships_yaml: List[Dict],
                                show_columns: bool = True,
                                highlight_broken: bool = False) -> str:
    """
    Generate Mermaid ERD from YAML structure (tables.yaml and relationships.yaml).

    Args:
        tables_yaml: Dictionary from tables.yaml:
            {
                "sql": {"table1": {"col1": "INT", ...}, ...},
                "snow": {"TABLE1": {"COL1": "NUMBER", ...}, ...}
            }
        relationships_yaml: List from relationships.yaml:
            [
                {"fact_table": "fact_1", "fk_column": "dim_1_id", "dim_reference": "dim_1.dim_1_id"},
                ...
            ]
        show_columns: Whether to show column details
        highlight_broken: Whether to highlight broken relationships

    Returns:
        Mermaid ERD syntax string
    """
    # Convert to standard format
    tables = {}
    sql_tables = tables_yaml.get("sql", {})
    for table_name, columns in sql_tables.items():
        tables[table_name] = {
            "table": table_name,
            "columns": columns
        }

    # Convert relationships to standard format
    relationships = []
    for rel in relationships_yaml:
        fact_table = rel.get("fact_table", "")
        fk_column = rel.get("fk_column", "")
        dim_reference = rel.get("dim_reference", "")

        # Parse dim_reference: "dim_table.dim_column"
        if "." in dim_reference:
            dim_table, dim_column = dim_reference.split(".", 1)
        else:
            dim_table = dim_reference
            dim_column = "id"

        relationships.append({
            "fact_table": fact_table,
            "fk_column": fk_column,
            "dim_table": dim_table,
            "dim_column": dim_column,
            "confidence": "high",
            "is_broken": False
        })

    payload = {
        "tables": tables,
        "relationships": relationships,
        "options": {
            "show_columns": show_columns,
            "show_confidence": False,
            "highlight_broken": highlight_broken,
            "max_columns": 10
        }
    }

    return generate_mermaid(payload)


def _extract_table_name(full_name: str) -> str:
    """Extract table name from schema.table format."""
    if "." in full_name:
        return full_name.split(".")[-1]
    return full_name


def generate_mermaid_with_inference(tables: Dict, inferred_relationships: List[Dict],
                                    existing_relationships: List[Dict] = None) -> str:
    """
    Generate Mermaid ERD combining existing and inferred relationships.

    Args:
        tables: Table metadata dictionary
        inferred_relationships: Relationships from inference engine
        existing_relationships: Existing relationships from YAML (optional)

    Returns:
        Mermaid ERD syntax string
    """
    # Combine existing and inferred relationships
    all_relationships = []

    if existing_relationships:
        for rel in existing_relationships:
            # Mark as high confidence (existing constraint)
            all_relationships.append({
                **rel,
                "confidence": "enforced",
                "is_broken": False
            })

    # Add inferred relationships
    all_relationships.extend(inferred_relationships)

    payload = {
        "tables": tables,
        "relationships": all_relationships,
        "options": {
            "show_columns": True,
            "show_confidence": True,
            "highlight_broken": True,
            "max_columns": 8
        }
    }

    return generate_mermaid(payload)
