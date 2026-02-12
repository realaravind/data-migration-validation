"""
AI-powered table type classifier for intelligent validation selection.

Uses LLM to determine if a table is a FACT or DIMENSION table based on:
- Table name patterns
- Column structure and types
- Optional: Sample data profiling

This allows the validation suggester to select appropriate validations:
- FACT tables: metric sums, averages, referential integrity, time-series
- DIMENSION tables: schema validation, uniqueness, primary keys, row counts
"""

import asyncio
import logging
from functools import lru_cache
from typing import Optional, Dict, List, Tuple, Any
from enum import Enum

logger = logging.getLogger(__name__)

# Cache for table classification results
_table_type_cache: Dict[str, 'TableType'] = {}


class TableType(str, Enum):
    """Table type classification."""
    FACT = "fact"
    DIMENSION = "dimension"
    BRIDGE = "bridge"  # Many-to-many relationship tables
    STAGING = "staging"  # ETL staging tables
    UNKNOWN = "unknown"


class TableClassification:
    """Result of table classification."""
    def __init__(
        self,
        table_type: TableType,
        confidence: float,
        reasoning: str,
        suggested_validations: List[str]
    ):
        self.table_type = table_type
        self.confidence = confidence
        self.reasoning = reasoning
        self.suggested_validations = suggested_validations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "table_type": self.table_type.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "suggested_validations": self.suggested_validations
        }


# Validation sets by table type
FACT_VALIDATIONS = [
    "validate_schema_columns",
    "validate_schema_datatypes",
    "validate_record_counts",
    "validate_nulls",
    "validate_metric_sums",
    "validate_metric_averages",
    "validate_ratios",
    "validate_foreign_keys",
    "validate_fact_dim_conformance",
    "validate_ts_continuity",
    "validate_ts_duplicates",
    "validate_period_over_period",
]

DIMENSION_VALIDATIONS = [
    "validate_schema_columns",
    "validate_schema_datatypes",
    "validate_schema_nullability",
    "validate_record_counts",
    "validate_nulls",
    "validate_uniqueness",  # Business key uniqueness
    "validate_dim_business_keys",
]

BRIDGE_VALIDATIONS = [
    "validate_schema_columns",
    "validate_record_counts",
    "validate_foreign_keys",
    "validate_uniqueness",
]

STAGING_VALIDATIONS = [
    "validate_schema_columns",
    "validate_record_counts",
]


def get_validations_for_table_type(table_type: TableType) -> List[str]:
    """Get appropriate validations for a table type."""
    if table_type == TableType.FACT:
        return FACT_VALIDATIONS
    elif table_type == TableType.DIMENSION:
        return DIMENSION_VALIDATIONS
    elif table_type == TableType.BRIDGE:
        return BRIDGE_VALIDATIONS
    elif table_type == TableType.STAGING:
        return STAGING_VALIDATIONS
    else:
        # Default to basic schema + row count validations
        return [
            "validate_schema_columns",
            "validate_schema_datatypes",
            "validate_record_counts",
        ]


def classify_table_by_rules(
    table_name: str,
    schema_name: str = "",
    columns: Dict[str, str] = None
) -> TableClassification:
    """
    Rule-based table classification (fallback when LLM is unavailable).

    Uses naming conventions and column patterns to classify tables.
    """
    table_lower = table_name.lower()
    schema_lower = schema_name.lower() if schema_name else ""
    columns = columns or {}

    # Check schema name first (most reliable)
    if 'dim' in schema_lower or schema_lower == 'dimension':
        return TableClassification(
            table_type=TableType.DIMENSION,
            confidence=0.9,
            reasoning=f"Schema '{schema_name}' indicates dimension table",
            suggested_validations=DIMENSION_VALIDATIONS
        )

    if 'fact' in schema_lower:
        return TableClassification(
            table_type=TableType.FACT,
            confidence=0.9,
            reasoning=f"Schema '{schema_name}' indicates fact table",
            suggested_validations=FACT_VALIDATIONS
        )

    # Check table name patterns
    # Dimension patterns
    dim_prefixes = ['dim_', 'd_', 'dimension_']
    dim_suffixes = ['_dim', '_dimension', '_lookup', '_ref', '_master']
    dim_keywords = ['customer', 'product', 'store', 'employee', 'date', 'time',
                    'geography', 'location', 'category', 'status', 'type']

    for prefix in dim_prefixes:
        if table_lower.startswith(prefix):
            return TableClassification(
                table_type=TableType.DIMENSION,
                confidence=0.85,
                reasoning=f"Table name prefix '{prefix}' indicates dimension table",
                suggested_validations=DIMENSION_VALIDATIONS
            )

    for suffix in dim_suffixes:
        if table_lower.endswith(suffix):
            return TableClassification(
                table_type=TableType.DIMENSION,
                confidence=0.85,
                reasoning=f"Table name suffix '{suffix}' indicates dimension table",
                suggested_validations=DIMENSION_VALIDATIONS
            )

    # Fact patterns
    fact_prefixes = ['fact_', 'f_', 'fct_']
    fact_suffixes = ['_fact', '_facts', '_transaction', '_transactions', '_sales', '_orders']
    fact_keywords = ['sales', 'orders', 'transactions', 'events', 'metrics', 'measures']

    for prefix in fact_prefixes:
        if table_lower.startswith(prefix):
            return TableClassification(
                table_type=TableType.FACT,
                confidence=0.85,
                reasoning=f"Table name prefix '{prefix}' indicates fact table",
                suggested_validations=FACT_VALIDATIONS
            )

    for suffix in fact_suffixes:
        if table_lower.endswith(suffix):
            return TableClassification(
                table_type=TableType.FACT,
                confidence=0.85,
                reasoning=f"Table name suffix '{suffix}' indicates fact table",
                suggested_validations=FACT_VALIDATIONS
            )

    # Bridge table patterns
    bridge_keywords = ['bridge', 'link', 'junction', 'xref', 'assoc']
    for keyword in bridge_keywords:
        if keyword in table_lower:
            return TableClassification(
                table_type=TableType.BRIDGE,
                confidence=0.8,
                reasoning=f"Table name contains '{keyword}' indicating bridge table",
                suggested_validations=BRIDGE_VALIDATIONS
            )

    # Staging patterns
    staging_keywords = ['stg_', 'staging_', '_staging', '_stg', 'tmp_', '_tmp']
    for keyword in staging_keywords:
        if keyword in table_lower:
            return TableClassification(
                table_type=TableType.STAGING,
                confidence=0.8,
                reasoning=f"Table name contains '{keyword}' indicating staging table",
                suggested_validations=STAGING_VALIDATIONS
            )

    # Analyze column structure
    if columns:
        col_names = [c.lower() for c in columns.keys()]
        col_types = [t.lower() for t in columns.values()]

        # Count numeric columns (potential metrics)
        numeric_types = ['int', 'decimal', 'numeric', 'number', 'float', 'money']
        numeric_count = sum(1 for t in col_types if any(nt in t for nt in numeric_types))

        # Count FK-like columns
        fk_count = sum(1 for c in col_names if c.endswith('_id') or c.endswith('_key') or c.endswith('_fk'))

        # Count date columns
        date_types = ['date', 'datetime', 'timestamp']
        date_count = sum(1 for t in col_types if any(dt in t for dt in date_types))

        total_cols = len(columns)

        # Fact tables typically have many FK columns and numeric metrics
        if total_cols > 0:
            fk_ratio = fk_count / total_cols
            numeric_ratio = numeric_count / total_cols

            # High FK ratio + numeric columns = likely fact table
            if fk_ratio > 0.3 and numeric_count >= 2:
                return TableClassification(
                    table_type=TableType.FACT,
                    confidence=0.7,
                    reasoning=f"Column structure suggests fact table: {fk_count} FK columns, {numeric_count} numeric columns",
                    suggested_validations=FACT_VALIDATIONS
                )

            # Few FK columns + mostly descriptive = likely dimension
            if fk_ratio < 0.2 and numeric_ratio < 0.3:
                return TableClassification(
                    table_type=TableType.DIMENSION,
                    confidence=0.65,
                    reasoning=f"Column structure suggests dimension table: few FK columns, mostly descriptive",
                    suggested_validations=DIMENSION_VALIDATIONS
                )

    # Default to unknown
    return TableClassification(
        table_type=TableType.UNKNOWN,
        confidence=0.3,
        reasoning="Could not determine table type from name or structure",
        suggested_validations=get_validations_for_table_type(TableType.UNKNOWN)
    )


async def classify_table_with_ai(
    table_name: str,
    schema_name: str = "",
    columns: Dict[str, str] = None,
    sample_data: List[Dict] = None
) -> TableClassification:
    """
    Use AI/LLM to classify a table as fact or dimension.

    Args:
        table_name: Name of the table
        schema_name: Schema/database the table belongs to
        columns: Dict of column_name -> data_type
        sample_data: Optional list of sample rows for profiling

    Returns:
        TableClassification with table type and suggested validations
    """
    cache_key = f"{schema_name}.{table_name}".lower()

    # Check cache first
    if cache_key in _table_type_cache:
        cached_type = _table_type_cache[cache_key]
        return TableClassification(
            table_type=cached_type,
            confidence=0.9,
            reasoning="Cached classification",
            suggested_validations=get_validations_for_table_type(cached_type)
        )

    try:
        from backend.llm import get_llm_provider

        # Build column info for prompt
        column_info = ""
        if columns:
            column_info = "\nColumns:\n" + "\n".join([f"  - {name}: {dtype}" for name, dtype in list(columns.items())[:20]])

        # Build sample data info
        sample_info = ""
        if sample_data and len(sample_data) > 0:
            sample_info = f"\nSample data ({len(sample_data)} rows available)"

        prompt = f"""You are a data warehouse expert. Classify the following table as one of: FACT, DIMENSION, BRIDGE, STAGING, or UNKNOWN.

Table: {schema_name}.{table_name} if schema else {table_name}
{column_info}
{sample_info}

FACT tables:
- Store measurable business events/transactions
- Have many foreign keys to dimension tables
- Contain numeric metrics (amounts, quantities, counts)
- Often have date/time columns for the event
- Names often contain: fact_, _fact, sales, orders, transactions

DIMENSION tables:
- Store descriptive attributes
- Have a primary/business key
- Contain text descriptions, names, codes
- Names often contain: dim_, _dim, _lookup, customer, product, store

BRIDGE tables:
- Handle many-to-many relationships
- Primarily contain foreign keys
- Names often contain: bridge, link, junction, xref

Respond with ONLY one line in format:
TYPE|confidence|brief_reason

Example: FACT|0.9|Contains sales metrics and FK to dimensions

Your response:"""

        provider = get_llm_provider()

        async with provider:
            response = await provider.generate(prompt)
            response = response.strip()

            # Parse response
            parts = response.split("|")
            if len(parts) >= 2:
                type_str = parts[0].strip().upper()
                try:
                    confidence = float(parts[1].strip())
                except:
                    confidence = 0.7
                reasoning = parts[2].strip() if len(parts) > 2 else "AI classification"

                # Map to TableType
                type_map = {
                    "FACT": TableType.FACT,
                    "DIMENSION": TableType.DIMENSION,
                    "DIM": TableType.DIMENSION,
                    "BRIDGE": TableType.BRIDGE,
                    "STAGING": TableType.STAGING,
                    "STG": TableType.STAGING,
                }
                table_type = type_map.get(type_str, TableType.UNKNOWN)

                # Cache the result
                _table_type_cache[cache_key] = table_type

                logger.info(f"[AI_TABLE_CLASSIFY] {table_name} -> {table_type.value} (confidence: {confidence})")

                return TableClassification(
                    table_type=table_type,
                    confidence=confidence,
                    reasoning=f"AI: {reasoning}",
                    suggested_validations=get_validations_for_table_type(table_type)
                )

    except Exception as e:
        logger.warning(f"[AI_TABLE_CLASSIFY] AI classification failed for {table_name}: {e}, using rule-based fallback")

    # Fallback to rule-based classification
    return classify_table_by_rules(table_name, schema_name, columns)


def classify_table_sync(
    table_name: str,
    schema_name: str = "",
    columns: Dict[str, str] = None,
    sample_data: List[Dict] = None
) -> TableClassification:
    """
    Synchronous wrapper for AI table classification.
    Falls back to rule-based if AI fails.
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # We're in an async context, need to use run_coroutine_threadsafe
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                future = pool.submit(
                    asyncio.run,
                    classify_table_with_ai(table_name, schema_name, columns, sample_data)
                )
                return future.result(timeout=15)
        else:
            return loop.run_until_complete(
                classify_table_with_ai(table_name, schema_name, columns, sample_data)
            )
    except RuntimeError:
        # No event loop, create one
        return asyncio.run(
            classify_table_with_ai(table_name, schema_name, columns, sample_data)
        )
    except Exception as e:
        logger.warning(f"[AI_TABLE_CLASSIFY] Sync classification failed: {e}, using rules")
        return classify_table_by_rules(table_name, schema_name, columns)


def filter_validations_for_table(
    table_name: str,
    schema_name: str,
    suggested_validations: List[str],
    columns: Dict[str, str] = None
) -> List[str]:
    """
    Filter suggested validations based on table type.

    This is the main entry point for intelligent validation filtering.
    Removes inappropriate validations (e.g., metric sums for dimension tables).
    """
    classification = classify_table_sync(table_name, schema_name, columns)

    # Get allowed validations for this table type
    allowed_validations = set(classification.suggested_validations)

    # Filter the suggested validations
    filtered = [v for v in suggested_validations if v in allowed_validations]

    logger.info(
        f"[AI_TABLE_CLASSIFY] {schema_name}.{table_name} -> {classification.table_type.value} "
        f"(filtered {len(suggested_validations)} -> {len(filtered)} validations)"
    )

    return filtered


def clear_classification_cache():
    """Clear the table classification cache."""
    global _table_type_cache
    _table_type_cache = {}
    logger.info("[AI_TABLE_CLASSIFY] Cache cleared")
